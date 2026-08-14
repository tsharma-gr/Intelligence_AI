import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Initialize Firebase Admin SDK
def get_db():
    try:
        # Check if already initialized to prevent errors
        firebase_admin.get_app()
    except ValueError:
        # Not initialized yet
        service_account_path = os.path.join(os.path.dirname(__file__), "..", "firebase-service-account.json")
        if os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        else:
            print(f"Warning: Firebase service account key not found at {service_account_path}")
            return None
            
    return firestore.client()

def save_qualified_company(company_data: dict):
    """Saves a highly qualified lead to the qualified_companies collection"""
    db = get_db()
    if not db: return
    
    # Drop the verbose evidence field to keep database lean
    if "qualification" in company_data and "evidence" in company_data["qualification"]:
        del company_data["qualification"]["evidence"]
    
    # Add timestamp
    company_data["created_at"] = datetime.utcnow().isoformat()
    
    # Create a readable Document ID from the company name (replacing slashes which break Firestore paths)
    doc_id = company_data.get("company_name", "").strip().replace("/", "-")
    
    if doc_id:
        doc_ref = db.collection("qualified_companies").document(doc_id)
    else:
        doc_ref = db.collection("qualified_companies").document()
        
    doc_ref.set(company_data)
    return doc_ref.id

def save_disqualified_company(company_data: dict):
    """Saves a rejected company to disqualified_companies collection (auto-deletes after 30 days)"""
    db = get_db()
    if not db: return
    
    if "qualification" in company_data and "evidence" in company_data["qualification"]:
        del company_data["qualification"]["evidence"]
        
    company_data["created_at"] = datetime.utcnow().isoformat()
    
    doc_id = company_data.get("company_name", "").strip().replace("/", "-")
    if doc_id:
        db.collection("disqualified_companies").document(doc_id).set(company_data)
    else:
        db.collection("disqualified_companies").add(company_data)

def save_search_history(search_id: str, criteria: dict, summary: dict):
    """Saves the search parameters and the execution summary as one merged document"""
    db = get_db()
    if not db: return
    
    history_doc = {
        "search_id": search_id,
        "timestamp": datetime.utcnow().isoformat(),
        "criteria": criteria,
        "summary": summary
    }
    
    # Create a highly readable Document ID: "YYYY-MM-DD - Product in Location"
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    product = criteria.get("product_or_service", "Unknown").replace("/", "-")
    location = criteria.get("location", "Unknown").replace("/", "-")
    
    # Example: "2026-08-11 - Underfloor Heating in UK"
    readable_id = f"{date_str} - {product} in {location}"
    
    # Use the readable ID for the document
    db.collection("search_history").document(readable_id).set(history_doc)
