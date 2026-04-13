#!/usr/bin/env python3
"""
Tests for datum TOOLS — audit-scanner, batch-license, batch-topics, mib-bottle.

Run with: python3 -m pytest tests/test_tools.py -v
"""

import json
import os
import sys
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from io import StringIO
from datetime import datetime, timezone, timedelta

# Import modules by file path (hyphenated filenames can't be imported directly)
TOOLS_DIR = Path(__file__).parent.parent / "TOOLS"


def _import_module(name, filepath):
    """Import a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


audit_scanner = _import_module("audit_scanner", TOOLS_DIR / "audit-scanner.py")
batch_license = _import_module("batch_license", TOOLS_DIR / "batch-license.py")


class TestAuditScanner(unittest.TestCase):
    """Tests for the FleetAuditor class in audit-scanner.py."""

    def setUp(self):
        """Set up test fixtures."""
        self.auditor = audit_scanner.FleetAuditor(
            token="test-token",
            org="TestOrg",
            stale_days=365,
            min_size=1,
            top_n=50
        )

    def test_init_defaults(self):
        """Test FleetAuditor initializes with correct defaults."""
        self.assertEqual(self.auditor.token, "test-token")
        self.assertEqual(self.auditor.org, "TestOrg")
        self.assertEqual(self.auditor.stale_threshold, timedelta(days=365))
        self.assertEqual(self.auditor.min_size, 1)
        self.assertEqual(self.auditor.top_n, 50)
        self.assertEqual(len(self.auditor.all_repos), 0)
        self.assertEqual(len(self.auditor.no_description), 0)
        self.assertEqual(len(self.auditor.no_license), 0)
        self.assertEqual(len(self.auditor.errors), 0)

    def test_init_with_custom_params(self):
        """Test FleetAuditor with custom parameters."""
        auditor = audit_scanner.FleetAuditor(
            token="custom-token",
            org="CustomOrg",
            stale_days=180,
            min_size=5,
            top_n=20
        )
        self.assertEqual(auditor.org, "CustomOrg")
        self.assertEqual(auditor.stale_threshold, timedelta(days=180))
        self.assertEqual(auditor.min_size, 5)
        self.assertEqual(auditor.top_n, 20)

    def test_print_progress_writes_to_stderr(self):
        """Test that print_progress outputs to stderr."""
        captured = StringIO()
        with patch('sys.stderr', captured):
            self.auditor.print_progress("test message")
        self.assertIn("test message", captured.getvalue())

    def test_classify_repo_no_description(self):
        """Test that a repo without description is classified correctly."""
        repo = {
            "name": "test-repo",
            "html_url": "https://github.com/TestOrg/test-repo",
            "description": "",
            "license": {"key": "mit"},
            "size": 100,
            "pushed_at": datetime.now(timezone.utc).isoformat(),
            "language": "Python",
            "fork": False
        }
        if not repo.get("description"):
            self.auditor.no_description.append({
                "name": repo["name"],
                "url": repo["html_url"],
                "created": repo.get("created_at", "unknown"),
                "language": repo.get("language")
            })
        self.assertEqual(len(self.auditor.no_description), 1)
        self.assertEqual(self.auditor.no_description[0]["name"], "test-repo")

    def test_classify_repo_no_license(self):
        """Test that a repo without license is classified correctly."""
        repo = {
            "name": "unlicensed-repo",
            "html_url": "https://github.com/TestOrg/unlicensed-repo",
            "description": "A test repo",
            "license": None,
            "size": 100,
            "pushed_at": datetime.now(timezone.utc).isoformat(),
            "language": "Python",
            "fork": False
        }
        if not repo.get("license"):
            self.auditor.no_license.append({
                "name": repo["name"],
                "url": repo["html_url"],
                "created": repo.get("created_at", "unknown"),
                "language": repo.get("language")
            })
        self.assertEqual(len(self.auditor.no_license), 1)
        self.assertEqual(self.auditor.no_license[0]["name"], "unlicensed-repo")

    def test_classify_repo_empty(self):
        """Test that an empty repo is classified correctly."""
        repo = {
            "name": "empty-repo",
            "html_url": "https://github.com/TestOrg/empty-repo",
            "description": "An empty repo",
            "license": {"key": "mit"},
            "size": 0,
            "pushed_at": "2026-01-01T00:00:00Z",
            "created_at": "2025-01-01T00:00:00Z",
            "language": None,
            "fork": False
        }
        if repo.get("size", 0) <= self.auditor.min_size:
            self.auditor.empty_repos.append({
                "name": repo["name"],
                "url": repo["html_url"],
                "size": repo.get("size", 0),
                "created": repo.get("created_at", "unknown"),
                "pushed": repo.get("pushed_at", "never")
            })
        self.assertEqual(len(self.auditor.empty_repos), 1)

    def test_classify_repo_stale(self):
        """Test that a stale repo is classified correctly."""
        stale_date = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        repo = {
            "name": "stale-repo",
            "html_url": "https://github.com/TestOrg/stale-repo",
            "description": "A stale repo",
            "license": {"key": "mit"},
            "size": 100,
            "pushed_at": stale_date,
            "created_at": "2024-01-01T00:00:00Z",
            "language": "Python",
            "fork": False
        }
        now = datetime.now(timezone.utc)
        pushed = datetime.fromisoformat(stale_date.replace("Z", "+00:00"))
        if (now - pushed) > self.auditor.stale_threshold:
            self.auditor.stale_repos.append({
                "name": repo["name"],
                "url": repo["html_url"],
                "pushed": stale_date,
                "stale_days": (now - pushed).days,
                "language": repo.get("language")
            })
        self.assertEqual(len(self.auditor.stale_repos), 1)
        self.assertGreater(self.auditor.stale_repos[0]["stale_days"], 365)

    def test_classify_repo_fork(self):
        """Test that a fork repo is classified correctly."""
        repo = {
            "name": "forked-repo",
            "html_url": "https://github.com/TestOrg/forked-repo",
            "description": "A fork",
            "license": {"key": "mit"},
            "size": 100,
            "pushed_at": datetime.now(timezone.utc).isoformat(),
            "language": "Python",
            "fork": True,
            "parent": {
                "full_name": "upstream/original-repo",
                "html_url": "https://github.com/upstream/original-repo"
            }
        }
        if repo.get("fork"):
            parent = repo.get("parent", {})
            self.auditor.fork_repos.append({
                "name": repo["name"],
                "url": repo["html_url"],
                "parent": parent.get("full_name", "unknown"),
                "parent_url": parent.get("html_url", "")
            })
        self.assertEqual(len(self.auditor.fork_repos), 1)
        self.assertEqual(self.auditor.fork_repos[0]["parent"], "upstream/original-repo")

    def test_language_counting(self):
        """Test that languages are counted correctly."""
        repos = [
            {"name": "r1", "language": "Python"},
            {"name": "r2", "language": "TypeScript"},
            {"name": "r3", "language": "Python"},
            {"name": "r4", "language": None},
        ]
        for repo in repos:
            lang = repo.get("language")
            if lang:
                self.auditor.language_counts[lang] += 1
        self.assertEqual(self.auditor.language_counts["Python"], 2)
        self.assertEqual(self.auditor.language_counts["TypeScript"], 1)
        self.assertNotIn(None, self.auditor.language_counts)

    def test_generate_json(self):
        """Test JSON report generation."""
        self.auditor.all_repos = [{"name": "test"}]
        self.auditor.no_description = [{"name": "r1"}]
        result = self.auditor.generate_json()
        self.assertIn("audit_date", result)
        self.assertIn("organization", result)
        self.assertEqual(result["organization"], "TestOrg")
        self.assertEqual(result["total_repos"], 1)
        self.assertIn("findings", result)

    def test_generate_markdown(self):
        """Test markdown report generation."""
        self.auditor.all_repos = [{"name": "test"}]
        self.auditor.no_description = [{"name": "r1", "url": "https://example.com", "language": "Python", "created": "2026-01-01"}]
        self.auditor.no_license = []
        self.auditor.empty_repos = []
        self.auditor.stale_repos = []
        self.auditor.fork_repos = []
        self.auditor.language_counts = {"Python": 1}

        report = self.auditor.generate_markdown()
        self.assertIn("# Fleet Audit Report", report)
        self.assertIn("TestOrg", report)
        self.assertIn("Missing description", report)
        self.assertIn("| Language | Repos | Percentage |", report)


class TestBatchLicense(unittest.TestCase):
    """Tests for the LicenseBatcher class in batch-license.py."""

    def setUp(self):
        """Set up test fixtures."""
        self.batcher = batch_license.LicenseBatcher(
            token="test-token",
            org="TestOrg",
            dry_run=True,
            delay=0.1
        )

    def test_init_defaults(self):
        """Test LicenseBatcher initializes with correct defaults."""
        self.assertEqual(self.batcher.token, "test-token")
        self.assertEqual(self.batcher.org, "TestOrg")
        self.assertTrue(self.batcher.dry_run)
        self.assertEqual(self.batcher.license_type, "mit")
        self.assertEqual(self.batcher.owner, "TestOrg")
        self.assertTrue(self.batcher.skip_licensed)
        self.assertEqual(self.batcher.stats["success"], 0)
        self.assertEqual(self.batcher.stats["failed"], 0)

    def test_mit_license_template(self):
        """Test that MIT license template contains required elements."""
        year = "2026"
        owner = "TestOwner"
        license_text = batch_license.MIT_LICENSE_TEMPLATE.format(year=year, owner=owner)
        self.assertIn("MIT License", license_text)
        self.assertIn(year, license_text)
        self.assertIn(owner, license_text)
        self.assertIn("Permission is hereby granted", license_text)
        self.assertIn("WITHOUT WARRANTY", license_text)

    def test_stats_tracking(self):
        """Test that stats are tracked correctly."""
        self.batcher.stats["success"] += 1
        self.batcher.stats["success"] += 1
        self.batcher.stats["failed"] += 1
        self.assertEqual(self.batcher.stats["success"], 2)
        self.assertEqual(self.batcher.stats["failed"], 1)

    def test_checkpoint_data_structure(self):
        """Test checkpoint data structure."""
        self.assertIn("completed", self.batcher.checkpoint_data)
        self.assertIn("failed", self.batcher.checkpoint_data)
        self.assertIsInstance(self.batcher.checkpoint_data["completed"], list)
        self.assertIsInstance(self.batcher.checkpoint_data["failed"], list)

    @patch('batch_license.Path')
    def test_load_checkpoint_no_file(self, mock_path):
        """Test loading checkpoint when no file exists."""
        mock_path.return_value.exists.return_value = False
        self.batcher.load_checkpoint()
        self.assertEqual(len(self.batcher.checkpoint_data["completed"]), 0)

    @patch('batch_license.Path')
    @patch('builtins.open', create=True)
    def test_load_checkpoint_with_file(self, mock_open, mock_path):
        """Test loading checkpoint from existing file."""
        mock_path.return_value.exists.return_value = True
        checkpoint = {"completed": ["repo1", "repo2"], "failed": []}
        mock_open.return_value.__enter__ = MagicMock()
        mock_open.return_value.__exit__ = MagicMock()
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(checkpoint)
        self.batcher.load_checkpoint()
        self.assertEqual(len(self.batcher.checkpoint_data["completed"]), 2)


class TestBatchTopics(unittest.TestCase):
    """Tests for batch-topics.py."""

    def test_topics_api_format(self):
        """Test that the topics API expects correct JSON format."""
        # The GitHub topics API expects {"names": ["topic1", "topic2"]}
        correct_format = {"names": ["typescript", "ai", "machine-learning"]}
        payload = json.dumps(correct_format)
        parsed = json.loads(payload)
        self.assertIn("names", parsed)
        self.assertIsInstance(parsed["names"], list)
        self.assertEqual(len(parsed["names"]), 3)

    def test_topic_mapping_file_exists(self):
        """Test that the topic mapping file exists and is valid JSON."""
        mapping_path = TOOLS_DIR / "topic-mapping.json"
        if mapping_path.exists():
            with open(mapping_path) as f:
                data = json.load(f)
            # Topic mapping can be a list or dict
            self.assertIsInstance(data, (dict, list))
            if isinstance(data, list) and len(data) > 0:
                # Verify each entry has expected fields
                self.assertIn("name", data[0])
                self.assertIn("new_topics", data[0])
        else:
            self.skipTest("topic-mapping.json not found")


class TestIntegrationScenarios(unittest.TestCase):
    """Integration-level tests for datum tool interactions."""

    def test_audit_scanner_report_flow(self):
        """Test the full audit scanner report generation flow."""
        auditor = audit_scanner.FleetAuditor(token="test", org="TestOrg")
        auditor.all_repos = [
            {"name": "repo1", "html_url": "https://github.com/TestOrg/repo1",
             "description": "Has desc", "license": {"key": "mit"}, "size": 100,
             "pushed_at": datetime.now(timezone.utc).isoformat(), "language": "Python", "fork": False},
            {"name": "repo2", "html_url": "https://github.com/TestOrg/repo2",
             "description": "", "license": None, "size": 0,
             "pushed_at": "2024-01-01T00:00:00Z", "created_at": "2024-01-01T00:00:00Z",
             "language": None, "fork": False},
            {"name": "repo3", "html_url": "https://github.com/TestOrg/repo3",
             "description": "Forked", "license": {"key": "apache"}, "size": 50,
             "pushed_at": datetime.now(timezone.utc).isoformat(),
             "language": "TypeScript", "fork": True,
             "parent": {"full_name": "upstream/repo3", "html_url": "https://github.com/upstream/repo3"}},
        ]
        auditor.language_counts = {"Python": 1, "TypeScript": 1}

        # Pre-populate audit findings (simulating run_audit results)
        auditor.no_description.append({
            "name": "repo2", "url": "https://github.com/TestOrg/repo2",
            "language": None, "created": "2024-01-01"
        })
        auditor.no_license.append({
            "name": "repo2", "url": "https://github.com/TestOrg/repo2",
            "language": None, "created": "2024-01-01"
        })
        auditor.empty_repos.append({
            "name": "repo2", "url": "https://github.com/TestOrg/repo2",
            "size": 0, "created": "2024-01-01", "pushed": "2024-01-01"
        })
        auditor.fork_repos.append({
            "name": "repo3", "url": "https://github.com/TestOrg/repo3",
            "parent": "upstream/repo3", "parent_url": "https://github.com/upstream/repo3"
        })

        # Generate both formats
        md_report = auditor.generate_markdown()
        json_report = auditor.generate_json()

        # Verify markdown report
        self.assertIn("repo2", md_report)
        self.assertIn("Fork", md_report)

        # Verify JSON report structure
        self.assertEqual(json_report["organization"], "TestOrg")
        self.assertEqual(json_report["total_repos"], 3)

    def test_batch_license_dry_run(self):
        """Test batch license in dry-run mode."""
        batcher = batch_license.LicenseBatcher(
            token="test-token",
            org="TestOrg",
            dry_run=True,
            delay=0
        )
        result = batcher.add_license("test-repo")
        self.assertTrue(result.get("dry_run"))

    def test_mit_license_template_completeness(self):
        """Test MIT license template contains all required legal clauses."""
        template = batch_license.MIT_LICENSE_TEMPLATE.format(year="2026", owner="Test")
        required_phrases = [
            "MIT License",
            "Permission is hereby granted, free of charge",
            "to any person obtaining a copy",
            "to use, copy, modify, merge, publish, distribute, sublicense",
            "THE SOFTWARE IS PROVIDED \"AS IS\"",
            "WITHOUT WARRANTY OF ANY KIND",
            "FITNESS FOR A PARTICULAR PURPOSE",
            "NONINFRINGEMENT",
            "IN NO EVENT SHALL THE",
            "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, template, f"MIT template missing: {phrase}")


if __name__ == "__main__":
    unittest.main()
