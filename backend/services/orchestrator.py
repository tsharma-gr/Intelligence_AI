import logging
import asyncio
import time
from typing import List, Dict, Any, Callable, Awaitable, Optional
from datetime import datetime
import uuid
from urllib.parse import urlparse

from backend.models.company import Company, SearchHistory, SearchResult
from backend.services.query_generator import QueryGeneratorService
from backend.services.search.factory import SearchFactory
from backend.crawler.crawler import WebsiteCrawler
from backend.services.qualification import QualificationService
from backend.services.sheets import GoogleSheetsService
from backend.services.llm.base import token_usage, reset_token_usage
from backend.api.config import settings

logger = logging.getLogger("company_intelligence.orchestrator")

class CompanyDiscoveryOrchestrator:
    def __init__(self, on_event: Callable[[str, Dict[str, Any]], Awaitable[None]]):
        self.on_event = on_event
        self.sheets_service = GoogleSheetsService()
        self.crawler = WebsiteCrawler(use_cache=True)
        self.ws_lock = asyncio.Lock()

    async def run_discovery(
        self,
        company_type: str,
        product_or_service: str,
        location: str
    ) -> Dict[str, Any]:
        search_id = str(uuid.uuid4())[:8]
        started_at = datetime.utcnow().isoformat()
        start_time = time.time()
        
        # Reset token counter for this new search session
        reset_token_usage()
        
        history = SearchHistory(
            search_id=search_id,
            company_type=company_type,
            product=product_or_service,
            location=location,
            timestamp=started_at
        )

        try:
            # Step 1: Generate Queries
            await self._send_progress("query_gen", "Generating search queries using AI...", {"search_id": search_id})
            queries = await QueryGeneratorService.generate_queries(
                company_type=company_type,
                product_or_service=product_or_service,
                location=location
            )
            await self._send_progress("query_gen_done", f"Generated {len(queries)} search variations", {"queries": queries})

            # Step 2: Perform Google Search
            await self._send_progress("search", f"Initiating Google Search (Target: {settings.max_unique_companies} unique companies)...", {})
            search_service = SearchFactory.get_service()
            unique_companies: Dict[str, SearchResult] = {}
            
            for idx, q in enumerate(queries, 1):
                await self._send_progress("search_progress", f"Searching Google variation {idx}/{len(queries)}: '{q}'", {})
                res = await search_service.search(q, num_results=settings.results_per_query)
                
                for item in res:
                    parsed = urlparse(item.website)
                    domain = parsed.netloc.lower()
                    if domain and domain not in unique_companies:
                        unique_companies[domain] = item
                
                # Check if we hit the limit
                if len(unique_companies) >= settings.max_unique_companies:
                    await self._send_progress("search_progress", f"Reached max unique limit ({settings.max_unique_companies}). Halting search early.", {})
                    break

            # Ensure we strictly cap at the maximum
            candidates = list(unique_companies.values())[:settings.max_unique_companies]
            await self._send_progress("search_done", f"Google Search complete. Proceeding with {len(candidates)} unique websites.", {"count": len(candidates)})

            if not candidates:
                raise ValueError("No search results returned from search provider.")

            # Step 3: Crawl & AI Qualification
            processed_companies: List[Company] = []
            qualified_count = 0
            disqualified_count = 0
            skipped_count = 0  # sites that couldn't be crawled (403, timeout, etc.)
            
            semaphore = asyncio.Semaphore(5)
            
            async def process_candidate(idx: int, candidate: SearchResult):
                nonlocal qualified_count, disqualified_count, skipped_count
                async with semaphore:
                    prefix = f"[{idx}/{len(candidates)}] {candidate.company_name}"
                    await self._send_progress("crawl_start", f"{prefix}: Visiting website...", {"url": candidate.website})
                    
                    # Progress callback inside crawler
                    async def crawler_progress(event_type, msg):
                        await self._send_progress("crawl_progress", f"{prefix}: {msg}", {})

                    # Crawl website
                    pages = await self.crawler.crawl_company(candidate.website, on_progress=crawler_progress)
                    
                    await self._send_progress("ai_start", f"{prefix}: Running AI qualification...", {})
                    
                    # Qualify company with LLM
                    qualification = await QualificationService.qualify_company(
                        company_name=candidate.company_name,
                        company_type=company_type,
                        product_or_service=product_or_service,
                        location=location,
                        pages=pages
                    )
                    
                    address = qualification.address
                    phone = qualification.phone
                    
                    # Fallback to regex if LLM missed it
                    if not phone or not address:
                        for p in pages:
                            if p.page_type in ("home", "contact"):
                                if not phone:
                                    phone_match = re_search_phone(p.content)
                                    if phone_match:
                                        phone = phone_match
                                if not address:
                                    addr_match = re_search_address(p.content)
                                    if addr_match:
                                        address = addr_match
                    
                    company = Company(
                        company_name=candidate.company_name,
                        website=candidate.website,
                        address=address,
                        phone=phone,
                        category=product_or_service,
                        qualification=qualification
                    )
                    
                    if not pages:
                        skipped_count += 1
                        await self._send_progress("crawl_skip", f"{prefix}: Skipped — website could not be accessed (blocked or timeout)", {})
                        return company

                    if qualification.qualified:
                        qualified_count += 1
                        await self._send_progress("ai_qualified", f"{prefix}: QUALIFIED ({qualification.confidence}% confidence)", {"company": company.model_dump()})
                    else:
                        disqualified_count += 1
                        await self._send_progress("ai_disqualified", f"{prefix}: DISQUALIFIED", {"company": company.model_dump()})
                        
                    return company

            tasks = [process_candidate(idx, candidate) for idx, candidate in enumerate(candidates, 1)]
            processed_companies = await asyncio.gather(*tasks)

            # Step 4: Write to Google Sheets
            await self._send_progress("sheets_start", "Exporting results to Google Sheets...", {})
            finished_at = datetime.utcnow().isoformat()
            duration_sec = time.time() - start_time
            duration_str = f"{duration_sec:.1f}s"
            
            errors_str = f"{skipped_count} site(s) blocked/unreachable" if skipped_count > 0 else "None"
            summary = {
                "started_at": started_at,
                "finished_at": finished_at,
                "total_processed": len(processed_companies),
                "qualified_count": qualified_count,
                "disqualified_count": disqualified_count,
                "skipped_count": skipped_count,
                "duration": duration_str,
                "errors": errors_str
            }
            
            self.sheets_service.write_results(history, processed_companies, summary)

            # ─────────────────────────────────────────────
            # TOKEN USAGE REPORT
            # ─────────────────────────────────────────────
            # DeepSeek pricing: $0.14 / 1M input tokens, $0.28 / 1M output tokens
            input_cost  = (token_usage["prompt_tokens"]     / 1_000_000) * 0.14
            output_cost = (token_usage["completion_tokens"] / 1_000_000) * 0.28
            total_cost  = input_cost + output_cost
            print("\n" + "═" * 52)
            print("  🧠  TOKEN CONSUMPTION REPORT")
            print("═" * 52)
            print(f"  LLM Calls Made      : {token_usage['call_count']}")
            print(f"  Prompt  Tokens      : {token_usage['prompt_tokens']:,}")
            print(f"  Completion Tokens   : {token_usage['completion_tokens']:,}")
            print(f"  Total Tokens        : {token_usage['total_tokens']:,}")
            print(f"  Est. Cost (DeepSeek): ~${total_cost:.4f} USD")
            print("═" * 52 + "\n")

            final_data = {
                "search_id": search_id,
                "summary": summary,
                "companies": [c.model_dump() for c in processed_companies]
            }
            await self._send_progress("completed", "Discovery pipeline complete!", final_data)
            return final_data

        except Exception as e:
            logger.exception("Discovery pipeline failed")
            finished_at = datetime.utcnow().isoformat()
            duration_sec = time.time() - start_time
            summary = {
                "started_at": started_at,
                "finished_at": finished_at,
                "total_processed": 0,
                "qualified_count": 0,
                "disqualified_count": 0,
                "duration": f"{duration_sec:.1f}s",
                "errors": str(e)
            }
            await self._send_progress("failed", f"Discovery failed: {str(e)}", summary)
            return {"error": str(e)}

    async def _send_progress(self, event_type: str, message: str, data: Dict[str, Any]):
        async with self.ws_lock:
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
