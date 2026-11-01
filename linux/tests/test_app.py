"""Unit and integration tests for KnowYourClicks (Linux)."""

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


class TestPrivacyFilter(unittest.TestCase):
    def test_scancode_whitelist(self):
        # Allowed keys
        self.assertEqual(PrivacyFilter.filter_scancode(57), ("Space", "space"))
        self.assertEqual(PrivacyFilter.filter_scancode(14), ("Backspace", "editing"))
        self.assertEqual(PrivacyFilter.filter_scancode(111), ("Delete", "editing"))
        self.assertEqual(PrivacyFilter.filter_scancode(52), ("Period (.)", "punctuation"))
        self.assertEqual(PrivacyFilter.filter_scancode(51), ("Comma (,)", "punctuation"))

        # Blocked keys (letters, numbers, functional)
        self.assertIsNone(PrivacyFilter.filter_scancode(30))  # KEY_A
        self.assertIsNone(PrivacyFilter.filter_scancode(48))  # KEY_B
        self.assertIsNone(PrivacyFilter.filter_scancode(2))   # KEY_1
        self.assertIsNone(PrivacyFilter.filter_scancode(28))  # KEY_ENTER

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
        self.assertIsNone(PrivacyFilter.filter_key_string("9", "9"))
        self.assertIsNone(PrivacyFilter.filter_key_string("Enter"))


class TestTextExpander(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.db.add_shortcut("idk", "i dont know")
        self.expander = TextExpander(self.db)

    def test_shortcut_lookup(self):
        self.assertEqual(self.expander.check_and_expand_word("idk"), "i dont know")
        self.assertIsNone(self.expander.check_and_expand_word("unknownword"))

    def test_space_triggered_expansion(self):
        # Buffer ending with idk + space
        text = "Well idk "
        new_text, expanded, trigger, rep = self.expander.process_text_on_space(text)
        self.assertTrue(expanded)
        self.assertEqual(trigger, "idk")
        self.assertEqual(rep, "i dont know")
        self.assertEqual(new_text, "Well i dont know ")

    def test_non_matching_space(self):
        text = "Hello world "
        new_text, expanded, _, _ = self.expander.process_text_on_space(text)
        self.assertFalse(expanded)
        self.assertEqual(new_text, text)


class TestDatabaseAndStats(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_shortcuts_crud(self):
        self.db.add_shortcut("testkey", "test replacement")
        self.assertEqual(self.db.find_shortcut("testkey"), "test replacement")
        
        shortcuts = self.db.get_shortcuts()
        target = next((s for s in shortcuts if s["shortcut"] == "testkey"), None)
        self.assertIsNotNone(target)
        
        self.db.delete_shortcut(target["id"])
        self.assertIsNone(self.db.find_shortcut("testkey"))

    def test_stats_recording(self):
        self.db.record_key_press("Space", "space")
        self.db.record_key_press("Backspace", "editing")
        self.db.record_key_press("Period (.)", "punctuation")

        stats_1h = self.db.get_statistics("1h")
        self.assertGreaterEqual(stats_1h["total_keys"], 3)
        self.assertGreaterEqual(stats_1h["spaces"], 1)
        self.assertGreaterEqual(stats_1h["edits"], 1)
        self.assertGreaterEqual(stats_1h["punctuations"], 1)


class TestSpeedTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = SpeedTracker()

    def test_given_text_finish(self):
        prompt = "Hello world test sentence."
        typed = "Hello world test sentence."
        result = self.tracker.finish_given_text_session(prompt, typed, 30.0)
        self.assertEqual(result["mode"], "given_text")
        self.assertEqual(result["duration"], 30)
        self.assertGreater(result["wpm"], 0)
        self.assertEqual(result["accuracy"], 100.0)


class TestUIModule(unittest.TestCase):
    def test_ui_import_and_paths(self):
        from src.ui_app import ICON_PNG, ICON_SVG
        self.assertTrue(ICON_PNG.exists())
        self.assertTrue(ICON_SVG.exists())


class TestAsyncBatchAndListener(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_rapid_key_batch_recording(self):
        # Push 50 keys rapidly
        for i in range(50):
            self.db.record_key_press("Space", "space")
        
        # Flushes immediately
        self.db.flush()
        stats = self.db.get_statistics("1h")
        self.assertGreaterEqual(stats["spaces"], 50)

    def test_software_dispatch_privacy(self):
        from src.input_listener import InputListener
        lis = InputListener()
        # Allowed key
        res = lis.dispatch_software_key("Space", " ")
        self.assertIsNotNone(res)
        self.assertEqual(res["key"], "Space")

        # Disallowed key (letter)
        res_blocked = lis.dispatch_software_key("k", "k")
        self.assertIsNone(res_blocked)


if __name__ == "__main__":
    unittest.main()
