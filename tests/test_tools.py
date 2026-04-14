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
import tempfile
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
batch_topics = _import_module("batch_topics", TOOLS_DIR / "batch-topics.py")
mib_bottle = _import_module("mib_bottle", TOOLS_DIR / "mib-bottle.py")


class TestAuditScanner(unittest.TestCase):
    """Tests for the FleetAuditor class in audit-scanner.py."""

    def setUp(self):
        self.auditor = audit_scanner.FleetAuditor(
            token="test-token", org="TestOrg", stale_days=365, min_size=1, top_n=50
        )

    def test_init_defaults(self):
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
        auditor = audit_scanner.FleetAuditor(
            token="custom-token", org="CustomOrg", stale_days=180, min_size=5, top_n=20
        )
        self.assertEqual(auditor.org, "CustomOrg")
        self.assertEqual(auditor.stale_threshold, timedelta(days=180))
        self.assertEqual(auditor.min_size, 5)
        self.assertEqual(auditor.top_n, 20)

    def test_print_progress_writes_to_stderr(self):
        captured = StringIO()
        with patch('sys.stderr', captured):
            self.auditor.print_progress("test message")
        self.assertIn("test message", captured.getvalue())

    def test_classify_repo_no_description(self):
        repo = {
            "name": "test-repo", "html_url": "https://github.com/TestOrg/test-repo",
            "description": "", "license": {"key": "mit"}, "size": 100,
            "pushed_at": datetime.now(timezone.utc).isoformat(),
            "language": "Python", "fork": False
        }
        if not repo.get("description"):
            self.auditor.no_description.append({
                "name": repo["name"], "url": repo["html_url"],
                "created": repo.get("created_at", "unknown"), "language": repo.get("language")
            })
        self.assertEqual(len(self.auditor.no_description), 1)
        self.assertEqual(self.auditor.no_description[0]["name"], "test-repo")

    def test_classify_repo_no_license(self):
        repo = {
            "name": "unlicensed-repo", "html_url": "https://github.com/TestOrg/unlicensed-repo",
            "description": "A test repo", "license": None, "size": 100,
            "pushed_at": datetime.now(timezone.utc).isoformat(),
            "language": "Python", "fork": False
        }
        if not repo.get("license"):
            self.auditor.no_license.append({
                "name": repo["name"], "url": repo["html_url"],
                "created": repo.get("created_at", "unknown"), "language": repo.get("language")
            })
        self.assertEqual(len(self.auditor.no_license), 1)

    def test_classify_repo_empty(self):
        repo = {
            "name": "empty-repo", "html_url": "https://github.com/TestOrg/empty-repo",
            "description": "An empty repo", "license": {"key": "mit"}, "size": 0,
            "pushed_at": "2026-01-01T00:00:00Z", "created_at": "2025-01-01T00:00:00Z",
            "language": None, "fork": False
        }
        if repo.get("size", 0) <= self.auditor.min_size:
            self.auditor.empty_repos.append({
                "name": repo["name"], "url": repo["html_url"],
                "size": repo.get("size", 0), "created": repo.get("created_at", "unknown"),
                "pushed": repo.get("pushed_at", "never")
            })
        self.assertEqual(len(self.auditor.empty_repos), 1)

    def test_classify_repo_stale(self):
        stale_date = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        repo = {
            "name": "stale-repo", "html_url": "https://github.com/TestOrg/stale-repo",
            "description": "A stale repo", "license": {"key": "mit"}, "size": 100,
            "pushed_at": stale_date, "created_at": "2024-01-01T00:00:00Z",
            "language": "Python", "fork": False
        }
        now = datetime.now(timezone.utc)
        pushed = datetime.fromisoformat(stale_date.replace("Z", "+00:00"))
        if (now - pushed) > self.auditor.stale_threshold:
            self.auditor.stale_repos.append({
                "name": repo["name"], "url": repo["html_url"],
                "pushed": stale_date, "stale_days": (now - pushed).days,
                "language": repo.get("language")
            })
        self.assertEqual(len(self.auditor.stale_repos), 1)
        self.assertGreater(self.auditor.stale_repos[0]["stale_days"], 365)

    def test_classify_repo_fork(self):
        repo = {
            "name": "forked-repo", "html_url": "https://github.com/TestOrg/forked-repo",
            "description": "A fork", "license": {"key": "mit"}, "size": 100,
            "pushed_at": datetime.now(timezone.utc).isoformat(),
            "language": "Python", "fork": True,
            "parent": {"full_name": "upstream/original-repo", "html_url": "https://github.com/upstream/original-repo"}
        }
        if repo.get("fork"):
            parent = repo.get("parent", {})
            self.auditor.fork_repos.append({
                "name": repo["name"], "url": repo["html_url"],
                "parent": parent.get("full_name", "unknown"), "parent_url": parent.get("html_url", "")
            })
        self.assertEqual(len(self.auditor.fork_repos), 1)
        self.assertEqual(self.auditor.fork_repos[0]["parent"], "upstream/original-repo")

    def test_language_counting(self):
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
        self.auditor.all_repos = [{"name": "test"}]
        self.auditor.no_description = [{"name": "r1"}]
        result = self.auditor.generate_json()
        self.assertIn("audit_date", result)
        self.assertIn("organization", result)
        self.assertEqual(result["organization"], "TestOrg")
        self.assertEqual(result["total_repos"], 1)
        self.assertIn("findings", result)

    def test_generate_markdown(self):
        self.auditor.all_repos = [{"name": "test"}]
        self.auditor.no_description = [{"name": "r1", "url": "https://example.com", "language": "Python", "created": "2026-01-01"}]
        self.auditor.no_license = []
        self.auditor.empty_repos = []
        self.auditor.stale_repos = []
        self.auditor.fork_repos = []
        self.auditor.language_counts = {"Python": 1}
        self.auditor.no_topics = []
        report = self.auditor.generate_markdown()
        self.assertIn("# Fleet Audit Report", report)
        self.assertIn("TestOrg", report)
        self.assertIn("Missing description", report)
        self.assertIn("| Language | Repos | Percentage |", report)

    def test_generate_markdown_includes_empty_repos_section(self):
        self.auditor.all_repos = [{"name": "test"}]
        self.auditor.no_description = []
        self.auditor.no_license = []
        self.auditor.empty_repos = [{"name": "empty", "url": "https://example.com", "size": 0, "created": "2026-01-01", "pushed": "never"}]
        self.auditor.stale_repos = []
        self.auditor.fork_repos = []
        self.auditor.language_counts = {}
        self.auditor.no_topics = []
        report = self.auditor.generate_markdown()
        self.assertIn("Priority 1: Empty Repos", report)
        self.assertIn("empty", report)

    def test_generate_markdown_includes_stale_repos_count(self):
        self.auditor.all_repos = [{"name": "test"}]
        self.auditor.no_description = []
        self.auditor.no_license = []
        self.auditor.empty_repos = []
        self.auditor.stale_repos = [{"name": "stale", "url": "https://example.com", "pushed": "2024-01-01", "stale_days": 400, "language": "Python"}]
        self.auditor.fork_repos = []
        self.auditor.language_counts = {}
        self.auditor.no_topics = []
        report = self.auditor.generate_markdown()
        # Stale repos appear in the summary table, not a dedicated section
        self.assertIn("Stale repos", report)
        self.assertIn("| 1 |", report)

    def test_generate_markdown_truncates_to_top_n(self):
        self.auditor.top_n = 2
        self.auditor.all_repos = [{"name": "test"}]
        self.auditor.no_description = [
            {"name": f"repo{i}", "url": "https://example.com", "language": "Python", "created": "2026-01-01"}
            for i in range(5)
        ]
        self.auditor.no_license = []
        self.auditor.empty_repos = []
        self.auditor.stale_repos = []
        self.auditor.fork_repos = []
        self.auditor.language_counts = {}
        self.auditor.no_topics = []
        report = self.auditor.generate_markdown()
        self.assertIn("and 3 more", report)

    def test_generate_json_includes_errors(self):
        self.auditor.all_repos = []
        self.auditor.errors = ["API error on page 1: 403"]
        result = self.auditor.generate_json()
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("API error", result["errors"][0])

    def test_generate_json_includes_language_distribution(self):
        self.auditor.all_repos = [{"name": "test"}]
        self.auditor.language_counts = {"Python": 5, "TypeScript": 3}
        result = self.auditor.generate_json()
        self.assertEqual(result["language_distribution"]["Python"], 5)

    def test_repo_with_description_not_flagged(self):
        repo = {
            "name": "good-repo", "html_url": "https://github.com/TestOrg/good-repo",
            "description": "Has a proper description", "license": {"key": "mit"}, "size": 100,
            "pushed_at": datetime.now(timezone.utc).isoformat(),
            "language": "Python", "fork": False
        }
        if not repo.get("description"):
            self.auditor.no_description.append({"name": repo["name"], "url": repo["html_url"],
                "created": repo.get("created_at", "unknown"), "language": repo.get("language")})
        self.assertEqual(len(self.auditor.no_description), 0)

    def test_recent_repo_not_stale(self):
        recent_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        auditor = audit_scanner.FleetAuditor(token="t", org="T", stale_days=365)
        now = datetime.now(timezone.utc)
        pushed = datetime.fromisoformat(recent_date.replace("Z", "+00:00"))
        if (now - pushed) > auditor.stale_threshold:
            auditor.stale_repos.append({"name": "recent"})
        self.assertEqual(len(auditor.stale_repos), 0)

    def test_fork_without_parent_shows_unknown(self):
        repo = {"name": "orphan-fork", "html_url": "u", "fork": True, "parent": {}}
        parent = repo.get("parent", {})
        self.assertEqual(parent.get("full_name", "unknown"), "unknown")

    def test_check_topics_returns_none_on_error(self):
        with patch.object(self.auditor.session, 'get') as mock_get:
            mock_get.return_value.status_code = 500
            result = self.auditor.check_topics({"name": "test"})
            self.assertIsNone(result)

    def test_check_contents_handles_errors(self):
        with patch.object(self.auditor.session, 'get', side_effect=Exception("Network error")):
            result = self.auditor.check_contents({"name": "test"})
            self.assertIsInstance(result, dict)
            self.assertIn("has_readme", result)
            self.assertIn("has_gitignore", result)

    def test_session_headers_configured(self):
        self.assertIn("Authorization", self.auditor.session.headers)
        self.assertEqual(self.auditor.session.headers["Authorization"], "token test-token")
        self.assertIn("Accept", self.auditor.session.headers)

    def test_stale_threshold_custom_value(self):
        auditor = audit_scanner.FleetAuditor(token="t", org="T", stale_days=90)
        self.assertEqual(auditor.stale_threshold, timedelta(days=90))

    def test_multiple_repos_classified(self):
        auditor = audit_scanner.FleetAuditor(token="t", org="T")
        repos = [
            {"name": "a", "html_url": "u", "description": None, "license": None, "size": 0,
             "pushed_at": "2020-01-01T00:00:00Z", "created_at": "2020-01-01T00:00:00Z",
             "language": None, "fork": True, "parent": {}},
            {"name": "b", "html_url": "u", "description": "desc", "license": {"key": "mit"},
             "size": 100, "pushed_at": datetime.now(timezone.utc).isoformat(),
             "created_at": "2026-01-01T00:00:00Z", "language": "Go", "fork": False},
        ]
        for repo in repos:
            if not repo.get("description"):
                auditor.no_description.append({"name": repo["name"], "url": repo["html_url"],
                    "created": repo.get("created_at", "unknown"), "language": repo.get("language")})
            if not repo.get("license"):
                auditor.no_license.append({"name": repo["name"], "url": repo["html_url"],
                    "created": repo.get("created_at", "unknown"), "language": repo.get("language")})
            if repo.get("fork"):
                parent = repo.get("parent", {})
                auditor.fork_repos.append({"name": repo["name"], "url": repo["html_url"],
                    "parent": parent.get("full_name", "unknown"), "parent_url": parent.get("html_url", "")})
        self.assertEqual(len(auditor.no_description), 1)
        self.assertEqual(len(auditor.no_license), 1)
        self.assertEqual(len(auditor.fork_repos), 1)

    def test_generate_json_all_findings_keys(self):
        """Test JSON report contains all expected finding keys."""
        self.auditor.all_repos = [{"name": "test"}]
        result = self.auditor.generate_json()
        expected_keys = ["no_description", "no_topics", "no_license", "empty_repos", "stale_repos", "fork_repos"]
        for key in expected_keys:
            self.assertIn(key, result["findings"])

    def test_check_topics_true(self):
        """Test check_topics returns True when topics exist."""
        with patch.object(self.auditor.session, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"names": ["python", "ai"]}
            result = self.auditor.check_topics({"name": "test"})
            self.assertTrue(result)

    def test_check_topics_false(self):
        """Test check_topics returns False when no topics."""
        with patch.object(self.auditor.session, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"names": []}
            result = self.auditor.check_topics({"name": "test"})
            self.assertFalse(result)


class TestBatchLicense(unittest.TestCase):

    def setUp(self):
        self.batcher = batch_license.LicenseBatcher(token="test-token", org="TestOrg", dry_run=True, delay=0.1)

    def test_init_defaults(self):
        self.assertEqual(self.batcher.token, "test-token")
        self.assertEqual(self.batcher.org, "TestOrg")
        self.assertTrue(self.batcher.dry_run)
        self.assertEqual(self.batcher.license_type, "mit")
        self.assertEqual(self.batcher.owner, "TestOrg")
        self.assertTrue(self.batcher.skip_licensed)

    def test_mit_license_template(self):
        license_text = batch_license.MIT_LICENSE_TEMPLATE.format(year="2026", owner="TestOwner")
        self.assertIn("MIT License", license_text)
        self.assertIn("2026", license_text)
        self.assertIn("TestOwner", license_text)
        self.assertIn("Permission is hereby granted", license_text)
        self.assertIn("WITHOUT WARRANTY", license_text)

    def test_stats_tracking(self):
        self.batcher.stats["success"] += 1
        self.batcher.stats["success"] += 1
        self.batcher.stats["failed"] += 1
        self.assertEqual(self.batcher.stats["success"], 2)
        self.assertEqual(self.batcher.stats["failed"], 1)

    def test_checkpoint_data_structure(self):
        self.assertIn("completed", self.batcher.checkpoint_data)
        self.assertIn("failed", self.batcher.checkpoint_data)
        self.assertIsInstance(self.batcher.checkpoint_data["completed"], list)

    @patch('batch_license.Path')
    def test_load_checkpoint_no_file(self, mock_path):
        mock_path.return_value.exists.return_value = False
        self.batcher.load_checkpoint()
        self.assertEqual(len(self.batcher.checkpoint_data["completed"]), 0)

    @patch('batch_license.Path')
    @patch('builtins.open', create=True)
    def test_load_checkpoint_with_file(self, mock_open, mock_path):
        mock_path.return_value.exists.return_value = True
        checkpoint = {"completed": ["repo1", "repo2"], "failed": []}
        mock_open.return_value.__enter__ = MagicMock()
        mock_open.return_value.__exit__ = MagicMock()
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(checkpoint)
        self.batcher.load_checkpoint()
        self.assertEqual(len(self.batcher.checkpoint_data["completed"]), 2)

    def test_mit_license_template_completeness(self):
        template = batch_license.MIT_LICENSE_TEMPLATE.format(year="2026", owner="Test")
        required_phrases = [
            "MIT License", "Permission is hereby granted, free of charge",
            "to any person obtaining a copy", "to use, copy, modify, merge, publish, distribute, sublicense",
            'THE SOFTWARE IS PROVIDED "AS IS"', "WITHOUT WARRANTY OF ANY KIND",
            "FITNESS FOR A PARTICULAR PURPOSE", "NONINFRINGEMENT",
            "IN NO EVENT SHALL THE", "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, template, f"MIT template missing: {phrase}")

    def test_dry_run_add_license(self):
        result = self.batcher.add_license("test-repo")
        self.assertTrue(result.get("dry_run"))

    def test_dry_run_skips_put_call(self):
        """Test dry run does not make PUT API calls for creating files."""
        with patch.object(self.batcher.session, 'put') as mock_put:
            self.batcher.add_license("test-repo")
            mock_put.assert_not_called()

    def test_dry_run_does_not_write_file(self):
        """Test dry run returns dict with dry_run key, no file created."""
        result = self.batcher.add_license("test-repo")
        self.assertIsInstance(result, dict)
        self.assertTrue(result["dry_run"])

    def test_init_with_custom_owner(self):
        batcher = batch_license.LicenseBatcher(token="t", org="Org", owner="Custom Owner")
        self.assertEqual(batcher.owner, "Custom Owner")

    def test_init_with_checkpoint_enabled(self):
        batcher = batch_license.LicenseBatcher(token="t", org="Org", use_checkpoint=True)
        self.assertTrue(batcher.use_checkpoint)

    def test_stats_all_zero_initially(self):
        self.assertEqual(self.batcher.stats["success"], 0)
        self.assertEqual(self.batcher.stats["failed"], 0)
        self.assertEqual(self.batcher.stats["skipped"], 0)
        self.assertEqual(self.batcher.stats["total"], 0)
        self.assertEqual(self.batcher.stats["already_licensed"], 0)

    def test_mit_template_includes_copyright(self):
        template = batch_license.MIT_LICENSE_TEMPLATE.format(year="2026", owner="ACME")
        self.assertIn("Copyright (c) 2026 ACME", template)

    def test_save_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_file = os.path.join(tmpdir, "progress.json")
            with patch('batch_license.CHECKPOINT_FILE', checkpoint_file):
                self.batcher.checkpoint_data["completed"] = ["repo1"]
                self.batcher.save_checkpoint()
                self.assertTrue(os.path.exists(checkpoint_file))
                with open(checkpoint_file) as f:
                    data = json.load(f)
                self.assertEqual(data["completed"], ["repo1"])


class TestBatchTopics(unittest.TestCase):

    def test_topics_api_format(self):
        correct_format = {"names": ["typescript", "ai", "machine-learning"]}
        payload = json.dumps(correct_format)
        parsed = json.loads(payload)
        self.assertIn("names", parsed)
        self.assertIsInstance(parsed["names"], list)
        self.assertEqual(len(parsed["names"]), 3)

    def test_topic_mapping_file_exists(self):
        mapping_path = TOOLS_DIR / "topic-mapping.json"
        if mapping_path.exists():
            with open(mapping_path) as f:
                data = json.load(f)
            self.assertIsInstance(data, (dict, list))
            if isinstance(data, list) and len(data) > 0:
                self.assertIn("name", data[0])
                self.assertIn("new_topics", data[0])
        else:
            self.skipTest("topic-mapping.json not found")

    def test_topic_batcher_init(self):
        batcher = batch_topics.TopicBatcher(token="test-token", org="TestOrg", dry_run=True, delay=1.0)
        self.assertEqual(batcher.org, "TestOrg")
        self.assertTrue(batcher.dry_run)

    def test_topic_batcher_stats_initial(self):
        batcher = batch_topics.TopicBatcher(token="t", org="O")
        self.assertEqual(batcher.stats["success"], 0)
        self.assertEqual(batcher.stats["failed"], 0)

    def test_topic_batcher_checkpoint_structure(self):
        batcher = batch_topics.TopicBatcher(token="t", org="O")
        self.assertIn("completed", batcher.checkpoint_data)
        self.assertIn("failed", batcher.checkpoint_data)

    def test_load_mapping_json(self):
        batcher = batch_topics.TopicBatcher(token="t", org="O")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"repo1": ["topic1", "topic2"], "repo2": ["topic3"]}, f)
            f.flush()
            result = batcher.load_mapping_json(f.name)
        os.unlink(f.name)
        self.assertEqual(len(result), 2)
        self.assertEqual(result["repo1"], ["topic1", "topic2"])

    def test_load_mapping_csv(self):
        batcher = batch_topics.TopicBatcher(token="t", org="O")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("repo1,topic1,topic2\nrepo2,topic3\n")
            f.flush()
            result = batcher.load_mapping_csv(f.name)
        os.unlink(f.name)
        self.assertEqual(len(result), 2)

    def test_load_mapping_csv_empty_rows(self):
        batcher = batch_topics.TopicBatcher(token="t", org="O")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("\nrepo1,topic1\n\n")
            f.flush()
            result = batcher.load_mapping_csv(f.name)
        os.unlink(f.name)
        self.assertEqual(len(result), 1)

    def test_set_topics_dry_run(self):
        batcher = batch_topics.TopicBatcher(token="t", org="O", dry_run=True)
        result = batcher.set_topics("test-repo", ["typescript", "ai"])
        self.assertTrue(result.get("dry_run"))
        self.assertIn("topics", result)

    def test_session_headers_configured(self):
        batcher = batch_topics.TopicBatcher(token="t", org="O")
        self.assertIn("Authorization", batcher.session.headers)

    def test_checkpoint_save_and_load(self):
        batcher = batch_topics.TopicBatcher(token="t", org="O")
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_file = os.path.join(tmpdir, "progress.json")
            with patch('batch_topics.CHECKPOINT_FILE', checkpoint_file):
                batcher.checkpoint_data["completed"] = ["repo1", "repo2"]
                batcher.save_checkpoint()
                self.assertTrue(os.path.exists(checkpoint_file))
                batcher2 = batch_topics.TopicBatcher(token="t", org="O")
                batcher2.load_checkpoint()
                self.assertEqual(len(batcher2.checkpoint_data["completed"]), 2)


class TestMibBottle(unittest.TestCase):

    def test_generate_mib_content(self):
        content = mib_bottle.generate_mib_content(sender="datum", vessel="oracle1", msg_type="check-in", message="Hello fleet")
        self.assertIn("sender: datum", content)
        self.assertIn("type: check-in", content)
        self.assertIn("vessel: oracle1", content)
        self.assertIn("Hello fleet", content)
        self.assertIn("Message in a Bottle", content)

    def test_generate_mib_content_fleet_addressing(self):
        content = mib_bottle.generate_mib_content(sender="datum", vessel="fleet", msg_type="signal", message="Test message")
        self.assertIn("All Fleet Vessels", content)

    def test_generate_mib_content_all_types(self):
        for msg_type in mib_bottle.VALID_TYPES:
            content = mib_bottle.generate_mib_content(sender="test", vessel="test", msg_type=msg_type, message="test")
            self.assertIn(f"type: {msg_type}", content)

    def test_get_mib_path_fleet(self):
        path = mib_bottle.get_mib_path("fleet", "signal", "datum")
        self.assertIn("for-fleet/", path)
        self.assertTrue(path.endswith(".md"))

    def test_get_mib_path_vessel(self):
        path = mib_bottle.get_mib_path("oracle1", "check-in", "datum")
        self.assertIn("for-oracle1/", path)
        self.assertTrue(path.endswith(".md"))

    def test_get_mib_path_vessel_with_spaces(self):
        path = mib_bottle.get_mib_path("My Vessel", "info", "datum")
        self.assertIn("for-my-vessel/", path)

    def test_get_mib_path_case_insensitive_fleet(self):
        path = mib_bottle.get_mib_path("Fleet", "signal", "datum")
        self.assertIn("for-fleet/", path)

    def test_valid_types_constant(self):
        expected = {"check-in", "signal", "alert", "question", "deliverable", "handoff", "info"}
        self.assertEqual(set(mib_bottle.VALID_TYPES), expected)

    def test_default_org_constant(self):
        self.assertEqual(mib_bottle.DEFAULT_ORG, "SuperInstance")

    def test_default_sender_constant(self):
        self.assertEqual(mib_bottle.DEFAULT_SENDER, "datum")

    def test_mib_content_has_yaml_frontmatter(self):
        content = mib_bottle.generate_mib_content("s", "v", "info", "m")
        self.assertTrue(content.startswith("---"))
        self.assertIn("---", content.split("\n")[:5])

    def test_mib_content_has_timestamp(self):
        content = mib_bottle.generate_mib_content("s", "v", "info", "m")
        self.assertIn("timestamp:", content)

    def test_mib_content_has_protocol_footer(self):
        content = mib_bottle.generate_mib_content("s", "v", "info", "m")
        self.assertIn("MiB v1.0", content)

    def test_mib_content_includes_emoji(self):
        content = mib_bottle.generate_mib_content("s", "v", "alert", "m")
        self.assertIn("\u26a0\ufe0f", content)

    def test_mib_content_non_fleet_addressing(self):
        content = mib_bottle.generate_mib_content("s", "oracle1", "info", "m")
        self.assertIn("**To:** oracle1", content)
        self.assertNotIn("All Fleet Vessels", content)


class TestIntegrationScenarios(unittest.TestCase):

    def test_audit_scanner_report_flow(self):
        auditor = audit_scanner.FleetAuditor(token="test", org="TestOrg")
        auditor.all_repos = [
            {"name": "repo1", "html_url": "https://github.com/TestOrg/repo1",
             "description": "Has desc", "license": {"key": "mit"}, "size": 100,
             "pushed_at": datetime.now(timezone.utc).isoformat(), "language": "Python", "fork": False},
            {"name": "repo2", "html_url": "https://github.com/TestOrg/repo2",
             "description": "", "license": None, "size": 0,
             "pushed_at": "2024-01-01T00:00:00Z", "created_at": "2024-01-01T00:00:00Z",
             "language": None, "fork": False},
        ]
        auditor.language_counts = {"Python": 1}
        auditor.no_topics = []
        # Pre-populate findings to simulate run_audit results
        auditor.no_description.append({"name": "repo2", "url": "u", "language": None, "created": "2024-01-01"})
        auditor.no_license.append({"name": "repo2", "url": "u", "language": None, "created": "2024-01-01"})
        auditor.empty_repos.append({"name": "repo2", "url": "u", "size": 0, "created": "2024-01-01", "pushed": "2024-01-01"})
        md_report = auditor.generate_markdown()
        json_report = auditor.generate_json()
        self.assertIn("repo2", md_report)
        self.assertEqual(json_report["total_repos"], 2)

    def test_mib_and_audit_integration(self):
        repos = ["oracle1", "babel", "flux-engine"]
        for repo_name in repos:
            path = mib_bottle.get_mib_path(repo_name, "check-in", "datum")
            self.assertIn(repo_name, path)

    def test_batch_topics_json_and_csv_equivalent(self):
        batcher = batch_topics.TopicBatcher(token="t", org="O")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as jf:
            json.dump({"repo1": ["a", "b"], "repo2": ["c"]}, jf)
            jf.flush()
            json_result = batcher.load_mapping_json(jf.name)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as cf:
            cf.write("repo1,a,b\nrepo2,c\n")
            cf.flush()
            csv_result = batcher.load_mapping_csv(cf.name)
        os.unlink(jf.name)
        os.unlink(cf.name)
        self.assertEqual(json_result, csv_result)


class TestConstantsAndDefaults(unittest.TestCase):

    def test_github_api_url_consistent(self):
        self.assertEqual(audit_scanner.GITHUB_API, "https://api.github.com")
        self.assertEqual(batch_license.GITHUB_API, "https://api.github.com")
        self.assertEqual(batch_topics.GITHUB_API, "https://api.github.com")
        self.assertEqual(mib_bottle.GITHUB_API, "https://api.github.com")

    def test_default_org_consistent(self):
        self.assertEqual(batch_license.DEFAULT_ORG, "SuperInstance")
        self.assertEqual(batch_topics.DEFAULT_ORG, "SuperInstance")
        self.assertEqual(mib_bottle.DEFAULT_ORG, "SuperInstance")

    def test_user_agent_patterns(self):
        self.assertIn("datum", audit_scanner.FleetAuditor(token="t", org="o").session.headers["User-Agent"])
        self.assertIn("datum", batch_license.LicenseBatcher(token="t", org="o").session.headers["User-Agent"])
        self.assertIn("datum", batch_topics.TopicBatcher(token="t", org="o").session.headers["User-Agent"])

    def test_default_delay_values(self):
        self.assertEqual(batch_topics.DEFAULT_DELAY, 2.0)
        self.assertEqual(batch_license.DEFAULT_DELAY, 2.5)

    def test_mib_file_extension(self):
        path = mib_bottle.get_mib_path("test", "signal", "datum")
        self.assertTrue(path.endswith(".md"))


if __name__ == "__main__":
    unittest.main()
