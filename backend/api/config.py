import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to the backend directory
_BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))

class Settings(BaseSettings):
    # API Keys
    serper_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    
    # Provider Settings
    llm_provider: str = "deepseek"  # "deepseek", "openai", "gemini"
    search_provider: str = "serper" # "serper", "google", "bing", "tavily"
    
    # Google Sheets Settings
    google_service_account_json: Optional[str] = None  # path to service account json file
    google_service_account_info: Optional[str] = None  # inline JSON string
    google_sheet_id: Optional[str] = None              # sheet id to use (creates one if blank)
    
    # Server configuration
    host: str = "127.0.0.1"
    port: int = 8000
    
    # Search Scale Configuration
    search_query_count: int = 5
    results_per_query: int = 30
    max_unique_companies: int = 100
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(_BACKEND_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def resolved_service_account_json(self) -> Optional[str]:
        """Resolve service account JSON path to absolute, relative to backend dir."""
        if not self.google_service_account_json:
            return None
        path = self.google_service_account_json
        if not os.path.isabs(path):
            path = os.path.join(_BACKEND_DIR, path)
        return path

settings = Settings()
