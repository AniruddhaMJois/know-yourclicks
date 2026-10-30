#!/usr/bin/env python3
"""KnowYourClicks CLI and desktop entrypoint for Windows."""

import os
import sys
import webbrowser
from pathlib import Path

# Add root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from src.daemon import (
    start_daemon,
    stop_daemon,
    daemon_status,
    get_running_pid,
    install_autostart,
    uninstall_autostart,
)
from src.config import DEFAULT_PORT, DEFAULT_HOST, DATA_DIR
from src.db import Database

is_windows = sys.platform == "win32"


def print_usage():
    print("""
KnowYourClicks - Privacy-First Keystroke & Typing Speed Analytics (Windows)

Usage:
    python knowyourclicks.py <command> [options]
    or
    knowyourclicks.bat <command>

Commands:
    app                  Start background service (if not running) & open Dashboard UI
    start                Start the background service process
    stop                 Stop the running background service process
    restart              Restart the background service
    status               Show service and Win32 hook status
    stats                Print summary of local keystroke statistics in terminal
    autostart-install    Configure autostart on Windows login (HKCU Run registry key)
    autostart-uninstall  Remove autostart from Windows registry
    help                 Show this help message
""")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("help", "-h", "--help"):
        print_usage()
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "start":
        foreground = "--foreground" in sys.argv or "-f" in sys.argv
        start_daemon(foreground=foreground)

    elif cmd == "stop":
        stop_daemon()

    elif cmd == "restart":
        stop_daemon()
        start_daemon()

    elif cmd == "status":
        daemon_status()

    elif cmd == "app":
        pid = get_running_pid()
        if not pid:
            print("[KnowYourClicks] Starting background service...")
            start_daemon(foreground=False)

        url = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/"
        print(f"[KnowYourClicks] Opening Dashboard at {url}...")
        webbrowser.open(url)

    elif cmd == "stats":
        db = Database()
        s = db.get_statistics("1d")
        print("\n--- KnowYourClicks (Windows): Last 24 Hours Statistics ---")
        print(f"Total Whitelisted Keystrokes: {s['total_keys']}")
        print(f"Spacebar Presses:             {s['spaces']}")
        print(f"Edits (Backspace/Delete):     {s['edits']}")
        print(f"Correction Rate:              {s['correction_rate']}%")
        print(f"Punctuation Marks:            {s['punctuations']}")
        print(f"Local Storage Path:           {DATA_DIR}\n")
        print("Top Whitelisted Keys:")
        for k in s['key_counts'][:5]:
            print(f"  • {k['key_name']}: {k['total']}")
        print("-----------------------------------------------------------\n")

    elif cmd == "autostart-install":
        install_autostart()

    elif cmd == "autostart-uninstall":
        uninstall_autostart()

    else:
        print(f"Unknown command: '{cmd}'")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
