import httpx
import logging
from typing import List
from urllib.parse import urlparse
from backend.services.search.base import BaseSearchService
from backend.models.company import SearchResult

logger = logging.getLogger("company_intelligence.search.serper")

class SerperSearchService(BaseSearchService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://google.serper.dev/search"

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        if not self.api_key or "YOUR_SERPER" in self.api_key:
            logger.warning("Serper API key is missing or default. Returning mock/empty results.")
            return self._get_mock_results(query)

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "num": num_results
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                organic_results = data.get("organic", [])
                results = []
                
                for item in organic_results:
                    link = item.get("link", "")
                    if not link:
                        continue
                        
                    # Deduce a neat fallback company name from website title or hostname
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    
                    parsed_url = urlparse(link)
                    domain = parsed_url.netloc
                    company_name = domain.replace("www.", "").split(".")[0].capitalize()
                    
                    results.append(SearchResult(
                        company_name=company_name,
                        website=link,
                        title=title,
                        snippet=snippet
                    ))
                    
                return results
                
        except Exception as e:
            logger.exception(f"Error calling Serper API for query '{query}'")
            return self._get_mock_results(query)

    def _get_mock_results(self, query: str) -> List[SearchResult]:
        """Fallback mock results if Serper key is missing or API errors out."""
        logger.info("Generating fallback search results for offline validation.")
        return [
            SearchResult(
                company_name="Apex Handling",
                website="https://www.apexhandling.co.uk",
                title="Apex Material Handling Solutions UK",
                snippet="Leading manufacturer of forklift trucks and custom material handling solutions across the UK."
            ),
            SearchResult(
                company_name="InnovateLifts",
                website="https://www.innovatelifts.com",
                title="Innovate Lifts - Platform & Passenger Lifts",
                snippet="Design, manufacture and installation of platform lifts, goods lifts and service lifts."
            ),
            SearchResult(
                company_name="EcoWaterHygiene",
                website="https://www.ecowaterhygiene.co.uk",
                title="Eco Water Hygiene Solutions",
                snippet="Comprehensive water safety, hygiene management and legionella risk assessment service provider."
            )
        ]
