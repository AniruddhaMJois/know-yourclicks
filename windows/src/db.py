"""Local SQLite database management for KnowYourClicks (Windows).

Zero cloud dependencies: all data stays strictly on local disk at %LOCALAPPDATA%\\KnowYourClicks\\stats.db.
Stores aggregated frequency counts and privacy-cleared statistics only.
"""

import queue
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from .config import DB_PATH


class Database:
    """Thread-safe SQLite database manager for Windows with WAL mode and async batch writes."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Database, cls).__new__(cls)
                cls._instance._init_db()
            return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH), timeout=20.0)
        conn.row_factory = sqlite3.Row
        # Enable Write-Ahead Logging (WAL) and robust timeout to prevent database locks
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=10000;")
        except Exception:
            pass
        return conn

    def _init_db(self):
        """Initializes tables, seeds default shortcuts, and starts async write worker."""
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

        # In-memory batch write queue for lock-free, zero-latency keystroke recording
        self._write_queue: queue.Queue = queue.Queue(maxsize=50000)
        self._worker_running = True
        self._worker_thread = threading.Thread(target=self._batch_flusher_loop, daemon=True)
        self._worker_thread.start()

    def record_key_press(self, key_name: str, category: str):
        """
        Pushes a whitelisted key press to the non-blocking in-memory queue.
        Zero disk latency on caller thread; completely eliminates LowLevelHook lag.
        """
        now = datetime.now()
        minute_bucket = now.strftime("%Y-%m-%d %H:%M")
        hour_bucket = now.strftime("%Y-%m-%d %H:00")
        try:
            self._write_queue.put_nowait((minute_bucket, hour_bucket, key_name, category))
        except queue.Full:
            pass  # Avoid blocking if queue is saturated

    def flush(self):
        """Immediately flushes pending in-memory keystroke batch to SQLite."""
        batch = []
        while True:
            try:
                item = self._write_queue.get_nowait()
                batch.append(item)
            except queue.Empty:
                break

        if not batch:
            return

        self._write_batch_to_db(batch)

    def _batch_flusher_loop(self):
        """Background worker loop writing accumulated keystrokes in atomic batches."""
        while self._worker_running:
            try:
                # Block until at least one keystroke arrives (timeout 0.2s for clean shutdown)
                item = self._write_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            batch = [item]
            # Rapidly drain any remaining pending keystrokes
            while len(batch) < 250:
                try:
                    batch.append(self._write_queue.get_nowait())
                except queue.Empty:
                    break

            self._write_batch_to_db(batch)

    def _write_batch_to_db(self, batch: List[tuple]):
        """Persists a batch of keystrokes to SQLite inside a single atomic transaction."""
        if not batch:
            return

        # Aggregate counts by bucket and key
        minute_aggregates = {}
        hour_aggregates = {}

        for min_b, hr_b, k_name, cat in batch:
            m_key = (min_b, k_name, cat)
            minute_aggregates[m_key] = minute_aggregates.get(m_key, 0) + 1

            h_key = (hr_b, k_name, cat)
            hour_aggregates[h_key] = hour_aggregates.get(h_key, 0) + 1

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                for (min_b, k_name, cat), count in minute_aggregates.items():
                    cursor.execute("""
                        INSERT INTO keystroke_minutes (minute_bucket, key_name, category, press_count)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(minute_bucket, key_name) DO UPDATE SET
                            press_count = press_count + excluded.press_count
                    """, (min_b, k_name, cat, count))

                for (hr_b, k_name, cat), count in hour_aggregates.items():
                    cursor.execute("""
                        INSERT INTO keystroke_hourly (hour_bucket, key_name, category, press_count)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(hour_bucket, key_name) DO UPDATE SET
                            press_count = press_count + excluded.press_count
                    """, (hr_b, k_name, cat, count))

                conn.commit()
        except Exception:
            pass  # Retry on next cycle

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

    def get_recent_speed_sessions(self, limit: int = 15) -> List[Dict[str, Any]]:
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

    def close(self):
        """Stops the background flusher thread and commits any remaining keys."""
        self._worker_running = False
        try:
            self.flush()
        except Exception:
            pass

    def get_statistics(self, timeframe: str = "1h") -> Dict[str, Any]:
        """
        Calculates aggregated stats for specified timeframe:
        - '1h': past 60 minutes (minute-by-minute timeline)
        - '1d': past 24 hours (hourly timeline)
        - '1w': past 7 days (daily timeline)
        - '1m': past 30 days (daily timeline)
        - 'all': all-time recorded activity
        """
        # Ensure any buffered keystrokes are flushed before calculating statistics
        self.flush()

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
            category_totals = {"space": 0, "editing": 0, "punctuation": 0, "other": 0}
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

            # 3. Timeline for chart rendering (includes total of all keystrokes)
            cursor.execute(f"""
                SELECT {bucket_col} as period, SUM(press_count) as total,
                       SUM(CASE WHEN category = 'space' THEN press_count ELSE 0 END) as space_count,
                       SUM(CASE WHEN category = 'editing' THEN press_count ELSE 0 END) as edit_count,
                       SUM(CASE WHEN category = 'punctuation' THEN press_count ELSE 0 END) as punct_count,
                       SUM(CASE WHEN category = 'other' THEN press_count ELSE 0 END) as other_count
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
            other = category_totals["other"]
            # Correction rate: editing keys (backspace/delete) as a percentage of total keys
            correction_rate = round((edits / total_keys * 100), 1) if total_keys > 0 else 0.0

            return {
                "timeframe": timeframe,
                "total_keys": total_keys,
                "spaces": spaces,
                "edits": edits,
                "punctuations": puncts,
                "other": other,
                "correction_rate": correction_rate,
                "category_totals": category_totals,
                "key_counts": key_counts,
                "timeline": timeline
            }
