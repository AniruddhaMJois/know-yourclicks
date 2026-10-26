"""Configuration settings and privacy whitelist for KnowYourClicks (Linux)."""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "knowyourclicks"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "knowyourclicks"

DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "stats.db"
PID_FILE = STATE_DIR / "daemon.pid"
LOG_FILE = STATE_DIR / "daemon.log"

# Server configuration
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 45678

# Linux evdev input event constants
EV_KEY = 0x01
KEY_RELEASE = 0
KEY_PRESS = 1
KEY_REPEAT = 2

# Hardware Whitelist: STRICT PRIVACY REQUIREMENT
# Only Spacebar, Backspace, Delete, and Punctuation marks are allowed.
# All alphanumeric keys (A-Z, 0-9) are STRICTLY excluded and never recorded.
SCANCODE_NAMES = {
    # Space key
    57: "Space",
    # Editing keys
    14: "Backspace",
    111: "Delete",
    # Punctuation keys
    12: "Minus (-)",
    13: "Equal (=)",
    26: "Left Bracket ([)",
    27: "Right Bracket (])",
    39: "Semicolon (;)",
    40: "Apostrophe (')",
    41: "Grave Accent (`)",
    43: "Backslash (\\)",
    51: "Comma (,)",
    52: "Period (.)",
    53: "Slash (/)",
    74: "Keypad Minus (-)",
    78: "Keypad Plus (+)",
    83: "Keypad Dot (.)",
    98: "Keypad Slash (/)",
    121: "Keypad Comma (,)",
}

ALLOWED_SCANCODES = set(SCANCODE_NAMES.keys())

# Punctuation character set for UI and software filtering
PUNCTUATION_CHARS = set(".,!?:;\"'-/\\()[]{}~`@#$%^&*+=<>_")
