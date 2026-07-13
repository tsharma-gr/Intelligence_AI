from typing import List
from backend.services.search.base import BaseSearchService
from backend.models.company import SearchResult

class BingSearchService(BaseSearchService):
    def __init__(self, api_key: str = None):
        self.api_key = api_key

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        # Bing Search API stub
        raise NotImplementedError("Bing Search provider is not yet implemented.")
