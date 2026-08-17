import re
import logging
from typing import Dict, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger("company_intelligence.crawler.indexer")

class WebsiteIndexer:
    # Page type keywords mapping
    PATTERNS = {
        "about": re.compile(r"about|company|who-we-are|leadership|profile", re.IGNORECASE),
        "products": re.compile(r"product|equipment|range|catalogue|solutions|devices", re.IGNORECASE),
        "services": re.compile(r"service|installation|capability|capabilities|what-we-do", re.IGNORECASE),
        "contact": re.compile(r"contact|contact-us|location|find-us", re.IGNORECASE)
    }

    @staticmethod
    async def discover_pages(root_url: str, html_content: str) -> Dict[str, str]:
        """
        Parses root HTML content and discovers URLs for key business pages.
        Uses Regex first, then falls back to AI for missing pages.
        Returns a dictionary mapping page types to absolute URLs.
        """
        discovered = {"home": root_url}
        parsed_root = urlparse(root_url)
        base_domain = parsed_root.netloc
        
        try:
            soup = BeautifulSoup(html_content, "html.parser")
        except Exception as e:
            logger.error(f"Failed to parse HTML in indexer: {e}")
            return discovered
            
        anchors = soup.find_all("a", href=True)
        
        seen_links: Dict[str, Set[str]] = {key: set() for key in WebsiteIndexer.PATTERNS.keys()}
        unknown_links: Set[str] = set()
        
        for anchor in anchors:
            href = anchor["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
                
            # Make URL absolute
            absolute_url = urljoin(root_url, href)
            parsed_link = urlparse(absolute_url)
            
            # Restrict to the same domain (ignore external links)
            if parsed_link.netloc != base_domain:
                continue
                
            # Determine link text or path matching
            link_path_and_text = f"{parsed_link.path} {anchor.get_text()}"
            matched = False
            
            for page_type, pattern in WebsiteIndexer.PATTERNS.items():
                if pattern.search(link_path_and_text):
                    seen_links[page_type].add(absolute_url)
                    matched = True
                    break
            
            if not matched:
                unknown_links.add(absolute_url)
                    
        # Select the best link for each type (shortest url path matches usually best)
        for page_type, links in seen_links.items():
            if links:
                # Sort by length and path depth to get clean URLs e.g. /products instead of /products/tags/new
                best_link = min(links, key=lambda l: (len(urlparse(l).path.split("/")), len(l)))
                discovered[page_type] = best_link
                
        # --- HYBRID AI FALLBACK ---
        missing_categories = [cat for cat in WebsiteIndexer.PATTERNS.keys() if cat not in discovered]
        
        if missing_categories and unknown_links:
            # We don't want to overwhelm the LLM, pick up to 20 short/clean unknown links
            sorted_unknown = sorted(list(unknown_links), key=lambda l: len(l))[:20]
            
            prompt = (
                f"I am scraping a company website ({root_url}).\n"
                f"I need to find the URLs that represent these missing page categories: {missing_categories}\n"
                f"Here are the unmapped internal links I found on the homepage:\n{sorted_unknown}\n\n"
                "Return a JSON object mapping the missing category name to the BEST matching URL from the list provided. "
                "If no URL in the list seems to match a category, map it to null.\n"
                "Example output format:\n"
                "{\n"
                '  "about": "https://example.com/our-story",\n'
                '  "contact": null\n'
                "}\n"
                "Output strictly valid JSON only."
            )
            
            try:
                from backend.services.llm.factory import LLMFactory
                import json
                llm = LLMFactory.get_service()
                
                logger.info(f"Triggering AI Link Router fallback for {root_url} to find {missing_categories}")
                response_text = await llm.generate_response(prompt=prompt, system_instruction="You are an expert web scraping assistant. Output JSON only.")
                
                # Clean response
                clean_text = response_text.strip()
                if "```json" in clean_text:
                    clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_text:
                    clean_text = clean_text.split("```")[1].strip()
                    
                ai_mapping = json.loads(clean_text)
                
                for cat, url in ai_mapping.items():
                    if cat in missing_categories and url and isinstance(url, str) and url in sorted_unknown:
                        discovered[cat] = url
                        logger.info(f"AI Router successfully found {cat}: {url}")
                        
            except Exception as e:
                logger.warning(f"AI Link Router fallback failed for {root_url}: {e}")

        logger.info(f"Final discovered subpages for {root_url}: {discovered}")
        return discovered
