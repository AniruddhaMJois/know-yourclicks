"""Text expander engine triggered exclusively on Space key.

Rules:
- Evaluates the preceding word ONLY when the Space key is triggered.
- If the word matches a configured shortcut (e.g., 'idk'), it substitutes the text (e.g., 'i dont know ').
"""

import re
from typing import Optional, Tuple
from .db import Database


class TextExpander:
    """Manages shortcut lookup and text replacement on Space trigger."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def check_and_expand_word(self, word: str) -> Optional[str]:
        """
        Given a single word token (preceding a Space), checks if a shortcut exists.
        Returns the replacement string if matched, else None.
        """
        if not word:
            return None
        # Strip trailing punctuation if needed or match exact word
        clean_word = word.strip().lower()
        return self.db.find_shortcut(clean_word)

    def process_text_on_space(self, current_text: str) -> Tuple[str, bool, Optional[str], Optional[str]]:
        """
        Processes a full text buffer when a Space is entered.
        Returns:
            (new_text, was_expanded, trigger_shortcut, replacement_text)
        """
        # Find the word immediately preceding the trailing space
        # Example: "Hello idk " -> match "idk"
        match = re.search(r'([A-Za-z0-9_-]+)\s*$', current_text)
        if not match:
            return current_text, False, None, None

        trigger = match.group(1)
        replacement = self.check_and_expand_word(trigger)

        if replacement:
            start, end = match.span(1)
            # Replace the trigger word with the expanded phrase + space
            new_text = current_text[:start] + replacement + " "
            return new_text, True, trigger, replacement

        return current_text, False, None, None
