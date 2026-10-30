"""Unit and integration test suite for KnowYourClicks (Windows)."""

import unittest
import sys
from pathlib import Path

# Add root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.privacy_filter import PrivacyFilter
from src.db import Database
from src.text_expander import TextExpander
from src.speed_tracker import SpeedTracker
from src.win_hook import WindowsInputListener


class TestWindowsPrivacyFilter(unittest.TestCase):
    def test_vk_code_whitelist(self):
        # Allowed keys
        self.assertEqual(PrivacyFilter.filter_vk_code(0x20), ("Space", "space"))
        self.assertEqual(PrivacyFilter.filter_vk_code(0x08), ("Backspace", "editing"))
        self.assertEqual(PrivacyFilter.filter_vk_code(0x2E), ("Delete", "editing"))
        self.assertEqual(PrivacyFilter.filter_vk_code(0xBE), ("Period (.)", "punctuation"))
        self.assertEqual(PrivacyFilter.filter_vk_code(0xBC), ("Comma (,)", "punctuation"))
        self.assertEqual(PrivacyFilter.filter_vk_code(0xBA), ("Semicolon (;)", "punctuation"))
        self.assertEqual(PrivacyFilter.filter_vk_code(0xBF), ("Slash (/)", "punctuation"))

        # Blocked keys: letters (0x41-0x5A), numbers (0x30-0x39), function keys (0x70-0x7B), Enter (0x0D)
        self.assertIsNone(PrivacyFilter.filter_vk_code(0x41))  # 'A'
        self.assertIsNone(PrivacyFilter.filter_vk_code(0x42))  # 'B'
        self.assertIsNone(PrivacyFilter.filter_vk_code(0x5A))  # 'Z'
        self.assertIsNone(PrivacyFilter.filter_vk_code(0x30))  # '0'
        self.assertIsNone(PrivacyFilter.filter_vk_code(0x39))  # '9'
        self.assertIsNone(PrivacyFilter.filter_vk_code(0x0D))  # Enter
        self.assertIsNone(PrivacyFilter.filter_vk_code(0x70))  # F1
        self.assertIsNone(PrivacyFilter.filter_vk_code(0x10))  # Shift

    def test_key_string_whitelist(self):
        # Allowed
        self.assertEqual(PrivacyFilter.filter_key_string("Space"), ("Space", "space"))
        self.assertEqual(PrivacyFilter.filter_key_string("Backspace"), ("Backspace", "editing"))
        self.assertEqual(PrivacyFilter.filter_key_string("Delete"), ("Delete", "editing"))
        self.assertEqual(PrivacyFilter.filter_key_string(".", "."), ("Punctuation (.)", "punctuation"))
        self.assertEqual(PrivacyFilter.filter_key_string("!", "!"), ("Punctuation (!)", "punctuation"))

        # Blocked
        self.assertIsNone(PrivacyFilter.filter_key_string("a", "a"))
        self.assertIsNone(PrivacyFilter.filter_key_string("Z", "Z"))
        self.assertIsNone(PrivacyFilter.filter_key_string("5", "5"))
        self.assertIsNone(PrivacyFilter.filter_key_string("Enter"))
        self.assertIsNone(PrivacyFilter.filter_key_string("Tab"))


class TestWindowsTextExpander(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.db.add_shortcut("idk", "i dont know")
        self.expander = TextExpander(self.db)

    def test_shortcut_lookup(self):
        self.assertEqual(self.expander.check_and_expand_word("idk"), "i dont know")
        self.assertIsNone(self.expander.check_and_expand_word("unregistered"))

    def test_space_triggered_expansion(self):
        text = "Hello idk "
        new_text, expanded, trigger, rep = self.expander.process_text_on_space(text)
        self.assertTrue(expanded)
        self.assertEqual(trigger, "idk")
        self.assertEqual(rep, "i dont know")
        self.assertEqual(new_text, "Hello i dont know ")

    def test_non_matching_space(self):
        text = "Just normal typing "
        new_text, expanded, _, _ = self.expander.process_text_on_space(text)
        self.assertFalse(expanded)
        self.assertEqual(new_text, text)


class TestWindowsDatabaseAndStats(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_shortcuts_crud(self):
        self.db.add_shortcut("winsc", "windows shortcut test")
        self.assertEqual(self.db.find_shortcut("winsc"), "windows shortcut test")

        shortcuts = self.db.get_shortcuts()
        target = next((s for s in shortcuts if s["shortcut"] == "winsc"), None)
        self.assertIsNotNone(target)

        self.db.delete_shortcut(target["id"])
        self.assertIsNone(self.db.find_shortcut("winsc"))

    def test_stats_recording(self):
        self.db.record_key_press("Space", "space")
        self.db.record_key_press("Backspace", "editing")
        self.db.record_key_press("Period (.)", "punctuation")

        stats_1h = self.db.get_statistics("1h")
        self.assertGreaterEqual(stats_1h["total_keys"], 3)
        self.assertGreaterEqual(stats_1h["spaces"], 1)
        self.assertGreaterEqual(stats_1h["edits"], 1)
        self.assertGreaterEqual(stats_1h["punctuations"], 1)

        stats_1d = self.db.get_statistics("1d")
        self.assertGreaterEqual(stats_1d["total_keys"], 3)


class TestWindowsSpeedTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = SpeedTracker()

    def test_given_text_finish(self):
        prompt = "Testing Windows speed tracker module."
        typed = "Testing Windows speed tracker module."
        result = self.tracker.finish_given_text_session(prompt, typed, 30.0)
        self.assertEqual(result["mode"], "given_text")
        self.assertEqual(result["duration"], 30)
        self.assertGreater(result["wpm"], 0)
        self.assertEqual(result["accuracy"], 100.0)


class TestWindowsInputListener(unittest.TestCase):
    def setUp(self):
        self.listener = WindowsInputListener()

    def test_dispatch_software_key_whitelisting(self):
        # Whitelisted
        res_space = self.listener.dispatch_software_key("Space")
        self.assertIsNotNone(res_space)
        self.assertEqual(res_space["category"], "space")

        res_bs = self.listener.dispatch_software_key("Backspace")
        self.assertIsNotNone(res_bs)
        self.assertEqual(res_bs["category"], "editing")

        res_dot = self.listener.dispatch_software_key(".", ".")
        self.assertIsNotNone(res_dot)
        self.assertEqual(res_dot["category"], "punctuation")

        # Dropped
        res_letter = self.listener.dispatch_software_key("a", "a")
        self.assertIsNone(res_letter)

        res_digit = self.listener.dispatch_software_key("7", "7")
        self.assertIsNone(res_digit)


if __name__ == "__main__":
    unittest.main()
