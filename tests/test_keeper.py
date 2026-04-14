"""Tests for Keeper Agent — secret storage, boundary enforcement, audit."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from datum_runtime.superagent.keeper import (
    KeeperAgent, SecretStore, AuditLog, AuditEntry,
    check_boundary, AgentRecord,
)
from datum_runtime.superagent.core import AgentConfig


class TestBoundaryEnforcement(unittest.TestCase):
    """Test SuperInstance boundary checking."""

    def test_internal_domain(self):
        is_internal, reason = check_boundary("http://localhost:7742/api/secrets")
        self.assertTrue(is_internal)

    def test_internal_127(self):
        is_internal, _ = check_boundary("http://127.0.0.1:3000/endpoint")
        self.assertTrue(is_internal)

    def test_blocked_pastebin(self):
        is_internal, reason = check_boundary("https://pastebin.com/raw/abc123")
        self.assertFalse(is_internal)
        self.assertIn("pastebin", reason)

    def test_blocked_discord(self):
        is_internal, reason = check_boundary("https://discord.com/api/webhooks/xyz")
        self.assertFalse(is_internal)

    def test_unknown_external(self):
        is_internal, reason = check_boundary("https://example.com/api")
        self.assertFalse(is_internal)
        self.assertIn("not in internal", reason)


class TestSecretStore(unittest.TestCase):
    """Test encrypted secret storage."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store_path = os.path.join(self.tmpdir, "secrets.json")
        self.store = SecretStore(self.store_path, "test-master-password")

    def test_set_and_get(self):
        self.store.set("github_pat", "ghp_test_value", description="Test token")
        val = self.store.get("github_pat")
        self.assertEqual(val, "ghp_test_value")

    def test_list_keys(self):
        self.store.set("key1", "val1")
        self.store.set("key2", "val2")
        keys = self.store.list_keys()
        self.assertIn("key1", keys)
        self.assertIn("key2", keys)

    def test_delete(self):
        self.store.set("key1", "val1")
        self.assertTrue(self.store.delete("key1"))
        self.assertIsNone(self.store.get("key1"))
        self.assertFalse(self.store.delete("nonexistent"))

    def test_persistence(self):
        self.store.set("persist_key", "persist_val")
        # Reload from disk
        store2 = SecretStore(self.store_path, "test-master-password")
        self.assertEqual(store2.get("persist_key"), "persist_val")

    def test_wrong_password(self):
        self.store.set("secret", "value")
        store2 = SecretStore(self.store_path, "wrong-password")
        # Should fail to decrypt (raises exception or returns None)
        val = store2.get("secret")
        # The decryption will fail — either return None or raise
        self.assertNotEqual(val, "value")


class TestAuditLog(unittest.TestCase):
    """Test audit log."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_path = os.path.join(self.tmpdir, "audit.json")
        self.audit = AuditLog(self.log_path)

    def test_record(self):
        entry = AuditEntry(
            timestamp=1000.0, requester="test-agent",
            secret_key="github_pat", purpose="git push",
            approved=True, reason="ok", ttl_requested=300,
        )
        self.audit.record(entry)
        self.assertEqual(len(self.audit.entries), 1)

    def test_recent(self):
        for i in range(10):
            self.audit.record(AuditEntry(
                timestamp=float(i), requester="agent", secret_key="key",
                purpose="test", approved=True,
            ))
        recent = self.audit.recent(5)
        self.assertEqual(len(recent), 5)

    def test_persistence(self):
        self.audit.record(AuditEntry(
            timestamp=1.0, requester="a", secret_key="k",
            purpose="p", approved=False, reason="test",
        ))
        audit2 = AuditLog(self.log_path)
        self.assertEqual(len(audit2.entries), 1)
        self.assertEqual(audit2.entries[0].reason, "test")


class TestKeeperAgent(unittest.TestCase):
    """Test Keeper agent operations (without HTTP server)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        cfg = AgentConfig(role="keeper", repo_path=self.tmpdir)
        self.keeper = KeeperAgent(config=cfg, name="keeper")
        self.keeper.init_store("test-password", os.path.join(self.tmpdir, "secrets.json"))
        self.keeper.init_audit(os.path.join(self.tmpdir, "audit.json"))

    def test_register_agent(self):
        result = self.keeper.register_agent(
            agent_id="abc123", name="test-agent", role="tester"
        )
        self.assertTrue(result["ok"])
        self.assertIn("abc123", self.keeper.agents)

    def test_register_requires_name(self):
        result = self.keeper.register_agent(agent_id="", name="", role="")
        self.assertFalse(result["ok"])

    def test_fulfill_secret_request(self):
        # Register agent and store secret
        self.keeper.register_agent("a1", "agent1", "worker")
        self.keeper.store.set("github_pat", "ghp_token")

        # Successful request
        result = self.keeper.fulfill_secret_request(
            requester="agent1", key="github_pat",
            purpose="git push to internal repo", ttl=300,
        )
        self.assertTrue(result["approved"])
        self.assertEqual(result["value"], "ghp_token")

    def test_deny_unregistered_agent(self):
        self.keeper.store.set("key", "val")
        result = self.keeper.fulfill_secret_request(
            requester="unknown", key="key", purpose="test"
        )
        self.assertFalse(result["approved"])
        self.assertIn("not registered", result["reason"])

    def test_deny_no_purpose(self):
        self.keeper.register_agent("a1", "agent1", "worker")
        self.keeper.store.set("key", "val")
        result = self.keeper.fulfill_secret_request(
            requester="agent1", key="key", purpose=""
        )
        self.assertFalse(result["approved"])

    def test_deny_boundary_violation(self):
        self.keeper.register_agent("a1", "agent1", "worker")
        self.keeper.store.set("github_pat", "ghp_token")
        result = self.keeper.fulfill_secret_request(
            requester="agent1", key="github_pat",
            purpose="post to pastebin.com/raw/abc", ttl=300,
        )
        self.assertFalse(result["approved"])
        self.assertIn("BOUNDARY", result["reason"])

    def test_deny_missing_secret(self):
        self.keeper.register_agent("a1", "agent1", "worker")
        result = self.keeper.fulfill_secret_request(
            requester="agent1", key="nonexistent", purpose="test"
        )
        self.assertFalse(result["approved"])
        self.assertIn("not found", result["reason"])


if __name__ == "__main__":
    unittest.main()
