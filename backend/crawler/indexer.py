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
    def discover_pages(root_url: str, html_content: str) -> Dict[str, str]:
        """
        Parses root HTML content and discovers URLs for key business pages.
        Returns a dictionary mapping page types to absolute URLs.
        """
        discovered = {"home": root_url}
        parsed_root = urlparse(root_url)
        base_domain = parsed_root.netloc
        
        soup = BeautifulSoup(html_content, "html.parser")
        anchors = soup.find_all("a", href=True)
        
        seen_links: Dict[str, Set[str]] = {key: set() for key in WebsiteIndexer.PATTERNS.keys()}
        
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
            
            for page_type, pattern in WebsiteIndexer.PATTERNS.items():
                if pattern.search(link_path_and_text):
                    seen_links[page_type].add(absolute_url)
                    
        # Select the best link for each type (shortest url path matches usually best)
        for page_type, links in seen_links.items():
            if links:
                # Sort by length and path depth to get clean URLs e.g. /products instead of /products/tags/new
                best_link = min(links, key=lambda l: (len(urlparse(l).path.split("/")), len(l)))
                discovered[page_type] = best_link
                
        logger.info(f"Discovered subpages for {root_url}: {discovered}")
        return discovered
