import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger("company_intelligence.job_manager")

class SearchJob:
    def __init__(self, company_type: str, product: str, location: str, user_id: Optional[str] = None):
        self.job_id = str(uuid.uuid4())[:8]
        self.user_id = user_id
        self.company_type = company_type
        self.product = product
        self.location = location
        self.status = "pending"
        self.created_at = datetime.utcnow().isoformat()
        self.finished_at = Optional[str]
        
        # Isolation Queues (AI queue is a Priority Queue)
        self.search_queue = asyncio.Queue()
        self.crawler_queue = asyncio.Queue()
        self.ai_queue = asyncio.PriorityQueue()
        self.sheets_queue = asyncio.Queue()
        
        # Thread-safe cancellation
        self.cancel_event = asyncio.Event()
        
        # Live Operational Metrics
        self.metrics = {
            "search_queries_generated": 0,
            "search_queries_completed": 0,
            "total_urls_found": 0,
            "unique_domains_found": 0,
            "crawled_count": 0,
            "extracted_count": 0,
            "qualified_count": 0,
            "disqualified_count": 0,
            "skipped_count": 0,
            "retry_count": 0,
            "avg_crawl_time_ms": 0.0,
            "avg_ai_time_ms": 0.0,
            "started_time": datetime.utcnow().timestamp(),
            "duration_sec": 0.0,
            
            # Detailed timing metrics for profiling (Milestone 4)
            "homepage_crawl_times": [],
            "subpage_crawl_times": [],
            "ai_qualification_times": [],
            "triage_skipped_subpages": 0,
            "triage_needs_more_info": 0,
            
            # Isolated Job Token Usage
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "call_count": 0
        }
        
        # Isolated final results list
        self.results: List[Dict[str, Any]] = []
        
        # Thread-safe metrics lock
        self._metrics_lock = asyncio.Lock()

    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def cancel(self):
        self.cancel_event.set()
        self.status = "cancelled"
        logger.info(f"Job {self.job_id} has been requested to cancel.")

    async def update_metrics(self, key: str, value: Any, add: bool = False):
        async with self._metrics_lock:
            if key in self.metrics:
                if add:
                    self.metrics[key] += value
                else:
                    self.metrics[key] = value
            self.metrics["duration_sec"] = datetime.utcnow().timestamp() - self.metrics["started_time"]


class JobManager:
    def __init__(self):
        self._jobs: Dict[str, SearchJob] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, company_type: str, product: str, location: str, user_id: Optional[str] = None) -> SearchJob:
        async with self._lock:
            job = SearchJob(company_type, product, location, user_id)
            self._jobs[job.job_id] = job
            logger.info(f"Created SearchJob {job.job_id} for {company_type} | {product} | {location}")
            return job

    async def get_job(self, job_id: str) -> Optional[SearchJob]:
        async with self._lock:
            return self._jobs.get(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.cancel()
                return True
            return False

    async def list_jobs(self) -> List[SearchJob]:
        async with self._lock:
            return list(self._jobs.values())
