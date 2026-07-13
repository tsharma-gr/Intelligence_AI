import logging
import asyncio
import sys
import os
from typing import List, Dict, Optional
from urllib.parse import urlparse
import httpx

from backend.crawler.models import CrawledPage
from backend.crawler.indexer import WebsiteIndexer
from backend.crawler.extractor import ContentExtractor
from backend.cache.cache import DomainCache

logger = logging.getLogger("company_intelligence.crawler")

# Playwright does NOT work on Windows with the default SelectorEventLoop.
# Also disable it if explicitly requested (e.g., on Render free tier to save memory).
_PLAYWRIGHT_AVAILABLE = sys.platform != "win32" and os.environ.get("DISABLE_PLAYWRIGHT") != "true"

class WebsiteCrawler:
    def __init__(self, use_cache: bool = True):
        self.cache = DomainCache() if use_cache else None
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

    async def crawl_company(self, root_url: str, on_progress: Optional[callable] = None) -> List[CrawledPage]:
        """
        Crawls the company website starting at root_url.
        Uses cached pages if available. Otherwise, crawls home, discovers key pages,
        crawls discovered pages, parses clean content, and caches results.
        """
        parsed_root = urlparse(root_url)
        domain = parsed_root.netloc.lower()
        if not domain:
            return []
            
        # Check cache
        if self.cache:
            cached_pages = self.cache.get(domain)
            if cached_pages:
                if on_progress:
                    await on_progress("cache_hit", f"Loaded pages for {domain} from cache")
                return cached_pages
                
        if on_progress:
            await on_progress("status", f"Visiting {root_url}")
            
        # 1. Fetch root page html
        root_html = await self._fetch_url(root_url)
        
        # Check if we should fall back to mock data
        if not root_html:
            mock_pages = self._get_mock_pages(root_url, domain)
            if mock_pages:
                logger.info(f"Using mock web pages fallback for {domain}")
                if on_progress:
                    await on_progress("status", f"Using offline mock pages for {domain}")
                if self.cache:
                    self.cache.set(domain, mock_pages)
                return mock_pages
            logger.warning(f"Could not retrieve homepage or mock fallback for {root_url}")
            return []
            
        # 2. Discover key pages
        discovered_links = WebsiteIndexer.discover_pages(root_url, root_html)
        
        # 3. Crawl target pages
        crawled_pages: List[CrawledPage] = []
        
        # Add home page content
        home_text = ContentExtractor.extract_clean_text(root_html)
        crawled_pages.append(CrawledPage(url=root_url, page_type="home", content=home_text))
        
        # Create list of tasks for other pages
        tasks = []
        page_types = []
        for ptype, url in discovered_links.items():
            if ptype == "home" or url == root_url:
                continue
            tasks.append(self._fetch_url(url))
            page_types.append((ptype, url))
            
        if tasks:
            if on_progress:
                await on_progress("status", f"Discovered {len(tasks)} business pages on {domain}. Starting parsing...")
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for (ptype, url), html in zip(page_types, results):
                if isinstance(html, Exception) or not html:
                    logger.warning(f"Failed to crawl discovered subpage {url}")
                    continue
                    
                if on_progress:
                    await on_progress("page_extracted", f"Extracting content from {ptype} page")
                    
                clean_text = ContentExtractor.extract_clean_text(html)
                crawled_pages.append(CrawledPage(url=url, page_type=ptype, content=clean_text))
                
        # Cache results
        if self.cache and crawled_pages:
            self.cache.set(domain, crawled_pages)
            
        return crawled_pages

    async def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL content. Uses Playwright on non-Windows; always falls back to HTTPX."""
        # 1. Playwright async attempt (Linux/Mac only — fails on Windows SelectorEventLoop)
        if _PLAYWRIGHT_AVAILABLE:
            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page(extra_http_headers=self.headers)
                    await page.goto(url, wait_until="domcontentloaded", timeout=12000)
                    html = await page.content()
                    await browser.close()
                    return html
            except Exception as e:
                logger.info(f"Playwright fetch failed for '{url}', falling back to HTTPX client: {e}")
            
        # 2. HTTPX client fallback with full browser-like headers
        try:
            async with httpx.AsyncClient(
                headers=self.headers,
                follow_redirects=True,
                timeout=15.0,
                http2=True
            ) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
                elif response.status_code in (301, 302, 303, 307, 308):
                    # Follow redirect manually if needed
                    location = response.headers.get("location", "")
                    if location:
                        response2 = await client.get(location)
                        if response2.status_code == 200:
                            return response2.text
                else:
                    logger.warning(f"HTTP {response.status_code} for '{url}'")
        except Exception as e:
            logger.error(f"HTTPX fallback fetch failed for '{url}': {e}")
            
        return None

    def _get_mock_pages(self, root_url: str, domain: str) -> Optional[List[CrawledPage]]:
        """Provides rich mock pages to enable offline testing."""
        if "apexhandling" in domain:
            return [
                CrawledPage(
                    url=root_url,
                    page_type="home",
                    content="Welcome to Apex Handling. We are the premier manufacturer and supplier of forklift trucks, custom attachments, and warehouse material handling systems in the UK. Contact us at +44 1234 56789 or visit our office at 12 Industrial Way, London."
                ),
                CrawledPage(
                    url=f"{root_url}/about-us",
                    page_type="about",
                    content="About Apex Handling. Founded in 1995, Apex Handling has grown to become the UK's leading designer and manufacturer of material handling systems. We build all our machinery locally at our plant in the UK."
                ),
                CrawledPage(
                    url=f"{root_url}/products",
                    page_type="products",
                    content="Our Products. We manufacture Forklift Trucks, Warehouse Equipment, Container Loaders, and custom lifting accessories."
                )
            ]
        elif "innovatelifts" in domain:
            return [
                CrawledPage(
                    url=root_url,
                    page_type="home",
                    content="Innovate Lifts - Platform & Passenger Lifts. Design, manufacture and installation of platform lifts, goods lifts and service lifts. Call us on +44 207 987 6543."
                ),
                CrawledPage(
                    url=f"{root_url}/products",
                    page_type="products",
                    content="Platform Lifts & Cabin Lifts. We manufacture vertical platform lifts, step lifts, and goods passenger lifts designed for accessibility."
                ),
                CrawledPage(
                    url=f"{root_url}/contact",
                    page_type="contact",
                    content="Contact Innovate Lifts. Head office address: 88 Elevator Tower, London, EC1A 2DD. Phone: +44 207 987 6543."
                )
            ]
        elif "ecowaterhygiene" in domain:
            return [
                CrawledPage(
                    url=root_url,
                    page_type="home",
                    content="Eco Water Hygiene Solutions. Comprehensive water safety, hygiene management and legionella risk assessment service provider."
                ),
                CrawledPage(
                    url=f"{root_url}/services",
                    page_type="services",
                    content="Water Hygiene Services. We provide legionella control, water testing, cleaning, and chemical disinfection services in the UK."
                )
            ]
        return None
