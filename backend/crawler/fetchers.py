import logging
import asyncio
import os
from typing import Optional
from abc import ABC, abstractmethod

import httpx

# Only import playwright when needed to prevent issues on systems where it isn't installed
try:
    from playwright.async_api import async_playwright, Error as PlaywrightError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger("company_intelligence.fetchers")

class BaseFetcher(ABC):
    @abstractmethod
    async def fetch(self, url: str) -> Optional[str]:
        """Fetch the HTML content of the URL. Returns None if it fails."""
        pass


class HTTPXFetcher(BaseFetcher):
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }

    async def fetch(self, url: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(
                headers=self.headers,
                follow_redirects=True,
                timeout=15.0,
                http2=True
            ) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "").lower()
                    if "text/html" in content_type or "text/plain" in content_type or not content_type:
                        return response.text
                    else:
                        logger.warning(f"[HTTPXFetcher] Returned non-HTML content-type '{content_type}' for '{url}'")
                elif response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location", "")
                    if location:
                        response2 = await client.get(location)
                        if response2.status_code == 200:
                            content_type2 = response2.headers.get("content-type", "").lower()
                            if "text/html" in content_type2 or "text/plain" in content_type2 or not content_type2:
                                return response2.text
                else:
                    logger.warning(f"[HTTPXFetcher] HTTP {response.status_code} for '{url}'")
        except Exception as e:
            logger.info(f"[HTTPXFetcher] Failed for '{url}': {e}")
            
        return None


class JinaFetcher(BaseFetcher):
    # Global semaphore across all instances to prevent Jina API from bursting
    _semaphore = asyncio.Semaphore(5)

    async def fetch(self, url: str) -> Optional[str]:
        try:
            async with self._semaphore:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    jina_api_key = os.getenv("JINA_API_KEY")
                    headers = {"Authorization": f"Bearer {jina_api_key}"} if jina_api_key else {}
                    
                    for attempt in range(3):
                        jina_resp = await client.get(f"https://r.jina.ai/{url}", headers=headers)
                        if jina_resp.status_code == 200:
                            # If Jina returns a Cloudflare block, it failed to bypass
                            if "Just a moment..." in jina_resp.text or "security verification" in jina_resp.text.lower() or "Cloudflare" in jina_resp.text:
                                logger.warning(f"[JinaFetcher] Returned a Cloudflare challenge page for {url}")
                                return None
                            logger.info(f"[JinaFetcher] Successfully fetched {url}")
                            return jina_resp.text
                        elif jina_resp.status_code == 429:
                            await asyncio.sleep(2)
                            continue
                        else:
                            logger.warning(f"[JinaFetcher] HTTP {jina_resp.status_code} for '{url}'")
                            break
        except Exception as e:
            logger.error(f"[JinaFetcher] Failed for '{url}': {e}")

        return None


class PlaywrightFetcher(BaseFetcher):
    # Enforce strict maximum of 1 concurrent browser to prevent OOM on 1GB instances
    _lock = asyncio.Lock()

    async def fetch(self, url: str) -> Optional[str]:
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("[PlaywrightFetcher] Playwright is not installed.")
            return None

        # Absolute protection against concurrent browser launches
        async with self._lock:
            try:
                async with async_playwright() as p:
                    logger.info(f"[PlaywrightFetcher] Launching Chromium for '{url}'")
                    # Launch minimal headless Chromium
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            '--disable-gpu',
                            '--disable-dev-shm-usage',
                            '--disable-setuid-sandbox',
                            '--no-sandbox',
                        ]
                    )
                    
                    context = await browser.new_context(
                        viewport={'width': 1280, 'height': 720},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    )
                    
                    page = await context.new_page()
                    # Block heavy resources to save RAM
                    await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font", "stylesheet"] else route.continue_())
                    
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        # Give SPAs a tiny bit of time to render text
                        await page.wait_for_timeout(2000)
                        html = await page.content()
                        logger.info(f"[PlaywrightFetcher] Successfully fetched {url}")
                        return html
                    except PlaywrightError as e:
                        logger.warning(f"[PlaywrightFetcher] Navigation failed for {url}: {e}")
                        return None
                    finally:
                        await context.close()
                        await browser.close()
            except Exception as e:
                logger.error(f"[PlaywrightFetcher] Critical failure for '{url}': {e}")
                return None
