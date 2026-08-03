import logging
import asyncio
import time
from typing import List, Dict, Any, Callable, Awaitable, Optional
from datetime import datetime
from urllib.parse import urlparse

from backend.models.company import Company, SearchHistory, SearchResult
from backend.services.query_generator import QueryGeneratorService
from backend.services.search.factory import SearchFactory
from backend.crawler.crawler import WebsiteCrawler, BotProtectionError
from backend.services.qualification import QualificationService
from backend.services.sheets import GoogleSheetsService
from backend.services.llm.base import token_usage, reset_token_usage
from backend.api.config import settings
from backend.services.job_manager import SearchJob, JobManager
from backend.crawler.browser_pool import browser_pool

# Milestone 2 Resiliency & Storage Imports
from backend.services.storage import SQLiteJobStore, SQLiteResultStore
from backend.services.retry_manager import RetryManager

logger = logging.getLogger("company_intelligence.orchestrator")

class CompanyDiscoveryOrchestrator:
    def __init__(self, on_event: Callable[[str, Dict[str, Any]], Awaitable[None]]):
        self.on_event = on_event
        self.sheets_service = GoogleSheetsService()
        self.crawler = WebsiteCrawler(use_cache=True)
        self.ws_lock = asyncio.Lock()
        self.job_manager = JobManager()
        
        # Repositories
        self.job_store = SQLiteJobStore()
        self.result_store = SQLiteResultStore()

    async def run_discovery(
        self,
        company_type: str,
        product_or_service: str,
        location: str
    ) -> Dict[str, Any]:
        """
        Main entry point for discovery. Creates a SearchJob and orchestrates
        fully decoupled streaming pipelines.
        """
        # 1. Warm up browser pool if not initialized
        await browser_pool.start()

        # 2. Create isolated SearchJob
        job = await self.job_manager.create_job(company_type, product_or_service, location)
        job.status = "running"
        reset_token_usage()

        # Save metadata to JobStore (Repository Pattern)
        await self.job_store.create_job(
            job_id=job.job_id,
            company_type=company_type,
            product=product_or_service,
            location=location
        )

        history = SearchHistory(
            search_id=job.job_id,
            company_type=company_type,
            product=product_or_service,
            location=location,
            timestamp=job.created_at
        )

        # Resolve Sheet ID upfront for streaming batch updates
        sheet_id = self.sheets_service.resolve_sheet_id()
        self.sheets_service.write_search_history(sheet_id, history)

        start_time = time.time()
        unique_domains: set = set()
        candidates_lock = asyncio.Lock()

        # Concurrency parameters
        max_crawl_workers = getattr(settings, "max_crawl_workers", 20)
        max_ai_workers = getattr(settings, "max_ai_workers", 10)
        cancellation_tasks = []
        ai_queue_counter = 0

        try:
            # ─────────────────────────────────────────────────────────────────
            # PHASE 1: Query Gen
            # ─────────────────────────────────────────────────────────────────
            query_gen_start_time = time.time()
            await self._send_progress(job.job_id, "query_gen", "Generating search queries using AI...", {"search_id": job.job_id})
            queries = await QueryGeneratorService.generate_queries(
                company_type=company_type,
                product_or_service=product_or_service,
                location=location,
                job=job
            )
            query_gen_finished_time = time.time()
            job.update_metrics("search_queries_generated", len(queries))
            await self._send_progress(job.job_id, "query_gen_done", f"Generated {len(queries)} search variations", {"queries": queries})

            # ─────────────────────────────────────────────────────────────────
            # PHASE 2: Parallel Search Workers (DDG -> Search Queue -> Deduplicator)
            # ─────────────────────────────────────────────────────────────────
            search_start_time = time.time()
            search_results_queue = asyncio.Queue()
            search_service = SearchFactory.get_service()
            
            # Circuit Breaker setup (Milestone 3)
            consecutive_search_failures = 0
            failures_lock = asyncio.Lock()
            fallback_service = None
            if settings.search_provider.lower() == "duckduckgo":
                from backend.services.search.serper import SerperSearchService
                fallback_service = SerperSearchService(api_key=settings.serper_api_key)
            
            async def search_worker(query: str, worker_idx: int):
                nonlocal consecutive_search_failures
                # Stagger the start time of each worker to prevent Serper 429 Rate Limit Errors
                await asyncio.sleep(worker_idx * 0.5)
                
                try:
                    await self._send_progress(job.job_id, "search_progress", f"Searching variation {worker_idx}: '{query}'", {})
                    
                    # Determine active search service based on circuit breaker status
                    active_service = search_service
                    async with failures_lock:
                        if consecutive_search_failures >= 3 and fallback_service:
                            active_service = fallback_service
                            
                    results = await RetryManager.run_with_retry(
                        lambda: active_service.search(query, num_results=settings.results_per_query),
                        retries=3,
                        context_name=f"Search Query '{query}'"
                    )
                    
                    # Reset failure count on success
                    async with failures_lock:
                        consecutive_search_failures = 0
                    
                    for item in results:
                        if job.is_cancelled():
                            break
                        await search_results_queue.put(item)
                except Exception as e:
                    logger.error(f"Search worker {worker_idx} failed for '{query}': {e}")
                    async with failures_lock:
                        consecutive_search_failures += 1
                        if consecutive_search_failures == 3 and fallback_service:
                            logger.critical("Circuit Breaker tripped! Switching search provider from DuckDuckGo to Serper.")
                finally:
                    job.update_metrics("search_queries_completed", 1, add=True)

            # Start search workers
            search_tasks = [
                asyncio.create_task(search_worker(q, idx))
                for idx, q in enumerate(queries, 1)
            ]
            cancellation_tasks.extend(search_tasks)

            # ─────────────────────────────────────────────────────────────────
            # PHASE 3: Domain Deduplicator & Aggregator Worker
            # ─────────────────────────────────────────────────────────────────
            async def deduplicator_worker():
                nonlocal unique_domains
                pending_searches = len(queries)
                
                while pending_searches > 0 or not search_results_queue.empty():
                    if job.is_cancelled():
                        break
                    
                    try:
                        item: SearchResult = await asyncio.wait_for(search_results_queue.get(), timeout=0.5)
                    except asyncio.TimeoutError:
                        finished_count = job.metrics["search_queries_completed"]
                        pending_searches = len(queries) - finished_count
                        continue

                    parsed = urlparse(item.website)
                    domain = parsed.netloc.lower()
                    
                    async with candidates_lock:
                        if domain and domain not in unique_domains:
                            unique_domains.add(domain)
                            job.update_metrics("unique_domains_found", len(unique_domains))
                            await job.crawler_queue.put(item)
                    
                    if len(unique_domains) >= settings.max_unique_companies:
                        logger.info("Deduplicator limit reached. Early search stopping initiated.")
                        for task in search_tasks:
                            if not task.done():
                                task.cancel()
                        break
                    
                    search_results_queue.task_done()
                
                # Signal crawler workers that search has finished enqueuing
                for _ in range(max_crawl_workers):
                    await job.crawler_queue.put(None)

            dedup_task = asyncio.create_task(deduplicator_worker())
            cancellation_tasks.append(dedup_task)

            # ─────────────────────────────────────────────────────────────────
            # PHASE 4: Crawl Workers (Leasing browser context, extraction)
            # ─────────────────────────────────────────────────────────────────
            async def crawl_worker(worker_id: int):
                while not job.is_cancelled():
                    candidate: Optional[SearchResult] = await job.crawler_queue.get()
                    if candidate is None:
                        job.crawler_queue.task_done()
                        break
                    
                    prefix = f"[Crawl {worker_id}] {candidate.company_name}"
                    try:
                        # Basic backpressure: Pause crawler if AI queue is overwhelmed
                        while job.ai_queue.qsize() > 20:
                            if job.is_cancelled():
                                break
                            await asyncio.sleep(0.5)

                        await self._send_progress(job.job_id, "crawl_start", f"{prefix}: Visiting website...", {"url": candidate.website})
                        
                        async def crawler_progress(event_type, msg):
                            await self._send_progress(job.job_id, "crawl_progress", f"{prefix}: {msg}", {})

                        # Pass company_type to crawl_company to run local homepage triage (Milestone 3)
                        crawl_start = time.time()
                        pages = await RetryManager.run_with_retry(
                            lambda: self.crawler.crawl_company(
                                root_url=candidate.website,
                                company_type=company_type,
                                on_progress=crawler_progress
                            ),
                            retries=2,
                            context_name=f"Crawl '{candidate.website}'"
                        )
                        crawl_duration = time.time() - crawl_start
                        
                        job.update_metrics("crawled_count", 1, add=True)
                        
                        # Decide Priority Queue routing (Milestone 3 Priority AI Queue)
                        priority = 2
                        if pages:
                            triage_decision = self.crawler.triage_content(pages[0].content, company_type)
                            if triage_decision != "NEEDS_MORE_INFO":
                                priority = 1 # High priority matching triage success
                                job.metrics["triage_skipped_subpages"] += 1
                                job.metrics["homepage_crawl_times"].append(crawl_duration)
                            else:
                                job.metrics["triage_needs_more_info"] += 1
                                job.metrics["subpage_crawl_times"].append(crawl_duration)
                                
                        # Increment counter to prevent SearchResult comparison TypeErrors
                        nonlocal ai_queue_counter
                        ai_queue_counter += 1
                        await job.ai_queue.put((priority, ai_queue_counter, (candidate, pages)))
                    except BotProtectionError as e:
                        logger.warning(f"Bot protection blocked {candidate.website}")
                        
                        from backend.models.company import Qualification
                        blocked_company = Company(
                            company_name=candidate.company_name,
                            website=candidate.website,
                            qualification=Qualification(qualified=False, is_blocked=True, reason="Blocked by Cloudflare/Anti-Bot Protection", confidence=0),
                            is_blocked=True
                        )
                        
                        await self.result_store.save_company(job.job_id, blocked_company.model_dump())
                        job.results.append(blocked_company.model_dump())
                        job.update_metrics("blocked_count", 1, add=True)
                        await self._send_progress(job.job_id, "ai_blocked", f"{prefix}: BLOCKED by Anti-Bot", {"company": blocked_company.model_dump()})
                        
                    except Exception as e:
                        logger.error(f"Crawl worker {worker_id} failed on {candidate.website}: {e}")
                        job.update_metrics("skipped_count", 1, add=True)
                    finally:
                        job.crawler_queue.task_done()

            # Start crawlers
            crawler_tasks = [
                asyncio.create_task(crawl_worker(idx))
                for idx in range(1, max_crawl_workers + 1)
            ]
            cancellation_tasks.extend(crawler_tasks)

            # ─────────────────────────────────────────────────────────────────
            # PHASE 5: AI Workers (Qualification Scoring)
            # ─────────────────────────────────────────────────────────────────
            async def ai_worker(worker_id: int):
                while not job.is_cancelled():
                    # Pick up candidate & page content from PriorityQueue
                    queue_item = await job.ai_queue.get()
                    priority, _, work_item = queue_item
                    
                    if work_item is None:
                        job.ai_queue.task_done()
                        break
                    
                    candidate, pages = work_item
                    prefix = f"[AI {worker_id} (P{priority})] {candidate.company_name}"
                    
                    try:
                        await self._send_progress(job.job_id, "ai_start", f"{prefix}: Running AI qualification...", {})
                        
                        # Track AI latency
                        ai_start = time.time()
                        qualification = await RetryManager.run_with_retry(
                            lambda: QualificationService.qualify_company(
                                company_name=candidate.company_name,
                                company_type=company_type,
                                product_or_service=product_or_service,
                                location=location,
                                pages=pages,
                                job=job
                            ),
                            retries=2,
                            context_name=f"Qualification '{candidate.company_name}'"
                        )
                        ai_duration = time.time() - ai_start
                        job.metrics["ai_qualification_times"].append(ai_duration)
                        
                        address = qualification.address
                        phone = qualification.phone
                        
                        if not phone or not address:
                            for p in pages:
                                if p.page_type in ("home", "contact"):
                                    if not phone:
                                        phone = re_search_phone(p.content) or phone
                                    if not address:
                                        address = re_search_address(p.content) or address
                        
                        company = Company(
                            company_name=candidate.company_name,
                            website=candidate.website,
                            address=address,
                            phone=phone,
                            category=product_or_service,
                            qualification=qualification
                        )
                        
                        await self.result_store.save_company(job.job_id, company.model_dump())
                        job.results.append(company.model_dump())
                        
                        if not pages:
                            job.update_metrics("skipped_count", 1, add=True)
                            await self._send_progress(job.job_id, "crawl_skip", f"{prefix}: Skipped (blocked or timeout)", {})
                        elif qualification.qualified:
                            job.update_metrics("qualified_count", 1, add=True)
                            await self._send_progress(job.job_id, "ai_qualified", f"{prefix}: QUALIFIED ({qualification.confidence}% confidence)", {"company": company.model_dump()})
                            await job.sheets_queue.put(company)
                        else:
                            job.update_metrics("disqualified_count", 1, add=True)
                            await self._send_progress(job.job_id, "ai_disqualified", f"{prefix}: DISQUALIFIED", {"company": company.model_dump()})
                            
                    except Exception as e:
                        logger.error(f"AI Worker {worker_id} failed qualification for {candidate.company_name}: {e}")
                        job.update_metrics("skipped_count", 1, add=True)
                    finally:
                        job.ai_queue.task_done()

            # Start AI Workers
            ai_tasks = [
                asyncio.create_task(ai_worker(idx))
                for idx in range(1, max_ai_workers + 1)
            ]
            cancellation_tasks.extend(ai_tasks)

            # ─────────────────────────────────────────────────────────────────
            # PHASE 6: Downstream Sheets worker (Real-Time Batch Exporter)
            # ─────────────────────────────────────────────────────────────────
            async def sheets_batch_worker():
                batch = []
                last_flush = time.time()
                
                while True:
                    try:
                        company = await asyncio.wait_for(job.sheets_queue.get(), timeout=1.0)
                        if company is None:
                            if batch:
                                self.sheets_service.append_companies_batch(sheet_id, history, batch)
                            job.sheets_queue.task_done()
                            break
                        
                        batch.append(company)
                        job.sheets_queue.task_done()
                        
                        if len(batch) >= 5 or (time.time() - last_flush) >= 5.0:
                            self.sheets_service.append_companies_batch(sheet_id, history, batch)
                            batch.clear()
                            last_flush = time.time()
                    except asyncio.TimeoutError:
                        if batch:
                            self.sheets_service.append_companies_batch(sheet_id, history, batch)
                            batch.clear()
                            last_flush = time.time()

            sheets_task = asyncio.create_task(sheets_batch_worker())
            cancellation_tasks.append(sheets_task)

            # Wait for search, deduplication and crawlers to finish enqueuing
            await asyncio.gather(*search_tasks, return_exceptions=True)
            search_finished_time = time.time()
            await dedup_task
            
            # Wait for crawler queue to drain, then terminate crawlers
            await job.crawler_queue.join()
            for task in crawler_tasks:
                task.cancel()

            # Signal AI workers to stop after crawler queue is fully completed (Milestone 3 Priority Queue)
            for _ in range(max_ai_workers):
                await job.ai_queue.put((3, 0, None))

            # Wait for AI workers to finish processing
            await job.ai_queue.join()
            for task in ai_tasks:
                task.cancel()

            # Signal sheets worker to stop and wait
            sheets_start_time = time.time()
            await job.sheets_queue.put(None)
            await sheets_task

            finished_at = datetime.utcnow().isoformat()
            duration_sec = time.time() - start_time
            duration_str = f"{duration_sec:.1f}s"
            
            sheets_duration = time.time() - sheets_start_time
            query_gen_duration = query_gen_finished_time - query_gen_start_time
            search_duration = search_finished_time - search_start_time

            summary = {
                "started_at": job.created_at,
                "finished_at": finished_at,
                "total_processed": len(job.results),
                "qualified_count": job.metrics["qualified_count"],
                "disqualified_count": job.metrics["disqualified_count"],
                "blocked_count": job.metrics.get("blocked_count", 0),
                "skipped_count": job.metrics["skipped_count"],
                "duration": duration_str,
                "timings": {
                    "query_generation_sec": f"{query_gen_duration:.2f}s",
                    "search_sec": f"{search_duration:.2f}s",
                    "sheets_write_sec": f"{sheets_duration:.2f}s",
                    "total_duration_sec": f"{duration_sec:.2f}s"
                },
                "errors": "None"
            }
            
            # Append final summary row
            self.sheets_service.write_results_summary(sheet_id, history, summary)
            
            # Update final job metrics to JobStore
            await self.job_store.update_job_status(job.job_id, "completed", job.metrics)

            # Output Token consumption and timing metrics
            job_p_tokens = job.metrics.get("prompt_tokens", 0)
            job_c_tokens = job.metrics.get("completion_tokens", 0)
            job_t_tokens = job.metrics.get("total_tokens", 0)
            job_calls = job.metrics.get("call_count", 0)

            input_cost  = (job_p_tokens / 1_000_000) * 0.14
            output_cost = (job_c_tokens / 1_000_000) * 0.28
            job_cost = input_cost + output_cost
            
            # Calculate Averages (avoiding DivisionByZero)
            hp_times = job.metrics["homepage_crawl_times"]
            sp_times = job.metrics["subpage_crawl_times"]
            ai_times = job.metrics["ai_qualification_times"]
            
            avg_homepage = sum(hp_times) / len(hp_times) if hp_times else 0.0
            avg_subpage = sum(sp_times) / len(sp_times) if sp_times else 0.0
            avg_ai = sum(ai_times) / len(ai_times) if ai_times else 0.0
            
            # Throughput
            processed_count = len(job.results)
            throughput_comp_sec = processed_count / duration_sec if duration_sec > 0 else 0.0

            summary = {
                "started_at": job.created_at,
                "finished_at": finished_at,
                "total_processed": processed_count,
                "qualified_count": job.metrics["qualified_count"],
                "disqualified_count": job.metrics["disqualified_count"],
                "skipped_count": job.metrics["skipped_count"],
                "duration": duration_str,
                "timings": {
                    "query_generation_sec": f"{query_gen_duration:.2f}s",
                    "search_sec": f"{search_duration:.2f}s",
                    "avg_homepage_sec": f"{avg_homepage:.2f}s",
                    "avg_subpage_sec": f"{avg_subpage:.2f}s",
                    "avg_ai_sec": f"{avg_ai:.2f}s",
                    "sheets_write_sec": f"{sheets_duration:.2f}s",
                    "total_duration_sec": f"{duration_sec:.2f}s"
                },
                "throughput": {
                    "companies_per_sec": f"{throughput_comp_sec:.2f}",
                    "triage_skipped": job.metrics["triage_skipped_subpages"],
                    "triage_deep_crawled": job.metrics["triage_needs_more_info"]
                },
                "errors": "None"
            }
            
            # Append final summary row
            self.sheets_service.write_results_summary(sheet_id, history, summary)
            
            # Update final job metrics to JobStore
            await self.job_store.update_job_status(job.job_id, "completed", job.metrics)

            print("\n" + "=" * 52)
            print("  [AI]  TOKEN & PIPELINE PERFORMANCE REPORT")
            print("=" * 52)
            print(f"  Job ID              : {job.job_id}")
            print(f"  LLM Calls Made      : {job_calls}")
            print(f"  Prompt Tokens       : {job_p_tokens:,}")
            print(f"  Completion Tokens   : {job_c_tokens:,}")
            print(f"  Total Tokens        : {job_t_tokens:,}")
            print(f"  Est. Cost (DeepSeek): ~${job_cost:.4f} USD")
            print("-" * 52)
            print(f"  Query Gen Duration  : {query_gen_duration:.2f}s")
            print(f"  Search Duration     : {search_duration:.2f}s")
            print(f"  Avg Homepage Crawl  : {avg_homepage:.2f}s (Skipped subpages: {job.metrics['triage_skipped_subpages']})")
            print(f"  Avg Subpage Crawl   : {avg_subpage:.2f}s (Deep crawled: {job.metrics['triage_needs_more_info']})")
            print(f"  Avg AI Qual Duration: {avg_ai:.2f}s")
            print(f"  Sheets Write        : {sheets_duration:.2f}s")
            print(f"  Total pipeline run  : {duration_sec:.2f}s")
            print(f"  Throughput          : {throughput_comp_sec:.2f} companies/sec")
            print("=" * 52 + "\n")

            final_data = {
                "search_id": job.job_id,
                "summary": summary,
                "companies": job.results
            }
            job.status = "completed"
            await self._send_progress(job.job_id, "completed", "Discovery pipeline complete!", final_data)
            return final_data

        except Exception as e:
            logger.exception("Discovery pipeline failed")
            for task in cancellation_tasks:
                if not task.done():
                    task.cancel()
                    
            finished_at = datetime.utcnow().isoformat()
            duration_sec = time.time() - start_time
            summary = {
                "started_at": job.created_at,
                "finished_at": finished_at,
                "total_processed": 0,
                "qualified_count": 0,
                "disqualified_count": 0,
                "duration": f"{duration_sec:.1f}s",
                "errors": str(e)
            }
            job.status = "failed"
            await self.job_store.update_job_status(job.job_id, "failed", job.metrics)
            await self._send_progress(job.job_id, "failed", f"Discovery failed: {str(e)}", summary)
            return {"error": str(e)}

    async def _send_progress(self, job_id: str, event_type: str, message: str, data: Dict[str, Any]):
        async with self.ws_lock:
            data = data.copy()
            data["job_id"] = job_id
            await self.on_event(event_type, {"message": message, "data": data})

def re_search_phone(text: str) -> Optional[str]:
    import re
    pattern = r"((?:\+44|0)(?:\s?\d){9,11})"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None

def re_search_address(text: str) -> Optional[str]:
    import re
    pattern = r"([^,\n]+,\s*[^,\n]+,\s*[A-Z]{1,2}[0-9R][0-9A-Z]?\s*[0-9][A-Z]{2})"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None
