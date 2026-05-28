"""
Database Module
"""
from typing import Optional
import sqlite3
from contextlib import contextmanager


class Database:
    """Simple SQLite database wrapper"""

    def __init__(self, path: str = "wolf.db"):
        self._path = path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_active REAL NOT NULL,
                    metadata TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    tool_call_id TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            # Add tool_calls/tool_call_id columns to existing table (safe if already exist)
            try:
                cursor.execute("ALTER TABLE messages ADD COLUMN tool_calls TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE messages ADD COLUMN tool_call_id TEXT")
            except sqlite3.OperationalError:
                pass
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    completed_at REAL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            conn.commit()

    @contextmanager
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()):
        """Execute INSERT/UPDATE/DELETE and commit"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

    def fetchone(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Execute SELECT and return one row as dict"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        """Execute SELECT and return all rows as list of dicts"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]


# Global database instance
_db: Optional[Database] = None


def get_database() -> Database:
    """Get global database instance"""
    global _db
    if _db is None:
        _db = Database()
    return _db