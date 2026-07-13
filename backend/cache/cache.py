import os
import sqlite3
import json
import logging
from typing import List, Optional
from datetime import datetime
from backend.crawler.models import CrawledPage

logger = logging.getLogger("company_intelligence.cache")

class DomainCache:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Place cache db in the current directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, "company_cache.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS domain_cache (
                    domain TEXT PRIMARY KEY,
                    crawled_at TEXT,
                    pages_json TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite cache database: {e}")

    def get(self, domain: str) -> Optional[List[CrawledPage]]:
        """Get cached pages for a domain if available."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT pages_json FROM domain_cache WHERE domain = ?", (domain,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                logger.info(f"Cache hit for domain: {domain}")
                pages_data = json.loads(row[0])
                return [CrawledPage(**p) for p in pages_data]
        except Exception as e:
            logger.error(f"Error reading from cache for domain '{domain}': {e}")
        return None

    def set(self, domain: str, pages: List[CrawledPage]):
        """Save crawled pages for a domain to the cache."""
        try:
            pages_data = [p.model_dump() for p in pages]
            pages_json = json.dumps(pages_data)
            crawled_at = datetime.utcnow().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO domain_cache (domain, crawled_at, pages_json) VALUES (?, ?, ?)",
                (domain, crawled_at, pages_json)
            )
            conn.commit()
            conn.close()
            logger.info(f"Cached crawled data for domain: {domain}")
        except Exception as e:
            logger.error(f"Error writing to cache for domain '{domain}': {e}")
