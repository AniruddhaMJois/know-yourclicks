"""Configuration settings and Windows virtual-key whitelist for KnowYourClicks (Windows)."""

import os
from pathlib import Path

# Paths: Use %LOCALAPPDATA%\KnowYourClicks on Windows
local_app_data = os.environ.get("LOCALAPPDATA")
if local_app_data:
    DATA_DIR = Path(local_app_data) / "KnowYourClicks"
else:
    # Fallback if LOCALAPPDATA is unset (e.g. during cross-platform testing)
    DATA_DIR = Path.home() / "AppData" / "Local" / "KnowYourClicks"

DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "stats.db"
PID_FILE = DATA_DIR / "daemon.pid"
LOG_FILE = DATA_DIR / "daemon.log"

# Server configuration
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 45678

# Windows Virtual-Key (VK) Codes Whitelist: STRICT PRIVACY REQUIREMENT
# Only Spacebar, Backspace, Delete, and Punctuation marks are allowed.
# All alphanumeric keys (A-Z: 0x41-0x5A, 0-9: 0x30-0x39) are STRICTLY excluded.
VK_NAMES = {
    # Space key
    0x20: "Space",
    # Editing keys
    0x08: "Backspace",
    0x2E: "Delete",
    # Punctuation keys (OEM Virtual Keys on standard US/UK keyboards)
    0xBE: "Period (.)",
    0xBC: "Comma (,)",
    0xBA: "Semicolon (;)",
    0xBF: "Slash (/)",
    0xC0: "Grave Accent (`)",
    0xDB: "Left Bracket ([)",
    0xDC: "Backslash (\\)",
    0xDD: "Right Bracket (])",
    0xDE: "Apostrophe (')",
    0xBD: "Minus (-)",
    0xBB: "Equal (=)",
    # Numpad punctuation/arithmetic symbols
    0x6A: "Keypad Asterisk (*)",
    0x6B: "Keypad Plus (+)",
    0x6D: "Keypad Minus (-)",
    0x6E: "Keypad Dot (.)",
    0x6F: "Keypad Slash (/)",
}

ALLOWED_VK_CODES = set(VK_NAMES.keys())

# Punctuation character set for UI and software filtering
PUNCTUATION_CHARS = set(".,!?:;\"'-/\\()[]{}~`@#$%^&*+=<>_")
