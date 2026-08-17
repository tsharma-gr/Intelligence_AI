from dotenv import load_dotenv
load_dotenv()

from services.recruitly import check_company_exists

# Test with a company we know probably exists in the database
test_website = "2cl.co.uk"
print(f"Testing Recruitly API for website: {test_website}")

cy_id = check_company_exists(test_website)

if cy_id:
    print(f"SUCCESS Condition A: Company exists! Returned ID: {cy_id}")
else:
    print(f"SUCCESS Condition B: Fresh Company! (Returned None - Display 'Add Company' button)")
