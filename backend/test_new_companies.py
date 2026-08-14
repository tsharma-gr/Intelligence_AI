import os
import sys
import pandas as pd
import asyncio
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))
from backend.services.recruitly import check_company_exists

companies = [
    ("VoyageX AI", "https://voyagex.ai/marine-fleet-management-software-guide/"),
    ("PRIME Marine", "https://www.primemarine.com/about-maritime-software/"),
    ("NOZZLE", "https://nozzlesoft.com/blog/best-ship-management-software-for-fleet-operators-in-2026/"),
    ("Napa Ltd", "https://www.napa.fi/software-and-services/ship-operations/napa-fleet-intelligence/"),
    ("BMT Group Ltd", "https://www.bmt.org/innovations/digital-twins/"),
    ("Arribatec Marine", "https://marine.arribatec.com/infoship-suite-fleet-asset-management/cms/"),
    ("AST Networks", "https://ast-networks.com/insights/blog/maritime-software-solutions/"),
    ("Hanseaticsoft GmbH (Cloud Fleet Manager)", "https://cloudfleetmanager.com/"),
    ("OneOcean", "https://www.oneocean.com/how-we-help/tsm/cloud-fleet-manager"),
    ("AST Reygar Ltd", "https://ast-reygar.com/maritime-fleet-management-system/")
]

async def main():
    results = []
    for name, url in companies:
        print(f"Checking {name}...")
        cy_id = await check_company_exists(name, url)
        print(f"  -> {cy_id or 'Add Company'}")
        results.append({"Company Name": name, "Website": url, "CY-ID": cy_id or "Add Company"})

    df = pd.DataFrame(results)
    output_path = os.path.join(os.getcwd(), "backend", "crm_test_results_2.csv")
    df.to_csv(output_path, index=False)
    print(f"\nResults saved to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
