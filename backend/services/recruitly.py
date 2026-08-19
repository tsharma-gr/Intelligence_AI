import os
import requests
import re
from typing import Optional, Tuple
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

import httpx
import asyncio

# Use a local asyncio Lock for rate limiting the Recruitly API across workers
recruitly_api_lock = asyncio.Lock()

async def check_company_exists(company_name: str, website: str) -> Optional[Tuple[str, str]]:
    """
    Checks if a company exists in the Recruitly Totaco database by its name, 
    and verifies the website matches to avoid false positives.
    Returns a tuple of (UUID, CY-ID) if it exists, otherwise returns None.
    """
    api_key = os.getenv("RECRUITLY_TOTACO_API_KEY")
    if not api_key:
        print("Warning: RECRUITLY_TOTACO_API_KEY is not set.")
        return None
        
    api_base_url = os.getenv("RECRUITLY_API_BASE_URL", "https://api.recruitly.io/api")
    
    # The endpoint to search companies
    url = f"{api_base_url}/company/search"
    
    # We pass only the first word of the company name to avoid strict-matching failures
    # (e.g. "Jungheinrich UK Ltd" failing to find "Jungheinrich UK")
    # We use regex to split on spaces or hyphens so "Roth-uk" becomes just "Roth"
    search_query = re.split(r'[\s-]+', company_name)[0] if company_name else ""
    
    # Strip common suffixes that might be squashed into the name (e.g. "Wundagroup" -> "Wunda")
    search_query = re.sub(r'(?i)(group|ltd|uk|limited|automation)$', '', search_query)
    
    # If the remaining query is too short (e.g. someone named "Uk Ltd"), fall back to the original
    if len(search_query) < 2:
        search_query = re.split(r'[\s-]+', company_name)[0] if company_name else ""
    
    params = {
        "apiKey": api_key,
        "query": search_query,
        "pageSize": 25
    }
    
    import asyncio
    import random
    
    # Add a tiny random jitter to spread out requests
    await asyncio.sleep(random.uniform(0.1, 1.0))
    
    for attempt in range(3):
        try:
            # Use local asyncio lock to ensure rate limits are respected
            async with recruitly_api_lock:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if "totalCount" in data and data["totalCount"] > 0:
                    if "data" in data:
                        search_domain = website.replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0]
                        
                        for company_data in data["data"]:
                            db_website = company_data.get("website", "")
                            if db_website:
                                db_domain = db_website.replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0]
                                if db_domain.lower() == search_domain.lower():
                                    return (company_data.get("id"), company_data.get("reference"))
                                    
                        return None
            elif response.status_code == 429:
                # Rate limited, wait and retry
                await asyncio.sleep(2 * (attempt + 1))
                continue
                
            return None
            
        except Exception as e:
            if attempt == 2:
                print(f"Error checking Recruitly API after 3 attempts: {e}")
                return None
            await asyncio.sleep(1.0)
            
    return None

async def fetch_company_contacts(company_id: str) -> list:
    """
    Fetches all contacts associated with a specific company in Recruitly.
    Extracts name, job title, linkedin, reference, and generates a CRM direct link.
    """
    api_key = os.getenv("RECRUITLY_TOTACO_API_KEY")
    api_base_url = os.getenv("RECRUITLY_API_BASE_URL", "https://api.recruitly.io/api")
    app_base_url = os.getenv("RECRUITLY_APP_BASE_URL", "https://secure.recruitly.io")

    if not api_key:
        return []
        
    url = f"{api_base_url}/contact/search"
    params = {
        "apiKey": api_key,
        "query": f"companyId:{company_id}",
        "pageSize": 50
    }
    
    import asyncio
    import random
    
    await asyncio.sleep(random.uniform(0.1, 1.0))
    
    extracted_contacts = []
    
    for attempt in range(3):
        try:
            async with recruitly_api_lock:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(url, params=params)
                    
            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    # Concurrently fetch full profiles for all contacts to get the 'linkedIn' field
                    async def fetch_full_contact(client: httpx.AsyncClient, contact_id: str):
                        try:
                            full_res = await client.get(f"{api_base_url}/contact/{contact_id}", params={"apiKey": api_key})
                            if full_res.status_code == 200:
                                return full_res.json()
                        except Exception:
                            pass
                        return None

                    # Only fetch up to 20 contacts to avoid massive rate limits
                    lightweight_contacts = data["data"][:20]
                    
                    async with httpx.AsyncClient(timeout=15.0) as full_client:
                        tasks = [fetch_full_contact(full_client, c.get("id")) for c in lightweight_contacts if c.get("id")]
                        full_profiles = await asyncio.gather(*tasks)

                    for idx, contact in enumerate(lightweight_contacts):
                        full_profile = full_profiles[idx] or contact
                        
                        first_name = contact.get("firstName", "")
                        last_name = contact.get("surname", "")
                        full_name = f"{first_name} {last_name}".strip()
                        if not full_name:
                            full_name = contact.get("fullName", "")
                            
                        reference_id = contact.get("reference", "")
                        contact_id = contact.get("id", "")
                        
                        # Generate the direct clickable link to the CRM styled Web App
                        crm_url = f"{app_base_url}/company" if not contact_id else f"{app_base_url}/contact?id={contact_id}"
                        
                        # Extract Last Contacted
                        recent_activity = full_profile.get("recentActivity") or {}
                        last_contacted = recent_activity.get("lastContacted") or "Never"
                        
                        extracted_contacts.append({
                            "name": full_name,
                            "job_title": full_profile.get("jobTitle") or contact.get("jobTitle") or "",
                            "linkedin": full_profile.get("linkedIn") or "",
                            "reference_id": reference_id,
                            "crm_url": crm_url,
                            "last_contacted": last_contacted
                        })
                return extracted_contacts
                
            elif response.status_code == 429:
                await asyncio.sleep(2 * (attempt + 1))
                continue
                
            return extracted_contacts
            
        except Exception as e:
            if attempt == 2:
                print(f"Error fetching Recruitly Contacts after 3 attempts: {e}")
                return extracted_contacts
            await asyncio.sleep(1.0)
            
    return extracted_contacts
