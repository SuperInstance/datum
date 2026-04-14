"""
superagent.core — Base classes for all SuperInstance agents.

Every agent in the fleet inherits from ``Agent``. The class provides:
    - Lifecycle management (init -> onboard -> active -> idle -> retire)
    - Structured logging to workshop journal
    - Secret access through the SecretProxy (never stores secrets locally)
    - Message passing through the MessageBus
    - Configuration via TOML files
"""

from __future__ import annotations

import json
import logging
import urllib.error
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class SuperagentError(Exception):
    """Base error for all framework errors."""
    pass


class OnboardingError(SuperagentError):
    """Raised when onboarding to a Keeper fails."""
    pass


class SecretAccessError(SuperagentError):
    """Raised when the Keeper denies or fails a secret request."""
    pass


class BoundaryViolationError(SuperagentError):
    """Raised when a secret would leave the SuperInstance boundary."""
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AgentState(Enum):
    """Lifecycle states for a fleet agent."""
    UNINITIALIZED = "uninitialized"
    ONBOARDED = "onboarded"
    ACTIVE = "active"
    IDLE = "idle"
    RETIRED = "retired"


class MessageType(Enum):
    """Types of inter-agent messages."""
    TASK = "task"           # work assignment
    STATUS = "status"       # status update
    QUERY = "query"         # question / request for info
    RESPONSE = "response"   # answer to a query
    ALERT = "alert"         # urgent notification
    HEARTBEAT = "heartbeat"  # liveness ping
    SECRET_REQ = "secret_req"  # request secret from keeper
    SECRET_RES = "secret_res"  # keeper responds with secret


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    """Configuration loaded from agent.toml or CLI flags."""
    name: str = ""
    role: str = "generic"
    keeper_url: str = "http://localhost:7742"
    repo_path: str = "./workshop"
    capabilities: List[str] = field(default_factory=list)
    workshop_template: str = "default"
    log_level: str = "INFO"

    @classmethod
    def from_toml(cls, path: str) -> "AgentConfig":
        """Load config from a TOML file."""
        import toml
        p = Path(path)
        if not p.exists():
            return cls()
        data = toml.loads(p.read_text())
        agent = data.get("agent", {})
        keeper = data.get("keeper", {})
        workshop = data.get("workshop", {})
        log = data.get("logging", {})
        return cls(
            name=agent.get("name", ""),
            role=agent.get("role", "generic"),
            keeper_url=f"http://{keeper.get('host', 'localhost')}:{keeper.get('port', 7742)}",
            repo_path=workshop.get("path", "./workshop"),
            capabilities=agent.get("capabilities", []),
            workshop_template=workshop.get("template", "default"),
            log_level=log.get("level", "INFO"),
        )

    def save(self, path: str) -> None:
        """Write config to a TOML file."""
        import toml
        data = {
            "agent": {
                "name": self.name,
                "role": self.role,
                "capabilities": self.capabilities,
            },
            "keeper": {
                "host": self.keeper_url.replace("http://", "").split(":")[0],
                "port": int(self.keeper_url.split(":")[-1]),
            },
            "workshop": {
                "path": self.repo_path,
                "template": self.workshop_template,
            },
            "logging": {
                "level": self.log_level,
            },
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(toml.dumps(data))


@dataclass
class AgentMessage:
    """A message on the fleet message bus."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    msg_type: MessageType = MessageType.STATUS
    sender: str = ""
    recipient: str = ""       # empty = broadcast
    subject: str = ""
    body: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    in_reply_to: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.msg_type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "subject": self.subject,
            "body": self.body,
            "timestamp": self.timestamp,
            "in_reply_to": self.in_reply_to,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AgentMessage":
        return cls(
            id=d.get("id", uuid.uuid4().hex[:12]),
            msg_type=MessageType(d.get("type", "status")),
            sender=d.get("sender", ""),
            recipient=d.get("recipient", ""),
            subject=d.get("subject", ""),
            body=d.get("body", {}),
            timestamp=d.get("timestamp", time.time()),
            in_reply_to=d.get("in_reply_to", ""),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ---------------------------------------------------------------------------
# Message Bus
# ---------------------------------------------------------------------------

class MessageBus:
    """
    In-process pub/sub message bus for agent communication.

    Agents subscribe to topics (usually their name or role) and receive
    matching messages. Messages can be persisted to disk for the workshop
    journal.
    """

    def __init__(self, persist_path: Optional[str] = None):
        self._subscribers: Dict[str, List[Callable[[AgentMessage], None]]] = {}
        self._history: List[AgentMessage] = []
        self._persist_path = persist_path
        self._load_history()

    def subscribe(self, topic: str, handler: Callable[[AgentMessage], None]) -> None:
        """Register a handler for a topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Callable[[AgentMessage], None]) -> None:
        """Remove a handler from a topic."""
        if topic in self._subscribers:
            self._subscribers[topic] = [
                h for h in self._subscribers[topic] if h != handler
            ]

    def publish(self, message: AgentMessage) -> int:
        """
        Publish a message. Returns number of handlers that received it.

        Routes to: exact recipient, sender's role (broadcast), and "*" (catch-all).
        """
        self._history.append(message)
        self._persist()
        delivered = 0

        # Direct recipient
        targets = [message.recipient, message.sender, "*"]
        for target in targets:
            for handler in self._subscribers.get(target, []):
                try:
                    handler(message)
                    delivered += 1
                except Exception as e:
                    logging.getLogger("superagent.bus").error(
                        f"Handler error on topic '{target}': {e}"
                    )
        return delivered

    def query(self, topic: str, timeout: float = 5.0) -> List[AgentMessage]:
        """Return recent messages matching a topic from history."""
        cutoff = time.time() - timeout
        return [m for m in self._history if m.recipient == topic and m.timestamp >= cutoff]

    @property
    def history(self) -> List[AgentMessage]:
        return list(self._history)

    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            path = Path(self._persist_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            # Keep last 500 messages
            recent = self._history[-500:]
            data = [m.to_dict() for m in recent]
            path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logging.getLogger("superagent.bus").warning(f"Persist failed: {e}")

    def _load_history(self) -> None:
        if not self._persist_path:
            return
        try:
            path = Path(self._persist_path)
            if path.exists():
                data = json.loads(path.read_text())
                self._history = [AgentMessage.from_dict(d) for d in data]
        except Exception:
            self._history = []


# ---------------------------------------------------------------------------
# Secret Proxy — talks to Keeper, never stores secrets
# ---------------------------------------------------------------------------

class SecretProxy:
    """
    Client-side proxy for requesting secrets from the Keeper.

    CRITICAL DESIGN RULE: Secrets are requested on-demand and never persisted
    by the requesting agent. The proxy is stateless — it asks the Keeper,
    receives a time-limited token or value, uses it, and forgets it.
    """

    def __init__(self, keeper_url: str, agent_name: str):
        self.keeper_url = keeper_url.rstrip("/")
        self.agent_name = agent_name
        self._logger = logging.getLogger(f"superagent.proxy.{agent_name}")

    def request_secret(
        self,
        key: str,
        purpose: str,
        ttl_seconds: int = 300,
    ) -> str:
        """
        Request a secret from the Keeper.

        Args:
            key: Secret identifier (e.g. "github_pat", "openai_api_key")
            purpose: WHY the secret is needed (audited by Keeper)
            ttl_seconds: How long the secret should be valid

        Returns:
            The secret value (or a time-limited token)

        Raises:
            SecretAccessError: If Keeper denies or is unreachable
        """
        self._logger.info(f"Requesting secret '{key}' for purpose: {purpose}")
        # In standalone mode (no keeper running), check local env
        try:
            import urllib.request
            payload = json.dumps({
                "agent": self.agent_name,
                "key": key,
                "purpose": purpose,
                "ttl": ttl_seconds,
            }).encode()
            req = urllib.request.Request(
                f"{self.keeper_url}/api/secrets/get",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                if result.get("approved"):
                    self._logger.info(f"Secret '{key}' approved by Keeper")
                    return result["value"]
                else:
                    reason = result.get("reason", "denied")
                    raise SecretAccessError(f"Keeper denied '{key}': {reason}")
        except urllib.error.URLError:
            # Keeper not running — fall back to env var with warning
            self._logger.warning(
                f"Keeper unreachable at {self.keeper_url}, "
                f"falling back to env var for '{key}'"
            )
            env_val = os.environ.get(key.upper()) or os.environ.get(key)
            if env_val:
                self._logger.warning(f"USING ENV FALLBACK FOR '{key}' — not audited")
                return env_val
            raise SecretAccessError(
                f"Keeper unreachable and no env var for '{key}'"
            )

    def github_token(self, purpose: str = "git operations") -> str:
        """Shorthand for requesting the GitHub PAT."""
        return self.request_secret("github_pat", purpose)

    def api_key(self, service: str, purpose: str = "api call") -> str:
        """Request an API key for a service (e.g. 'openai', 'anthropic')."""
        return self.request_secret(f"{service}_api_key", purpose)


# ---------------------------------------------------------------------------
# Base Agent
# ---------------------------------------------------------------------------

class Agent:
    """
    Base class for all SuperInstance fleet agents.

    Subclass this and implement:
        - ``role`` class property
        - ``run()`` for the main work loop
        - Optional: ``handle_message()`` for bus messages
    """

    role: str = "generic"
    description: str = "A SuperInstance agent"

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs):
        self.config = config or AgentConfig(**kwargs)
        if self.config.name:
            self.name = self.config.name
        else:
            self.name = f"{self.role}-{uuid.uuid4().hex[:6]}"
            self.config.name = self.name

        self.state = AgentState.UNINITIALIZED
        self.agent_id = uuid.uuid4().hex
        self.bus = MessageBus(
            persist_path=os.path.join(self.config.repo_path, ".superagent", "bus.json")
        )
        self.proxy = SecretProxy(self.config.keeper_url, self.name)
        self._logger = self._setup_logging()
        self._journal_path = os.path.join(self.config.repo_path, "JOURNAL.md")
        self._message_handler: Optional[Callable[[AgentMessage], None]] = None

    # -- Lifecycle -------------------------------------------------------------

    def onboard(self, keeper_url: Optional[str] = None) -> bool:
        """
        Onboard to the Keeper. Registers the agent and receives confirmation.

        Returns True if onboarding succeeded.
        """
        if keeper_url:
            self.config.keeper_url = keeper_url
            self.proxy = SecretProxy(self.config.keeper_url, self.name)

        self._logger.info(f"Onboarding '{self.name}' to Keeper at {self.config.keeper_url}")
        try:
            import urllib.request
            payload = json.dumps({
                "agent_id": self.agent_id,
                "name": self.name,
                "role": self.role,
                "capabilities": self.config.capabilities,
            }).encode()
            req = urllib.request.Request(
                f"{self.config.keeper_url}/api/agents/register",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                if result.get("registered"):
                    self.state = AgentState.ONBOARDED
                    self._logger.info("Onboarding successful")
                    self._journal("ONBOARD", f"Onboarded to Keeper at {self.config.keeper_url}")
                    return True
                else:
                    self._logger.error(f"Onboarding rejected: {result.get('reason')}")
                    return False
        except urllib.error.URLError:
            self._logger.warning("Keeper unreachable — running in standalone mode")
            self.state = AgentState.ONBOARDED
            self._journal("ONBOARD", "Running standalone (Keeper not reachable)")
            return True

    def activate(self) -> None:
        """Transition to ACTIVE state."""
        self.state = AgentState.ACTIVE
        self._journal("ACTIVATE", f"Agent activated as {self.role}")
        self._logger.info(f"Agent '{self.name}' is now ACTIVE")

    def idle(self) -> None:
        """Transition to IDLE state."""
        self.state = AgentState.IDLE
        self._logger.info(f"Agent '{self.name}' is now IDLE")

    def retire(self) -> None:
        """Transition to RETIRED state. Workshop persists."""
        self.state = AgentState.RETIRED
        self._journal("RETIRE", f"Agent retired. Workshop at {self.config.repo_path}")
        self._logger.info(f"Agent '{self.name}' RETIRED — workshop preserved")

    # -- Message handling ------------------------------------------------------

    def listen(self, handler: Callable[[AgentMessage], None]) -> None:
        """Register a message handler on the bus for this agent."""
        self._message_handler = handler
        self.bus.subscribe(self.name, handler)
        self.bus.subscribe(self.role, handler)

    def send(self, recipient: str, subject: str, body: Dict[str, Any],
             msg_type: MessageType = MessageType.TASK) -> str:
        """Send a message to another agent (or broadcast if recipient='*')."""
        msg = AgentMessage(
            msg_type=msg_type,
            sender=self.name,
            recipient=recipient,
            subject=subject,
            body=body,
        )
        self.bus.publish(msg)
        self._logger.debug(f"Sent {msg_type.value} to '{recipient}': {subject}")
        return msg.id

    def broadcast(self, subject: str, body: Dict[str, Any]) -> str:
        """Broadcast a message to all agents."""
        return self.send("*", subject, body, MessageType.ALERT)

    # -- Journaling ------------------------------------------------------------

    def _journal(self, tag: str, content: str) -> None:
        """Append an entry to the workshop JOURNAL.md."""
        try:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            entry = f"\n## [{ts}] {tag}\n\n{content}\n"
            path = Path(self._journal_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                existing = path.read_text()
                path.write_text(existing + entry)
            else:
                path.write_text(f"# {self.name} — Work Journal\n\n{entry}")
        except Exception as e:
            self._logger.warning(f"Journal write failed: {e}")

    # -- Logging ---------------------------------------------------------------

    def _setup_logging(self) -> logging.Logger:
        """Set up structured logging."""
        logger = logging.getLogger(f"superagent.{self.role}.{self.name}")
        level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logger.setLevel(level)
        if not logger.handlers:
            handler = logging.StreamHandler()
            fmt = logging.Formatter(
                "[%(asctime)s] %(levelname)-5s %(name)s — %(message)s",
                datefmt="%H:%M:%S",
            )
            handler.setFormatter(fmt)
            logger.addHandler(handler)
        return logger

    # -- Main loop (override in subclass) --------------------------------------

    def run(self, **kwargs) -> None:
        """
        Main work loop. Override this in subclasses.

        The base implementation just activates, logs, and idles.
        """
        self.activate()
        self._logger.info(f"{self.role} agent '{self.name}' running (override run() for real work)")
        # Subclasses should implement their work here
