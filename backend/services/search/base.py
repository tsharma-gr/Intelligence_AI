from abc import ABC, abstractmethod
from typing import List
from backend.models.company import SearchResult

class BaseSearchService(ABC):
    @abstractmethod
    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """
        Executes a search query and returns structured SearchResult list.
        """
        pass
