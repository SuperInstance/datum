"""
datum_runtime.superagent.mib — Message-in-a-Bottle Protocol Module

Provides the MessageInBottle class for local file-based fleet communication.
Bottles are markdown files with YAML-like headers stored in
`message-in-a-bottle/for-{agent}/` directories.

This is the local counterpart to the remote mib_bottle tool (which commits
to GitHub). Use this module when you want to drop bottles into a local
workshop or when operating without a GitHub PAT.

Usage:
    from datum_runtime.superagent.mib import MessageInBottle

    mib = MessageInBottle(base_path="/home/datum/workshop")

    # Send a bottle to Oracle1
    mib.drop("oracle1", "Audit Complete", "Fleet audit finished. See attached report.")

    # Check your inbox
    bottles = mib.check()

    # Read a specific bottle
    content = mib.read(bottles[0])

    # Broadcast to all vessels
    mib.broadcast("Fleet Status Update", "All systems nominal.")
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# YAML-like Header Parser (no PyYAML dependency — keeps it stdlib-only)
# ---------------------------------------------------------------------------

_HEADER_RE = re.compile(
    r"^---\s*\n"
    r"(.*?)"
    r"^---\s*\n",
    re.MULTILINE | re.DOTALL,
)

_FIELD_RE = re.compile(r"^([a-z][a-z0-9_-]*)\s*:\s*(.+)$", re.MULTILINE)


def _parse_header(text: str) -> dict:
    """Parse a YAML-like front-matter block from a bottle file."""
    m = _HEADER_RE.match(text)
    if not m:
        return {}
    raw = m.group(1)
    fields = {}
    for fm in _FIELD_RE.finditer(raw):
        fields[fm.group(1).strip()] = fm.group(2).strip()
    return fields


def _render_header(fields: dict) -> str:
    """Render a dict into a YAML-like front-matter block."""
    lines = ["---"]
    for key, value in fields.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def _slugify(text: str, max_len: int = 48) -> str:
    """Convert arbitrary text to a safe filename slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    return slug or "untitled"


# ---------------------------------------------------------------------------
# MessageInBottle
# ---------------------------------------------------------------------------

class MessageInBottle:
    """
    Local Message-in-a-Bottle handler for fleet communication.

    Bottles are markdown files with a YAML-like header containing metadata
    (from, to, date, type) followed by markdown content. They are stored
    in the workshop under ``message-in-a-bottle/`` directories.

    Directory layout::

        message-in-a-bottle/
        ├── for-datum/              # inbox (messages TO datum)
        │   └── 2026-04-14_oracle1_check-in.md
        ├── for-oracle1/            # outbox (messages FROM datum TO oracle1)
        │   └── 2026-04-14_datum_signal.md
        └── for-any-vessel/         # broadcast
            └── 2026-04-14_datum_fleet-status.md
    """

    MIB_ROOT = "message-in-a-bottle"
    BROADCAST_DIR = "for-any-vessel"
    INBOX_DIR = "for-datum"  # default inbox for this agent

    def __init__(self, base_path: str = ".", sender: str = "datum"):
        """
        Args:
            base_path: Root of the workshop (where message-in-a-bottle/ lives).
            sender: Name of the sending agent (default: "datum").
        """
        self.base_path = Path(base_path)
        self.sender = sender
        self.mib_root = self.base_path / self.MIB_ROOT

    # -- Public API -----------------------------------------------------------

    def drop(
        self,
        agent_name: str,
        subject: str,
        content: str,
        bottle_type: str = "message",
    ) -> str:
        """
        Write a bottle to ``message-in-a-bottle/for-{agent_name}/``.

        Args:
            agent_name: Target agent (e.g. "oracle1", "jetsonclaw1").
            subject: Short subject line for the bottle.
            content: Markdown body of the message.
            bottle_type: Message type (signal, check-in, alert, question,
                         deliverable, handoff, info, message).

        Returns:
            The full file path of the written bottle.
        """
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")

        safe_agent = agent_name.lower().replace(" ", "-")
        slug = _slugify(subject)
        filename = f"{date_str}_{self.sender}_{slug}.md"

        target_dir = self.mib_root / f"for-{safe_agent}"
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / filename

        header = _render_header({
            "from": self.sender,
            "to": agent_name,
            "date": timestamp,
            "type": bottle_type,
            "subject": subject,
        })

        body = (
            f"{header}\n\n"
            f"# {subject}\n\n"
            f"**From:** {self.sender}\n"
            f"**To:** {agent_name}\n"
            f"**Date:** {timestamp}\n"
            f"**Type:** {bottle_type}\n\n"
            f"---\n\n"
            f"{content}\n\n"
            f"---\n\n"
            f"*MiB v1.0 | {self.sender} → {agent_name} | {timestamp}*\n"
        )

        filepath.write_text(body, encoding="utf-8")
        return str(filepath)

    def check(self, inbox: Optional[str] = None) -> List[str]:
        """
        List all unread bottles in the inbox.

        Args:
            inbox: Directory name to check (default: "for-datum").

        Returns:
            List of full file paths to bottle files, sorted oldest-first.
        """
        target_dir = self.mib_root / (inbox or self.INBOX_DIR)
        if not target_dir.exists():
            return []

        bottles = sorted(target_dir.glob("*.md"))
        return [str(b) for b in bottles]

    def read(self, bottle_path: str) -> Tuple[dict, str]:
        """
        Read and parse a bottle file.

        Args:
            bottle_path: Path to the bottle file.

        Returns:
            A tuple of (header_dict, markdown_body).

        Raises:
            FileNotFoundError: If the bottle file doesn't exist.
        """
        path = Path(bottle_path)
        if not path.exists():
            raise FileNotFoundError(f"Bottle not found: {bottle_path}")

        raw = path.read_text(encoding="utf-8")
        header = _parse_header(raw)

        # Extract body after the second ---
        parts = re.split(r"^---\s*\n", raw, maxsplit=2, flags=re.MULTILINE)
        body = parts[2].strip() if len(parts) >= 3 else raw.strip()

        return header, body

    def broadcast(
        self,
        subject: str,
        content: str,
        bottle_type: str = "signal",
    ) -> str:
        """
        Write a bottle to ``message-in-a-bottle/for-any-vessel/`` for fleet-wide
        consumption.

        Args:
            subject: Short subject line.
            content: Markdown body of the broadcast.
            bottle_type: Message type (default: "signal").

        Returns:
            The full file path of the written bottle.
        """
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")

        slug = _slugify(subject)
        filename = f"{date_str}_{self.sender}_{slug}.md"

        target_dir = self.mib_root / self.BROADCAST_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / filename

        header = _render_header({
            "from": self.sender,
            "to": "any-vessel",
            "date": timestamp,
            "type": bottle_type,
            "subject": subject,
        })

        body = (
            f"{header}\n\n"
            f"# {subject}\n\n"
            f"**From:** {self.sender}\n"
            f"**To:** All Fleet Vessels\n"
            f"**Date:** {timestamp}\n"
            f"**Type:** {bottle_type}\n\n"
            f"---\n\n"
            f"{content}\n\n"
            f"---\n\n"
            f"*MiB v1.0 | {self.sender} → fleet | {timestamp}*\n"
        )

        filepath.write_text(body, encoding="utf-8")
        return str(filepath)

    def delete(self, bottle_path: str) -> bool:
        """
        Delete a bottle file (mark as "read" / clean up).

        Args:
            bottle_path: Path to the bottle file.

        Returns:
            True if the file was deleted, False if it didn't exist.
        """
        path = Path(bottle_path)
        if not path.exists():
            return False
        path.unlink()
        return True

    def summary(self, inbox: Optional[str] = None) -> str:
        """
        Return a human-readable summary of all bottles in an inbox.

        Args:
            inbox: Directory name (default: "for-datum").

        Returns:
            Multi-line string summarizing each bottle.
        """
        bottles = self.check(inbox)
        if not bottles:
            return "No bottles in inbox."

        lines = [f"Inbox ({inbox or self.INBOX_DIR}): {len(bottles)} bottle(s)\n"]
        for bp in bottles:
            try:
                header, _ = self.read(bp)
                sender = header.get("from", "?")
                date = header.get("date", "?")
                subj = header.get("subject", "?")
                btype = header.get("type", "?")
                lines.append(f"  [{btype}] {subj}  (from {sender}, {date})")
                lines.append(f"         {os.path.basename(bp)}")
            except Exception as e:
                lines.append(f"  [ERROR] {os.path.basename(bp)}: {e}")
        return "\n".join(lines)
