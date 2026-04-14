"""
superagent.datum — Datum Agent: research, analysis, audit, and journal specialist.

Datum observes and reports. It doesn't act directly on workshops but provides
insights through audits, cross-repo analysis, conformance testing, and
journal management. Think of Datum as the fleet's quality engineer.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from datum_runtime.superagent.core import (
    Agent,
    AgentConfig,
    AgentMessage,
    AgentState,
    MessageType,
)


# ---------------------------------------------------------------------------
# Audit Types
# ---------------------------------------------------------------------------

class AuditSeverity(Enum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


@dataclass
class AuditFinding:
    severity: AuditSeverity
    category: str
    agent: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.name, "category": self.category,
            "agent": self.agent, "message": self.message,
            "details": self.details, "timestamp": self.timestamp,
        }


class AuditReport:
    """Collection of audit findings with summary stats and markdown output."""

    def __init__(self, title: str = "Audit Report"):
        self.title = title
        self.findings: List[AuditFinding] = []
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.completed_at: Optional[str] = None

    def add(self, severity: AuditSeverity, category: str, agent: str,
            message: str, details: Optional[Dict] = None) -> None:
        self.findings.append(AuditFinding(
            severity=severity, category=category, agent=agent,
            message=message, details=details or {},
        ))

    def complete(self) -> None:
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in self.findings:
            counts[f.severity.name] = counts.get(f.severity.name, 0) + 1
        return counts

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", "",
                 f"**Started:** {self.started_at}",
                 f"**Completed:** {self.completed_at or 'In progress'}",
                 f"**Total findings:** {len(self.findings)}", ""]

        counts = self.summary()
        if counts:
            lines += ["## Summary", "", "| Severity | Count |",
                       "|----------|-------|"]
            for s, c in sorted(counts.items()):
                lines.append(f"| {s} | {c} |")
            lines.append("")

        for sev in AuditSeverity:
            items = [f for f in self.findings if f.severity == sev]
            if not items:
                continue
            lines.append(f"## {sev.name}")
            lines.append("")
            for f in items:
                lines.append(f"- **[{f.category}]** {f.agent}: {f.message}")
                if f.details:
                    lines.append(f"  - `{json.dumps(f.details)}`")
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Journal Manager
# ---------------------------------------------------------------------------

@dataclass
class JournalEntry:
    timestamp: str
    agent: str
    category: str
    content: str
    tags: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        tags_str = " ".join(f"`{t}`" for t in self.tags) if self.tags else ""
        return f"### [{self.timestamp}] {self.agent} — {self.category}\n\n{self.content}\n\n{tags_str}\n"


class JournalManager:
    """Manages JOURNAL.md — the chronological work log."""

    def __init__(self, workshop_path: str):
        self.path = Path(workshop_path) / "JOURNAL.md"
        self._entries: List[JournalEntry] = []
        self._logger = logging.getLogger("datum.journal")
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            content = self.path.read_text()
            for match in re.finditer(
                r"### \[([^\]]+)\] (\S+) — (\S+)\n\n(.*?)(?=\n### |\Z)",
                content, re.DOTALL,
            ):
                ts, agent, cat, body = match.groups()
                self._entries.append(JournalEntry(
                    timestamp=ts.strip(), agent=agent.strip(),
                    category=cat.strip(), content=body.strip(),
                ))
        except Exception as e:
            self._logger.error(f"Journal load error: {e}")

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# Agent Journal", "",
                 "Chronological log of agent activities, discoveries, and notes.", ""]
        for entry in self._entries:
            lines.append(entry.to_markdown())
            lines.append("---")
            lines.append("")
        self.path.write_text("\n".join(lines))

    def add(self, agent: str, category: str, content: str,
            tags: Optional[List[str]] = None) -> JournalEntry:
        entry = JournalEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent=agent, category=category, content=content,
            tags=tags or [],
        )
        self._entries.append(entry)
        self._save()
        return entry

    def search(self, query: str, agent: Optional[str] = None) -> List[JournalEntry]:
        results = self._entries
        if agent:
            results = [e for e in results if agent in e.agent]
        if query:
            results = [e for e in results if query.lower() in e.content.lower()]
        return results

    def recent(self, limit: int = 20) -> List[JournalEntry]:
        return self._entries[-limit:]


# ---------------------------------------------------------------------------
# Cross-Repo Analyzer
# ---------------------------------------------------------------------------

@dataclass
class WorkshopProfile:
    path: str
    name: str
    total_files: int = 0
    total_dirs: int = 0
    has_bootcamp: bool = False
    has_dojo: bool = False
    has_tools: bool = False
    has_wiki: bool = False
    has_recipes: bool = False
    languages_used: List[str] = field(default_factory=list)
    tool_count: int = 0
    commit_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


class CrossRepoAnalyzer:
    """Profiles workshops for cross-repo comparison."""

    EXT_MAP = {
        ".py": "Python", ".sh": "Bash", ".rs": "Rust", ".c": "C",
        ".zig": "Zig", ".ts": "TypeScript", ".js": "JavaScript",
        ".json": "JSON", ".toml": "TOML", ".md": "Markdown",
        ".wasm": "WebAssembly", ".cu": "CUDA",
    }

    def profile(self, path: str) -> WorkshopProfile:
        ws = Path(path).resolve()
        if not ws.exists():
            return WorkshopProfile(path=str(ws), name=ws.name)

        p = WorkshopProfile(path=str(ws), name=ws.name)
        p.has_bootcamp = (ws / "bootcamp").is_dir()
        p.has_dojo = (ws / "dojo").is_dir()
        p.has_tools = (ws / "tools").is_dir()
        p.has_wiki = (ws / "wiki").is_dir()
        p.has_recipes = (ws / "recipes").is_dir()

        langs: Set[str] = set()
        for item in ws.rglob("*"):
            if item.is_file() and not any(part.startswith(".") for part in item.parts):
                p.total_files += 1
                lang = self.EXT_MAP.get(item.suffix.lower())
                if lang:
                    langs.add(lang)
                rel = item.relative_to(ws)
                if rel.parts and rel.parts[0] == "tools":
                    p.tool_count += 1
            elif item.is_dir() and not any(part.startswith(".") for part in item.parts):
                p.total_dirs += 1

        p.languages_used = sorted(langs)

        # Commit count
        try:
            r = subprocess.run(
                ["git", "-C", str(ws), "rev-list", "--count", "HEAD"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                p.commit_count = int(r.stdout.strip())
        except Exception:
            pass

        return p

    def compare(self, paths: List[str]) -> Dict[str, Any]:
        profiles = [self.profile(p) for p in paths]
        shared = set.intersection(*[set(p.languages_used) for p in profiles]) if profiles else set()
        return {
            "workshops": [p.to_dict() for p in profiles],
            "shared_languages": sorted(shared),
            "count": len(profiles),
        }


# ---------------------------------------------------------------------------
# Datum Agent
# ---------------------------------------------------------------------------

class DatumAgent(Agent):
    """
    Research, analysis, and audit specialist.

    Datum observes the fleet and workshops, produces audit reports,
    compares cross-repo profiles, and manages the journal. It's the
    quality engineer — it watches, measures, and reports.
    """

    role = "datum"
    description = "Research, analysis, and audit specialist."

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs):
        super().__init__(config or AgentConfig(role="datum"), **kwargs)
        self.name = self.name or "datum"
        self.config.capabilities = ["audit", "analyze", "journal", "report", "cross-repo"]
        self._journal_mgr: Optional[JournalManager] = None
        self._crossrepo = CrossRepoAnalyzer()

    def init_journal(self, workshop_path: Optional[str] = None) -> JournalManager:
        path = workshop_path or self.config.repo_path
        self._journal_mgr = JournalManager(path)
        return self._journal_mgr

    # -- Audit operations ------------------------------------------------------

    def audit_workshop(self, path: Optional[str] = None) -> AuditReport:
        """Audit a workshop for structure, conformance, and health."""
        report = AuditReport("Workshop Audit")
        ws = Path(path or self.config.repo_path)

        required = ["bootcamp", "dojo", "tools", "wiki", "recipes"]
        for d in required:
            if not (ws / d).is_dir():
                report.add(AuditSeverity.WARNING, "structure", "workshop",
                           f"Missing required directory: {d}/")

        if not (ws / "TASKBOARD.md").exists():
            report.add(AuditSeverity.WARNING, "structure", "workshop",
                       "No TASKBOARD.md found")

        if not (ws / "JOURNAL.md").exists():
            report.add(AuditSeverity.INFO, "structure", "workshop",
                       "No JOURNAL.md found (will be auto-created)")

        sa_dir = ws / ".superagent"
        if not sa_dir.exists():
            report.add(AuditSeverity.ERROR, "conformance", "workshop",
                       "Missing .superagent/ directory — not onboarded")
        else:
            if not (sa_dir / "agent.toml").exists():
                report.add(AuditSeverity.WARNING, "conformance", "workshop",
                           "Missing .superagent/agent.toml")

        report.complete()
        return report

    def audit_fleet(self, agents: Optional[List[Dict]] = None) -> AuditReport:
        """Audit the fleet — check agent health and coverage."""
        report = AuditReport("Fleet Audit")

        if not agents:
            report.add(AuditSeverity.INFO, "fleet", "datum",
                       "No agent list provided — running local-only audit")
        else:
            for a in agents:
                name = a.get("name", "unknown")
                state = a.get("state", "unknown")
                if state not in ("active", "onboarded"):
                    report.add(AuditSeverity.WARNING, "fleet", name,
                               f"Agent state is '{state}' — may need attention")
                caps = a.get("capabilities", [])
                if not caps:
                    report.add(AuditSeverity.INFO, "fleet", name,
                               "No capabilities registered")

            report.add(AuditSeverity.INFO, "fleet", "datum",
                       f"Fleet audit: {len(agents)} agents checked")

        report.complete()
        return report

    # -- Analysis operations ---------------------------------------------------

    def analyze_workshop(self, path: Optional[str] = None) -> Dict[str, Any]:
        p = self._crossrepo.profile(path or self.config.repo_path)
        return p.to_dict()

    def compare_workshops(self, paths: List[str]) -> Dict[str, Any]:
        return self._crossrepo.compare(paths)

    # -- Journal operations ----------------------------------------------------

    def journal(self, category: str, content: str,
                agent: Optional[str] = None, tags: Optional[List[str]] = None) -> Dict:
        if not self._journal_mgr:
            self.init_journal()
        entry = self._journal_mgr.add(
            agent=agent or self.name,
            category=category, content=content, tags=tags,
        )
        return {"status": "recorded", "timestamp": entry.timestamp}

    def journal_search(self, query: str, agent: Optional[str] = None) -> List[Dict]:
        if not self._journal_mgr:
            return []
        return [{"timestamp": e.timestamp, "agent": e.agent,
                 "category": e.category, "content": e.content}
                for e in self._journal_mgr.search(query, agent)]

    def journal_recent(self, limit: int = 20) -> List[Dict]:
        if not self._journal_mgr:
            return []
        return [{"timestamp": e.timestamp, "agent": e.agent,
                 "category": e.category, "content": e.content}
                for e in self._journal_mgr.recent(limit)]

    # -- Report generation -----------------------------------------------------

    def generate_report(self, report_type: str = "fleet", **kwargs) -> str:
        if report_type == "workshop":
            profile = self.analyze_workshop(kwargs.get("path"))
            lines = ["# Workshop Analysis Report", "",
                     f"**Path:** {profile.get('path', 'N/A')}",
                     f"**Files:** {profile.get('total_files', 0)}",
                     f"**Languages:** {', '.join(profile.get('languages_used', []))}",
                     f"**Commits:** {profile.get('commit_count', 0)}", ""]
            return "\n".join(lines)
        elif report_type == "fleet":
            report = self.audit_fleet(kwargs.get("agents"))
            return report.to_markdown()
        elif report_type == "conformance":
            report = self.audit_workshop(kwargs.get("path"))
            return report.to_markdown()
        else:
            return f"Unknown report type: {report_type}"

    # -- Message handling ------------------------------------------------------

    def handle_message(self, msg: AgentMessage) -> None:
        if msg.msg_type == MessageType.QUERY:
            qt = msg.body.get("query_type", "")
            if qt == "audit":
                report = self.audit_workshop()
                self.send(msg.sender, f"response:{msg.id}", {
                    "query": "audit", "report": report.to_markdown(),
                    "in_reply_to": msg.id,
                }, MessageType.RESPONSE)
            elif qt == "analyze":
                profile = self.analyze_workshop(msg.body.get("path"))
                self.send(msg.sender, f"response:{msg.id}", {
                    "query": "analyze", "profile": profile,
                    "in_reply_to": msg.id,
                }, MessageType.RESPONSE)

    def run(self, **kwargs) -> None:
        self.activate()
        if not self._journal_mgr:
            self.init_journal()
        self.listen(self.handle_message)
        self._logger.info("Datum active. Ready for audit and analysis requests.")
