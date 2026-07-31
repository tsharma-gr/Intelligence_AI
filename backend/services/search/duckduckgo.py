import asyncio
import logging
from typing import List
from urllib.parse import urlparse
from ddgs import DDGS
from backend.services.search.base import BaseSearchService
from backend.models.company import SearchResult

logger = logging.getLogger("company_intelligence.search.duckduckgo")


class DuckDuckGoSearchService(BaseSearchService):
    """
    Free search provider using DuckDuckGo — no API key required.
    Uses a small delay between queries to avoid rate limiting.
    """

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        try:
            results = []

            # DuckDuckGo is synchronous — run it in a thread so it doesn't block the async loop
            def _sync_search():
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=num_results))

            raw_results = await asyncio.get_event_loop().run_in_executor(None, _sync_search)

            for item in raw_results:
                link = item.get("href", "")
                if not link:
                    continue

                title = item.get("title", "")
                snippet = item.get("body", "")

                parsed_url = urlparse(link)
                domain = parsed_url.netloc
                company_name = domain.replace("www.", "").split(".")[0].capitalize()

                results.append(SearchResult(
                    company_name=company_name,
                    website=link,
                    title=title,
                    snippet=snippet
                ))

            logger.info(f"DuckDuckGo returned {len(results)} results for: '{query}'")
            return results[:num_results]

        except Exception as e:
            logger.exception(f"DuckDuckGo search failed for query '{query}': {e}")
            return []
