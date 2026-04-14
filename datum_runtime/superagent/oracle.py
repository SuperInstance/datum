"""
superagent.oracle — Oracle Agent: fleet coordination, task dispatch, priority management.

The Oracle watches the task board and dispatches work to the most appropriate
agent based on capabilities, availability, and priority. It discovers agents
through the message bus and maintains a live fleet registry.

The Oracle doesn't do the work — it orchestrates. The thinking agents do the work.
The Oracle just makes sure the right agent gets the right task at the right time.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional

from datum_runtime.superagent.core import (
    Agent,
    AgentConfig,
    AgentMessage,
    AgentState,
    MessageType,
)


# ---------------------------------------------------------------------------
# Task Priority & Status
# ---------------------------------------------------------------------------

class Priority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKLOG = 5

    @classmethod
    def from_str(cls, s: str) -> "Priority":
        m = {"critical": cls.CRITICAL, "high": cls.HIGH, "medium": cls.MEDIUM,
             "low": cls.LOW, "backlog": cls.BACKLOG}
        return m.get(s.lower(), cls.MEDIUM)


class TaskStatus(Enum):
    OPEN = auto()
    IN_PROGRESS = auto()
    BLOCKED = auto()
    REVIEW = auto()
    DONE = auto()
    CANCELLED = auto()


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A unit of work on the task board."""
    id: str = ""
    title: str = ""
    description: str = ""
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.OPEN
    assignee: Optional[str] = None
    requested_by: str = ""
    required_capabilities: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)
    parent_task: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "title": self.title,
            "description": self.description,
            "priority": self.priority.name, "status": self.status.name,
            "assignee": self.assignee, "requested_by": self.requested_by,
            "required_capabilities": self.required_capabilities,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "completed_at": self.completed_at, "tags": self.tags,
            "subtasks": self.subtasks, "parent_task": self.parent_task,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Task":
        return cls(
            id=d["id"], title=d["title"],
            description=d.get("description", ""),
            priority=Priority.from_str(d.get("priority", "medium")),
            status=TaskStatus[d.get("status", "OPEN")],
            assignee=d.get("assignee"),
            requested_by=d.get("requested_by", ""),
            required_capabilities=d.get("required_capabilities", []),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            completed_at=d.get("completed_at"),
            tags=d.get("tags", []),
            subtasks=d.get("subtasks", []),
            parent_task=d.get("parent_task"),
            metadata=d.get("metadata", {}),
        )

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Task Board — persistent, human-readable via TASKBOARD.md
# ---------------------------------------------------------------------------

class TaskBoard:
    """
    Central task tracking. Stored as TASKBOARD.md in the workshop for
    human readability AND machine-parseable JSON in HTML comments.
    """

    def __init__(self, workshop_path: str):
        self.workshop_path = Path(workshop_path)
        self.board_path = self.workshop_path / "TASKBOARD.md"
        self._tasks: Dict[str, Task] = {}
        self._counter = 0
        self._logger = logging.getLogger("oracle.board")
        self._load()

    def _load(self) -> None:
        if not self.board_path.exists():
            return
        try:
            content = self.board_path.read_text()
            import re
            match = re.search(
                r"<!--\s*TASKS_JSON_START\s*-->(.+?)<!--\s*TASKS_JSON_END\s*-->",
                content, re.DOTALL,
            )
            if match:
                data = json.loads(match.group(1).strip())
                for tid, td in data.items():
                    self._tasks[tid] = Task.from_dict(td)
                self._counter = len(self._tasks)
                self._logger.info(f"Loaded {self._counter} tasks from board")
        except Exception as e:
            self._logger.error(f"Board load error: {e}")

    def _save(self) -> None:
        self.board_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Task Board",
            "",
            f"Last updated: {datetime.now(timezone.utc).isoformat()}",
            f"Total tasks: {len(self._tasks)}",
            "",
            "## Summary",
            "",
            "| Status | Count |",
            "|--------|-------|",
        ]
        counts: Dict[str, int] = {}
        for t in self._tasks.values():
            counts[t.status.name] = counts.get(t.status.name, 0) + 1
        for s, c in sorted(counts.items()):
            lines.append(f"| {s} | {c} |")
        lines.append("")

        # By priority
        for pri in Priority:
            tasks = [t for t in self._tasks.values()
                     if t.priority == pri and t.status != TaskStatus.DONE]
            if not tasks:
                continue
            lines.append(f"## {pri.name}")
            lines.append("")
            for t in sorted(tasks, key=lambda x: x.created_at):
                who = t.assignee or "unassigned"
                desc = (t.description[:80] + "...") if len(t.description) > 80 else t.description
                lines.append(f"- [{t.id}] **{t.title}** ({who}) — {desc}")
            lines.append("")

        # Completed
        done = [t for t in self._tasks.values() if t.status == TaskStatus.DONE]
        if done:
            lines.append("## Completed")
            lines.append("")
            for t in sorted(done, key=lambda x: x.completed_at or "", reverse=True)[:20]:
                lines.append(f"- ~~[{t.id}] {t.title}~~")
            lines.append("")

        # Machine-parseable JSON
        tasks_json = {t.id: t.to_dict() for t in self._tasks.values()}
        lines.append("<!-- TASKS_JSON_START -->")
        lines.append(json.dumps(tasks_json, indent=2))
        lines.append("<!-- TASKS_JSON_END -->")

        self.board_path.write_text("\n".join(lines) + "\n")

    def add_task(self, title: str, description: str = "",
                 priority: Priority = Priority.MEDIUM,
                 requested_by: str = "",
                 required_capabilities: Optional[List[str]] = None,
                 tags: Optional[List[str]] = None) -> Task:
        self._counter += 1
        tid = f"TASK-{self._counter:03d}"
        task = Task(
            id=tid, title=title, description=description,
            priority=priority, requested_by=requested_by,
            required_capabilities=required_capabilities or [],
            tags=tags or [],
        )
        self._tasks[tid] = task
        self._save()
        self._logger.info(f"Task added: {tid} — {title}")
        return task

    def get_task(self, tid: str) -> Optional[Task]:
        return self._tasks.get(tid)

    def update_task(self, tid: str, **kwargs) -> Optional[Task]:
        task = self._tasks.get(tid)
        if not task:
            return None
        for k, v in kwargs.items():
            if hasattr(task, k):
                setattr(task, k, v)
        task.touch()
        if kwargs.get("status") == TaskStatus.DONE:
            task.completed_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return task

    def list_tasks(self, status=None, priority=None, assignee=None) -> List[Task]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        if assignee:
            tasks = [t for t in tasks if t.assignee == assignee]
        return sorted(tasks, key=lambda t: (t.priority.value, t.created_at))

    def next_dispatchable(self) -> List[Task]:
        return [t for t in self._tasks.values()
                if t.status == TaskStatus.OPEN and t.assignee is None]


# ---------------------------------------------------------------------------
# Fleet Discovery
# ---------------------------------------------------------------------------

@dataclass
class FleetAgent:
    name: str
    role: str
    capabilities: List[str] = field(default_factory=list)
    state: str = "active"
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FleetDiscovery:
    """Discover and track agents in the SuperInstance fleet."""

    def __init__(self):
        self._agents: Dict[str, FleetAgent] = {}
        self._logger = logging.getLogger("oracle.discovery")

    def register(self, name: str, role: str, capabilities: Optional[List[str]] = None) -> None:
        self._agents[name] = FleetAgent(
            name=name, role=role,
            capabilities=capabilities or [],
        )
        self._logger.info(f"Fleet: +{name} ({role})")

    def find_best(self, required: List[str]) -> Optional[FleetAgent]:
        best, score = None, 0
        for a in self._agents.values():
            if a.state != "active":
                continue
            s = sum(1 for c in required if c in a.capabilities)
            if s > score:
                score, best = s, a
        return best

    def list_fleet(self) -> List[Dict[str, Any]]:
        return [{"name": a.name, "role": a.role,
                 "capabilities": a.capabilities, "state": a.state}
                for a in self._agents.values()]

    @property
    def size(self) -> int:
        return len(self._agents)


# ---------------------------------------------------------------------------
# Oracle Agent
# ---------------------------------------------------------------------------

class OracleAgent(Agent):
    """
    Fleet coordinator. Watches the task board, discovers agents, dispatches work.

    The Oracle never does the work itself — it finds the right agent for each
    task and sends it via the message bus. The thinking agent executes, the
    GitAgent commits the results, and the Oracle marks the task done.
    """

    role = "oracle"
    description = "Fleet coordinator — task board, discovery, dispatch."

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs):
        super().__init__(config or AgentConfig(role="oracle"), **kwargs)
        self.name = self.name or "oracle"
        self._board: Optional[TaskBoard] = None
        self._discovery = FleetDiscovery()
        self._dispatch_count = 0

    def init_board(self, workshop_path: Optional[str] = None) -> TaskBoard:
        """Initialize the task board."""
        path = workshop_path or self.config.repo_path
        self._board = TaskBoard(path)
        self._logger.info(f"Task board initialized: {path} ({len(self._board._tasks)} existing tasks)")
        return self._board

    # -- Task operations -------------------------------------------------------

    def add_task(self, title: str, description: str = "", priority: str = "medium",
                 requested_by: str = "", capabilities: Optional[List[str]] = None) -> Dict:
        if not self._board:
            return {"error": "Board not initialized"}
        task = self._board.add_task(
            title=title, description=description,
            priority=Priority.from_str(priority),
            requested_by=requested_by,
            required_capabilities=capabilities,
        )
        return {"status": "created", "task": task.to_dict()}

    def dispatch(self, task_id: str, agent_name: Optional[str] = None) -> Dict:
        """Dispatch a task to an agent (manual or auto-dispatch)."""
        if not self._board:
            return {"error": "Board not initialized"}
        task = self._board.get_task(task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}
        if task.status != TaskStatus.OPEN:
            return {"error": f"Task {task_id} status is {task.status.name}"}

        target = agent_name
        if not target:
            agent = self._discovery.find_best(task.required_capabilities)
            target = agent.name if agent else None

        if not target:
            return {"error": f"No agent available for {task_id}"}

        # Send via message bus
        self.send(target, f"task:{task_id}", {
            "task_id": task.id, "title": task.title,
            "description": task.description,
            "priority": task.priority.name,
        }, MessageType.TASK)

        self._board.update_task(task_id, status=TaskStatus.IN_PROGRESS, assignee=target)
        self._dispatch_count += 1
        self._logger.info(f"Dispatched {task_id} -> {target}")
        return {"status": "dispatched", "task_id": task_id, "assignee": target}

    def auto_dispatch(self) -> List[Dict]:
        """Dispatch all open unassigned tasks."""
        if not self._board:
            return []
        results = []
        for task in self._board.next_dispatchable():
            r = self.dispatch(task.id)
            results.append(r)
        return results

    # -- Fleet operations ------------------------------------------------------

    def register_agent(self, name: str, role: str, capabilities: Optional[List[str]] = None) -> None:
        self._discovery.register(name, role, capabilities)

    # -- Status & inspection ---------------------------------------------------

    def show_board(self) -> Dict:
        if not self._board:
            return {"error": "Board not initialized"}
        tasks = self._board.list_tasks()
        return {
            "total": len(tasks),
            "open": len([t for t in tasks if t.status == TaskStatus.OPEN]),
            "in_progress": len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS]),
            "done": len([t for t in tasks if t.status == TaskStatus.DONE]),
            "tasks": [t.to_dict() for t in tasks],
        }

    def status(self) -> Dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "dispatch_count": self._dispatch_count,
            "fleet_size": self._discovery.size,
            "tasks_total": len(self._board._tasks) if self._board else 0,
        }

    # -- Message handling ------------------------------------------------------

    def handle_message(self, msg: AgentMessage) -> None:
        """Handle incoming bus messages."""
        if msg.msg_type == MessageType.RESPONSE:
            payload = msg.body
            if payload.get("result") == "done" and payload.get("task_id"):
                tid = payload["task_id"]
                if self._board:
                    self._board.update_task(tid, status=TaskStatus.DONE)
                    self._logger.info(f"Task {tid} completed by {msg.sender}")

        elif msg.msg_type == MessageType.STATUS:
            if msg.sender in self._discovery._agents:
                self._discovery._agents[msg.sender].state = msg.body.get("state", "active")
                self._discovery._agents[msg.sender].last_seen = datetime.now(timezone.utc).isoformat()

        elif msg.msg_type == MessageType.HEARTBEAT:
            if msg.sender not in self._discovery._agents:
                self._discovery.register(msg.sender, msg.body.get("role", "unknown"),
                                         msg.body.get("capabilities", []))

    def run(self, **kwargs) -> None:
        """Main loop — periodic board check and auto-dispatch."""
        self.activate()
        if not self._board:
            self._board = TaskBoard(self.config.repo_path)
        self.listen(self.handle_message)
        self._logger.info("Oracle active. Monitoring board and fleet...")
        try:
            while self.state == AgentState.ACTIVE:
                dispatched = self.auto_dispatch()
                if dispatched:
                    self._logger.info(f"Auto-dispatched {len(dispatched)} tasks")
                time.sleep(30)
        except KeyboardInterrupt:
            self.idle()
