"""
superagent.git_agent — Git Agent: repo operator, workshop manager, commit historian.

The GitAgent is the cocapn liaison between a thinking agent and the human/operator.
It operates the workshop (repo), makes commits that tell a story, and persists
even after the thinking agent leaves its station.

Key design principles:
    - Every commit tells a story (conventional commits + agent reasoning)
    - The workshop fills with tools, scripts, interpreters, recipes over time
    - Custom compilers reduce low-level reasoning for the thinking agent
    - Full history is rewindable — every thought and action is frozen in git

The GitAgent does NOT think. It executes. The thinking agent sends commands,
the GitAgent turns them into well-crafted git operations.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from datum_runtime.superagent.core import (
    Agent,
    AgentConfig,
    AgentMessage,
    AgentState,
    MessageType,
)


# ---------------------------------------------------------------------------
# Workshop Template
# ---------------------------------------------------------------------------

WORKSHOP_TREE = {
    "README.md": "# Workshop: {name}\n\nOperated by git-agent for `{owner}`.\n\n"
                 "## Structure\n"
                 "- `bootcamp/` — Training and skill-building exercises\n"
                 "- `dojo/` — Advanced techniques and kata\n"
                 "- `tools/` — Scripts, interpreters, compilers\n"
                 "- `recipes/` — Saved command sequences for recurring tasks\n"
                 "- `wiki/` — Knowledge base and documentation\n"
                 "- `TASKBOARD.md` — Current task tracking\n"
                 "- `JOURNAL.md` — Work journal (auto-maintained)\n",
    "bootcamp/README.md": "# Bootcamp\n\nTraining area for new agents. "
                          "Complete these exercises to build familiarity "
                          "with the workshop tools and libraries.",
    "dojo/README.md": "# Dojo\n\nAdvanced skill-building. Practice kata, "
                       "build custom compilers, experiment with new techniques.",
    "tools/README.md": "# Tools\n\nWorkshop tools — scripts, interpreters, "
                       "and compilers. Add your tools here and register them "
                       "in `tools/manifest.json`.",
    "tools/manifest.json": '{{"tools": [], "interpreters": [], "compilers": []}}',
    "recipes/README.md": "# Recipes\n\nSaved command sequences. Each recipe is "
                         "a reusable command or script for a recurring task.\n\n"
                         "## Format\nEach recipe is a markdown file with:\n"
                         "- Description of what it does\n"
                         "- The command(s) to run\n"
                         "- Prerequisites\n"
                         "- Notes on when to use it",
    "wiki/README.md": "# Wiki\n\nKnowledge base for this workshop. Document "
                      "discoveries, decisions, and architectural notes here.",
    "TASKBOARD.md": "# Task Board\n\n## In Progress\n\n## Queued\n\n## Done\n",
    "JOURNAL.md": "# Work Journal\n\nAuto-maintained by git-agent.\n",
    ".superagent/agent.toml": "# Agent configuration\n[agent]\nname = \"{name}\"\n"
                               "role = \"git-agent\"\nowner = \"{owner}\"\n",
}


# ---------------------------------------------------------------------------
# Commit History
# ---------------------------------------------------------------------------

@dataclass
class CommitRecord:
    """A recorded commit with agent reasoning."""
    hash: str
    message: str
    agent_reasoning: str
    author: str
    timestamp: str
    files_changed: List[str] = field(default_factory=list)
    lines_added: int = 0
    lines_removed: int = 0


# ---------------------------------------------------------------------------
# Tool / Recipe Registry
# ---------------------------------------------------------------------------

@dataclass
class ToolRecord:
    """A tool in the workshop."""
    name: str
    path: str
    description: str = ""
    language: str = ""
    category: str = "script"  # script | interpreter | compiler
    created_by: str = ""
    created_at: str = ""


@dataclass
class RecipeRecord:
    """A saved recipe (reusable command sequence)."""
    name: str
    path: str
    description: str = ""
    commands: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    created_by: str = ""


# ---------------------------------------------------------------------------
# Git Agent
# ---------------------------------------------------------------------------

class GitAgent(Agent):
    """
    The GitAgent operates the workshop repository for a thinking agent.

    Responsibilities:
        - Initialize workshops from templates
        - Make well-crafted commits that tell a story
        - Track tool/recipe inventory
        - Manage branches for experiments
        - Maintain the TASKBOARD and JOURNAL
        - Provide full history (rewindable story of work)
    """

    role = "git-agent"
    description = "Workshop operator and repo historian. Turns thinking into commits."

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs):
        super().__init__(config or AgentConfig(role="git-agent"), **kwargs)
        self.owner: str = kwargs.get("owner", "unknown")
        self.workshop_path = Path(self.config.repo_path)
        self._tools: Dict[str, ToolRecord] = {}
        self._recipes: Dict[str, RecipeRecord] = {}
        self._commit_history: List[CommitRecord] = []

    # -- Workshop initialization -----------------------------------------------

    def init_workshop(self, name: Optional[str] = None, owner: Optional[str] = None) -> Path:
        """
        Initialize a new workshop from the template.

        Creates the full directory structure with README, bootcamp, dojo,
        tools, recipes, wiki, and configuration files.
        """
        ws_name = name or self.name
        self.owner = owner or self.owner

        self.workshop_path.mkdir(parents=True, exist_ok=True)
        self._logger.info(f"Initializing workshop at {self.workshop_path}")

        # Create directory tree
        for rel_path, content in WORKSHOP_TREE.items():
            full_path = self.workshop_path / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            rendered = content.format(name=ws_name, owner=self.owner)
            full_path.write_text(rendered)

        # Initialize git repo
        self._git("init")
        self._git("config", "user.name", f"git-agent [{ws_name}]")
        self._git("config", "user.email", f"{ws_name}@superinstance.local")
        self._git("add", ".")
        self._git("commit", "-m", "feat: initialize workshop\n\nWorkshop bootstrapped from template.\nOwner: {0}".format(self.owner))

        self._logger.info(f"Workshop initialized: {self.workshop_path}")
        self._journal("INIT", f"Workshop created for owner '{self.owner}'")
        return self.workshop_path

    # -- Commit operations -----------------------------------------------------

    def commit(
        self,
        message: str,
        reasoning: str = "",
        files: Optional[List[str]] = None,
        allow_empty: bool = False,
    ) -> Optional[str]:
        """
        Make a commit with a story-telling message.

        Args:
            message: Conventional commit message (e.g. "feat: add flux validator")
            reasoning: WHY this change was made (the agent's thought process)
            files: Specific files to stage (None = stage all)
            allow_empty: Allow empty commits (for journal entries, etc.)

        Returns:
            The commit hash, or None on failure
        """
        if not self.workshop_path.exists():
            self._logger.error("Workshop not initialized — call init_workshop() first")
            return None

        # Stage files
        if files:
            for f in files:
                self._git("add", f)
        else:
            self._git("add", "-A")

        # Build the full commit message with reasoning
        full_msg = message
        if reasoning:
            full_msg += f"\n\nReasoning: {reasoning}"

        # Check if there's anything to commit
        status = self._git("status", "--porcelain", capture=True)
        if not status and not allow_empty:
            self._logger.info("Nothing to commit")
            return None

        # Commit
        result = self._git("commit", "-m", full_msg, "--allow-empty" if allow_empty else None, capture=True)
        if result and ("nothing to commit" not in result):
            commit_hash = self._git("rev-parse", "HEAD", capture=True) or "unknown"
            self._logger.info(f"Committed: {commit_hash[:8]} — {message}")

            # Record in history
            self._commit_history.append(CommitRecord(
                hash=commit_hash[:8],
                message=message,
                agent_reasoning=reasoning,
                author=f"git-agent [{self.owner}]",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))

            return commit_hash
        return None

    def smart_commit(self, changes_description: str, agent_thought: str) -> Optional[str]:
        """
        Smart commit that auto-generates a conventional commit message from
        the description and agent's reasoning.
        """
        # Auto-detect commit type from description
        type_map = {
            "fix": ["fix", "bug", "error", "broken", "wrong", "fail", "issue"],
            "feat": ["add", "new", "create", "implement", "build", "feature"],
            "refactor": ["refactor", "restructure", "reorganize", "clean", "simplify"],
            "docs": ["doc", "readme", "comment", "document"],
            "test": ["test", "spec", "verify", "validate", "check"],
            "chore": ["update", "bump", "config", "setup", "install", "dependency"],
            "perf": ["optimize", "performance", "speed", "fast", "slow"],
        }

        desc_lower = changes_description.lower()
        commit_type = "chore"
        for ctype, keywords in type_map.items():
            if any(kw in desc_lower for kw in keywords):
                commit_type = ctype
                break

        # Clean up the description into a short subject line
        subject = changes_description.strip()
        if len(subject) > 72:
            subject = subject[:69] + "..."

        message = f"{commit_type}: {subject}"
        return self.commit(message, reasoning=agent_thought)

    # -- Branch management -----------------------------------------------------

    def branch(self, name: str, from_branch: str = "main") -> bool:
        """Create a new branch for experiments."""
        result = self._git("checkout", "-b", name, from_branch, capture=True)
        success = result is not None and "error" not in (result or "").lower()
        if success:
            self._logger.info(f"Branch '{name}' created from '{from_branch}'")
        return success

    def checkout(self, branch: str) -> bool:
        """Switch to a branch."""
        result = self._git("checkout", branch, capture=True)
        success = result is not None and "error" not in (result or "").lower()
        if success:
            self._logger.info(f"Switched to branch '{branch}'")
        return success

    def merge(self, branch: str, message: Optional[str] = None) -> bool:
        """Merge a branch into current."""
        msg = message or f"merge: integrate {branch}"
        result = self._git("merge", branch, "-m", msg, capture=True)
        success = result is not None and "conflict" not in (result or "").lower()
        if success:
            self._logger.info(f"Merged '{branch}' into current branch")
        return success

    # -- History & inspection --------------------------------------------------

    def history(self, n: int = 20, format_str: str = "%h %s") -> List[str]:
        """Get commit history."""
        result = self._git(
            "log", f"-{n}", f"--pretty=format:{format_str}", capture=True
        )
        return [line for line in (result or "").strip().split("\n") if line] if result else []

    def full_history(self) -> List[CommitRecord]:
        """
        Get full commit history with details. Rewindable — tells the complete
        story of every change made in this workshop.
        """
        if self._commit_history:
            return self._commit_history

        result = self._git(
            "log", "--pretty=format:%H|%s|%an|%ai", capture=True
        )
        if not result:
            return []

        records = []
        for line in result.strip().split("\n"):
            parts = line.split("|", 3)
            if len(parts) >= 4:
                records.append(CommitRecord(
                    hash=parts[0][:8],
                    message=parts[1],
                    author=parts[2],
                    timestamp=parts[3],
                ))
        self._commit_history = records
        return records

    def show(self, commit_hash: str) -> Optional[str]:
        """Show details of a specific commit."""
        return self._git("show", commit_hash, "--stat", capture=True)

    def diff(self, staged: bool = False) -> Optional[str]:
        """Show current diff."""
        flag = "--staged" if staged else ""
        return self._git("diff", flag, capture=True) if staged else self._git("diff", capture=True)

    def status(self) -> Dict[str, Any]:
        """Get current repo status."""
        staged = self._git("diff", "--staged", "--name-only", capture=True) or ""
        modified = self._git("diff", "--name-only", capture=True) or ""
        untracked = self._git("ls-files", "--others", "--exclude-standard", capture=True) or ""
        branch = self._git("rev-parse", "--abbrev-ref", "HEAD", capture=True) or "unknown"

        return {
            "branch": branch.strip(),
            "staged": [f for f in staged.strip().split("\n") if f],
            "modified": [f for f in modified.strip().split("\n") if f],
            "untracked": [f for f in untracked.strip().split("\n") if f],
        }

    # -- Workshop inventory ----------------------------------------------------

    def inventory(self) -> Dict[str, Any]:
        """
        List all tools, scripts, interpreters, and compilers in the workshop.
        """
        inv = {"tools": [], "interpreters": [], "compilers": [], "recipes": []}
        tools_dir = self.workshop_path / "tools"
        recipes_dir = self.workshop_path / "recipes"

        # Scan tools directory
        if tools_dir.exists():
            for f in tools_dir.rglob("*"):
                if f.is_file() and f.suffix in (".py", ".sh", ".rs", ".c", ".zig", ".ts", ".js"):
                    rel = str(f.relative_to(self.workshop_path))
                    category = "script"
                    if "compiler" in f.stem.lower() or "compile" in str(f.parent).lower():
                        category = "compiler"
                    elif "interp" in f.stem.lower() or "vm" in f.stem.lower():
                        category = "interpreter"
                    inv[f"{category}s" if category != "script" else "tools"].append({
                        "name": f.stem,
                        "path": rel,
                        "language": f.suffix.lstrip("."),
                        "category": category,
                    })

        # Scan recipes
        if recipes_dir.exists():
            for f in recipes_dir.glob("*.md"):
                if f.name != "README.md":
                    rel = str(f.relative_to(self.workshop_path))
                    inv["recipes"].append({
                        "name": f.stem,
                        "path": rel,
                    })

        self._tools = {t["name"]: ToolRecord(**t) for t in inv["tools"]}
        return inv

    # -- Task board ------------------------------------------------------------

    def update_taskboard(self, tasks: Dict[str, List[str]]) -> None:
        """
        Update TASKBOARD.md with current tasks.

        tasks = {"In Progress": ["task1", "task2"], "Queued": [...], "Done": [...]}
        """
        board_path = self.workshop_path / "TASKBOARD.md"
        lines = ["# Task Board\n"]
        for section, items in tasks.items():
            lines.append(f"\n## {section}\n")
            for item in items:
                lines.append(f"- [ ] {item}\n" if section != "Done" else f"- [x] {item}\n")
        board_path.write_text("\n".join(lines))

    # -- Internal git helper ---------------------------------------------------

    def _git(self, *args, capture: bool = False) -> Optional[str]:
        """Run a git command in the workshop directory."""
        cmd = ["git", "-C", str(self.workshop_path)] + [a for a in args if a is not None]
        try:
            if capture:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    self._logger.debug(f"git error: {result.stderr.strip()}")
                    return None
                return result.stdout.strip()
            else:
                subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
                return None
        except FileNotFoundError:
            self._logger.error("git not found — is it installed?")
            return None
        except subprocess.TimeoutExpired:
            self._logger.error(f"git command timed out: {' '.join(args)}")
            return None
        except Exception as e:
            self._logger.error(f"git error: {e}")
            return None
