from typing import List, Optional
from pydantic import BaseModel, Field

class SearchResult(BaseModel):
    company_name: str
    website: str
    title: str
    snippet: str

class Page(BaseModel):
    url: str
    page_type: str  # 'home', 'about', 'products', 'services', 'solutions', 'contact', etc.
    content: str

class Evidence(BaseModel):
    page: str
    quote: str

class Qualification(BaseModel):
    qualified: bool
    reason: str
    confidence: int = Field(..., ge=0, le=100)
    evidence: List[Evidence] = []

class Company(BaseModel):
    company_name: str
    website: str
    address: Optional[str] = None
    phone: Optional[str] = None
    category: Optional[str] = None
    qualification: Optional[Qualification] = None

class SearchHistory(BaseModel):
    search_id: str
    company_type: str
    product: str
    location: str
    timestamp: str
