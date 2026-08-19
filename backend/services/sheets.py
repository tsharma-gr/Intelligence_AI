import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

from backend.api.config import settings
from backend.models.company import Company, SearchHistory

logger = logging.getLogger("company_intelligence.sheets")


class GoogleSheetsService:
    def __init__(self):
        self.creds = self._get_credentials()
        self.service = None
        if self.creds:
            try:
                self.service = build('sheets', 'v4', credentials=self.creds)
            except Exception as e:
                logger.error(f"Failed to build Google Sheets service client: {e}")
        else:
            logger.warning("No Google Sheets credentials provided. Running in LOCAL CSV/JSON fallback mode.")

    def _get_credentials(self) -> Optional[service_account.Credentials]:
        if settings.google_service_account_info:
            try:
                info = json.loads(settings.google_service_account_info)
                return service_account.Credentials.from_service_account_info(
                    info, scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            except Exception as e:
                logger.error(f"Failed to load credentials from GOOGLE_SERVICE_ACCOUNT_INFO: {e}")

        if settings.resolved_service_account_json:
            if os.path.exists(settings.resolved_service_account_json):
                try:
                    return service_account.Credentials.from_service_account_file(
                        settings.resolved_service_account_json,
                        scopes=['https://www.googleapis.com/auth/spreadsheets']
                    )
                except Exception as e:
                    logger.error(f"Failed to load service account file from path: {e}")
            else:
                logger.warning(f"Google service account file path not found: {settings.resolved_service_account_json}")
                
        return None

    def _create_spreadsheet(self) -> str:
        if not self.service:
            return ""
            
        try:
            spreadsheet_body = {
                'properties': {
                    'title': f"Lead Gen App Discoveries - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
                },
                'sheets': [
                    {'properties': {'title': 'Execution Summary'}},
                    {'properties': {'title': 'Search History'}},
                    {'properties': {'title': 'Qualified Companies'}},
                    {'properties': {'title': 'Disqualified Companies'}},
                    {'properties': {'title': 'Execution Logs'}}
                ]
            }
            request = self.service.spreadsheets().create(body=spreadsheet_body)
            response = request.execute()
            sheet_id = response.get('spreadsheetId')
            logger.info(f"Created new spreadsheet with ID: {sheet_id}")
            
            self._write_headers(sheet_id)
            return sheet_id
        except Exception as e:
            logger.error(f"Failed to create spreadsheet: {e}")
            return ""

    def _write_headers(self, sheet_id: str):
        headers = {
            "'Execution Summary'!A1:F1": [["Search Date", "Search ID", "Total Companies", "Qualified", "Disqualified", "Duration"]],
            "'Search History'!A1:E1": [["Search Date", "Search ID", "Company Type", "Product", "Location"]],
            "'Qualified Companies'!A1:L1": [["Search Date", "Search ID", "Company Name", "Website", "Address", "Phone", "Category", "Reason", "Evidence", "Source Page", "Confidence", "CRM Contacts"]],
            "'Disqualified Companies'!A1:G1": [["Search Date", "Search ID", "Company Name", "Website", "Reason", "Evidence", "Source Page"]],
            "'Execution Logs'!A1:F1": [["Search Date", "Search ID", "Finished", "Companies Processed", "Duration", "Errors"]]
        }
        
        for range_name, values in headers.items():
            body = {'values': values}
            self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body
            ).execute()

    def resolve_sheet_id(self) -> str:
        """Resolve sheet_id from config settings or create a new sheet."""
        if not self.service:
            return "local_fallback"
        sheet_id = settings.google_sheet_id or self._create_spreadsheet()
        return sheet_id or "local_fallback"

    def write_search_history(self, sheet_id: str, history: SearchHistory):
        """Streaming Stage: Save search history metadata to sheets."""
        if sheet_id == "local_fallback" or not self.service:
            return
        
        try:
            history_row = [[
                history.timestamp,
                history.search_id,
                history.company_type,
                history.product,
                history.location
            ]]
            self._append_row(sheet_id, "'Search History'!A:E", history_row)
        except Exception as e:
            logger.error(f"Failed to write history metadata to sheets: {e}")

    def append_companies_batch(self, sheet_id: str, history: SearchHistory, companies: List[Company]):
        """Streaming Stage: Append a batch of parsed and qualified companies."""
        if sheet_id == "local_fallback" or not self.service:
            # Local fallback handles everything at the end
            return

        qualified_rows = []
        disqualified_rows = []
        
        for c in companies:
            if not c.qualification:
                continue
                
            q = c.qualification
            evidence_text = "; ".join([e.quote for e in q.evidence]) if q.evidence else "None"
            source_pages = "; ".join([e.page for e in q.evidence]) if q.evidence else "None"
            
            if q.qualified:
                contacts_str = "None"
                if c.existing_contacts:
                    contacts_str = " | ".join([
                        f"{cnt.get('name', 'Unknown')} ({cnt.get('job_title', 'No Title')}) - Last Contacted: {cnt.get('last_contacted', 'Never')}" 
                        for cnt in c.existing_contacts
                    ])
                    
                qualified_rows.append([
                    history.timestamp,
                    history.search_id,
                    c.company_name,
                    c.website,
                    c.address or "N/A",
                    c.phone or "N/A",
                    c.category or "N/A",
                    q.reason,
                    evidence_text,
                    source_pages,
                    f"{q.confidence}%",
                    contacts_str
                ])
            else:
                disqualified_rows.append([
                    history.timestamp,
                    history.search_id,
                    c.company_name,
                    c.website,
                    q.reason,
                    evidence_text,
                    source_pages
                ])

        try:
            if qualified_rows:
                self._append_row(sheet_id, "'Qualified Companies'!A:K", qualified_rows)
            if disqualified_rows:
                self._append_row(sheet_id, "'Disqualified Companies'!A:G", disqualified_rows)
        except Exception as e:
            logger.error(f"Failed to write batch to sheets: {e}")

    def write_results_summary(self, sheet_id: str, history: SearchHistory, summary: Dict[str, Any]):
        """Streaming Stage: Final log write summarizing run metrics."""
        if sheet_id == "local_fallback" or not self.service:
            return

        try:
            summary_row = [[
                history.timestamp,
                history.search_id,
                summary.get("total_processed", 0),
                summary.get("qualified_count", 0),
                summary.get("disqualified_count", 0),
                summary.get("duration", "0s")
            ]]
            log_row = [[
                history.timestamp,
                history.search_id,
                summary.get("finished_at", ""),
                summary.get("total_processed", 0),
                summary.get("duration", "0s"),
                summary.get("errors", "")
            ]]
            
            self._append_row(sheet_id, "'Execution Summary'!A:F", summary_row)
            self._append_row(sheet_id, "'Execution Logs'!A:F", log_row)
        except Exception as e:
            logger.error(f"Failed to append final summary to sheets: {e}")

    def write_results(
        self,
        history: SearchHistory,
        companies: List[Company],
        summary: Dict[str, Any]
    ):
        """Main method (Backward compatible legacy API). Writes everything at the end."""
        sheet_id = self.resolve_sheet_id()
        if sheet_id == "local_fallback":
            self._write_to_local_fallback(history, companies, summary)
            return

        self.write_search_history(sheet_id, history)
        self.append_companies_batch(sheet_id, history, companies)
        self.write_results_summary(sheet_id, history, summary)

    def _append_row(self, sheet_id: str, range_name: str, values: List[List[Any]]):
        body = {'values': values}
        self.service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()

    def _write_to_local_fallback(
        self,
        history: SearchHistory,
        companies: List[Company],
        summary: Dict[str, Any]
    ):
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
        os.makedirs(data_dir, exist_ok=True)
        
        file_path = os.path.join(data_dir, f"search_{history.search_id}.json")
        payload = {
            "search_id": history.search_id,
            "metadata": history.model_dump(),
            "summary": summary,
            "companies": [c.model_dump() for c in companies]
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved results to local fallback file: {file_path}")
