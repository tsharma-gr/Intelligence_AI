import asyncio
import os
import sys
import httpx
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

async def main():
    api_key = os.getenv("RECRUITLY_TOTACO_API_KEY")
    url = "https://api.recruitly.io/api/company/search"
    params = {
        "apiKey": api_key,
        "query": "Fastwarm",
        "pageSize": 25
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
    data = response.json()
    print(f"Total count: {data.get('totalCount')}")
    for item in data.get("data", []):
        print(item.get("name"), item.get("website"))

if __name__ == "__main__":
    asyncio.run(main())
