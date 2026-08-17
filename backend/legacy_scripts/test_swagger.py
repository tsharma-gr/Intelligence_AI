import json
import urllib.request

try:
    req = urllib.request.Request(
        "https://api.recruitly.io/v3/api-docs", 
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        
        # Let's look at the Contact schema
        if "components" in data and "schemas" in data["components"]:
            schemas = data["components"]["schemas"]
            if "Contact" in schemas:
                print("--- CONTACT FIELDS ---")
                properties = schemas["Contact"].get("properties", {})
                for prop, details in properties.items():
                    print(f"- {prop}: {details.get('type', 'unknown')}")
            else:
                # Try finding something containing contact
                for k in schemas.keys():
                    if "Contact" in k:
                        print(f"Found schema: {k}")
        else:
            print("No schemas found")
except Exception as e:
    print(f"Error: {e}")
