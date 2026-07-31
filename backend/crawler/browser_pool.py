import asyncio
import logging
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext
from backend.api.config import settings

logger = logging.getLogger("company_intelligence.browser_pool")

class PooledContext:
    def __init__(self, context: BrowserContext, browser_index: int):
        self.context = context
        self.browser_index = browser_index
        self.visit_count = 0
        self.lock = asyncio.Lock()

class BrowserPoolManager:
    def __init__(self):
        self.max_browsers = getattr(settings, "max_browsers", 2)
        self.max_contexts = getattr(settings, "max_contexts_per_browser", 10)
        self.context_recycle_limit = 20
        
        self._playwright = None
        self._browsers: List[Browser] = []
        self._contexts_pool: asyncio.Queue = asyncio.Queue()
        self._active_contexts_count = 0
        self._pool_lock = asyncio.Lock()
        self._initialized = False

    async def start(self):
        """Warm up all browser processes and pre-populate contexts."""
        async with self._pool_lock:
            if self._initialized:
                return
            
            logger.info("Initializing BrowserPoolManager...")
            self._playwright = await async_playwright().start()
            
            launch_args = [
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--single-process",
                "--no-zygote",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-default-apps",
                "--disable-sync",
                "--no-first-run",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-software-rasterizer",
                "--disable-features=TranslateUI",
            ]
            
            # Start browsers in parallel
            launch_tasks = [
                self._playwright.chromium.launch(headless=True, args=launch_args)
                for _ in range(self.max_browsers)
            ]
            self._browsers = await asyncio.gather(*launch_tasks)
            
            # Pre-populate contexts in the queue
            for b_idx, browser in enumerate(self._browsers):
                for _ in range(self.max_contexts):
                    context = await browser.new_context(
                        java_script_enabled=True,
                        bypass_csp=True,
                    )
                    pooled = PooledContext(context, b_idx)
                    await self._contexts_pool.put(pooled)
                    self._active_contexts_count += 1
            
            self._initialized = True
            logger.info(f"BrowserPoolManager ready. Warmed up {len(self._browsers)} browsers with {self._active_contexts_count} contexts.")

    async def close(self):
        """Close all contexts and browser processes cleanly."""
        async with self._pool_lock:
            if not self._initialized:
                return
            logger.info("Closing BrowserPoolManager...")
            
            # Drain queue
            while not self._contexts_pool.empty():
                pooled = await self._contexts_pool.get()
                try:
                    await pooled.context.close()
                except Exception:
                    pass
            
            # Close browsers
            for browser in self._browsers:
                try:
                    await browser.close()
                except Exception:
                    pass
            
            # Stop Playwright
            if self._playwright:
                await self._playwright.stop()
                
            self._browsers.clear()
            self._active_contexts_count = 0
            self._initialized = False
            logger.info("BrowserPoolManager closed down.")

    @asynccontextmanager
    async def lease_context(self):
        """
        Lease a context from the pool. Handles recycling after 20 visits
        and crash recovery.
        """
        if not self._initialized:
            await self.start()

        # Block until a context becomes available in the queue
        pooled: PooledContext = await self._contexts_pool.get()
        
        async with pooled.lock:
            try:
                # Basic context sanity check
                if pooled.context.browser is None or not pooled.context.browser.is_connected():
                    logger.warning(f"Browser of context {pooled.browser_index} disconnected. Recreating browser.")
                    await self._respawn_browser(pooled.browser_index)
                    # Replace the context after browser respawn
                    pooled.context = await self._browsers[pooled.browser_index].new_context(
                        java_script_enabled=True,
                        bypass_csp=True
                    )
                    pooled.visit_count = 0
                
                yield pooled.context
                
                # Context completed task successfully: increment visit count
                pooled.visit_count += 1
                
                # Recycle context if it exceeds visit limit
                if pooled.visit_count >= self.context_recycle_limit:
                    logger.info(f"Recycling context in browser {pooled.browser_index} after {pooled.visit_count} visits.")
                    await pooled.context.close()
                    pooled.context = await self._browsers[pooled.browser_index].new_context(
                        java_script_enabled=True,
                        bypass_csp=True
                    )
                    pooled.visit_count = 0
                
            except Exception as e:
                logger.exception(f"Exception using leased context from browser {pooled.browser_index}. Context will be replaced: {e}")
                # Replace crashed context
                try:
                    await pooled.context.close()
                except Exception:
                    pass
                
                # Respawn context
                try:
                    pooled.context = await self._browsers[pooled.browser_index].new_context(
                        java_script_enabled=True,
                        bypass_csp=True
                    )
                    pooled.visit_count = 0
                except Exception as respawn_err:
                    logger.critical(f"Failed to respawn context on browser crash: {respawn_err}")
                
                raise
            finally:
                # Return it back to the pool
                await self._contexts_pool.put(pooled)

    async def _respawn_browser(self, index: int):
        """Spawns a new browser process to replace a crashed one."""
        logger.info(f"Respawning crashed browser process at index {index}")
        try:
            try:
                await self._browsers[index].close()
            except Exception:
                pass
            
            launch_args = [
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--single-process",
                "--no-zygote",
                "--disable-extensions",
                "--no-sandbox",
            ]
            self._browsers[index] = await self._playwright.chromium.launch(headless=True, args=launch_args)
            logger.info(f"Browser at index {index} successfully respawned.")
        except Exception as e:
            logger.error(f"Failed to respawn browser at index {index}: {e}")

# Global pool instance
browser_pool = BrowserPoolManager()
