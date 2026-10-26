"""Local SQLite database management for KnowYourClicks.

Zero cloud dependencies: all data stays strictly on local disk.
Stores aggregated frequency counts and privacy-cleared statistics only.
"""

import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from .config import DB_PATH


class Database:
    """Thread-safe SQLite database manager."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Database, cls).__new__(cls)
                cls._instance._init_db()
            return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH), timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes tables and seeds default shortcuts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Table for minute-level buckets (enables detailed 1-hour view)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keystroke_minutes (
                    minute_bucket TEXT NOT NULL,
                    key_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    press_count INTEGER DEFAULT 1,
                    PRIMARY KEY (minute_bucket, key_name)
                )
            """)

            # Table for hour-level buckets (enables efficient daily/weekly/monthly views)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keystroke_hourly (
                    hour_bucket TEXT NOT NULL,
                    key_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    press_count INTEGER DEFAULT 1,
                    PRIMARY KEY (hour_bucket, key_name)
                )
            """)

            # Table for custom user shortcuts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shortcuts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shortcut TEXT UNIQUE NOT NULL,
                    replacement TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Table for speed test history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS speed_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    spaces_count INTEGER NOT NULL,
                    punctuations_count INTEGER NOT NULL,
                    backspaces_count INTEGER NOT NULL,
                    total_allowed_keys INTEGER NOT NULL,
                    wpm REAL NOT NULL,
                    cpm REAL DEFAULT 0.0,
                    accuracy REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Seed initial shortcuts if table is empty
            cursor.execute("SELECT COUNT(*) FROM shortcuts")
            if cursor.fetchone()[0] == 0:
                initial_shortcuts = [
                    ("idk", "i dont know"),
                    ("brb", "be right back"),
                    ("omw", "on my way"),
                    ("btw", "by the way"),
                    ("ty", "thank you"),
                ]
                cursor.executemany(
                    "INSERT INTO shortcuts (shortcut, replacement) VALUES (?, ?)",
                    initial_shortcuts
                )

            conn.commit()

    def record_key_press(self, key_name: str, category: str):
        """Records a single whitelisted key press into minute and hour buckets."""
        now = datetime.now()
        minute_bucket = now.strftime("%Y-%m-%d %H:%M")
        hour_bucket = now.strftime("%Y-%m-%d %H:00")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Upsert into minute buckets
            cursor.execute("""
                INSERT INTO keystroke_minutes (minute_bucket, key_name, category, press_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(minute_bucket, key_name) DO UPDATE SET
                    press_count = press_count + 1
            """, (minute_bucket, key_name, category))

            # Upsert into hour buckets
            cursor.execute("""
                INSERT INTO keystroke_hourly (hour_bucket, key_name, category, press_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(hour_bucket, key_name) DO UPDATE SET
                    press_count = press_count + 1
            """, (hour_bucket, key_name, category))

            conn.commit()

    def get_shortcuts(self) -> List[Dict[str, Any]]:
        """Returns all registered shortcuts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, shortcut, replacement, created_at FROM shortcuts ORDER BY shortcut ASC")
            return [dict(row) for row in cursor.fetchall()]

    def add_shortcut(self, shortcut: str, replacement: str) -> bool:
        """Adds or updates a shortcut."""
        clean_sc = shortcut.strip().lower()
        clean_rep = replacement.strip()
        if not clean_sc or not clean_rep:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO shortcuts (shortcut, replacement)
                VALUES (?, ?)
                ON CONFLICT(shortcut) DO UPDATE SET
                    replacement = excluded.replacement
            """, (clean_sc, clean_rep))
            conn.commit()
            return True

    def delete_shortcut(self, shortcut_id: int) -> bool:
        """Deletes a shortcut by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM shortcuts WHERE id = ?", (shortcut_id,))
            conn.commit()
            return cursor.rowcount > 0

    def find_shortcut(self, shortcut: str) -> Optional[str]:
        """Looks up replacement for a given shortcut token."""
        clean_sc = shortcut.strip().lower()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT replacement FROM shortcuts WHERE shortcut = ?", (clean_sc,))
            row = cursor.fetchone()
            return row["replacement"] if row else None

    def record_speed_session(
        self,
        mode: str,
        duration: int,
        spaces: int,
        punctuations: int,
        backspaces: int,
        total_keys: int,
        wpm: float,
        cpm: float = 0.0,
        accuracy: Optional[float] = None
    ):
        """Saves a completed typing speed session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO speed_sessions (
                    mode, duration_seconds, spaces_count, punctuations_count,
                    backspaces_count, total_allowed_keys, wpm, cpm, accuracy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (mode, duration, spaces, punctuations, backspaces, total_keys, wpm, cpm, accuracy))
            conn.commit()

    def get_recent_speed_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns recent speed test records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, mode, duration_seconds, spaces_count, punctuations_count,
                       backspaces_count, total_allowed_keys, wpm, cpm, accuracy, timestamp
                FROM speed_sessions
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self, timeframe: str = "1h") -> Dict[str, Any]:
        """
        Calculates aggregated stats for specified timeframe:
        - '1h': past 60 minutes (minute-by-minute timeline)
        - '1d': past 24 hours (hourly timeline)
        - '1w': past 7 days (daily timeline)
        - '1m': past 30 days (daily timeline)
        - 'all': all-time recorded activity
        """
        now = datetime.now()

        if timeframe == "1h":
            start_time = now - timedelta(hours=1)
            bucket_col = "minute_bucket"
            table = "keystroke_minutes"
            time_filter = start_time.strftime("%Y-%m-%d %H:%M")
        elif timeframe == "1d":
            start_time = now - timedelta(days=1)
            bucket_col = "hour_bucket"
            table = "keystroke_hourly"
            time_filter = start_time.strftime("%Y-%m-%d %H:00")
        elif timeframe == "1w":
            start_time = now - timedelta(days=7)
            bucket_col = "SUBSTR(hour_bucket, 1, 10)"  # Date portion
            table = "keystroke_hourly"
            time_filter = start_time.strftime("%Y-%m-%d 00:00")
        elif timeframe == "1m":
            start_time = now - timedelta(days=30)
            bucket_col = "SUBSTR(hour_bucket, 1, 10)"  # Date portion
            table = "keystroke_hourly"
            time_filter = start_time.strftime("%Y-%m-%d 00:00")
        else:  # 'all'
            bucket_col = "SUBSTR(hour_bucket, 1, 7)"  # Month portion
            table = "keystroke_hourly"
            time_filter = "1970-01-01 00:00"

        time_col = "minute_bucket" if timeframe == "1h" else "hour_bucket"

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Total counts by category
            cursor.execute(f"""
                SELECT category, SUM(press_count) as total
                FROM {table}
                WHERE {time_col} >= ?
                GROUP BY category
            """, (time_filter,))
            category_totals = {"space": 0, "editing": 0, "punctuation": 0}
            for row in cursor.fetchall():
                category_totals[row["category"]] = row["total"] or 0

            # 2. Key-specific counts
            cursor.execute(f"""
                SELECT key_name, SUM(press_count) as total
                FROM {table}
                WHERE {time_col} >= ?
                GROUP BY key_name
                ORDER BY total DESC
            """, (time_filter,))
            key_counts = [dict(row) for row in cursor.fetchall()]

            # 3. Timeline for chart rendering
            cursor.execute(f"""
                SELECT {bucket_col} as period, SUM(press_count) as total,
                       SUM(CASE WHEN category = 'space' THEN press_count ELSE 0 END) as space_count,
                       SUM(CASE WHEN category = 'editing' THEN press_count ELSE 0 END) as edit_count,
                       SUM(CASE WHEN category = 'punctuation' THEN press_count ELSE 0 END) as punct_count
                FROM {table}
                WHERE {time_col} >= ?
                GROUP BY period
                ORDER BY period ASC
            """, (time_filter,))
            timeline = [dict(row) for row in cursor.fetchall()]

            total_keys = sum(category_totals.values())
            spaces = category_totals["space"]
            edits = category_totals["editing"]
            puncts = category_totals["punctuation"]
            correction_rate = round((edits / spaces * 100), 1) if spaces > 0 else 0.0

            return {
                "timeframe": timeframe,
                "total_keys": total_keys,
                "spaces": spaces,
                "edits": edits,
                "punctuations": puncts,
                "correction_rate": correction_rate,
                "category_totals": category_totals,
                "key_counts": key_counts,
                "timeline": timeline
            }
