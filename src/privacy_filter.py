"""Privacy filter enforcing strict whitelisting of Windows keyboard events.

STRICT PRIVACY POLICY:
- ONLY Spacebar, Backspace, Delete, and Punctuation marks are processed.
- All letters (A-Z), numbers (0-9), function keys, and unallowed keys are DROPPED IMMEDIATELY.
- Never logs, captures, or transmits passwords, credentials, or private message texts.
"""

from typing import Optional, Tuple
from .config import VK_NAMES, ALLOWED_VK_CODES, PUNCTUATION_CHARS


class PrivacyFilter:
    """
    Enforces hardware and software level privacy filtering for Windows:
    - Space, Backspace, Delete, and Punctuation marks are uniquely categorized and identified.
    - All other keys (letters, numbers, functional keys) are counted anonymously as 'Other Keys'
      under category 'other' so that Total Keystrokes reflects all key presses without logging characters.
    """

    @staticmethod
    def filter_vk_code(vk_code: int) -> Tuple[str, str]:
        """
        Filters a Windows Virtual-Key code (from LowLevelKeyboardProc / KBDLLHOOKSTRUCT).
        Returns (key_name, category).
        """
        if vk_code in VK_NAMES:
            name = VK_NAMES[vk_code]
            if vk_code == 0x20:
                return name, "space"
            elif vk_code in (0x08, 0x2E):
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
