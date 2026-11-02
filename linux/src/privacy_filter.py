"""Privacy filter enforcing strict whitelisting of keyboard events.

STRICT PRIVACY POLICY:
- ONLY Spacebar, Backspace, Delete, and Punctuation marks are processed.
- All letters (A-Z), numbers (0-9), and non-whitelisted keys are DROPPED IMMEDIATELY.
- Never logs, captures, or transmits passwords, credentials, or private message texts.
"""

from typing import Optional, Tuple
from .config import SCANCODE_NAMES, ALLOWED_SCANCODES, PUNCTUATION_CHARS


class PrivacyFilter:
    """
    Enforces hardware and software level privacy filtering:
    - Space, Backspace, Delete, and Punctuation marks are uniquely categorized and identified.
    - All other keys (letters, numbers, functional keys) are counted anonymously as 'Other Keys'
      under category 'other' so that Total Keystrokes reflects all key presses without logging characters.
    """

    @staticmethod
    def filter_scancode(scancode: int) -> Tuple[str, str]:
        """
        Filters a Linux hardware evdev scancode.
        Returns (key_name, category).
        """
        if scancode in SCANCODE_NAMES:
            name = SCANCODE_NAMES[scancode]
            if scancode == 57:
                return name, "space"
            elif scancode in (14, 111):
                return name, "editing"
            else:
                return name, "punctuation"

        # Letters, numbers, and other keys are counted anonymously for total count
        return "Other Keys", "other"

    @staticmethod
    def filter_key_string(key_name: str, char_val: str = "") -> Tuple[str, str]:
        """
        Filters software/UI key inputs.
        Identifies Space, Backspace, Delete, and Punctuation specifically,
        and categorizes all other keys anonymously as 'Other Keys'.
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

        # All other keys (alphanumerics, etc.)
        return "Other Keys", "other"
