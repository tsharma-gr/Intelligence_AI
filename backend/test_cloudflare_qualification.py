import asyncio
import httpx
from backend.services.qualification import QualificationService
from backend.crawler.extractor import ContentExtractor
from backend.models.company import SearchResult, Page

class MockJob:
    def __init__(self):
        self.job_id = "test_cloudflare_bypass_job"
        
    def update_metrics(self, key, value, add=False):
        pass

async def test_full_bypass_and_qualify(url: str, company_name: str, company_type: str):
    print(f"\n==============================================")
    print(f"  Testing Bypass & AI Qualification: {company_name}")
    print(f"==============================================")
    
    fallback_success = False
    fallback_content = ""
    page_type = ""
    
    # Simulate Tier 1: Jina Reader API
    print("  Attempting Jina Reader Bypass...")
    try:
        jina_api = f"https://r.jina.ai/{url}"
        async with httpx.AsyncClient() as client:
            jina_resp = await client.get(jina_api, timeout=20)
            if jina_resp.status_code == 200 and len(jina_resp.text) > 200:
                fallback_content = jina_resp.text
                page_type = "home (jina reader bypass)"
                fallback_success = True
                print(f"  [SUCCESS]: Jina Reader extracted {len(fallback_content)} bytes of text.")
            elif jina_resp.status_code == 429:
                print(f"  [FAIL]: Jina Reader Rate Limited.")
    except Exception as e:
        print(f"  [FAIL]: Jina Error: {e}")

    # Simulate Tier 2: Wayback Machine
    if not fallback_success:
        print("  Attempting Wayback Machine Bypass...")
        try:
            wayback_api = f"https://archive.org/wayback/available?url={url}"
            async with httpx.AsyncClient() as client:
                wb_resp = await client.get(wayback_api, timeout=10)
                wb_data = wb_resp.json()
                if wb_data.get("archived_snapshots") and "closest" in wb_data["archived_snapshots"]:
                    snapshot_url = wb_data["archived_snapshots"]["closest"]["url"]
                    snap_resp = await client.get(snapshot_url, timeout=15)
                    if snap_resp.status_code == 200:
                        fallback_content = ContentExtractor.extract_clean_text(snap_resp.text)
                        page_type = "home (wayback machine cache)"
                        fallback_success = True
                        print(f"  [SUCCESS]: Wayback Machine extracted {len(fallback_content)} bytes of text.")
        except Exception as e:
            print(f"  [FAIL]: Wayback Error: {e}")

    if not fallback_success:
        print("  [CRITICAL]: Both fallbacks failed. Cannot test AI Qualification without text.")
        return

    # Simulate AI Qualification using the bypassed text
    print("\n  Sending bypassed text to DeepSeek AI for Qualification...")
    mock_pages = [Page(url=url, page_type=page_type, content=fallback_content)]
    
    try:
        qualification = await QualificationService.qualify_company(
            company_name=company_name,
            company_type=company_type,
            product_or_service="High-speed doors, roller shutters, industrial doors",
            location="UK",
            current_employer="",
            pages=mock_pages,
            job=MockJob()
        )
        
        print("\n  --- AI VERDICT ---")
        print(f"Qualified: {'[YES]' if qualification.qualified else '[NO]'}")
        print(f"Confidence: {qualification.confidence}%")
        print(f"Reason: {qualification.reason}")
        print(f"Corrected Name: {qualification.corrected_company_name}")
        print(f"Address: {qualification.address}")
        print(f"Phone: {qualification.phone}")
        
    except Exception as e:
        print(f"  [FAIL] AI Qualification Error: {e}")

async def main():
    # 3 websites that previously failed with Cloudflare 403s
    targets = [
        ("https://www.ukrollershutters.com/", "UK Roller Shutters", "Manufacturer"),
        ("https://unionindustries.co.uk/bespoke-solutions/", "Union Industries", "Manufacturer"),
        ("https://www.businessmagnet.co.uk/company/industrialrollershutterdoors-3793.htm", "Avon Industrial Doors", "Distributor")
    ]
    
    for url, name, ctype in targets:
        await test_full_bypass_and_qualify(url, name, ctype)
        await asyncio.sleep(2) # Brief pause between requests

if __name__ == "__main__":
    asyncio.run(main())
