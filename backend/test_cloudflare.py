import asyncio
import httpx
from bs4 import BeautifulSoup
import re

# Fallback text extractor (simplified version of ContentExtractor for testing)
def extract_clean_text(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.decompose()
    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)
    return text[:500] + "..." if len(text) > 500 else text

async def test_bypass(url: str):
    print(f"\n[{url}]")
    
    # 1. Simulate the "Before" state (Live site that blocks us)
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(url, headers=headers, timeout=5)
            if resp.status_code in [403, 401]:
                print(f"  [FAIL] LIVE SITE: Failed (Bot Protection - {resp.status_code} Forbidden)")
            else:
                print(f"  LIVE SITE: Status {resp.status_code}")
    except Exception as e:
        print(f"  [FAIL] LIVE SITE: Failed ({type(e).__name__})")
        
    print(f"  --- Running New Bypass Logic ---")
    
    # 2. Simulate Tier 1: Wayback Machine
    try:
        wayback_api = f"https://archive.org/wayback/available?url={url}"
        async with httpx.AsyncClient() as client:
            wb_resp = await client.get(wayback_api, timeout=10)
            wb_data = wb_resp.json()
            if wb_data.get("archived_snapshots") and "closest" in wb_data["archived_snapshots"]:
                snapshot_url = wb_data["archived_snapshots"]["closest"]["url"]
                snap_resp = await client.get(snapshot_url, timeout=15)
                if snap_resp.status_code == 200:
                    text = extract_clean_text(snap_resp.text)
                    print(f"  [SUCCESS] TIER 1 (WAYBACK): Extracted {len(snap_resp.text)} bytes of HTML.")
                    print(f"     Preview: {text[:100]}...\n")
                    return # Stop here if Tier 1 succeeds
            print(f"  [FAIL] TIER 1 (WAYBACK): Failed (No snapshot found)")
    except Exception as e:
        print(f"  [FAIL] TIER 1 (WAYBACK): Error - {e}")
        
    # 3. Simulate Tier 2: Jina Reader API
    try:
        jina_api = f"https://r.jina.ai/{url}"
        async with httpx.AsyncClient() as client:
            jina_resp = await client.get(jina_api, timeout=15)
            if jina_resp.status_code == 200 and len(jina_resp.text) > 100:
                print(f"  [SUCCESS] TIER 2 (JINA): Extracted {len(jina_resp.text)} bytes of Markdown.")
                print(f"     Preview: {jina_resp.text[:100].replace(chr(10), ' ')}...\n")
                return # Stop here if Tier 2 succeeds
            print(f"  [FAIL] TIER 2 (JINA): Failed (Status {jina_resp.status_code})")
    except Exception as e:
        print(f"  [FAIL] TIER 2 (JINA): Error - {e}")

async def main():
    print("=== CLOUDFLARE BYPASS TEST ===")
    
    # These are the exact 3 websites that threw 403 Forbidden in your earlier logs
    test_urls = [
        "https://www.ukrollershutters.com/",
        "https://unionindustries.co.uk/bespoke-solutions/",
        "https://www.businessmagnet.co.uk/company/industrialrollershutterdoors-3793.htm"
    ]
    
    for url in test_urls:
        await test_bypass(url)

if __name__ == "__main__":
    asyncio.run(main())
