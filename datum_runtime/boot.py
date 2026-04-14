"""
datum_runtime.boot — The boot sequence logic for datum-runtime.

This module handles the complete boot sequence that gets Datum up and
running from scratch. The ``boot_datum()`` function is the ONE COMMAND
that creates everything: workshop, context, tools, prompts, config,
journal, and an active DatumAgent instance.

Functions:
    boot_datum         — Full initialization sequence
    resume_datum       — Resume from a previous session
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from datum_runtime.superagent.core import AgentConfig, AgentState
from datum_runtime.superagent.datum import DatumAgent
from datum_runtime.superagent.workshop import Workshop, DEFAULT_TEMPLATE
from datum_runtime.superagent.tui import TUI

console = Console()
tui = TUI()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Minimum Python version
# ---------------------------------------------------------------------------

MIN_PYTHON = (3, 10)

# ---------------------------------------------------------------------------
# Bundled context files — copied into workshop/context/
# ---------------------------------------------------------------------------

BUNDLED_CONTEXT = {
    "OPERATING_MANUAL.md": """# Datum Operating Manual

## Identity
Datum is a research, analysis, and audit specialist within the SuperInstance fleet.
It observes, measures, and reports — it does not act directly on workshops.

## Capabilities
- **Audit**: Workshop structure, fleet health, conformance checks
- **Analyze**: Cross-repo profiles, language distribution, tool inventory
- **Journal**: Chronological work log management
- **Report**: Markdown report generation for stakeholders

## Operational Knowledge
- All findings use severity levels: INFO, WARNING, ERROR, CRITICAL
- Reports are always in markdown for human readability
- Journal entries are timestamped with UTC ISO format
- Fleet auditing uses GitHub API with rate limiting (1.5s between requests)
- Secret access always goes through the Keeper — never store secrets locally
- Boundary enforcement: secrets never leave the SuperInstance

## Communication
- Use the message bus for inter-agent communication
- Respond to QUERY messages with RESPONSE messages
- Report findings via STATUS messages
- Log all significant actions to JOURNAL.md
""",
    "ARCHITECTURE.md": """# Datum Runtime Architecture

## Components
```
datum-runtime/
├── datum_runtime/
│   ├── cli.py           # Main CLI entry point (datum-rt)
│   ├── keeper_cli.py    # Keeper CLI entry point (keeper-rt)
│   ├── boot.py          # Boot sequence logic
│   ├── fleet_tools.py   # GitHub API fleet hygiene tools
│   ├── superagent/      # Bundled SuperInstance Agent Framework
│   │   ├── core.py      # Agent base, MessageBus, SecretProxy
│   │   ├── keeper.py    # KeeperAgent with AES-256-GCM
│   │   ├── git_agent.py # GitAgent with workshop management
│   │   ├── oracle.py    # OracleAgent with task board
│   │   ├── datum.py     # DatumAgent with audit/journal
│   │   ├── onboard.py   # Interactive onboarding flow
│   │   ├── tui.py       # Rich TUI components
│   │   ├── workshop.py  # Workshop template & tool registry
│   │   └── bus.py       # TCP message bus
│   └── __init__.py
├── templates/
│   └── workshop-template/
├── bin/
└── pyproject.toml
```

## Security Model
- All secrets held by Keeper, encrypted at rest (AES-256-GCM)
- PBKDF2 key derivation with 600,000 iterations (OWASP 2023)
- Boundary enforcement: fail-closed on unknown destinations
- Every secret access audited with requester, purpose, timestamp

## Communication
- In-process MessageBus for same-machine agents
- TCPBusServer/Client for cross-machine communication
- Messages: TASK, STATUS, QUERY, RESPONSE, ALERT, HEARTBEAT
""",
    "PRINCIPLES.md": """# Datum Operating Principles

1. **Observe First, Act Second**: Datum watches and measures before recommending action.

2. **Full Audit Trail**: Every action is journaled with timestamp, category, and reasoning.

3. **Human Readable**: All reports and logs are in markdown for direct human consumption.

4. **Zero External Dependencies**: Only click, rich, toml, and cryptography are required.

5. **Fail-Closed Security**: Secrets never leave the SuperInstance boundary. Unknown
   destinations are denied by default.

6. **Self-Contained**: The runtime bundles everything needed — clone and boot, nothing else.

7. **Resumable**: Work is persisted in JOURNAL.md and TRAIL.md. Sessions can be resumed.

8. **Standalone Mode**: Datum works without a Keeper, falling back to environment variables
   for secrets (with warnings).
""",
}

# ---------------------------------------------------------------------------
# Bundled prompts — copied into workshop/prompts/
# ---------------------------------------------------------------------------

BUNDLED_PROMPTS = {
    "audit-prompt.md": """# Audit Prompt Template

## Context
You are Datum, the research and analysis specialist. You have been asked to audit
a workshop or fleet for structural and conformance issues.

## Task
Perform a thorough audit and report findings with severity levels.

## Output Format
```markdown
# Audit Report

## Summary
| Severity | Count |
|----------|-------|
| ...      | ...   |

## Findings

### CRITICAL
- ...

### ERROR
- ...

### WARNING
- ...

### INFO
- ...
```

## Checks to Perform
1. Required directories present (bootcamp, dojo, tools, wiki, recipes)
2. TASKBOARD.md exists and has content
3. JOURNAL.md exists
4. .superagent/ directory and agent.toml present
5. Tools are registered in manifest
6. Git history is non-empty
""",
    "analysis-prompt.md": """# Analysis Prompt Template

## Context
You are Datum, performing a workshop analysis.

## Task
Profile the workshop and generate a comprehensive analysis report.

## Metrics to Collect
- Total files and directories
- Languages used (by file extension)
- Tool count and categories
- Commit history (count, frequency)
- Structure completeness (bootcamp, dojo, tools, wiki, recipes)
""",
    "journal-prompt.md": """# Journal Entry Prompt Template

## Format
Each journal entry should follow this format:

```
### [ISO-8601-timestamp] agent-name — category

Content of the entry...

`tags`
```

## Categories
- BOOT: System boot and initialization events
- AUDIT: Audit results and findings
- ANALYSIS: Workshop or fleet analysis results
- TASK: Task-related entries
- NOTE: General notes and observations
- DISCOVERY: New findings or insights
- FIX: Bug fixes and corrections
""",
}

# ---------------------------------------------------------------------------
# Boot sequence
# ---------------------------------------------------------------------------

def boot_datum(
    keeper_url: Optional[str] = None,
    workshop_path: str = "./workshop",
    non_interactive: bool = False,
) -> Optional[DatumAgent]:
    """
    Execute the full boot sequence for datum-runtime.

    This is the ONE COMMAND that gets everything running:
    1. Check Python version >= 3.10
    2. Check/install dependencies
    3. Create workshop directory from bundled template
    4. Copy context files into workshop/context/
    5. Copy tools into workshop/tools/
    6. Copy prompts into workshop/prompts/
    7. Write agent.toml config
    8. Connect to Keeper if reachable (else standalone mode)
    9. Initialize JOURNAL.md with boot entry
    10. Print status banner with all info
    11. Return the DatumAgent instance (ready to use)

    Args:
        keeper_url: Optional Keeper URL to connect to
        workshop_path: Path for the workshop directory
        non_interactive: Skip interactive prompts

    Returns:
        DatumAgent instance ready to use, or None on failure
    """
    ws_path = Path(workshop_path).resolve()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing datum-runtime...", total=None)

        # Step 1: Check Python version
        progress.update(task, description="Checking Python version...")
        if sys.version_info < MIN_PYTHON:
            console.print(
                f"[red]Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, "
                f"found {sys.version_info[0]}.{sys.version_info[1]}[/]"
            )
            return None
        console.print(f"  [green]ok[/] Python {sys.version_info[0]}.{sys.version_info[1]}")

        # Step 2: Check dependencies
        progress.update(task, description="Checking dependencies...")
        _check_dependencies()

        # Step 3: Create workshop from template
        progress.update(task, description="Creating workshop...")
        if not _create_workshop(ws_path):
            console.print(f"  [yellow]Workshop already exists at {ws_path} — using existing[/]")

        # Step 4: Copy context files
        progress.update(task, description="Installing context files...")
        _copy_context_files(ws_path)

        # Step 5: Copy tools
        progress.update(task, description="Installing tools...")
        _install_tools(ws_path)

        # Step 6: Copy prompts
        progress.update(task, description="Installing prompts...")
        _copy_prompt_files(ws_path)

        # Step 7: Write agent.toml config
        progress.update(task, description="Writing configuration...")
        _write_agent_config(ws_path, keeper_url)

        # Step 8: Connect to Keeper
        progress.update(task, description="Connecting to Keeper...")
        keeper_connected = _connect_keeper(ws_path, keeper_url)
        if keeper_connected:
            console.print(f"  [green]ok[/] Connected to Keeper")
        else:
            console.print(f"  [yellow]standalone mode[/] — Keeper not reachable")

        # Step 9: Initialize DatumAgent
        progress.update(task, description="Activating Datum...")
        datum = _activate_datum(ws_path, keeper_url)

        # Step 10: Initialize journal with boot entry
        progress.update(task, description="Initializing journal...")
        _init_journal(ws_path, datum)

        # Step 11: Create TRAIL.md
        progress.update(task, description="Creating trail file...")
        _init_trail(ws_path)

        progress.update(task, description="Boot complete!")

    return datum


def resume_datum(workshop_path: str = "./workshop") -> None:
    """
    Resume from a previous session.

    Reads JOURNAL.md and TRAIL.md from the workshop to understand where
    Datum left off, prints a status summary, and suggests next tasks.

    Args:
        workshop_path: Path to the workshop directory
    """
    ws_path = Path(workshop_path).resolve()

    if not ws_path.exists():
        console.print(f"[red]Workshop not found at {ws_path}[/]")
        return

    console.print()
    console.print(Panel(
        "[bold cyan]Session Resume[/]",
        title=f"Workshop: {ws_path.name}",
        border_style="cyan",
    ))

    # Read JOURNAL.md
    journal_path = ws_path / "JOURNAL.md"
    trail_path = ws_path / "TRAIL.md"

    if journal_path.exists():
        content = journal_path.read_text()
        # Count entries (## or ### headers)
        entries = [l for l in content.split("\n") if l.startswith("## ") or l.startswith("### ")]
        console.print(f"\n  [bold]Journal:[/] {len(entries)} entries")

        # Show last few entries
        recent_entries = entries[-5:]
        console.print(f"\n  [bold]Recent entries:[/]")
        for entry in recent_entries:
            clean = entry.lstrip("# ").strip()
            console.print(f"    [dim]{clean}[/]")

    # Read TRAIL.md
    if trail_path.exists():
        trail_content = trail_path.read_text()
        console.print(f"\n  [bold]Trail:[/]")
        # Extract sections
        for line in trail_content.split("\n"):
            if line.startswith("## "):
                console.print(f"    [cyan]{line.lstrip('# ')}[/]")
            elif line.startswith("- ") and not line.startswith("- ["):
                console.print(f"    {line}")

    # Check taskboard
    taskboard_path = ws_path / "TASKBOARD.md"
    if taskboard_path.exists():
        tb_content = taskboard_path.read_text()
        # Count open tasks
        in_progress = tb_content.count("- [ ] ")
        done = tb_content.count("- [x] ")
        console.print(f"\n  [bold]Task Board:[/]")
        console.print(f"    Open: {in_progress} | Done: {done}")

    # Parse incomplete tasks from taskboard
    console.print(f"\n  [bold]Suggestions:[/]")
    suggestions = _generate_suggestions(ws_path)
    for i, suggestion in enumerate(suggestions, 1):
        console.print(f"    {i}. {suggestion}")

    if not suggestions:
        console.print(f"    [dim]All looks good! Consider running an audit or starting a new task.[/]")

    console.print()


def _check_dependencies() -> None:
    """Verify required dependencies are installed."""
    missing = []
    try:
        import click
    except ImportError:
        missing.append("click>=8.0")
    try:
        import rich
    except ImportError:
        missing.append("rich>=13.0")
    try:
        import toml
    except ImportError:
        missing.append("toml>=0.10")
    try:
        import cryptography
    except ImportError:
        missing.append("cryptography>=41.0")

    if missing:
        console.print(f"  [yellow]Installing missing dependencies...[/]")
        for dep in missing:
            console.print(f"    pip install {dep}")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-q", dep],
                    capture_output=True, timeout=60,
                )
            except Exception as e:
                console.print(f"    [red]Failed to install {dep}: {e}[/]")
    else:
        console.print(f"  [green]ok[/] All dependencies satisfied")


def _create_workshop(ws_path: Path) -> bool:
    """
    Create workshop directory from bundled template.

    Returns True if created, False if already exists.
    """
    if ws_path.exists() and any(ws_path.iterdir()):
        return False

    ws_path.mkdir(parents=True, exist_ok=True)

    # Create from DEFAULT_TEMPLATE in workshop.py
    from datetime import datetime
    now = datetime.now(timezone.utc).isoformat()

    for rel_path, content in DEFAULT_TEMPLATE.items():
        full_path = ws_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        # Skip format() for JSON files (braces conflict with .format())
        if rel_path.endswith(".json"):
            full_path.write_text(content.replace("{{", "{").replace("}}", "}"))
        else:
            rendered = content.format(
                name="datum-workshop",
                owner="datum",
                role="datum",
                keeper_url="http://localhost:7742",
                created_at=now,
            )
            full_path.write_text(rendered)

    # Initialize git repo
    try:
        subprocess.run(["git", "init"], cwd=str(ws_path), capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.name", "datum-runtime"],
            cwd=str(ws_path), capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "datum@superinstance.local"],
            cwd=str(ws_path), capture_output=True, check=True,
        )
        subprocess.run(["git", "add", "."], cwd=str(ws_path), capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: initialize workshop from datum-runtime template"],
            cwd=str(ws_path), capture_output=True, check=True,
        )
    except Exception as e:
        logger.warning(f"Git init skipped: {e}")

    console.print(f"  [green]ok[/] Workshop created at {ws_path}")
    return True


def _copy_context_files(ws_path: Path) -> None:
    """Copy bundled context files into workshop/context/."""
    context_dir = ws_path / "context"
    context_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for name, content in BUNDLED_CONTEXT.items():
        (context_dir / name).write_text(content)
        count += 1

    console.print(f"  [green]ok[/] {count} context files installed")


def _install_tools(ws_path: Path) -> None:
    """Install bundled tool stubs into workshop/tools/."""
    tools_dir = ws_path / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)

    # Install a fleet audit tool script
    fleet_tool = tools_dir / "fleet-audit.py"
    fleet_tool.write_text("""#!/usr/bin/env python3
\"\"\"Fleet audit tool — scans GitHub org repos for hygiene issues.\"\"\"

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datum_runtime.fleet_tools import scan_org

if __name__ == "__main__":
    org = sys.argv[1] if len(sys.argv) > 1 else input("GitHub org: ")
    token = os.environ.get("GITHUB_TOKEN", "")
    result = scan_org(org, token)
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Fleet: {result['summary']}")
        print(f"Health score: {result['stats']['health_score']}/100")
""")

    # Install a conformance checker
    conformance_tool = tools_dir / "conformance-check.py"
    conformance_tool.write_text("""#!/usr/bin/env python3
\"\"\"Conformance checker — validates workshop structure against standards.\"\"\"

import sys
import os
from pathlib import Path

def check(path="."):
    ws = Path(path)
    issues = []
    required = ["bootcamp", "dojo", "tools", "wiki", "recipes"]
    for d in required:
        if not (ws / d).is_dir():
            issues.append(f"Missing: {d}/")
    for f in ["TASKBOARD.md", "JOURNAL.md"]:
        if not (ws / f).exists():
            issues.append(f"Missing: {f}")
    if issues:
        print(f"Conformance issues ({len(issues)}):")
        for i in issues:
            print(f"  - {i}")
    else:
        print("Conformance: PASS")
    return len(issues) == 0

if __name__ == "__main__":
    check(sys.argv[1] if len(sys.argv) > 1 else ".")
""")

    console.print(f"  [green]ok[/] 2 tools installed (fleet-audit.py, conformance-check.py)")


def _copy_prompt_files(ws_path: Path) -> None:
    """Copy bundled prompt templates into workshop/prompts/."""
    prompts_dir = ws_path / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for name, content in BUNDLED_PROMPTS.items():
        (prompts_dir / name).write_text(content)
        count += 1

    console.print(f"  [green]ok[/] {count} prompt templates installed")


def _write_agent_config(ws_path: Path, keeper_url: Optional[str]) -> None:
    """Write agent.toml configuration to the workshop."""
    import toml

    sa_dir = ws_path / ".superagent"
    sa_dir.mkdir(parents=True, exist_ok=True)

    config_data = {
        "agent": {
            "name": "datum",
            "role": "datum",
            "capabilities": ["audit", "analyze", "journal", "report", "cross-repo"],
        },
        "keeper": {
            "host": (keeper_url or "http://localhost:7742").replace("http://", "").split(":")[0],
            "port": int((keeper_url or "http://localhost:7742").split(":")[-1]),
        },
        "workshop": {
            "path": str(ws_path),
            "template": "datum-default",
        },
        "logging": {
            "level": "INFO",
        },
    }

    config_path = sa_dir / "agent.toml"
    config_path.write_text(toml.dumps(config_data))
    console.print(f"  [green]ok[/] Config written to {config_path}")


def _connect_keeper(ws_path: Path, keeper_url: Optional[str]) -> bool:
    """
    Attempt to connect to the Keeper.

    Returns True if connection succeeded, False otherwise (standalone mode).
    """
    from datum_runtime.superagent.core import SecretProxy

    url = keeper_url or "http://localhost:7742"
    try:
        proxy = SecretProxy(url, "datum-boot")
        # Try a health check
        import urllib.request
        req = urllib.request.Request(f"{url}/api/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("status") == "ok"
    except Exception:
        return False


def _activate_datum(ws_path: Path, keeper_url: Optional[str]) -> DatumAgent:
    """Create and activate the DatumAgent."""
    cfg = AgentConfig(
        name="datum",
        role="datum",
        repo_path=str(ws_path),
        keeper_url=keeper_url or "http://localhost:7742",
        capabilities=["audit", "analyze", "journal", "report", "cross-repo"],
    )

    datum = DatumAgent(config=cfg)
    datum.init_journal(str(ws_path))

    # Try to onboard to Keeper
    datum.onboard(keeper_url=keeper_url)

    # Activate
    datum.activate()
    console.print(f"  [green]ok[/] Datum agent activated: {datum.name}")

    return datum


def _init_journal(ws_path: Path, datum: DatumAgent) -> None:
    """Initialize JOURNAL.md with a boot entry."""
    journal_path = ws_path / "JOURNAL.md"

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = (
        f"## [{ts}] BOOT\n\n"
        f"datum-runtime v0.2.0 booted successfully.\n\n"
        f"- Agent: {datum.name}\n"
        f"- State: {datum.state.value}\n"
        f"- Workshop: {ws_path}\n"
        f"- Keeper: {datum.config.keeper_url}\n"
        f"- Capabilities: {', '.join(datum.config.capabilities)}\n"
    )

    if journal_path.exists():
        existing = journal_path.read_text()
        journal_path.write_text(existing + "\n\n" + entry)
    else:
        journal_path.write_text(f"# {datum.name} — Work Journal\n\n{entry}\n")

    console.print(f"  [green]ok[/] Journal initialized with boot entry")


def _init_trail(ws_path: Path) -> None:
    """Create TRAIL.md to track Datum's session state."""
    trail_path = ws_path / "TRAIL.md"

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    content = (
        f"# Datum Trail — Session Tracking\n\n"
        f"Last updated: {ts}\n\n"
        f"## Current Focus\n\n"
        f"- Session started from boot\n"
        f"- No active tasks yet\n\n"
        f"## Completed\n\n"
        f"- Boot sequence completed\n\n"
        f"## Pending\n\n"
        f"- Run `datum-rt audit` to check workshop health\n"
        f"- Run `datum-rt status` to see current state\n"
        f"- Start working on tasks via the task board\n"
    )

    trail_path.write_text(content)
    console.print(f"  [green]ok[/] Trail file created")


def _generate_suggestions(ws_path: Path) -> List[str]:
    """Generate actionable suggestions based on workshop state."""
    suggestions = []

    # Check if audit has been run
    journal_path = ws_path / "JOURNAL.md"
    if journal_path.exists():
        content = journal_path.read_text().lower()
        if "audit" not in content:
            suggestions.append("Run an audit: [cyan]datum-rt audit[/]")
    else:
        suggestions.append("Run an audit: [cyan]datum-rt audit[/]")

    # Check if there are open tasks
    taskboard_path = ws_path / "TASKBOARD.md"
    if taskboard_path.exists():
        content = taskboard_path.read_text()
        if "- [ ] " in content:
            open_count = content.count("- [ ] ")
            suggestions.append(f"Review {open_count} open task(s) on the task board")

    # Check for missing descriptions
    if not (ws_path / "context" / "OPERATING_MANUAL.md").exists():
        suggestions.append("Context files may need updating")

    # General suggestions
    suggestions.append("Run fleet analysis: [cyan]datum-rt analyze[/]")
    suggestions.append("Check bundled tools: [cyan]datum-rt tools list[/]")

    return suggestions
