import asyncio
import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from backend.crawler.crawler import WebsiteCrawler
from backend.services.qualification import QualificationService

async def main():
    print("Initializing crawler...")
    crawler = WebsiteCrawler(use_cache=True)
    
    url = "https://cloudfleetmanager.com/"
    print(f"Crawling {url}...")
    pages = await crawler.crawl_company(url)
    print(f"Crawled {len(pages)} pages.")
    
    if not pages:
        print("Failed to crawl any pages.")
        return
        
    print("Sending to LLM for qualification and extraction...")
    qual = await QualificationService.qualify_company(
        company_name="Cloud Fleet Manager",
        company_type="Maritime Software Provider",
        product_or_service="Fleet management software",
        location="Global",
        pages=pages
    )
    
    print("\n--- Phase 1 LLM Extraction Result ---")
    print(f"Company Name (Corrected): {qual.corrected_company_name}")
    print("\n--- Phase 2 CRM Matching Result ---")
    from backend.services.recruitly import check_company_exists
    cy_id = await check_company_exists(
        company_name=qual.corrected_company_name or "Cloud Fleet Manager",
        website=qual.official_website or url
    )
    print(f"CRM Match: {cy_id or 'Add Company'}")

if __name__ == "__main__":
    asyncio.run(main())
