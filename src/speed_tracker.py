"""Speed tracker engine for on-demand typing speed measurement on Windows.

Supports:
- Timer durations: 30, 60, 90, 120 seconds
- Mode 1: Given Text (Interactive in-app typing test)
- Mode 2: Background (Passive cadence measurement across all Windows apps)
- Zero cloud storage: results are saved to local SQLite
- Windows Toast / PowerShell notifications
"""

import time
import subprocess
import threading
from typing import Optional, Dict, Any, List
from .db import Database

# Sample prompt texts for "Try with given text" mode
GIVEN_TEXT_PROMPTS = [
    "The quick brown fox jumps over the lazy dog. Programming requires patience, logic, and consistent attention to detail.",
    "Clean code always looks like it was written by someone who cares. Simple things should be simple and complex things should be possible.",
    "Technology is best when it brings people together without compromising their privacy or ownership over their personal data.",
    "In the middle of difficulty lies opportunity. Keep typing steadily and focus on accuracy rather than pure rushing speed."
]


class SpeedTracker:
    """Manages on-demand typing speed sessions."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SpeedTracker, cls).__new__(cls)
                cls._instance._init_tracker()
            return cls._instance

    def _init_tracker(self):
        self.db = Database()
        self.active_session: Optional[Dict[str, Any]] = None
        self._timer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def get_sample_prompts(self) -> List[str]:
        return GIVEN_TEXT_PROMPTS

    def start_session(self, mode: str, duration_seconds: int) -> Dict[str, Any]:
        """
        Starts a timed typing speed session.
        duration_seconds must be in [30, 60, 90, 120].
        mode must be 'given_text' or 'background'.
        """
        if duration_seconds not in (30, 60, 90, 120):
            duration_seconds = 60

        with self._lock:
            self._stop_event.set()
            if self._timer_thread and self._timer_thread.is_alive():
                self._timer_thread.join(timeout=1.0)
            self._stop_event.clear()

            self.active_session = {
                "mode": mode,
                "duration": duration_seconds,
                "start_time": time.time(),
                "end_time": time.time() + duration_seconds,
                "spaces": 0,
                "punctuations": 0,
                "backspaces": 0,
                "total_keys": 0,
                "completed": False,
                "result": None
            }

            if mode == "background":
                self._timer_thread = threading.Thread(
                    target=self._run_background_timer,
                    args=(duration_seconds,),
                    daemon=True
                )
                self._timer_thread.start()

            return self.get_status()

    def record_key(self, key_name: str, category: str):
        """Accumulates keystrokes if a speed session is active."""
        with self._lock:
            if not self.active_session or self.active_session.get("completed"):
                return

            if time.time() > self.active_session["end_time"]:
                self._finish_session()
                return

            self.active_session["total_keys"] += 1
            if category == "space":
                self.active_session["spaces"] += 1
            elif category == "punctuation":
                self.active_session["punctuations"] += 1
            elif category == "editing":
                self.active_session["backspaces"] += 1

    def _run_background_timer(self, duration: int):
        """Timer loop for passive background tracking."""
        start = time.time()
        while not self._stop_event.is_set():
            remaining = (start + duration) - time.time()
            if remaining <= 0:
                with self._lock:
                    self._finish_session()
                break
            time.sleep(0.5)

    def _finish_session(self):
        """Finalizes the active session, saves to SQLite, and notifies user."""
        if not self.active_session or self.active_session.get("completed"):
            return

        session = self.active_session
        session["completed"] = True
        duration = session["duration"]
        elapsed_min = duration / 60.0

        # Background mode cadence WPM calculation:
        # Words are defined by completed spacebars and punctuation delimiters
        words_counted = session["spaces"] + session["punctuations"]
        wpm = round(words_counted / elapsed_min, 1) if elapsed_min > 0 else 0.0
        cpm = round(session["total_keys"] / elapsed_min, 1) if elapsed_min > 0 else 0.0

        result = {
            "mode": session["mode"],
            "duration": duration,
            "spaces": session["spaces"],
            "punctuations": session["punctuations"],
            "backspaces": session["backspaces"],
            "total_keys": session["total_keys"],
            "wpm": wpm,
            "cpm": cpm,
            "accuracy": None
        }
        session["result"] = result

        # Save to local SQLite
        self.db.record_speed_session(
            mode=session["mode"],
            duration=duration,
            spaces=session["spaces"],
            punctuations=session["punctuations"],
            backspaces=session["backspaces"],
            total_keys=session["total_keys"],
            wpm=wpm,
            cpm=cpm,
            accuracy=None
        )

        # Send native Windows desktop notification if in background mode
        if session["mode"] == "background":
            self._send_windows_notification(
                "KnowYourClicks: Speed Test Finished",
                f"Completed {duration}s Background Test!\nSpeed: {wpm} WPM ({words_counted} words, {session['backspaces']} corrections)"
            )

    def finish_given_text_session(
        self,
        prompt_text: str,
        typed_text: str,
        total_time_seconds: float
    ) -> Dict[str, Any]:
        """Finalizes an in-app given text session with word and accuracy matching."""
        with self._lock:
            elapsed_min = max(0.01, total_time_seconds / 60.0)
            target_words = prompt_text.split()
            typed_words = typed_text.split()

            # Count correct words
            correct_words = 0
            for tw, pw in zip(typed_words, target_words):
                if tw == pw:
                    correct_words += 1

            # Standard WPM based on typed length
            total_chars = len(typed_text)
            gross_wpm = round((total_chars / 5.0) / elapsed_min, 1)
            cpm = round(total_chars / elapsed_min, 1)

            # Accuracy calculation
            matches = sum(1 for c1, c2 in zip(typed_text, prompt_text) if c1 == c2)
            accuracy = round((matches / max(1, len(prompt_text))) * 100, 1)

            result = {
                "mode": "given_text",
                "duration": int(total_time_seconds),
                "spaces": typed_text.count(" "),
                "punctuations": sum(1 for c in typed_text if not c.isalnum() and not c.isspace()),
                "backspaces": self.active_session["backspaces"] if self.active_session else 0,
                "total_keys": total_chars,
                "wpm": gross_wpm,
                "cpm": cpm,
                "accuracy": accuracy
            }

            self.db.record_speed_session(
                mode="given_text",
                duration=int(total_time_seconds),
                spaces=result["spaces"],
                punctuations=result["punctuations"],
                backspaces=result["backspaces"],
                total_keys=total_chars,
                wpm=gross_wpm,
                cpm=cpm,
                accuracy=accuracy
            )

            if self.active_session:
                self.active_session["completed"] = True
                self.active_session["result"] = result

            return result

    def get_status(self) -> Dict[str, Any]:
        """Returns the current state of speed measurement."""
        with self._lock:
            if not self.active_session:
                return {"active": False, "session": None}

            now = time.time()
            remaining = max(0, int(self.active_session["end_time"] - now))
            elapsed = int(now - self.active_session["start_time"])

            if remaining <= 0 and not self.active_session.get("completed"):
                self._finish_session()

            return {
                "active": not self.active_session.get("completed", False),
                "remaining_seconds": remaining,
                "elapsed_seconds": elapsed,
                "session": self.active_session
            }

    def stop_session(self) -> Dict[str, Any]:
        """Cancels any running session."""
        with self._lock:
            self._stop_event.set()
            if self.active_session and not self.active_session.get("completed"):
                self._finish_session()
            status = self.get_status()
            self.active_session = None
            return status

    @staticmethod
    def _send_windows_notification(title: str, message: str):
        """Sends native Windows desktop notification via PowerShell."""
        clean_title = title.replace('"', '`"')
        clean_msg = message.replace('"', '`"').replace('\n', ' ')
        ps_script = (
            f'[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;'
            f'$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);'
            f'$textNodes = $template.GetElementsByTagName("text");'
            f'$textNodes.Item(0).AppendChild($template.CreateTextNode("{clean_title}")) > $null;'
            f'$textNodes.Item(1).AppendChild($template.CreateTextNode("{clean_msg}")) > $null;'
            f'$toast = [Windows.UI.Notifications.ToastNotification]::new($template);'
            f'[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("KnowYourClicks").Show($toast)'
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
        except Exception:
            pass
