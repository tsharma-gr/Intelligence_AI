import os
import sys
import csv
from dotenv import load_dotenv
from services.recruitly import check_company_exists

# Load environment variables
load_dotenv(".env")

# =========================================================
# PASTE YOUR LIST OF QUALIFIED COMPANIES HERE
# Format: {"name": "Company Name", "website": "Website URL"}
# =========================================================
COMPANIES_TO_TEST = [
    {"name": "Roth-uk", "website": "https://www.roth-uk.com/products/underfloor-heating"},
    {"name": "Grantuk", "website": "https://www.grantuk.com/products/underfloor-heating/"},
    {"name": "Wundagroup", "website": "https://www.wundagroup.com/"},
    {"name": "Heatmat", "website": "https://www.heatmat.co.uk/electric-underfloor-heating/"},
    {"name": "Uponor", "website": "https://www.uponor.com/en-gb/products/underfloor-heating-solutions"},
    {"name": "Ambienteufh", "website": "https://ambienteufh.co.uk/"},
    {"name": "Thermosphere", "website": "https://www.thermosphere.com/"},
    {"name": "Maincor", "website": "https://www.maincor.co.uk/underfloor-heating/"},
    {"name": "Itherme", "website": "https://itherme.com/"},
    {"name": "Flexel", "website": "https://flexel.co.uk/flexel-underfloor-heating/?srsltid=AfmBOoq3u2gNkzE4ilESQzZHWsv8NE3O9Joon_rzRinGl-AI1FJwDjC-"},
    {"name": "Devi", "website": "https://devi.com/uk/products/heating-cables"},
    {"name": "Pipelife", "website": "https://www.pipelife.co.uk/"},
    {"name": "Wavin", "website": "https://wavin.com/gb/c?category=C05"},
    {"name": "Magnumheating", "website": "https://www.magnumheating.co.uk/"},
    {"name": "Floorheating-direct", "website": "https://floorheating-direct.co.uk/products/in-screed-heating-cable-kits?srsltid=AfmBOorhyMf67ynJP4waK4eN1z0JQsIxFyDUQr5xEDLjNe1WowYSu7zW"},
    {"name": "Emmeti", "website": "https://emmeti.co.uk/"},
    {"name": "Horstad", "website": "https://horstad.com/product-category/underfloor-heating-pipe/"},
    {"name": "Sp-automation", "website": "https://sp-automation.co.uk/"},
    {"name": "Ckf", "website": "https://www.ckf.co.uk/"},
    {"name": "Rmgroupuk", "website": "https://www.rmgroupuk.com/robotics-automation/"},
    {"name": "Sewtec", "website": "https://www.sewtec.co.uk/application/industrial-robotics-automation/"},
    {"name": "Alsmechatronic", "website": "https://alsmechatronic.com/article/robotics-systems-integrators-in-manufacturing-automation/"},
    {"name": "Motiontech", "website": "https://www.motiontech.co.uk/custom-robotic-systems"},
    {"name": "Rnaautomation", "website": "https://www.rnaautomation.com/products/bespoke-automation/robotic-systems/robotic-systems-integration/"},
    {"name": "Riseautomation", "website": "https://www.riseautomation.co.uk/"},
    {"name": "Abb", "website": "https://www.abb.com/global/en/areas/robotics"},
    {"name": "Robomotion", "website": "https://www.robomotion.co.uk/"},
    {"name": "Solent-automation", "website": "https://www.solent-automation.uk/"},
    {"name": "Rollon", "website": "https://www.rollon.com/gbr/en/educationals/industrial-robotic-arm/"},
    {"name": "Shepherdsuk", "website": "https://shepherdsuk.com/"},
    {"name": "Geoplas", "website": "https://www.geoplas.co.uk/"},
    {"name": "Wavin", "website": "https://wavin.com/gb"},
    {"name": "Penrynplastics", "website": "https://www.penrynplastics.co.uk/"},
    {"name": "Nbp", "website": "https://www.nbp.co.uk/?srsltid=AfmBOopaoz9gRCFX8VI_Q3N_jaWCODGQgyDGu8ix2JfvKc0IY-RDcfzE"},
    {"name": "Palram", "website": "https://www.palram.com/uk/"},
    {"name": "Trulypvc", "website": "https://www.trulypvc.com/pages/brands"},
    {"name": "Plastic-buildingsupplies", "website": "https://www.plastic-buildingsupplies.co.uk/"},
    {"name": "Gap", "website": "https://www.gap.uk.com/"},
    {"name": "Rockwellbuildingplastics", "website": "https://www.rockwellbuildingplastics.co.uk/"},
    {"name": "Meridianbp", "website": "https://meridianbp.co.uk/"},
    {"name": "Totalplastic", "website": "https://www.totalplastic.co.uk/"},
    {"name": "Clearambershop", "website": "https://clearambershop.com/?srsltid=AfmBOop-gU94oyzmpMcqBE-ZAtmT6sdkNVVIQ70JVrcn9tfPWAASJivN"},
    {"name": "Masterbuildplastics", "website": "https://www.masterbuildplastics.co.uk/"},
    {"name": "Buildingplastics", "website": "https://www.buildingplastics.co.uk/"},
    {"name": "Gbplastics", "website": "https://www.gbplastics.co.uk/"},
    {"name": "Venturebp", "website": "https://www.venturebp.co.uk/"},
    {"name": "Quayplastics", "website": "https://www.quayplastics.co.uk/"},
    {"name": "Simplyplastics", "website": "https://www.simplyplastics.com/catalog/products-by-use/roofing/c-24/c-132"},
    {"name": "Plasticcentre", "website": "https://plasticcentre.co.uk/?srsltid=AfmBOop_mKko3z-TLDSMJU7Wo4L-61cZrsLFw-xUDrUCZKJx9EgeDxqB"},
    {"name": "Plasticexperts", "website": "https://plasticexperts.co.uk/"},
    {"name": "Varicoltd", "website": "https://www.varicoltd.com/"},
    {"name": "Trusealplastics", "website": "https://trusealplastics.co.uk/"},
    {"name": "Uplbuildingsupplies", "website": "https://uplbuildingsupplies.co.uk/building-plastics.html"},
    {"name": "Comcoplastics", "website": "https://www.comcoplastics.co.uk/"},
    {"name": "Plasticbuildingsupplies", "website": "https://www.plasticbuildingsupplies.com/"},
    {"name": "Directplastics", "website": "https://www.directplastics.com/"},
    {"name": "Polycarbonatex", "website": "https://polycarbonatex.co.uk/?srsltid=AfmBOoqUk15NHHUfvT_kCFudXYydqOD6Rt1UR1Z6T844BY3YzZrx9Awq"},
    {"name": "Theglazingshop", "website": "https://www.theglazingshop.co.uk/product-range/polycarbonate-sheets/polycarbonate-sheets.html?srsltid=AfmBOopqS0DikydGygsjeGhTQlQmRKbBhZsdWQhO49PsaDr0C8YiaCIq"},
    {"name": "Directcladding", "website": "https://directcladding.com/"},
    {"name": "Thepolycarbonateroofing", "website": "https://www.thepolycarbonateroofing.co.uk/?srsltid=AfmBOoqowKZc4LVvCIFqf_i_I23O-mqpk4qCBu1N-Galjgn67RRZ44gp"},
    {"name": "Rhnuttall", "website": "https://www.rhnuttall.co.uk/polycarbonate-sheet-suppliers/"},
    {"name": "Livsupplies", "website": "https://livsupplies.co.uk/"},
    {"name": "Longeatonbuildingplastics", "website": "https://longeatonbuildingplastics.co.uk/"},
    {"name": "Wickes", "website": "https://www.wickes.co.uk/Products/Building-Materials/Roofing/Polycarbonate-Sheets/c/1000251"},
    {"name": "Plasticssouthwest", "website": "https://plasticssouthwest.co.uk/"},
    {"name": "Newplas", "website": "https://newplas.co.uk/"},
    {"name": "Polycarbonatesheets", "website": "https://www.polycarbonatesheets.co.uk/"},
    {"name": "Home-is", "website": "https://home-is.co.uk/?srsltid=AfmBOor1fLIONW--AOKcDqXZBVyG6CrUyloc67bAjmNHvVEgtdPWI92K"},
    {"name": "Ppwgroup", "website": "https://www.ppwgroup.co.uk/"},
    {"name": "Claddingwarehouse", "website": "https://www.claddingwarehouse.co.uk/?srsltid=AfmBOooyDRyai7JIpld_iYB-27MB94edhnm9F6iiaExwVKqiTFoeTQ2Y"},
    {"name": "Wilplas", "website": "https://www.wilplas.com/"},
    {"name": "Tamstar", "website": "https://tamstar.co.uk/category/plastic-sheets/polycarbonate-sheets/"},
    {"name": "Pvcbuildingproducts", "website": "https://www.pvcbuildingproducts.co.uk/"},
    {"name": "Homebuildingplastics", "website": "https://www.homebuildingplastics.co.uk/"},
    {"name": "Trademouldings", "website": "https://trademouldings.com/kbb-2026-birmingham/"},
    {"name": "Watsonmanufacturing", "website": "https://watsonmanufacturing.co.uk/sectors/kitchens-bedrooms-bathrooms/"},
    {"name": "Camco", "website": "https://camco.uk/industries/"},
    {"name": "Fkandb", "website": "https://www.fkandb.co.uk/the-benefits-of-buying-direct-from-the-manufacturer/"},
    {"name": "Symphony-group", "website": "https://symphony-group.co.uk/"}
]

def main():
    print(f"Testing {len(COMPANIES_TO_TEST)} companies against Recruitly CRM...")
    
    results = []
    
    companies = COMPANIES_TO_TEST
    
    for company in companies:
        name = company["name"]
        website = company["website"]
        cy_id = await check_company_exists(name, website)
        
        results.append({
            "Company Name": name,
            "Website": website,
            "CY-ID": cy_id or "Add Company"
        })
        
        print(f"{name} -> {cy_id or 'Add Company'}")

    # Output to CSV to verify
    df = pd.DataFrame(results)
    df.to_csv("crm_test_results.csv", index=False)
    print("\nSaved to crm_test_results.csv")
        
    print("\n" + "="*50)
    print("You can open this CSV file and manually check the IDs in your Recruitly CRM to confirm.")

if __name__ == "__main__":
    main()
