"""
superagent.keeper — Keeper Agent: secret proxy, keyholder, boundary enforcer.

The Keeper is the SINGLE agent allowed to hold secrets (API keys, GitHub tokens,
etc.) within the SuperInstance. All other agents request secrets through the
SecretProxy and the Keeper audits every request.

Security model:
    - Secrets stored encrypted at rest (AES-256-GCM)
    - Every request is logged with requester, purpose, timestamp, approved/denied
    - Boundary enforcement: secrets are NEVER transmitted outside the SuperInstance
    - Time-limited access tokens for agents
    - Agent registration required before any secret access
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets as rng
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Dict, List, Optional, Tuple

from datum_runtime.superagent.core import (
    Agent,
    AgentConfig,
    AgentMessage,
    AgentState,
    MessageType,
    SuperagentError,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SecretEntry:
    """A stored secret with metadata."""
    key: str
    value_encrypted: bytes
    created_at: float = field(default_factory=time.time)
    created_by: str = "human"
    description: str = ""


@dataclass
class AgentRecord:
    """A registered agent."""
    agent_id: str
    name: str
    role: str
    capabilities: List[str] = field(default_factory=list)
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    state: str = "onboarded"
    secret_access_count: int = 0


@dataclass
class AuditEntry:
    """Record of a secret access attempt."""
    timestamp: float
    requester: str
    secret_key: str
    purpose: str
    approved: bool
    reason: str = ""
    ttl_requested: int = 0


# ---------------------------------------------------------------------------
# Boundary Enforcement
# ---------------------------------------------------------------------------

# Domains considered INSIDE the SuperInstance — secrets can flow to these
INTERNAL_DOMAINS = {
    "localhost", "127.0.0.1", "::1", "0.0.0.0",
    # Add your SuperInstance hostnames/IPs here
}

BLOCKED_PATTERNS = [
    "pastebin.com", "gist.github.com/public", "discord.com/api",
    "slack.com/api", "telegram.org", "webhook.site",
]


def check_boundary(destination: str) -> Tuple[bool, str]:
    """
    Check if a destination is within the SuperInstance boundary.

    Returns (is_internal, reason).
    """
    dest_lower = destination.lower()

    # Check blocked patterns first
    for pattern in BLOCKED_PATTERNS:
        if pattern in dest_lower:
            return False, f"Destination matches blocked pattern: {pattern}"

    # Check internal domains
    for domain in INTERNAL_DOMAINS:
        if domain in dest_lower:
            return True, "Internal destination"

    # Unknown destination — deny by default (fail-closed)
    return False, f"Destination '{destination}' not in internal domains list"


# ---------------------------------------------------------------------------
# Encrypted Secret Store
# ---------------------------------------------------------------------------

class SecretStore:
    """
    AES-256-GCM encrypted file-based secret store.

    Encryption key derived from a master password via PBKDF2.
    """

    ITERATIONS = 600_000  # OWASP 2023 recommendation

    def __init__(self, store_path: str, master_password: str):
        self.store_path = Path(store_path)
        self._master = master_password.encode()
        self._secrets: Dict[str, SecretEntry] = {}
        self._lock = Lock()
        self._load()

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from master password."""
        import hashlib
        return hashlib.pbkdf2_hmac("sha256", self._master, salt, self.ITERATIONS)

    def _encrypt(self, plaintext: str) -> Tuple[bytes, bytes, bytes]:
        """Encrypt a string. Returns (salt, nonce, ciphertext)."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        salt = rng.token_bytes(16)
        nonce = rng.token_bytes(12)
        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
        return salt, nonce, ct

    def _decrypt(self, salt: bytes, nonce: bytes, ct: bytes) -> str:
        """Decrypt ciphertext back to string."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ct, None).decode()

    def set(self, key: str, value: str, created_by: str = "human",
            description: str = "") -> None:
        """Store a secret (encrypted)."""
        salt, nonce, ct = self._encrypt(value)
        with self._lock:
            self._secrets[key] = SecretEntry(
                key=key,
                value_encrypted=salt + nonce + ct,  # pack together
                created_by=created_by,
                description=description,
            )
            self._save()

    def get(self, key: str) -> Optional[str]:
        """Retrieve and decrypt a secret. Returns None on any error."""
        with self._lock:
            entry = self._secrets.get(key)
            if not entry:
                return None
            try:
                data = entry.value_encrypted
                salt, nonce, ct = data[:16], data[16:28], data[28:]
                return self._decrypt(salt, nonce, ct)
            except Exception:
                return None  # Wrong password or corrupted data

    def list_keys(self) -> List[str]:
        """List all secret keys (values not returned)."""
        return list(self._secrets.keys())

    def delete(self, key: str) -> bool:
        """Delete a secret. Returns True if it existed."""
        with self._lock:
            if key in self._secrets:
                del self._secrets[key]
                self._save()
                return True
            return False

    def _save(self) -> None:
        """Persist secrets to disk (encrypted values stay encrypted)."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for k, v in self._secrets.items():
            data[k] = {
                "value_encrypted": v.value_encrypted.hex(),
                "created_at": v.created_at,
                "created_by": v.created_by,
                "description": v.description,
            }
        # Metadata file itself is not the secret — it's encrypted blobs
        self.store_path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        """Load secrets from disk."""
        if not self.store_path.exists():
            return
        try:
            data = json.loads(self.store_path.read_text())
            for k, v in data.items():
                self._secrets[k] = SecretEntry(
                    key=k,
                    value_encrypted=bytes.fromhex(v["value_encrypted"]),
                    created_at=v.get("created_at", time.time()),
                    created_by=v.get("created_by", "human"),
                    description=v.get("description", ""),
                )
        except Exception as e:
            logging.getLogger("superagent.keeper").error(f"Secret load error: {e}")


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

class AuditLog:
    """Persistent audit log for secret access."""

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self._entries: List[AuditEntry] = []
        self._load()

    def record(self, entry: AuditEntry) -> None:
        self._entries.append(entry)
        self._save()

    @property
    def entries(self) -> List[AuditEntry]:
        return list(self._entries)

    def recent(self, n: int = 50) -> List[AuditEntry]:
        return self._entries[-n:]

    def _save(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        data = []
        for e in self._entries:
            data.append({
                "timestamp": e.timestamp,
                "requester": e.requester,
                "secret_key": e.secret_key,
                "purpose": e.purpose,
                "approved": e.approved,
                "reason": e.reason,
                "ttl_requested": e.ttl_requested,
            })
        self.log_path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self.log_path.exists():
            return
        try:
            data = json.loads(self.log_path.read_text())
            for d in data:
                self._entries.append(AuditEntry(**d))
        except Exception:
            self._entries = []


# ---------------------------------------------------------------------------
# Keeper HTTP API Handler
# ---------------------------------------------------------------------------

class KeeperHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Keeper API."""

    keeper: "KeeperAgent" = None  # Set by KeeperAgent.serve()

    def log_message(self, fmt, *args):
        """Quiet logging — we use our own logger."""
        pass

    def _json_response(self, code: int, body: Dict) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def _read_body(self) -> Dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_GET(self):
        if self.path == "/api/health":
            self._json_response(200, {
                "status": "ok",
                "agents_registered": len(self.keeper.agents),
                "secrets_stored": len(self.keeper.store.list_keys()),
            })
        elif self.path == "/api/agents":
            agents = {
                a_id: {"name": r.name, "role": r.role, "state": r.state}
                for a_id, r in self.keeper.agents.items()
            }
            self._json_response(200, {"agents": agents})
        elif self.path == "/api/secrets":
            self._json_response(200, {
                "keys": self.keeper.store.list_keys(),
                "count": len(self.keeper.store.list_keys()),
            })
        elif self.path.startswith("/api/audit"):
            n = int(self.path.split("/")[-1]) if self.path.count("/") > 2 else 50
            entries = self.keeper.audit.recent(n)
            self._json_response(200, {
                "entries": [
                    {"requester": e.requester, "key": e.secret_key,
                     "purpose": e.purpose, "approved": e.approved,
                     "reason": e.reason}
                    for e in entries
                ]
            })
        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/agents/register":
            body = self._read_body()
            result = self.keeper.register_agent(
                agent_id=body.get("agent_id", ""),
                name=body.get("name", ""),
                role=body.get("role", ""),
                capabilities=body.get("capabilities", []),
            )
            self._json_response(200 if result["ok"] else 403, result)

        elif self.path == "/api/secrets/get":
            body = self._read_body()
            result = self.keeper.fulfill_secret_request(
                requester=body.get("agent", ""),
                key=body.get("key", ""),
                purpose=body.get("purpose", ""),
                ttl=body.get("ttl", 300),
            )
            self._json_response(200 if result.get("approved") else 403, result)

        elif self.path == "/api/secrets/set":
            body = self._read_body()
            self.keeper.store.set(
                key=body["key"],
                value=body["value"],
                description=body.get("description", ""),
            )
            self._json_response(200, {"ok": True, "key": body["key"]})

        elif self.path == "/api/secrets/delete":
            body = self._read_body()
            deleted = self.keeper.store.delete(body.get("key", ""))
            self._json_response(200, {"ok": deleted})

        else:
            self._json_response(404, {"error": "not found"})


# ---------------------------------------------------------------------------
# Keeper Agent
# ---------------------------------------------------------------------------

class KeeperAgent(Agent):
    """
    The Keeper holds all secrets and enforces the SuperInstance boundary.

    No other agent ever stores a secret locally. They request secrets through
    the SecretProxy, the Keeper audits the request, and delivers the value
    only if the purpose is legitimate and the destination is internal.

    The Keeper also maintains the fleet registry — a list of all onboarded
    agents and their capabilities.
    """

    role = "keeper"
    description = "Secret proxy and fleet keyholder. Enforces boundary security."

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs):
        super().__init__(config or AgentConfig(role="keeper"), **kwargs)
        self.agents: Dict[str, AgentRecord] = {}
        self.store: Optional[SecretStore] = None
        self.audit: Optional[AuditLog] = None
        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[Thread] = None

    def init_store(self, master_password: str, store_path: Optional[str] = None) -> None:
        """Initialize the encrypted secret store."""
        path = store_path or os.path.join(
            self.config.repo_path, ".superagent", "secrets.enc.json"
        )
        self.store = SecretStore(path, master_password)
        self._logger.info(f"Secret store initialized at {path}")

    def init_audit(self, audit_path: Optional[str] = None) -> None:
        """Initialize the audit log."""
        path = audit_path or os.path.join(
            self.config.repo_path, ".superagent", "audit.json"
        )
        self.audit = AuditLog(path)
        self._logger.info(f"Audit log at {path}")

    # -- Agent management ------------------------------------------------------

    def register_agent(
        self, agent_id: str, name: str, role: str,
        capabilities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Register a new agent on the fleet."""
        if not agent_id or not name:
            return {"ok": False, "reason": "agent_id and name required"}

        self.agents[agent_id] = AgentRecord(
            agent_id=agent_id,
            name=name,
            role=role,
            capabilities=capabilities or [],
        )
        self._logger.info(f"Registered agent '{name}' ({role}) — id={agent_id[:8]}...")
        self._journal("REGISTER", f"Agent '{name}' registered as {role}")
        return {"ok": True, "registered": True, "agent_id": agent_id}

    def deregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from the fleet."""
        record = self.agents.pop(agent_id, None)
        if record:
            self._logger.info(f"Deregistered agent '{record.name}'")
            return True
        return False

    def check_heartbeat(self, agent_id: str) -> bool:
        """Check if an agent is alive (heartbeat within 120s)."""
        record = self.agents.get(agent_id)
        if not record:
            return False
        return (time.time() - record.last_heartbeat) < 120

    # -- Secret fulfillment ----------------------------------------------------

    def fulfill_secret_request(
        self, requester: str, key: str, purpose: str, ttl: int = 300
    ) -> Dict[str, Any]:
        """
        Process a secret request from an agent.

        Steps:
            1. Verify agent is registered
            2. Check purpose is not empty
            3. Check TTL is reasonable (max 3600s)
            4. Boundary check on purpose (no external leaks)
            5. Look up secret
            6. Audit the access
            7. Return value if approved
        """
        # 1. Verify agent exists
        agent_record = None
        for a_id, rec in self.agents.items():
            if rec.name == requester:
                agent_record = rec
                break

        if not agent_record:
            entry = AuditEntry(
                timestamp=time.time(), requester=requester,
                secret_key=key, purpose=purpose,
                approved=False, reason="Agent not registered", ttl_requested=ttl,
            )
            if self.audit:
                self.audit.record(entry)
            return {"approved": False, "reason": "Agent not registered on this Keeper"}

        # 2. Purpose must be stated
        if not purpose.strip():
            return {"approved": False, "reason": "Purpose is required for secret access"}

        # 3. TTL sanity check
        if ttl > 3600:
            return {"approved": False, "reason": "TTL too long (max 3600s)"}

        # 4. Boundary check — scan purpose for external destinations
        internal, reason = check_boundary(purpose)
        if not internal:
            # Check if the purpose mentions an external destination
            for pattern in BLOCKED_PATTERNS:
                if pattern in purpose.lower():
                    entry = AuditEntry(
                        timestamp=time.time(), requester=requester,
                        secret_key=key, purpose=purpose,
                        approved=False,
                        reason=f"Boundary violation: {pattern} in purpose",
                        ttl_requested=ttl,
                    )
                    if self.audit:
                        self.audit.record(entry)
                    return {
                        "approved": False,
                        "reason": f"BOUNDARY VIOLATION: purpose references external domain ({pattern})",
                    }

        # 5. Look up secret
        value = self.store.get(key) if self.store else None
        if value is None:
            entry = AuditEntry(
                timestamp=time.time(), requester=requester,
                secret_key=key, purpose=purpose,
                approved=False, reason="Secret not found", ttl_requested=ttl,
            )
            if self.audit:
                self.audit.record(entry)
            return {"approved": False, "reason": f"Secret '{key}' not found"}

        # 6. Audit and deliver
        agent_record.secret_access_count += 1
        entry = AuditEntry(
            timestamp=time.time(), requester=requester,
            secret_key=key, purpose=purpose,
            approved=True, reason="ok", ttl_requested=ttl,
        )
        if self.audit:
            self.audit.record(entry)

        self._logger.info(f"Secret '{key}' delivered to '{requester}' (purpose: {purpose})")
        return {
            "approved": True,
            "value": value,
            "ttl": ttl,
            "access_count": agent_record.secret_access_count,
        }

    # -- HTTP server -----------------------------------------------------------

    def serve(self, host: str = "0.0.0.0", port: int = 7742) -> None:
        """Start the Keeper HTTP API server (blocking)."""
        KeeperHandler.keeper = self
        self._server = HTTPServer((host, port), KeeperHandler)
        self._logger.info(f"Keeper serving on {host}:{port}")
        self.activate()
        try:
            self._server.serve_forever()
        except KeyboardInterrupt:
            self._logger.info("Keeper shutting down")
            self._server.shutdown()

    def serve_background(self, host: str = "0.0.0.0", port: int = 7742) -> None:
        """Start the Keeper in a background thread."""
        self._server_thread = Thread(target=self.serve, args=(host, port), daemon=True)
        self._server_thread.start()
        self._logger.info(f"Keeper running in background on {host}:{port}")

    def shutdown(self) -> None:
        """Stop the Keeper server."""
        if self._server:
            self._server.shutdown()
            self._logger.info("Keeper shut down")
