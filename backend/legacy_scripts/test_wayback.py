import asyncio
import httpx

async def test_wayback():
    url = "https://www.ukrollershutters.com/"
    wayback_api = f"https://archive.org/wayback/available?url={url}"
    
    # 1. Test without headers (What we did before)
    print("--- Testing WITHOUT User-Agent ---")
    async with httpx.AsyncClient() as client:
        resp = await client.get(wayback_api)
        print(f"Status Code: {resp.status_code}")
        print(f"Content Type: {resp.headers.get('content-type')}")
        try:
            print(f"JSON: {resp.json()}")
        except Exception as e:
            print(f"JSON Error: {e}")
            print(f"Raw Text Preview: {resp.text[:100]}")
            
    # 2. Test with headers (The potential fix)
    print("\n--- Testing WITH User-Agent ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(wayback_api, headers=headers)
        print(f"Status Code: {resp.status_code}")
        print(f"Content Type: {resp.headers.get('content-type')}")
        try:
            print(f"JSON: {resp.json()}")
        except Exception as e:
            print(f"JSON Error: {e}")
            print(f"Raw Text Preview: {resp.text[:100]}")

if __name__ == "__main__":
    asyncio.run(test_wayback())
