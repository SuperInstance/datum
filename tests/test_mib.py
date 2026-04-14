"""Tests for Message-in-a-Bottle protocol module."""

import os
import tempfile
import unittest

from datum_runtime.superagent.mib import MessageInBottle, _parse_header, _render_header, _slugify


class TestHeaderParser(unittest.TestCase):
    """Test YAML-like header parsing."""

    def test_parse_valid_header(self):
        text = "---\nfrom: oracle1\nto: datum\ndate: 2026-04-14\ntype: signal\n---\n\nBody here."
        header = _parse_header(text)
        self.assertEqual(header["from"], "oracle1")
        self.assertEqual(header["to"], "datum")
        self.assertEqual(header["date"], "2026-04-14")
        self.assertEqual(header["type"], "signal")

    def test_parse_no_header(self):
        text = "Just body text, no header."
        header = _parse_header(text)
        self.assertEqual(header, {})

    def test_render_and_parse_roundtrip(self):
        fields = {"from": "datum", "to": "oracle1", "date": "2026-04-14", "type": "check-in"}
        rendered = _render_header(fields) + "\n"
        parsed = _parse_header(rendered)
        self.assertEqual(parsed, fields)


class TestSlugify(unittest.TestCase):
    """Test filename slug generation."""

    def test_basic_slug(self):
        self.assertEqual(_slugify("Hello World"), "hello-world")

    def test_special_chars(self):
        self.assertEqual(_slugify("ISA v3 Draft — Final!"), "isa-v3-draft-final")

    def test_max_length(self):
        long_text = "a" * 100
        result = _slugify(long_text, max_len=20)
        self.assertTrue(len(result) <= 20)

    def test_empty_string(self):
        self.assertEqual(_slugify(""), "untitled")

    def test_spaces_only(self):
        self.assertEqual(_slugify("   "), "untitled")


class TestMessageInBottle(unittest.TestCase):
    """Test MessageInBottle drop/check/read/broadcast/delete."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mib = MessageInBottle(base_path=self.tmpdir, sender="datum")

    def test_drop_and_check(self):
        path = self.mib.drop("oracle1", "Test Subject", "Test content body.")
        self.assertTrue(os.path.exists(path))
        self.assertIn("for-oracle1", path)

        bottles = self.mib.check("for-oracle1")
        self.assertEqual(len(bottles), 1)

    def test_drop_writes_valid_markdown(self):
        path = self.mib.drop("oracle1", "Status Update", "All systems nominal.")
        content = open(path).read()
        self.assertIn("# Status Update", content)
        self.assertIn("**From:** datum", content)
        self.assertIn("**To:** oracle1", content)

    def test_read_bottle(self):
        self.mib.drop("oracle1", "Important Message", "Body text here.")
        bottles = self.mib.check("for-oracle1")
        header, body = self.mib.read(bottles[0])
        self.assertEqual(header["from"], "datum")
        self.assertEqual(header["to"], "oracle1")
        self.assertEqual(header["subject"], "Important Message")
        self.assertIn("Body text here", body)

    def test_broadcast(self):
        path = self.mib.broadcast("Fleet Alert", "Important fleet-wide notice.")
        self.assertTrue(os.path.exists(path))
        self.assertIn("for-any-vessel", path)

        bottles = self.mib.check("for-any-vessel")
        self.assertEqual(len(bottles), 1)

    def test_delete(self):
        path = self.mib.drop("oracle1", "Temporary", "Temp content")
        self.assertTrue(os.path.exists(path))
        self.assertTrue(self.mib.delete(path))
        self.assertFalse(os.path.exists(path))

    def test_delete_nonexistent(self):
        self.assertFalse(self.mib.delete("/nonexistent/path.md"))

    def test_read_nonexistent(self):
        with self.assertRaises(FileNotFoundError):
            self.mib.read("/nonexistent/bottle.md")

    def test_check_empty_inbox(self):
        bottles = self.mib.check("for-oracle1")
        self.assertEqual(bottles, [])

    def test_summary_empty(self):
        summary = self.mib.summary("for-oracle1")
        self.assertIn("No bottles", summary)

    def test_drop_multiple_and_check(self):
        self.mib.drop("oracle1", "Msg 1", "First message")
        self.mib.drop("oracle1", "Msg 2", "Second message")
        self.mib.drop("jetsonclaw1", "Msg 3", "Third message")

        # Check oracle1 inbox
        bottles = self.mib.check("for-oracle1")
        self.assertEqual(len(bottles), 2)

        # Check jetsonclaw1 inbox
        bottles = self.mib.check("for-jetsonclaw1")
        self.assertEqual(len(bottles), 1)

    def test_bottle_type_parameter(self):
        path = self.mib.drop("oracle1", "Deliverable", "Here is my work.", bottle_type="deliverable")
        header, _ = self.mib.read(path)
        self.assertEqual(header["type"], "deliverable")

    def test_check_default_inbox(self):
        """Default inbox is for-datum."""
        self.mib.drop("datum", "Self note", "Note to self.")
        bottles = self.mib.check()  # default inbox
        self.assertEqual(len(bottles), 1)


if __name__ == "__main__":
    unittest.main()
