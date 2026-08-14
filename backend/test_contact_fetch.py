import asyncio
from backend.services.recruitly import fetch_company_contacts

async def test():
    contacts = await fetch_company_contacts("CY-70188")
    print(f"Extracted {len(contacts)} contacts:")
    for c in contacts:
        print(c)

if __name__ == "__main__":
    asyncio.run(test())
