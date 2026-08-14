import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("RECRUITLY_TOTACO_API_KEY")

async def test_contacts():
    url2 = "https://api.recruitly.io/api/contact"
    params2 = {
        "apiKey": api_key,
        "companyId": "CY-70188"
    }
    
    async with httpx.AsyncClient() as client:
        resp2 = await client.get(url2, params=params2)
        if resp2.status_code == 200:
            data = resp2.json().get("data", [])
            if data:
                print("First contact full JSON:")
                print(json.dumps(data[0], indent=2))
            else:
                print("No contacts found.")

if __name__ == "__main__":
    asyncio.run(test_contacts())
