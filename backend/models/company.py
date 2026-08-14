from typing import List, Optional
from pydantic import BaseModel, Field

class SearchResult(BaseModel):
    company_name: str
    website: str
    title: str
    snippet: str
    is_blocked: bool = False
    bypass_used: Optional[str] = None

class Page(BaseModel):
    url: str
    page_type: str  # 'home', 'about', 'products', 'services', 'solutions', 'contact', etc.
    content: str

class Qualification(BaseModel):
    qualified: bool
    is_blocked: bool = False
    reason: str
    confidence: int = Field(..., ge=0, le=100)
    corrected_company_name: Optional[str] = None
    official_website: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None

class Company(BaseModel):
    company_name: str
    website: str
    address: Optional[str] = None
    phone: Optional[str] = None
    category: Optional[str] = None
    qualification: Optional[Qualification] = None
    is_blocked: bool = False
    bypass_used: Optional[str] = None

class SearchHistory(BaseModel):
    search_id: str
    company_type: str
    product: str
    location: str
    timestamp: str
