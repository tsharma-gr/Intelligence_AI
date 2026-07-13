from backend.api.config import settings
from backend.services.search.base import BaseSearchService
from backend.services.search.serper import SerperSearchService
from backend.services.search.google import GoogleSearchService
from backend.services.search.bing import BingSearchService
from backend.services.search.tavily import TavilySearchService

class SearchFactory:
    @staticmethod
    def get_service() -> BaseSearchService:
        provider = settings.search_provider.lower()
        if provider == "serper":
            return SerperSearchService(api_key=settings.serper_api_key)
        elif provider == "google":
            return GoogleSearchService(api_key=settings.serper_api_key)  # or specific key if added
        elif provider == "bing":
            return BingSearchService()
        elif provider == "tavily":
            return TavilySearchService()
        else:
            raise ValueError(f"Unsupported search provider: {provider}")
