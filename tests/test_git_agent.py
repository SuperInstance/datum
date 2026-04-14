"""Tests for Git Agent — workshop init, commits, inventory."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from datum_runtime.superagent.git_agent import GitAgent
from datum_runtime.superagent.core import AgentConfig


def shutil_which(cmd):
    import shutil
    return shutil.which(cmd) is not None


@unittest.skipIf(not shutil_which("git"), "git not available")
class TestGitAgent(unittest.TestCase):
    """Test GitAgent workshop operations."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        cfg = AgentConfig(role="git-agent", repo_path=self.tmpdir)
        self.ga = GitAgent(config=cfg, owner="test-owner")

    def test_init_workshop(self):
        path = self.ga.init_workshop(name="test-workshop", owner="test-owner")
        self.assertTrue((path / "README.md").exists())
        self.assertTrue((path / "bootcamp" / "README.md").exists())
        self.assertTrue((path / "tools" / "manifest.json").exists())
        self.assertTrue((path / "TASKBOARD.md").exists())
        self.assertTrue((path / "JOURNAL.md").exists())

    def test_commit(self):
        self.ga.init_workshop(name="test", owner="test")
        # Modify a file
        readme = Path(self.tmpdir) / "test.txt"
        readme.write_text("hello")
        h = self.ga.commit("feat: add test file", reasoning="Testing commit flow")
        self.assertIsNotNone(h)

    def test_status(self):
        self.ga.init_workshop(name="test", owner="test")
        s = self.ga.status()
        self.assertIn(s["branch"], ("main", "master"))
        self.assertIsInstance(s["staged"], list)
        self.assertIsInstance(s["modified"], list)

    def test_history(self):
        self.ga.init_workshop(name="test", owner="test")
        h = self.ga.history(5)
        self.assertTrue(len(h) >= 1)  # At least the init commit

    def test_inventory(self):
        self.ga.init_workshop(name="test", owner="test")
        inv = self.ga.inventory()
        self.assertIn("tools", inv)
        self.assertIn("recipes", inv)


if __name__ == "__main__":
    unittest.main()
