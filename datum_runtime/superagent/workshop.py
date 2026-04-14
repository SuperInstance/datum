"""
superagent.workshop — Workshop management: templates, tool registry, recipes.

A workshop is a git repo that serves as an agent's persistent workspace.
It accumulates tools, scripts, interpreters, compilers, and recipes over
time — each commit tells the story of how the agent thought and acted.

Language stack philosophy:
    - Low-level (C, Rust, Zig): Interpreters and custom compilers built
      just-so for the application's needs, not generic language needs
    - Mid-level (Python, Bash): Tools, automation, one-off scripts
    - High-level (Python, JSON, TS): Iteration, parsing, filter-prompting,
      iterative refinement of prompts and responses
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from datum_runtime.superagent.core import AgentConfig


# ---------------------------------------------------------------------------
# Workshop Template
# ---------------------------------------------------------------------------

DEFAULT_TEMPLATE = {
    "README.md": (
        "# Workshop: {name}\n\n"
        "Operated by git-agent for `{owner}`.\n\n"
        "## Structure\n\n"
        "| Directory | Purpose |\n"
        "|-----------|---------|\n"
        "| bootcamp/ | Training and skill-building exercises |\n"
        "| dojo/ | Advanced techniques and kata |\n"
        "| tools/ | Scripts, interpreters, compilers |\n"
        "| recipes/ | Saved command sequences for recurring tasks |\n"
        "| wiki/ | Knowledge base and documentation |\n\n"
        "## Language Stack\n\n"
        "| Level | Languages | Purpose |\n"
        "|-------|-----------|---------|\n"
        "| Low | C, Rust, Zig | Custom interpreters, compilers |\n"
        "| Mid | Python, Bash | Tools, automation |\n"
        "| High | Python, JSON, TS | Iteration, parsing, prompting |\n"
    ),
    "bootcamp/README.md": (
        "# Bootcamp\n\n"
        "Training area for new agents. Complete exercises to build\n"
        "familiarity with workshop tools and libraries.\n\n"
        "## Exercises\n\n"
        "1. Read the tools manifest: `tools/manifest.json`\n"
        "2. Run a recipe: check `recipes/` for available commands\n"
        "3. Explore the wiki for domain knowledge\n"
        "4. Write your first tool in `tools/` and register it\n"
    ),
    "bootcamp/01-hello.py": (
        '#!/usr/bin/env python3\n"""Bootcamp exercise 1: Hello World."""\n'
        'print("Hello from bootcamp!")\n'
    ),
    "dojo/README.md": (
        "# Dojo\n\n"
        "Advanced skill-building. Practice kata, build custom compilers,\n"
        "experiment with novel techniques.\n\n"
        "## Philosophy\n\n"
        "Over time, build custom compilers for recurring tasks so the\n"
        "git-agent operator thinks about low-level work less and less.\n"
    ),
    "tools/README.md": (
        "# Tools\n\n"
        "Workshop tools — scripts, interpreters, and compilers.\n"
        "Register each tool in `tools/manifest.json`.\n"
    ),
    "tools/manifest.json": json.dumps({
        "tools": [],
        "interpreters": [],
        "compilers": [],
        "recipes": [],
    }, indent=2).replace("{", "{{").replace("}", "}}"),
    "recipes/README.md": (
        "# Recipes\n\n"
        "Saved command sequences for recurring tasks.\n\n"
        "## Format\n"
        "Each recipe is a markdown file with:\n"
        "- Description\n"
        "- Commands to run\n"
        "- Prerequisites\n"
        "- Usage notes\n"
    ),
    "wiki/README.md": (
        "# Wiki\n\n"
        "Knowledge base. Document discoveries, decisions, architecture.\n"
    ),
    "TASKBOARD.md": (
        "# Task Board\n\n"
        "## In Progress\n\n"
        "## Queued\n\n"
        "## Done\n"
    ),
    "JOURNAL.md": (
        "# Work Journal\n\n"
        "Auto-maintained by agents. Every thought and action recorded.\n"
    ),
    ".superagent/agent.toml": (
        "[agent]\n"
        "name = \"{name}\"\n"
        "role = \"{role}\"\n"
        "owner = \"{owner}\"\n\n"
        "[keeper]\n"
        "url = \"{keeper_url}\"\n\n"
        "[workshop]\n"
        "template = \"default\"\n"
        "created_at = \"{created_at}\"\n"
    ),
}


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

@dataclass
class ToolEntry:
    name: str
    path: str
    description: str = ""
    language: str = ""
    category: str = "script"  # script | interpreter | compiler | recipe
    created_by: str = ""
    created_at: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


class ToolRegistry:
    """Manages the tools/manifest.json registry."""

    def __init__(self, workshop_path: str):
        self.manifest_path = Path(workshop_path) / "tools" / "manifest.json"
        self._tools: Dict[str, ToolEntry] = {}
        self._logger = logging.getLogger("workshop.tools")
        self._load()

    def _load(self) -> None:
        if not self.manifest_path.exists():
            return
        try:
            data = json.loads(self.manifest_path.read_text())
            for cat in ("tools", "interpreters", "compilers", "recipes"):
                for entry in data.get(cat, []):
                    self._tools[entry["name"]] = ToolEntry(**entry, category=cat.rstrip("s"))
        except Exception as e:
            self._logger.error(f"Manifest load error: {e}")

    def _save(self) -> None:
        data = {"tools": [], "interpreters": [], "compilers": [], "recipes": []}
        for tool in self._tools.values():
            cat = tool.category + "s"
            if cat in data:
                data[cat].append(tool.to_dict())
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(data, indent=2))

    def register(self, name: str, path: str, description: str = "",
                 language: str = "", category: str = "script",
                 created_by: str = "", tags: Optional[List[str]] = None) -> ToolEntry:
        entry = ToolEntry(
            name=name, path=path, description=description,
            language=language, category=category, created_by=created_by,
            created_at=datetime.now(timezone.utc).isoformat(),
            tags=tags or [],
        )
        self._tools[name] = entry
        self._save()
        self._logger.info(f"Registered tool: {name} ({category})")
        return entry

    def unregister(self, name: str) -> bool:
        if name in self._tools:
            del self._tools[name]
            self._save()
            return True
        return False

    def get(self, name: str) -> Optional[ToolEntry]:
        return self._tools.get(name)

    def list_all(self) -> List[ToolEntry]:
        return list(self._tools.values())

    def by_category(self, category: str) -> List[ToolEntry]:
        return [t for t in self._tools.values() if t.category == category]

    def search(self, query: str) -> List[ToolEntry]:
        q = query.lower()
        return [t for t in self._tools.values()
                if q in t.name.lower() or q in t.description.lower()
                or q in t.language.lower() or any(q in tag for tag in t.tags)]


# ---------------------------------------------------------------------------
# Recipe Manager
# ---------------------------------------------------------------------------

@dataclass
class Recipe:
    name: str
    description: str = ""
    commands: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    created_by: str = ""
    tags: List[str] = field(default_factory=list)


class RecipeManager:
    """Manages recipes in the workshop."""

    def __init__(self, workshop_path: str):
        self.recipes_dir = Path(workshop_path) / "recipes"
        self._logger = logging.getLogger("workshop.recipes")

    def create(self, name: str, description: str, commands: List[str],
               prerequisites: Optional[List[str]] = None,
               created_by: str = "", tags: Optional[List[str]] = None) -> Path:
        recipe = Recipe(
            name=name, description=description, commands=commands,
            prerequisites=prerequisites or [], created_by=created_by,
            tags=tags or [],
        )
        path = self.recipes_dir / f"{name}.md"
        self.recipes_dir.mkdir(parents=True, exist_ok=True)
        content = self._render(recipe)
        path.write_text(content)
        self._logger.info(f"Recipe created: {name}")
        return path

    def list_recipes(self) -> List[str]:
        if not self.recipes_dir.exists():
            return []
        return [p.stem for p in self.recipes_dir.glob("*.md") if p.stem != "README"]

    def _render(self, recipe: Recipe) -> str:
        lines = [
            f"# {recipe.name}",
            "",
            recipe.description,
            "",
            "## Commands",
            "",
        ]
        for cmd in recipe.commands:
            lines.append(f"```bash\n{cmd}\n```")
            lines.append("")
        if recipe.prerequisites:
            lines.append("## Prerequisites")
            lines.append("")
            for prereq in recipe.prerequisites:
                lines.append(f"- {prereq}")
            lines.append("")
        if recipe.tags:
            lines.append(f"Tags: {', '.join(f'`{t}`' for t in recipe.tags)}")
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Workshop
# ---------------------------------------------------------------------------

class Workshop:
    """
    High-level workshop manager.

    Combines template initialization, tool registry, recipe management,
    and git operations into a single interface.
    """

    def __init__(self, path: str, config: Optional[AgentConfig] = None):
        self.path = Path(path)
        self.config = config
        self.tools = ToolRegistry(str(self.path))
        self.recipes = RecipeManager(str(self.path))
        self._logger = logging.getLogger("workshop")

    def initialize(self, template: str = "default", name: str = "workshop",
                   owner: str = "unknown", role: str = "git-agent",
                   keeper_url: str = "http://localhost:7742") -> bool:
        """
        Initialize workshop from template. Returns True on success.
        """
        if self.path.exists() and any(self.path.iterdir()):
            self._logger.warning(f"Workshop path already exists: {self.path}")
            return False

        # Create files from template
        for rel, content in DEFAULT_TEMPLATE.items():
            full = self.path / rel
            full.parent.mkdir(parents=True, exist_ok=True)
            # Skip format() for JSON files (braces conflict with .format())
            if rel.endswith(".json"):
                full.write_text(content.replace("{{", "{").replace("}}", "}"))
            else:
                rendered = content.format(
                    name=name, owner=owner, role=role,
                    keeper_url=keeper_url,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                full.write_text(rendered)

        # Initialize git
        try:
            subprocess.run(["git", "init"], cwd=str(self.path),
                           capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", f"git-agent [{name}]"],
                           cwd=str(self.path), capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", f"{name}@superinstance.local"],
                           cwd=str(self.path), capture_output=True, check=True)
            subprocess.run(["git", "add", "."], cwd=str(self.path),
                           capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m",
                           f"feat: initialize workshop for {owner}"],
                           cwd=str(self.path), capture_output=True, check=True)
        except Exception as e:
            self._logger.error(f"Git init failed: {e}")
            return False

        self._logger.info(f"Workshop initialized: {self.path}")
        return True

    def inventory(self) -> Dict[str, Any]:
        """Full workshop inventory."""
        tools = self.tools.list_all()
        recipes = self.recipes.list_recipes()
        return {
            "path": str(self.path),
            "tools": [t.to_dict() for t in tools],
            "tool_count": len(tools),
            "recipes": recipes,
            "recipe_count": len(recipes),
        }
