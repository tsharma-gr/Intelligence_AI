import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from backend.services.search.serper import SerperSearchService

async def main():
    print("Initializing Serper API...")
    api_key = os.environ.get("SERPER_API_KEY")
    search_service = SerperSearchService(api_key=api_key)
    
    # These are highly targeted queries based on the extra keywords
    test_queries = [
        "aircraft hangar doors manufacturer UK",
        "commercial aircraft hangar doors supplier UK",
        "automatic entrance systems manufacturer UK",
        "commercial sliding door solutions UK"
    ]
    
    target_domains = ["jewersdoors.co.uk", "gilgendoorsystems.co.uk", "geze.co.uk"]
    
    print("\n--- Running Google Searches ---\n")
    
    for query in test_queries:
        print(f"Searching: '{query}'")
        try:
            results = await search_service.search(query, num_results=50)
            
            found_targets = []
            for res in results:
                website = res.website.lower()
                for target in target_domains:
                    if target in website:
                        found_targets.append(target)
            
            # Deduplicate the targets found in this query
            found_targets = list(set(found_targets))
            
            if found_targets:
                print(f"  ✅ SUCCESS: Found {', '.join(found_targets)} in the top 50 results!")
            else:
                print(f"  ❌ Did not find target companies in this specific query.")
                
        except Exception as e:
            print(f"  Error searching: {e}")

if __name__ == "__main__":
    asyncio.run(main())
