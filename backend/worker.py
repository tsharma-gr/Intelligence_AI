import asyncio
import json
import logging
from typing import Dict, Any
import redis.asyncio as redis
from arq import worker

from backend.api.config import settings
from backend.services.orchestrator import CompanyDiscoveryOrchestrator

logger = logging.getLogger("company_intelligence.worker")

async def run_discovery_job(ctx: Dict[Any, Any], job_id: str, company_type: str, product_or_service: str, location: str):
    """
    Background task executed by ARQ worker.
    Runs the discovery pipeline and streams events back via Redis PubSub.
    """
    logger.info(f"Starting background job {job_id}")
    redis_client = redis.from_url(settings.redis_url)
    
    async def on_event(event_type: str, event_payload: Dict[str, Any]):
        message = {
            "type": event_type,
            "message": event_payload.get("message", ""),
            "data": event_payload.get("data", {})
        }
        # Publish exactly what the websocket expects to the job channel
        await redis_client.publish(f"job_{job_id}", json.dumps(message))
        
    orchestrator = CompanyDiscoveryOrchestrator(on_event=on_event)
    
    try:
        await orchestrator.run_discovery(
            company_type=company_type,
            product_or_service=product_or_service,
            location=location
        )
        logger.info(f"Job {job_id} finished successfully")
    except Exception as e:
        logger.exception(f"Job {job_id} failed")
        await redis_client.publish(f"job_{job_id}", json.dumps({
            "type": "error",
            "message": f"Orchestrator failed: {str(e)}"
        }))
    finally:
        # Send a termination signal to close the websocket
        await redis_client.publish(f"job_{job_id}", json.dumps({"type": "job_complete"}))
        await redis_client.aclose()


async def startup(ctx: Dict[Any, Any]):
    logger.info("ARQ Worker starting up...")

async def shutdown(ctx: Dict[Any, Any]):
    logger.info("ARQ Worker shutting down...")

class WorkerSettings:
    functions = [run_discovery_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = worker.RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 600  # 10 minutes max per job
