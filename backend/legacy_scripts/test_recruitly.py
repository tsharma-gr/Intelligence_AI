import os
import requests
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()

# Get the API key you just added
API_KEY = os.getenv("RECRUITLY_TOTACO_API_KEY")

if not API_KEY:
    print("Error: RECRUITLY_TOTACO_API_KEY is not set in .env")
    exit(1)

# Endpoint to fetch a list of companies (limit 1) just to test connection
url = f"https://api.recruitly.io/api/company/list?apiKey={API_KEY}&pageSize=1"

print(f"Testing Recruitly API connection...")

try:
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print("\nSUCCESS! Connected to Recruitly Database.")
        
        # Try to print some sample data to prove it works
        if "data" in data and len(data["data"]) > 0:
            sample_company = data["data"][0]
            print(f"Sample Company Name: {sample_company.get('companyName')}")
            print(f"Sample Company ID: {sample_company.get('reference')}")
            print(f"Total Companies in Totaco Database: {data.get('totalElements', 'Unknown')}")
    else:
        print(f"\nFAILED! Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"\nError connecting: {str(e)}")
