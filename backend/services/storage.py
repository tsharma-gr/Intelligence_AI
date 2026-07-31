import sqlite3
import json
import os
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("company_intelligence.storage")

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "company_intelligence.db")

# Ensure the backend/data directory exists
os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Base Interfaces (The Repository Pattern)
# ─────────────────────────────────────────────────────────────────────────────

class BaseResultStore(ABC):
    @abstractmethod
    async def save_company(self, job_id: str, company_data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def get_companies(self, job_id: str) -> List[Dict[str, Any]]:
        pass


class BaseCacheStore(ABC):
    @abstractmethod
    async def get_cached_domain(self, domain: str) -> Optional[List[Dict[str, Any]]]:
        pass

    @abstractmethod
    async def set_cached_domain(self, domain: str, pages_data: List[Dict[str, Any]]) -> None:
        pass


class BaseJobStore(ABC):
    @abstractmethod
    async def create_job(self, job_id: str, company_type: str, product: str, location: str) -> None:
        pass

    @abstractmethod
    async def update_job_status(self, job_id: str, status: str, metrics: Optional[Dict[str, Any]] = None) -> None:
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# 2. SQLite Implementations
# ─────────────────────────────────────────────────────────────────────────────

class SQLiteStorageInitializer:
    """Helper class to initialize SQLite database tables."""
    @staticmethod
    def initialize_db():
        logger.info(f"Initializing SQLite database at {_DB_PATH}")
        conn = sqlite3.connect(_DB_PATH)
        cursor = conn.cursor()
        
        # 1. Jobs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                company_type TEXT,
                product TEXT,
                location TEXT,
                status TEXT,
                created_at TEXT,
                finished_at TEXT,
                metrics TEXT
            )
        """)
        
        # 2. Results Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                company_name TEXT,
                website TEXT,
                address TEXT,
                phone TEXT,
                category TEXT,
                qualified INTEGER,
                confidence INTEGER,
                reason TEXT,
                evidence TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs (job_id)
            )
        """)
        
        # 3. Cache Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                domain TEXT PRIMARY KEY,
                pages TEXT,
                updated_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()


class SQLiteResultStore(BaseResultStore):
    async def save_company(self, job_id: str, company_data: Dict[str, Any]) -> None:
        loop = asyncio.get_event_loop()
        def _sync_save():
            conn = sqlite3.connect(_DB_PATH)
            cursor = conn.cursor()
            qual = company_data.get("qualification", {})
            cursor.execute("""
                INSERT INTO results (job_id, company_name, website, address, phone, category, qualified, confidence, reason, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                company_data.get("company_name"),
                company_data.get("website"),
                company_data.get("address"),
                company_data.get("phone"),
                company_data.get("category"),
                1 if qual.get("qualified") else 0,
                qual.get("confidence", 0),
                qual.get("reason", ""),
                json.dumps(qual.get("evidence", []))
            ))
            conn.commit()
            conn.close()
        await loop.run_in_executor(None, _sync_save)

    async def get_companies(self, job_id: str) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        def _sync_get():
            conn = sqlite3.connect(_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM results WHERE job_id = ?", (job_id,))
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                results.append({
                    "company_name": row["company_name"],
                    "website": row["website"],
                    "address": row["address"],
                    "phone": row["phone"],
                    "category": row["category"],
                    "qualification": {
                        "qualified": bool(row["qualified"]),
                        "confidence": row["confidence"],
                        "reason": row["reason"],
                        "evidence": json.loads(row["evidence"] or "[]")
                    }
                })
            return results
        return await loop.run_in_executor(None, _sync_get)


class SQLiteCacheStore(BaseCacheStore):
    async def get_cached_domain(self, domain: str) -> Optional[List[Dict[str, Any]]]:
        loop = asyncio.get_event_loop()
        def _sync_get():
            conn = sqlite3.connect(_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT pages FROM cache WHERE domain = ?", (domain,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
            return None
        return await loop.run_in_executor(None, _sync_get)

    async def set_cached_domain(self, domain: str, pages_data: List[Dict[str, Any]]) -> None:
        loop = asyncio.get_event_loop()
        def _sync_set():
            conn = sqlite3.connect(_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO cache (domain, pages, updated_at)
                VALUES (?, ?, ?)
            """, (domain, json.dumps(pages_data), datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
        await loop.run_in_executor(None, _sync_set)


class SQLiteJobStore(BaseJobStore):
    async def create_job(self, job_id: str, company_type: str, product: str, location: str) -> None:
        loop = asyncio.get_event_loop()
        def _sync_create():
            conn = sqlite3.connect(_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO jobs (job_id, company_type, product, location, status, created_at, finished_at, metrics)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                company_type,
                product,
                location,
                "pending",
                datetime.utcnow().isoformat(),
                None,
                json.dumps({})
            ))
            conn.commit()
            conn.close()
        await loop.run_in_executor(None, _sync_create)

    async def update_job_status(self, job_id: str, status: str, metrics: Optional[Dict[str, Any]] = None) -> None:
        loop = asyncio.get_event_loop()
        def _sync_update():
            conn = sqlite3.connect(_DB_PATH)
            cursor = conn.cursor()
            finished_at = datetime.utcnow().isoformat() if status in ("completed", "failed", "cancelled") else None
            
            if metrics:
                cursor.execute("""
                    UPDATE jobs SET status = ?, finished_at = ?, metrics = ? WHERE job_id = ?
                """, (status, finished_at, json.dumps(metrics), job_id))
            else:
                cursor.execute("""
                    UPDATE jobs SET status = ?, finished_at = ? WHERE job_id = ?
                """, (status, finished_at, job_id))
            conn.commit()
            conn.close()
        await loop.run_in_executor(None, _sync_update)

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        def _sync_get():
            conn = sqlite3.connect(_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "job_id": row["job_id"],
                    "company_type": row["company_type"],
                    "product": row["product"],
                    "location": row["location"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "finished_at": row["finished_at"],
                    "metrics": json.loads(row["metrics"] or "{}")
                }
            return None
        return await loop.run_in_executor(None, _sync_get)


# Initialize DB structures automatically upon load
import asyncio
SQLiteStorageInitializer.initialize_db()
