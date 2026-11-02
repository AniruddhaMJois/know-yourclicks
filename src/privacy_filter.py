"""Privacy filter enforcing strict whitelisting of Windows keyboard events.

STRICT PRIVACY POLICY:
- ONLY Spacebar, Backspace, Delete, and Punctuation marks are processed.
- All letters (A-Z), numbers (0-9), function keys, and unallowed keys are DROPPED IMMEDIATELY.
- Never logs, captures, or transmits passwords, credentials, or private message texts.
"""

from typing import Optional, Tuple
from .config import VK_NAMES, ALLOWED_VK_CODES, PUNCTUATION_CHARS


class PrivacyFilter:
    """Enforces hardware and software level privacy filtering for Windows."""

    @staticmethod
    def filter_vk_code(vk_code: int) -> Optional[Tuple[str, str]]:
        """
        Filters a Windows Virtual-Key code (from LowLevelKeyboardProc / KBDLLHOOKSTRUCT).
        Returns (key_name, category) if allowed, or None if blocked.
        """
        if vk_code not in ALLOWED_VK_CODES:
            # Drop immediately: letters (0x41-0x5A), numbers (0x30-0x39), function keys, etc.
            return None

        name = VK_NAMES[vk_code]
        if vk_code == 0x20:
            category = "space"
        elif vk_code in (0x08, 0x2E):
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
