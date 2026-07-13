from pydantic import BaseModel

class CrawledPage(BaseModel):
    url: str
    page_type: str  # e.g., 'home', 'about', 'products', 'services', 'solutions', 'contact'
    content: str
