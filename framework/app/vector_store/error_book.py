"""
Error Book — Retrieval error persistence + two-stage self-correction
Inspired by LLM-Wiki (Tencent, arXiv:2605.25480)

Stage 1: Rule-based deterministic fixes (spelling, synonyms, aliases)
Stage 2: LLM-driven pattern analysis for recurring failure modes
"""
import os
import json
import sqlite3
import time
from typing import List, Dict, Optional
from datetime import datetime


class ErrorBook:
    """
    SQLite-backed retrieval error tracker with auto-correction.
    Tracks failed queries, applies fixes, prevents repeating mistakes.
    """

    def __init__(self, db_path: str = None):
        db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "wolf_data", "error_book.db"
        )
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_tables()

        # Stage 1: known corrections (self-learning dictionary)
        self._corrections: Dict[str, str] = {}
        self._synonyms: Dict[str, List[str]] = {}
        self._load_corrections()

    def _init_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS retrieval_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                error_type TEXT NOT NULL,
                context TEXT,
                attempted_at TEXT NOT NULL,
                resolved INTEGER DEFAULT 0,
                resolution TEXT,
                resolution_stage TEXT
            );
            CREATE TABLE IF NOT EXISTS corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wrong_term TEXT UNIQUE NOT NULL,
                correct_term TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                usage_count INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS synonyms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT NOT NULL,
                synonym TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                created_at TEXT NOT NULL,
                UNIQUE(term, synonym)
            );
            CREATE TABLE IF NOT EXISTS error_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                error_type TEXT,
                frequency INTEGER DEFAULT 1,
                last_seen TEXT NOT NULL,
                fix_suggestion TEXT
            );
        """)
        self._conn.commit()

    # ---- Stage 1: Rule-based correction ----

    def _load_corrections(self):
        """Load learned corrections from DB"""
        try:
            rows = self._conn.execute(
                "SELECT wrong_term, correct_term FROM corrections WHERE confidence >= 0.3"
            ).fetchall()
            for row in rows:
                self._corrections[row["wrong_term"].lower()] = row["correct_term"]
        except Exception:
            pass

        try:
            rows = self._conn.execute("SELECT term, synonym FROM synonyms").fetchall()
            for row in rows:
                term = row["term"].lower()
                if term not in self._synonyms:
                    self._synonyms[term] = []
                self._synonyms[term].append(row["synonym"].lower())
        except Exception:
            pass

    def correct_query(self, query: str) -> str:
        """Apply known corrections to a query (Stage 1)"""
        corrected = query

        # Apply learned corrections
        for wrong, correct in self._corrections.items():
            if wrong in corrected.lower():
                corrected = corrected.replace(wrong, correct)

        # Expand with synonyms (add alternative terms)
        for term, syns in self._synonyms.items():
            if term in corrected.lower():
                for syn in syns:
                    if syn not in corrected.lower():
                        corrected += f" {syn}"

        return corrected

    # ---- Error recording ----

    def record_error(self, query: str, error_type: str,
                     context: str = "", attempt_auto_fix: bool = True) -> int:
        """Record a retrieval failure"""
        now = datetime.now().isoformat()
        cursor = self._conn.execute(
            "INSERT INTO retrieval_errors (query, error_type, context, attempted_at) VALUES (?, ?, ?, ?)",
            (query, error_type, context[:500], now)
        )
        self._conn.commit()
        error_id = cursor.lastrowid

        # Auto-fix attempt (Stage 1)
        if attempt_auto_fix and error_type in ("no_results", "low_relevance"):
            fix = self._attempt_fix(query, error_type)
            if fix:
                self._conn.execute(
                    "UPDATE retrieval_errors SET resolved=1, resolution=?, resolution_stage='stage1_auto' WHERE id=?",
                    (fix, error_id)
                )
                self._conn.commit()

        # Update error patterns
        self._update_patterns(query, error_type)

        return error_id

    def _attempt_fix(self, query: str, error_type: str) -> Optional[str]:
        """Stage 1 auto-fix: try corrections and synonyms"""
        corrected = self.correct_query(query)
        if corrected != query:
            return f"Query corrected: '{query}' → '{corrected}'"

        if error_type == "no_results":
            # Broaden the query by removing specific terms
            words = query.split()
            if len(words) > 3:
                broader = ' '.join(words[:len(words)//2])
                return f"Query broadened: '{query}' → '{broader}'"

        return None

    def _update_patterns(self, query: str, error_type: str):
        """Track recurring error patterns"""
        now = datetime.now().isoformat()
        # Simple pattern: extract key terms from query
        pattern = ' '.join(query.lower().split()[:5])
        existing = self._conn.execute(
            "SELECT id, frequency FROM error_patterns WHERE pattern=? AND error_type=?",
            (pattern, error_type)
        ).fetchone()

        if existing:
            self._conn.execute(
                "UPDATE error_patterns SET frequency=?, last_seen=? WHERE id=?",
                (existing["frequency"] + 1, now, existing["id"])
            )
        else:
            self._conn.execute(
                "INSERT INTO error_patterns (pattern, error_type, frequency, last_seen) VALUES (?, ?, 1, ?)",
                (pattern, error_type, now)
            )
        self._conn.commit()

    # ---- Stage 2: LLM-driven pattern analysis ----

    def get_recurring_patterns(self, min_frequency: int = 3) -> List[Dict]:
        """Get error patterns that repeat frequently (for LLM analysis)"""
        rows = self._conn.execute(
            "SELECT * FROM error_patterns WHERE frequency >= ? ORDER BY frequency DESC LIMIT 20",
            (min_frequency,)
        ).fetchall()
        return [dict(r) for r in rows]

    def analyze_patterns_with_llm(self, llm_client=None) -> Dict:
        """
        Stage 2: Use LLM to analyze recurring error patterns and suggest fixes.
        Returns analysis results with suggested corrections.
        """
        patterns = self.get_recurring_patterns(min_frequency=2)
        if not patterns:
            return {"patterns_found": 0, "suggestions": []}

        if llm_client:
            return self._llm_analyze(patterns, llm_client)

        # Without LLM, do basic frequency analysis
        suggestions = []
        for p in patterns:
            if p["frequency"] >= 5:
                suggestions.append({
                    "pattern": p["pattern"],
                    "error_type": p["error_type"],
                    "frequency": p["frequency"],
                    "suggestion": f"Consider adding synonyms or aliases for: {p['pattern']}"
                })

        return {"patterns_found": len(patterns), "suggestions": suggestions}

    def _llm_analyze(self, patterns: List[Dict], llm_client) -> Dict:
        """LLM-driven error pattern analysis"""
        pattern_text = "\n".join(
            f"- Query pattern: '{p['pattern']}' | Error: {p['error_type']} | Frequency: {p['frequency']}x"
            for p in patterns
        )
        prompt = (
            "Analyze these recurring retrieval error patterns and suggest corrections:\n\n"
            f"{pattern_text}\n\n"
            "For each pattern, suggest: (1) The likely root cause, "
            "(2) A specific correction (synonym, alias, or query rewriting rule), "
            "(3) A confidence score (0.0-1.0).\n\n"
            "Output in JSON format: [{\"pattern\": \"...\", \"root_cause\": \"...\", "
            "\"correction\": \"...\", \"confidence\": 0.X}]"
        )
        try:
            import asyncio
            response = asyncio.get_event_loop().run_until_complete(
                llm_client.complete(prompt)
            )
            suggestions = json.loads(response) if isinstance(response, str) else response

            # Apply suggested corrections to the DB
            for s in suggestions:
                if s.get("confidence", 0) >= 0.5:
                    wrong = s["pattern"]
                    correct = s.get("correction", "")
                    self.add_correction(wrong, correct, s.get("confidence", 0.5))
                    self._corrections[wrong.lower()] = correct

            return {"patterns_found": len(patterns), "suggestions": suggestions,
                    "corrections_applied": len([s for s in suggestions if s.get("confidence", 0) >= 0.5])}
        except Exception:
            return {"patterns_found": len(patterns), "suggestions": [],
                    "error": "LLM analysis failed, using basic patterns only"}

    # ---- Correction management ----

    def add_correction(self, wrong_term: str, correct_term: str, confidence: float = 0.5):
        """Add or update a correction rule"""
        now = datetime.now().isoformat()
        self._conn.execute(
            """INSERT INTO corrections (wrong_term, correct_term, confidence, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(wrong_term) DO UPDATE SET
               correct_term=excluded.correct_term,
               confidence=(confidence * usage_count + excluded.confidence) / (usage_count + 1),
               usage_count=usage_count + 1""",
            (wrong_term.lower(), correct_term, confidence, now)
        )
        self._conn.commit()
        self._corrections[wrong_term.lower()] = correct_term

    def add_synonym(self, term: str, synonym: str):
        """Add a synonym pair"""
        now = datetime.now().isoformat()
        try:
            self._conn.execute(
                "INSERT INTO synonyms (term, synonym, created_at) VALUES (?, ?, ?)",
                (term.lower(), synonym.lower(), now)
            )
            self._conn.commit()
            if term.lower() not in self._synonyms:
                self._synonyms[term.lower()] = []
            self._synonyms[term.lower()].append(synonym.lower())
        except sqlite3.IntegrityError:
            pass  # Already exists

    # ---- Stats ----

    @property
    def stats(self) -> dict:
        total_errors = self._conn.execute("SELECT COUNT(*) as c FROM retrieval_errors").fetchone()["c"]
        resolved = self._conn.execute(
            "SELECT COUNT(*) as c FROM retrieval_errors WHERE resolved=1"
        ).fetchone()["c"]
        patterns = self._conn.execute("SELECT COUNT(*) as c FROM error_patterns").fetchone()["c"]
        corrections = self._conn.execute("SELECT COUNT(*) as c FROM corrections").fetchone()["c"]

        return {
            "total_errors": total_errors,
            "resolved": resolved,
            "resolution_rate": round(resolved / max(total_errors, 1) * 100, 1),
            "error_patterns": patterns,
            "active_corrections": corrections,
            "synonyms": len(self._synonyms)
        }

    def get_recent_errors(self, limit: int = 20) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT * FROM retrieval_errors ORDER BY attempted_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


_error_book: Optional[ErrorBook] = None


def get_error_book(db_path: str = None) -> ErrorBook:
    global _error_book
    if _error_book is None:
        _error_book = ErrorBook(db_path)
    return _error_book
