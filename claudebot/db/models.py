# .claudebot/db/models.py
"""SQLite database models"""

import aiosqlite
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from ..api.enums import TaskType, TaskStatus

class Task(BaseModel):
    id: str
    type: TaskType
    status: TaskStatus
    description: str
    repo_path: str
    branch: Optional[str] = None
    files: str = "[]"  # JSON array
    result: Optional[str] = None  # JSON object
    error: Optional[str] = None
    logs: str = "[]"  # JSON array
    priority: int = 0
    max_retries: int = 3
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

DB_PATH = ".claudebot/tasks.db"

async def init_db():
    """Initialize database schema"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                status TEXT NOT NULL,
                description TEXT NOT NULL,
                repo_path TEXT NOT NULL,
                branch TEXT,
                files TEXT DEFAULT '[]',
                result TEXT,
                error TEXT,
                logs TEXT DEFAULT '[]',
                priority INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)
        """)
        await db.commit()

async def get_db():
    """Get database connection"""
    return aiosqlite.connect(DB_PATH)
