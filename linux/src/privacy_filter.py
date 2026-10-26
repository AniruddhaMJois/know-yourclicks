"""Privacy filter enforcing strict whitelisting of keyboard events.

STRICT PRIVACY POLICY:
- ONLY Spacebar, Backspace, Delete, and Punctuation marks are processed.
- All letters (A-Z), numbers (0-9), and non-whitelisted keys are DROPPED IMMEDIATELY.
- Never logs, captures, or transmits passwords, credentials, or private message texts.
"""

from typing import Optional, Tuple
from .config import SCANCODE_NAMES, ALLOWED_SCANCODES, PUNCTUATION_CHARS


class PrivacyFilter:
    """Enforces hardware and software level privacy filtering."""

    @staticmethod
    def filter_scancode(scancode: int) -> Optional[Tuple[str, str]]:
        """
        Filters a Linux hardware evdev scancode.
        Returns (key_name, category) if allowed, or None if blocked.
        """
        if scancode not in ALLOWED_SCANCODES:
            # Drop immediately: letters, numbers, functional keys
            return None

        name = SCANCODE_NAMES[scancode]
        if scancode == 57:
            category = "space"
        elif scancode in (14, 111):
            category = "editing"
        else:
            category = "punctuation"

        return name, category

    @staticmethod
    def filter_key_string(key_name: str, char_val: str = "") -> Optional[Tuple[str, str]]:
        """
        Filters software/UI key inputs.
        Accepts: 'Space', ' ', 'Backspace', 'Delete', or any single punctuation character.
        Rejects: Any letter (a-z, A-Z), digit (0-9), or unspecified key.
        """
        norm_key = key_name.strip()
        
        # Check Space
        if norm_key in ("Space", " ", "space", "Spacebar"):
            return "Space", "space"
        
        # Check Backspace and Delete
        if norm_key in ("Backspace", "backspace"):
            return "Backspace", "editing"
        if norm_key in ("Delete", "delete"):
            return "Delete", "editing"

        # Check single punctuation character
        target = char_val if char_val else (norm_key if len(norm_key) == 1 else "")
        if target and target in PUNCTUATION_CHARS:
            return f"Punctuation ({target})", "punctuation"

        # Any alphanumeric or unallowed key is rejected
        return None
