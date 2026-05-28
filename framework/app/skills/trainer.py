"""Skill 自动训练器 — TextualLR + 轨迹缓冲"""
from typing import List, Optional
import sqlite3
import json
import os
from datetime import datetime


class SkillTrainer:
    """基于执行轨迹的 Skill 训练器"""

    def __init__(self, db_path: str = None):
        self._db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "wolf_data", "skill_training.db"
        )
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trajectories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    tokens_used INTEGER,
                    error TEXT,
                    timestamp TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    content TEXT NOT NULL,
                    score REAL DEFAULT 0,
                    timestamp TEXT DEFAULT (datetime('now'))
                )
            """)

    def record(self, skill_name: str, success: bool, tokens_used: int = 0, error: str = ""):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO trajectories (skill_name, success, tokens_used, error) VALUES (?, ?, ?, ?)",
                (skill_name, int(success), tokens_used, error)
            )

    def get_stats(self, skill_name: str, limit: int = 100) -> dict:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT success, tokens_used FROM trajectories WHERE skill_name=? ORDER BY id DESC LIMIT ?",
                (skill_name, limit)
            ).fetchall()
            if not rows:
                return {"success_rate": 1.0, "avg_tokens": 0, "samples": 0}
            successes = sum(r[0] for r in rows)
            avg_tokens = sum(r[1] for r in rows) / len(rows) if rows else 0
            return {
                "success_rate": round(successes / len(rows), 3),
                "avg_tokens": round(avg_tokens, 1),
                "samples": len(rows)
            }

    def save_version(self, skill_name: str, version: str, content: str, score: float = 0.0):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO versions (skill_name, version, content, score) VALUES (?, ?, ?, ?)",
                (skill_name, version, content, score)
            )

    def get_versions(self, skill_name: str) -> list:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT version, score, timestamp FROM versions WHERE skill_name=? ORDER BY id DESC",
                (skill_name,)
            ).fetchall()
            return [{"version": r[0], "score": r[1], "timestamp": r[2]} for r in rows]
