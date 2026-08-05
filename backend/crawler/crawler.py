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

class BotProtectionError(Exception):
    pass

logger = logging.getLogger("company_intelligence.crawler")

_PLAYWRIGHT_AVAILABLE = os.environ.get("DISABLE_PLAYWRIGHT") != "true"

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

    def triage_content(self, text: str, company_type: str) -> str:
        """
        Lightweight homepage triage heuristic (Phase 7).
        Analyzes keyword density to avoid deep crawling when homepage is highly definitive.
        """
        text_lower = text.lower()
        company_type_lower = company_type.lower()
        
        keywords = {
            "manufacturer": ["manufactur", "factory", "production", "oem", "made in", "fabricat", "foundry", "workshop"],
            "distributor": ["distributor", "dealer", "wholesaler", "stockist", "warehouse", "retailer", "merchant"],
            "service": ["service", "consulting", "advisor", "agency", "repair", "maintenance", "installation"]
        }
        
        scores = {}
        for cat, words in keywords.items():
            count = 0
            for w in words:
                count += text_lower.count(w)
            scores[cat] = count
            
        target_cat = None
        if "manufactur" in company_type_lower:
            target_cat = "manufacturer"
        elif any(x in company_type_lower for x in ["distributor", "dealer", "wholesaler", "supplier"]):
            target_cat = "distributor"
        elif any(x in company_type_lower for x in ["service", "consult", "advisor"]):
            target_cat = "service"
            
        if not target_cat:
            return "NEEDS_MORE_INFO"
            
        target_score = scores[target_cat]
        other_scores = sum(scores[cat] for cat in scores if cat != target_cat)
        
        if target_score >= 4 and other_scores <= 1:
            return "HIGH_CONFIDENCE_QUALIFIED"
        if target_score == 0 and other_scores >= 5:
            return "HIGH_CONFIDENCE_DISQUALIFIED"
            
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

        # 2. Heuristic Triage Check (Adaptive Crawling - Milestone 3)
        triage_decision = "NEEDS_MORE_INFO"
        if company_type:
            triage_decision = self.triage_content(home_text, company_type)
            if triage_decision != "NEEDS_MORE_INFO":
                if on_progress:
                    await on_progress("status", f"Triage check: {triage_decision}. Skipping subpages.")
                if self.cache and crawled_pages:
                    self.cache.set(domain, crawled_pages)
                return crawled_pages

        # 3. Discover key subpages if triage needs more info
        discovered_links = WebsiteIndexer.discover_pages(root_url, root_html)
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
        Fetch URL content using a leased context from the BrowserPoolManager.
        Falls back to HTTPX if Playwright is unavailable.
        """
        # 1. HTTPX client (Lightweight fast path)
        html = None
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
                        html = response.text
                    else:
                        logger.warning(f"HTTPX fetch returned non-HTML content-type '{content_type}' for '{url}'")
                elif response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location", "")
                    if location:
                        response2 = await client.get(location)
                        if response2.status_code == 200:
                            content_type2 = response2.headers.get("content-type", "").lower()
                            if "text/html" in content_type2 or "text/plain" in content_type2 or not content_type2:
                                html = response2.text
                            else:
                                logger.warning(f"HTTPX redirect returned non-HTML content-type '{content_type2}' for '{location}'")
                else:
                    logger.warning(f"HTTP {response.status_code} for '{url}'")
        except Exception as e:
            logger.info(f"HTTPX fetch failed for '{url}': {e}")

        # Heuristic check to see if we need Playwright fallback
        needs_playwright = False
        if not html:
            needs_playwright = True
        else:
            clean_text = ContentExtractor.extract_clean_text(html)
            clean_text_lower = clean_text.lower()
            
            # Check for Cloudflare/Bot protection immediately on HTTPX fast path
            if any(hint in clean_text_lower for hint in ["just a moment", "verify you are human", "checking your browser", "enable javascript", "please enable js", "cloudflare", "attention required"]):
                logger.warning(f"Bot protection detected on HTTPX fetch for '{url}'")
                raise BotProtectionError(f"Bot protection active on {url}")
                
            if len(clean_text) < 150:
                logger.info(f"HTTPX returned empty or shell for '{url}', triggering Playwright fallback")
                needs_playwright = True

        if not needs_playwright:
            return html

        # 2. Playwright: use shared browser pool context (Heavy fallback)
        if _PLAYWRIGHT_AVAILABLE:
            try:
                from backend.crawler.browser_pool import browser_pool
                async with browser_pool.lease_context() as context:
                    page = await context.new_page()

                    # Block heavy resources — images, fonts, CSS, ads (30-50% faster per page)
                    async def _block_resources(route):
                        if route.request.resource_type in ("image", "media", "font", "stylesheet", "other"):
                            await route.abort()
                        else:
                            await route.continue_()

                    await page.route("**/*", _block_resources)

                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=12000)
                        html = await page.content()
                        
                        # Post-render bot protection check
                        if html:
                            clean_pw_text = ContentExtractor.extract_clean_text(html).lower()
                            if any(hint in clean_pw_text for hint in ["just a moment", "verify you are human", "checking your browser", "attention required"]):
                                logger.warning(f"Bot protection detected on Playwright fetch for '{url}'")
                                raise BotProtectionError(f"Bot protection active on {url}")
                        
                        return html
                    finally:
                        # Close only the page, the context remains active in the pool
                        await page.close()

            except BotProtectionError:
                raise
            except Exception as e:
                logger.error(f"Playwright fallback fetch failed for '{url}': {e}")

        return html

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
