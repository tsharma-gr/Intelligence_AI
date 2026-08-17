import os
import sys
import logging

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.sheets import GoogleSheetsService
from backend.api.config import settings

logging.basicConfig(level=logging.INFO)

def setup_sheet():
    svc = GoogleSheetsService()
    if not svc.service:
        print("Failed to initialize Google Sheets service.")
        return
        
    sheet_id = settings.google_sheet_id
    if not sheet_id:
        print("No sheet id")
        return
        
    # Create the required tabs
    tabs = [
        'Execution Summary',
        'Search History',
        'Qualified Companies',
        'Disqualified Companies',
        'Execution Logs'
    ]
    
    # 1. Add sheets
    requests = []
    for tab in tabs:
        requests.append({
            'addSheet': {
                'properties': {
                    'title': tab
                }
            }
        })
        
    try:
        svc.service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={'requests': requests}
        ).execute()
        print("Successfully created tabs!")
    except Exception as e:
        print(f"Tabs might already exist: {e}")
        
    # 2. Write headers
    print("Writing headers...")
    svc._write_headers(sheet_id)
    print("Google Sheet fully initialized!")

if __name__ == "__main__":
    setup_sheet()
