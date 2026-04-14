"""Tests for core framework — Agent, AgentConfig, MessageBus, SecretProxy."""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from datum_runtime.superagent.core import (
    Agent, AgentConfig, AgentMessage, AgentState, MessageType,
    MessageBus, SecretProxy, SuperagentError,
)


class TestAgentConfig(unittest.TestCase):
    """Test AgentConfig loading and saving."""

    def test_default_config(self):
        cfg = AgentConfig()
        self.assertEqual(cfg.role, "generic")
        self.assertEqual(cfg.log_level, "INFO")

    def test_from_kwargs(self):
        cfg = AgentConfig(name="test", role="keeper", keeper_url="http://localhost:9999")
        self.assertEqual(cfg.name, "test")
        self.assertEqual(cfg.role, "keeper")

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "agent.toml")
            cfg = AgentConfig(name="test", role="keeper", capabilities=["audit", "scan"])
            cfg.save(path)
            loaded = AgentConfig.from_toml(path)
            self.assertEqual(loaded.name, "test")
            self.assertEqual(loaded.role, "keeper")
            self.assertEqual(loaded.capabilities, ["audit", "scan"])


class TestAgentMessage(unittest.TestCase):
    """Test message creation and serialization."""

    def test_create_message(self):
        msg = AgentMessage(
            msg_type=MessageType.TASK,
            sender="oracle",
            recipient="datum",
            subject="audit please",
            body={"type": "workshop"},
        )
        self.assertEqual(msg.msg_type, MessageType.TASK)
        self.assertEqual(msg.sender, "oracle")

    def test_to_from_dict(self):
        msg = AgentMessage(sender="alice", recipient="bob", subject="hello")
        d = msg.to_dict()
        msg2 = AgentMessage.from_dict(d)
        self.assertEqual(msg2.sender, "alice")
        self.assertEqual(msg2.recipient, "bob")
        self.assertEqual(msg2.subject, "hello")

    def test_to_json(self):
        msg = AgentMessage(sender="a", recipient="b", body={"key": "val"})
        j = msg.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["sender"], "a")
        self.assertEqual(parsed["body"]["key"], "val")


class TestMessageBus(unittest.TestCase):
    """Test in-process message bus."""

    def test_subscribe_and_publish(self):
        bus = MessageBus()
        received = []

        def handler(msg):
            received.append(msg)

        bus.subscribe("test-agent", handler)
        msg = AgentMessage(sender="oracle", recipient="test-agent", subject="task")
        delivered = bus.publish(msg)
        self.assertEqual(delivered, 1)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].subject, "task")

    def test_broadcast(self):
        bus = MessageBus()
        received = []

        def handler(msg):
            received.append(msg)

        bus.subscribe("*", handler)
        msg = AgentMessage(sender="oracle", recipient="*", subject="alert!")
        bus.publish(msg)
        self.assertTrue(len(received) >= 1)

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "bus.json")
            bus = MessageBus(persist_path=path)
            bus.publish(AgentMessage(sender="a", recipient="b", subject="test"))
            self.assertTrue(Path(path).exists())

            # Load from persistence
            bus2 = MessageBus(persist_path=path)
            self.assertEqual(len(bus2.history), 1)


class TestAgent(unittest.TestCase):
    """Test base Agent class."""

    def test_create_agent(self):
        cfg = AgentConfig(name="test-agent", role="tester")
        agent = Agent(config=cfg)
        self.assertEqual(agent.name, "test-agent")
        self.assertEqual(agent.role, "generic")
        self.assertEqual(agent.state, AgentState.UNINITIALIZED)

    def test_auto_name(self):
        agent = Agent()
        self.assertTrue(agent.name.startswith("generic-"))

    def test_lifecycle(self):
        agent = Agent(config=AgentConfig(name="lc-test"))
        self.assertEqual(agent.state, AgentState.UNINITIALIZED)
        agent.activate()
        self.assertEqual(agent.state, AgentState.ACTIVE)
        agent.idle()
        self.assertEqual(agent.state, AgentState.IDLE)
        agent.retire()
        self.assertEqual(agent.state, AgentState.RETIRED)

    def test_journal(self):
        with tempfile.TemporaryDirectory() as td:
            agent = Agent(config=AgentConfig(name="j-test", repo_path=td))
            agent._journal("TEST", "This is a test entry")
            journal_path = os.path.join(td, "JOURNAL.md")
            self.assertTrue(os.path.exists(journal_path))
            content = Path(journal_path).read_text()
            self.assertIn("TEST", content)
            self.assertIn("This is a test entry", content)


class TestSecretProxy(unittest.TestCase):
    """Test SecretProxy (without running Keeper)."""

    def test_env_fallback(self):
        os.environ["TEST_SECRET_KEY"] = "test-value-123"
        proxy = SecretProxy("http://localhost:19999", "test-agent")
        val = proxy.request_secret("test_secret_key", "testing", ttl_seconds=60)
        self.assertEqual(val, "test-value-123")
        del os.environ["TEST_SECRET_KEY"]


if __name__ == "__main__":
    unittest.main()
