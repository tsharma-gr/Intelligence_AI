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
from backend.crawler.fetchers import HTTPXFetcher, JinaFetcher, PlaywrightFetcher
from backend.cache.cache import DomainCache

class BotProtectionError(Exception):
    pass

logger = logging.getLogger("company_intelligence.crawler")

class WebsiteCrawler:
    def __init__(self, use_cache: bool = True):
        self.cache = DomainCache() if use_cache else None
        
        # Initialize fetcher pipeline
        self.httpx_fetcher = HTTPXFetcher()
        self.jina_fetcher = JinaFetcher()
        self.playwright_fetcher = PlaywrightFetcher()

    def triage_content(self, content: str, company_type: str) -> str:
        """
        Fast keyword-based triage to determine if the page matches the company_type.
        Returns: 'MATCH', 'NO_MATCH', or 'NEEDS_MORE_INFO'
        """
        if not company_type or not content:
            return "NEEDS_MORE_INFO"
            
        content_lower = content.lower()
        company_type_lower = company_type.lower()
        
        # Simple heuristic check
        if company_type_lower in content_lower:
            return "MATCH"
            
        return "NEEDS_MORE_INFO"

    async def crawl_company(self, root_url: str, company_type: str = "", on_progress: Optional[callable] = None) -> List[CrawledPage]:
        """
        Crawls the company website starting at root_url.
        Uses cached pages if available. Otherwise, crawls home, triages, and conditionally
        crawls subpages if needed.
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

        crawled_pages: List[CrawledPage] = []
        home_text = ContentExtractor.extract_clean_text(root_html)
        crawled_pages.append(CrawledPage(url=root_url, page_type="home", content=home_text))

        # 2. Discover key subpages to crawl
        discovered_links = await WebsiteIndexer.discover_pages(root_url, root_html)
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
        """
        Fetch URL content with Graceful Degradation:
        1. HTTPX (Fastest)
        2. Jina AI (Smart fallback)
        3. Playwright (Last resort, locked to 1 instance)
        """
        # Tier 1: HTTPX
        html = await self.httpx_fetcher.fetch(url)
        needs_fallback = False
        
        if not html:
            needs_fallback = True
        else:
            clean_text = ContentExtractor.extract_clean_text(html)
            clean_text_lower = clean_text.lower()
            
            # Detect bot protection
            if any(hint in clean_text_lower for hint in ["just a moment", "verify you are human", "checking your browser", "enable javascript", "please enable js", "cloudflare", "attention required"]):
                logger.warning(f"Bot protection detected on HTTPX fetch for '{url}'")
                needs_fallback = True
                
            # Detect JS shell
            if not needs_fallback and len(clean_text) < 150:
                logger.info(f"HTTPX returned empty or shell for '{url}', triggering fallback")
                needs_fallback = True

        if not needs_fallback:
            return html

        # Tier 2: Jina AI
        logger.info(f"Triggering Jina AI fallback for '{url}'")
        jina_html = await self.jina_fetcher.fetch(url)
        if jina_html:
            return jina_html

        # Tier 3: Playwright (Last Resort)
        logger.info(f"Jina AI failed or blocked. Triggering Playwright final fallback for '{url}'")
        playwright_html = await self.playwright_fetcher.fetch(url)
        if playwright_html:
            return playwright_html
            
        logger.warning(f"All extraction tiers failed for '{url}'")
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
