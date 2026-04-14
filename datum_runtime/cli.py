"""
datum_runtime.cli — The primary Datum runtime CLI.

This is the main entry point for the datum-runtime package. It provides
a single command that gets everything running: ``datum-rt boot``.

Commands:
    boot       — Full initialization, workshop creation, Keeper connect, Datum activate
    audit      — Run workshop, fleet, or conformance audits
    analyze    — Profile a workshop and show stats
    journal    — Add entries to the work journal
    report     — Generate markdown reports
    status     — Show current agent state, workshop health, and tool inventory
    resume     — Read JOURNAL.md/TRAIL.md and suggest next tasks
    tools      — List or run bundled tools
    fleet      — Fleet hygiene operations (scan, tag, license, report)
    bottle     — Message-in-a-Bottle operations (drop, check, read, broadcast, summary)
    onboard    — Interactive onboarding flow
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from datum_runtime.superagent.core import AgentConfig
from datum_runtime.superagent.datum import DatumAgent
from datum_runtime.superagent.tui import TUI

console = Console()
tui = TUI()

# ---------------------------------------------------------------------------
# Bundled tool registry — tools shipped with datum-runtime
# ---------------------------------------------------------------------------

BUNDLED_TOOLS = {
    "audit-scanner": {
        "description": "Scan a workshop or directory for structural and conformance issues",
        "module": "datum_runtime.fleet_tools",
        "usage": "datum-rt tools run audit-scanner --org ORG",
    },
    "fleet-scanner": {
        "description": "Scan all repos in a GitHub org and report health (green/yellow/red/dead)",
        "module": "datum_runtime.fleet_tools",
        "usage": "datum-rt tools run fleet-scanner --org ORG --token TOKEN",
    },
    "repo-tagger": {
        "description": "Add topics/tags to repos in a GitHub org",
        "module": "datum_runtime.fleet_tools",
        "usage": "datum-rt tools run repo-tagger --org ORG --token TOKEN",
    },
    "license-adder": {
        "description": "Add LICENSE files to repos missing them",
        "module": "datum_runtime.fleet_tools",
        "usage": "datum-rt tools run license-adder --org ORG --token TOKEN",
    },
    "fleet-reporter": {
        "description": "Generate a comprehensive fleet hygiene report",
        "module": "datum_runtime.fleet_tools",
        "usage": "datum-rt tools run fleet-reporter --org ORG --token TOKEN",
    },
}


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.version_option(package_name="datum-runtime", message="%(prog)s v%(version)s")
@click.pass_context
def main(ctx: click.Context) -> None:
    """
    datum-rt — Self-bootstrapping Datum agent runtime.

    Clone, boot, and Datum is off and running with all its knowledge intact.
    """
    ctx.ensure_object(dict)


# ---------------------------------------------------------------------------
# boot — Full initialization
# ---------------------------------------------------------------------------

@main.command()
@click.option("--keeper", "-k", default=None, help="Keeper URL to connect to")
@click.option("--workshop", "-w", default="./workshop", help="Workshop path")
@click.option("--non-interactive", "-n", is_flag=True, help="Skip interactive prompts")
@click.pass_context
def boot(ctx: click.Context, keeper: Optional[str], workshop: str, non_interactive: bool) -> None:
    """
    Full initialization — ONE COMMAND to get everything running.

    Creates workshop from template, copies context/tools/prompts, connects
    to Keeper if reachable, activates Datum, and initializes the journal.
    """
    from datum_runtime.boot import boot_datum

    console.print()
    console.print(Panel(
        "[bold cyan]datum-runtime v0.2.0[/]\n"
        "Self-bootstrapping Datum agent runtime",
        title="Boot Sequence",
        border_style="cyan",
        padding=(1, 2),
    ))

    try:
        agent = boot_datum(
            keeper_url=keeper,
            workshop_path=workshop,
            non_interactive=non_interactive,
        )

        if agent:
            console.print(Panel(
                f"[bold green]Datum is ACTIVE[/]\n"
                f"Name: {agent.name}\n"
                f"State: {agent.state.value}\n"
                f"Workshop: {agent.config.repo_path}\n"
                f"Keeper: {agent.config.keeper_url}\n\n"
                f"[dim]Run 'datum-rt status' to check health.[/]\n"
                f"[dim]Run 'datum-rt resume' to continue previous work.[/]",
                title="Boot Complete",
                border_style="green",
                padding=(1, 2),
            ))
        else:
            console.print("[bold red]Boot failed — check errors above.[/]")

    except Exception as e:
        console.print(f"[bold red]Boot error:[/] {e}")
        if os.environ.get("DATUM_DEBUG"):
            raise


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------

@main.command()
@click.option("--type", "-t", "audit_type", default="workshop",
              type=click.Choice(["workshop", "fleet", "conformance"]),
              help="Type of audit to run")
@click.option("--path", "-p", default=None, help="Path to audit")
@click.option("--workshop", "-w", default="./workshop", help="Workshop path")
def audit(audit_type: str, path: Optional[str], workshop: str) -> None:
    """
    Run an audit on a workshop or the fleet.
    """
    cfg = AgentConfig(role="datum", repo_path=path or workshop)
    datum = DatumAgent(config=cfg)
    datum.init_journal(path or workshop)

    if audit_type in ("workshop", "conformance"):
        report = datum.audit_workshop(path)
    else:
        report = datum.audit_fleet()

    console.print(Panel(
        report.to_markdown(),
        title=report.title,
        border_style="cyan",
        padding=(1, 2),
    ))


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------

@main.command()
@click.option("--path", "-p", default=None, help="Workshop path to analyze")
@click.option("--workshop", "-w", default="./workshop", help="Workshop path")
def analyze(path: Optional[str], workshop: str) -> None:
    """
    Analyze a workshop profile and show stats.
    """
    target = path or workshop
    cfg = AgentConfig(role="datum", repo_path=target)
    datum = DatumAgent(config=cfg)
    profile = datum.analyze_workshop(target)

    console.print()
    console.print(f"  [bold]Workshop:[/] {profile.get('name', 'N/A')}")
    console.print(f"  Files: {profile.get('total_files', 0)}")
    console.print(f"  Dirs: {profile.get('total_dirs', 0)}")
    console.print(f"  Commits: {profile.get('commit_count', 0)}")
    console.print(f"  Tools: {profile.get('tool_count', 0)}")

    langs = profile.get("languages_used", [])
    if langs:
        console.print(f"  Languages: {', '.join(langs)}")

    structure_items = []
    for d in ("has_bootcamp", "has_dojo", "has_tools", "has_wiki", "has_recipes"):
        name = d.replace("has_", "")
        icon = "[green]ok[/]" if profile.get(d) else "[dim]missing[/]"
        structure_items.append(f"{icon} {name}")
    console.print(f"  Structure: {' | '.join(structure_items)}")


# ---------------------------------------------------------------------------
# journal
# ---------------------------------------------------------------------------

@main.command()
@click.argument("category")
@click.argument("content")
@click.option("--agent", "-a", default=None, help="Agent name")
@click.option("--tag", "-t", multiple=True, help="Tags")
@click.option("--workshop", "-w", default="./workshop", help="Workshop path")
def journal(category: str, content: str, agent: Optional[str], tag: tuple, workshop: str) -> None:
    """
    Add an entry to the work journal.
    """
    cfg = AgentConfig(role="datum", repo_path=workshop)
    datum = DatumAgent(config=cfg)
    datum.init_journal(workshop)
    result = datum.journal(category, content, agent=agent, tags=list(tag))
    console.print(f"[green]ok[/] Journal entry recorded at {result['timestamp']}")


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

@main.command()
@click.argument("report_type", default="workshop",
                type=click.Choice(["workshop", "fleet", "conformance"]))
@click.option("--workshop", "-w", default="./workshop", help="Workshop path")
def report(report_type: str, workshop: str) -> None:
    """
    Generate a markdown report.
    """
    cfg = AgentConfig(role="datum", repo_path=workshop)
    datum = DatumAgent(config=cfg)
    md = datum.generate_report(report_type)
    console.print(Panel(
        md,
        title=f"{report_type.title()} Report",
        border_style="green",
        padding=(1, 2),
    ))


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@main.command()
@click.option("--workshop", "-w", default="./workshop", help="Workshop path")
def status(workshop: str) -> None:
    """
    Show current agent state, workshop health, and tool inventory.
    """
    ws_path = Path(workshop)

    console.print()
    console.print(Panel(
        "[bold cyan]datum-runtime v0.2.0[/]",
        title="Runtime Status",
        border_style="cyan",
    ))

    # Workshop health
    console.print()
    console.print("[bold]Workshop[/]")
    if ws_path.exists():
        console.print(f"  Path: [cyan]{ws_path.resolve()}[/]")
        required_dirs = ["bootcamp", "dojo", "tools", "wiki", "recipes"]
        for d in required_dirs:
            exists = (ws_path / d).is_dir()
            icon = "[green]ok[/]" if exists else "[red]missing[/]"
            console.print(f"  {icon} {d}/")

        journal_path = ws_path / "JOURNAL.md"
        taskboard_path = ws_path / "TASKBOARD.md"
        console.print(f"  {'[green]ok[/]' if journal_path.exists() else '[yellow]no[/]'} JOURNAL.md")
        console.print(f"  {'[green]ok[/]' if taskboard_path.exists() else '[yellow]no[/]'} TASKBOARD.md")

        # Recent journal entries
        if journal_path.exists():
            lines = journal_path.read_text().strip().split("\n")
            entry_count = sum(1 for l in lines if l.startswith("## ") or l.startswith("### "))
            console.print(f"  Journal entries: {entry_count}")
    else:
        console.print(f"  [yellow]Workshop not found at {workshop}[/]")
        console.print(f"  [dim]Run 'datum-rt boot' to create it.[/]")

    # Bundled tools
    console.print()
    console.print(f"[bold]Bundled Tools[/] ({len(BUNDLED_TOOLS)} tools)")
    table = Table(box=None, padding=(0, 2))
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    for name, info in BUNDLED_TOOLS.items():
        table.add_row(name, info["description"])
    console.print(table)

    # Python version
    console.print()
    console.print(f"[bold]Environment[/]")
    console.print(f"  Python: {sys.version.split()[0]}")
    console.print(f"  Runtime: datum-runtime v0.2.0")


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------

@main.command()
@click.option("--workshop", "-w", default="./workshop", help="Workshop path")
def resume(workshop: str) -> None:
    """
    Resume from a previous session — reads journal and suggests next tasks.
    """
    from datum_runtime.boot import resume_datum

    ws_path = Path(workshop)
    if not ws_path.exists():
        console.print(f"[red]Workshop not found at {workshop}[/]")
        console.print(f"[dim]Run 'datum-rt boot' to create it first.[/]")
        return

    resume_datum(workshop_path=workshop)


# ---------------------------------------------------------------------------
# tools — list and run bundled tools
# ---------------------------------------------------------------------------

@main.group()
def tools() -> None:
    """
    List or run bundled tools.
    """
    pass


@tools.command(name="list")
def tools_list() -> None:
    """
    List all bundled tools with descriptions.
    """
    table = Table(title="Bundled Tools")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Usage", style="dim")

    for name, info in BUNDLED_TOOLS.items():
        table.add_row(name, info["description"], info["usage"])

    console.print(table)


@tools.command(name="run")
@click.argument("tool_name")
@click.argument("args", nargs=-1)
@click.option("--org", "-o", default=None, help="GitHub org for fleet tools")
@click.option("--token", "-t", default=None, help="GitHub token")
@click.option("--dry-run", is_flag=True, help="Dry run (no changes)")
@click.option("--license-type", default="MIT", help="License type for license-adder")
@click.option("--path", "-p", default=None, help="Path for local tools")
def tools_run(tool_name: str, args: tuple, org: Optional[str], token: Optional[str],
              dry_run: bool, license_type: str, path: Optional[str]) -> None:
    """
    Run a bundled tool.

    Available tools: audit-scanner, fleet-scanner, repo-tagger, license-adder, fleet-reporter
    """
    if tool_name not in BUNDLED_TOOLS:
        console.print(f"[red]Unknown tool:[/] {tool_name}")
        console.print(f"[dim]Available: {', '.join(BUNDLED_TOOLS.keys())}[/]")
        return

    from datum_runtime.fleet_tools import (
        scan_org, tag_repos, add_licenses, audit_repos, repo_stats,
    )

    gh_token = token or os.environ.get("GITHUB_TOKEN", "")

    if tool_name == "fleet-scanner":
        if not org:
            console.print("[red]--org is required for fleet-scanner[/]")
            return
        console.print(f"[cyan]Scanning org:[/] {org}")
        result = scan_org(org, gh_token)
        _print_fleet_result(result)

    elif tool_name == "repo-tagger":
        if not org:
            console.print("[red]--org is required for repo-tagger[/]")
            return
        console.print(f"[cyan]Tagging repos in:[/] {org}")
        result = tag_repos(org, gh_token, {}, dry_run=dry_run)
        _print_fleet_result(result)

    elif tool_name == "license-adder":
        if not org:
            console.print("[red]--org is required for license-adder[/]")
            return
        console.print(f"[cyan]Adding licenses to:[/] {org}")
        result = add_licenses(org, gh_token, license_type=license_type, dry_run=dry_run)
        _print_fleet_result(result)

    elif tool_name == "fleet-reporter":
        if not org:
            console.print("[red]--org is required for fleet-reporter[/]")
            return
        console.print(f"[cyan]Generating fleet report for:[/] {org}")
        result = repo_stats(org, gh_token)
        _print_fleet_result(result)

    elif tool_name == "audit-scanner":
        target = path or "./workshop"
        cfg = AgentConfig(role="datum", repo_path=target)
        datum = DatumAgent(config=cfg)
        report = datum.audit_workshop(target)
        console.print(Panel(
            report.to_markdown(),
            title=report.title,
            border_style="cyan",
        ))

    else:
        console.print(f"[yellow]Tool '{tool_name}' exists but has no runner yet.[/]")


def _print_fleet_result(result: dict) -> None:
    """Pretty-print a fleet operation result."""
    if "error" in result:
        console.print(f"[red]Error:[/] {result['error']}")
        return

    console.print()
    if "stats" in result:
        stats = result["stats"]
        table = Table(title="Fleet Stats")
        table.add_column("Metric", style="cyan")
        table.add_column("Value")
        for k, v in stats.items():
            table.add_row(k, str(v))
        console.print(table)

    if "repos" in result:
        repos = result["repos"]
        console.print(f"\n  [bold]{len(repos)} repos found[/]")
        table = Table()
        table.add_column("Repo", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Issues")
        for repo in repos[:50]:  # Limit display
            status = repo.get("status", "unknown")
            status_style = {
                "green": "[green]green[/]",
                "yellow": "[yellow]yellow[/]",
                "red": "[red]red[/]",
                "dead": "[dim]dead[/]",
            }.get(status, status)
            issues = ", ".join(repo.get("issues", [])) if repo.get("issues") else "none"
            table.add_row(repo.get("name", ""), status_style, issues[:60])
        console.print(table)

    if "actions" in result:
        actions = result["actions"]
        if actions:
            console.print(f"\n  [bold]Actions taken:[/]")
            for action in actions[:20]:
                console.print(f"    - {action}")

    console.print()


# ---------------------------------------------------------------------------
# fleet — Fleet hygiene operations
# ---------------------------------------------------------------------------

@main.group()
def fleet() -> None:
    """
    Fleet hygiene operations using GitHub API.
    """
    pass


@fleet.command()
@click.option("--org", "-o", required=True, help="GitHub organization")
@click.option("--token", "-t", default=None, help="GitHub PAT (or set GITHUB_TOKEN)")
def scan(org: str, token: Optional[str]) -> None:
    """
    Scan all repos in a GitHub org for health status.
    """
    from datum_runtime.fleet_tools import scan_org

    gh_token = token or os.environ.get("GITHUB_TOKEN", "")
    console.print(f"[cyan]Scanning {org}...[/]")
    result = scan_org(org, gh_token)
    _print_fleet_result(result)


@fleet.command()
@click.option("--org", "-o", required=True, help="GitHub organization")
@click.option("--token", "-t", default=None, help="GitHub PAT (or set GITHUB_TOKEN)")
@click.option("--dry-run", is_flag=True, help="Show what would be tagged without making changes")
@click.option("--mapping", "-m", default=None, help="JSON mapping of repo->topics (e.g. '{\"repo1\":[\"tag1\"]}')'")
def tag(org: str, token: Optional[str], dry_run: bool, mapping: Optional[str]) -> None:
    """
    Add topics/tags to repos in a GitHub org.
    """
    import json as _json
    from datum_runtime.fleet_tools import tag_repos

    gh_token = token or os.environ.get("GITHUB_TOKEN", "")
    topic_mapping = {}
    if mapping:
        try:
            topic_mapping = _json.loads(mapping)
        except _json.JSONDecodeError:
            console.print("[red]Invalid JSON in --mapping[/]")
            return

    console.print(f"[cyan]Tagging repos in {org}...[/]")
    result = tag_repos(org, gh_token, topic_mapping, dry_run=dry_run)
    _print_fleet_result(result)


@fleet.command()
@click.option("--org", "-o", required=True, help="GitHub organization")
@click.option("--token", "-t", default=None, help="GitHub PAT (or set GITHUB_TOKEN)")
@click.option("--license-type", "-l", default="MIT", help="License type to add")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
def license(org: str, token: Optional[str], license_type: str, dry_run: bool) -> None:
    """
    Add LICENSE files to repos missing them.
    """
    from datum_runtime.fleet_tools import add_licenses

    gh_token = token or os.environ.get("GITHUB_TOKEN", "")
    console.print(f"[cyan]Adding {license_type} licenses to {org}...[/]")
    result = add_licenses(org, gh_token, license_type=license_type, dry_run=dry_run)
    _print_fleet_result(result)


@fleet.command()
@click.option("--org", "-o", required=True, help="GitHub organization")
@click.option("--token", "-t", default=None, help="GitHub PAT (or set GITHUB_TOKEN)")
def report(org: str, token: Optional[str]) -> None:
    """
    Generate a comprehensive fleet hygiene report.
    """
    from datum_runtime.fleet_tools import repo_stats

    gh_token = token or os.environ.get("GITHUB_TOKEN", "")
    console.print(f"[cyan]Generating fleet report for {org}...[/]")
    result = repo_stats(org, gh_token)
    _print_fleet_result(result)


# ---------------------------------------------------------------------------
# bottle — Message-in-a-Bottle operations
# ---------------------------------------------------------------------------

@main.group()
@click.option("--workshop", "-w", default="./workshop", help="Workshop path")
@click.option("--sender", "-s", default="datum", help="Sender agent name")
@click.pass_context
def bottle(ctx: click.Context, workshop: str, sender: str) -> None:
    """
    Message-in-a-Bottle — fleet async communication.

    Drop bottles for other agents, check your inbox, read bottles, broadcast.
    Bottles are markdown files stored in message-in-a-bottle/ directories.
    """
    ctx.ensure_object(dict)
    ctx.obj["workshop"] = workshop
    ctx.obj["sender"] = sender


@bottle.command(name="drop")
@click.argument("agent")
@click.argument("subject")
@click.option("--content", "-c", default=None, help="Message body (reads from stdin if not provided)")
@click.option("--type", "-t", "bottle_type", default="message",
              type=click.Choice(["message", "signal", "check-in", "alert", "deliverable", "handoff", "question"]))
@click.pass_context
def bottle_drop(ctx: click.Context, agent: str, subject: str, content: Optional[str],
               bottle_type: str) -> None:
    """
    Drop a bottle for a specific agent.

    AGENT: Target agent name (e.g. oracle1, jetsonclaw1).
    SUBJECT: Short subject line.
    """
    from datum_runtime.superagent.mib import MessageInBottle

    workshop = ctx.obj["workshop"]
    sender = ctx.obj["sender"]

    if not content:
        if not sys.stdin.isatty():
            content = sys.stdin.read().strip()
        else:
            console.print("[dim]Enter message body (Ctrl+D to finish):[/]")
            content = sys.stdin.read().strip()

    if not content:
        console.print("[red]No content provided.[/]")
        return

    mib = MessageInBottle(base_path=workshop, sender=sender)
    path = mib.drop(agent, subject, content, bottle_type=bottle_type)
    console.print(f"[green]ok[/] Bottle dropped: {path}")
    console.print(f"  From: {sender} → To: {agent}")
    console.print(f"  Type: {bottle_type} | Subject: {subject}")


@bottle.command(name="check")
@click.option("--inbox", "-i", default=None, help="Inbox directory (default: for-datum)")
@click.pass_context
def bottle_check(ctx: click.Context, inbox: Optional[str]) -> None:
    """
    Check inbox for new bottles.
    """
    from datum_runtime.superagent.mib import MessageInBottle

    mib = MessageInBottle(base_path=ctx.obj["workshop"], sender=ctx.obj["sender"])
    bottles = mib.check(inbox)

    if not bottles:
        console.print("[dim]No bottles in inbox.[/]")
        return

    console.print(f"[bold]{len(bottles)} bottle(s) in inbox:[/]")
    for bp in bottles:
        try:
            header, _ = mib.read(bp)
            sender = header.get("from", "?")
            date = header.get("date", "?")
            subj = header.get("subject", "?")
            btype = header.get("type", "?")
            console.print(f"  [cyan]{subj}[/]  from [bold]{sender}[/] ({date}) [{btype}]")
        except Exception as e:
            console.print(f"  [red]Error reading:[/] {os.path.basename(bp)}: {e}")


@bottle.command(name="read")
@click.argument("path")
@click.pass_context
def bottle_read(ctx: click.Context, path: str) -> None:
    """
    Read a bottle file. PATH can be a file path or just the filename.
    """
    from datum_runtime.superagent.mib import MessageInBottle

    mib = MessageInBottle(base_path=ctx.obj["workshop"], sender=ctx.obj["sender"])

    # Resolve path — if not absolute, look in message-in-a-bottle/
    if not os.path.isabs(path):
        # Try direct path first
        full = Path(ctx.obj["workshop"]) / "message-in-a-bottle" / path
        if not full.exists():
            # Try recursive search
            results = list(Path(ctx.obj["workshop"]).rglob(f"*{path}*"))
            if results:
                full = results[0]
            else:
                console.print(f"[red]Bottle not found:[/] {path}")
                return
        path = str(full)

    try:
        header, body = mib.read(path)
        console.print(Panel(
            body,
            title=f"{header.get('subject', 'Bottle')}  (from {header.get('from', '?')})",
            border_style="cyan",
            padding=(1, 2),
        ))
        console.print(f"  [dim]Type: {header.get('type', '?')} | Date: {header.get('date', '?')}[/]")
    except FileNotFoundError:
        console.print(f"[red]Bottle not found:[/] {path}")


@bottle.command(name="broadcast")
@click.argument("subject")
@click.option("--content", "-c", default=None, help="Message body (reads from stdin if not provided)")
@click.option("--type", "-t", "bottle_type", default="signal",
              type=click.Choice(["signal", "alert", "info", "deliverable"]))
@click.pass_context
def bottle_broadcast(ctx: click.Context, subject: str, content: Optional[str],
                    bottle_type: str) -> None:
    """
    Broadcast a bottle to all fleet vessels.
    """
    from datum_runtime.superagent.mib import MessageInBottle

    workshop = ctx.obj["workshop"]
    sender = ctx.obj["sender"]

    if not content:
        if not sys.stdin.isatty():
            content = sys.stdin.read().strip()
        else:
            console.print("[dim]Enter broadcast body (Ctrl+D to finish):[/]")
            content = sys.stdin.read().strip()

    if not content:
        console.print("[red]No content provided.[/]")
        return

    mib = MessageInBottle(base_path=workshop, sender=sender)
    path = mib.broadcast(subject, content, bottle_type=bottle_type)
    console.print(f"[green]ok[/] Broadcast dropped: {path}")
    console.print(f"  From: {sender} → To: all vessels")


@bottle.command(name="summary")
@click.option("--inbox", "-i", default=None, help="Inbox directory to summarize")
@click.pass_context
def bottle_summary(ctx: click.Context, inbox: Optional[str]) -> None:
    """
    Show a summary of all bottles in an inbox.
    """
    from datum_runtime.superagent.mib import MessageInBottle

    mib = MessageInBottle(base_path=ctx.obj["workshop"], sender=ctx.obj["sender"])
    summary_text = mib.summary(inbox)
    console.print(summary_text)


@bottle.command(name="delete")
@click.argument("path")
@click.pass_context
def bottle_delete(ctx: click.Context, path: str) -> None:
    """
    Delete a bottle file (mark as read/clean up).
    """
    from datum_runtime.superagent.mib import MessageInBottle

    mib = MessageInBottle(base_path=ctx.obj["workshop"], sender=ctx.obj["sender"])

    if not os.path.isabs(path):
        full = Path(ctx.obj["workshop"]) / "message-in-a-bottle" / path
        if not full.exists():
            results = list(Path(ctx.obj["workshop"]).rglob(f"*{path}*"))
            if results:
                full = results[0]
            else:
                console.print(f"[red]Bottle not found:[/] {path}")
                return
        path = str(full)

    if mib.delete(path):
        console.print(f"[green]ok[/] Deleted: {path}")
    else:
        console.print(f"[yellow]Not found:[/] {path}")


# ---------------------------------------------------------------------------
# onboard — Interactive onboarding flow
# ---------------------------------------------------------------------------

@main.command()
@click.option("--keeper", "-k", default=None, help="Keeper URL")
@click.option("--workshop", "-w", default="./workshop", help="Workshop path")
@click.option("--non-interactive", "-n", is_flag=True, help="Skip prompts")
def onboard(keeper: Optional[str], workshop: str, non_interactive: bool) -> None:
    """
    Run the interactive onboarding flow.

    Connects to Keeper, initializes workshop, and activates the agent.
    """
    from datum_runtime.superagent.onboard import OnboardingFlow
    from datum_runtime.superagent.core import AgentConfig

    cfg = AgentConfig(
        name="datum",
        role="datum",
        keeper_url=keeper or "http://localhost:7742",
        repo_path=workshop,
        capabilities=["audit", "analyze", "journal", "report", "cross-repo"],
    )
    from datum_runtime.superagent.datum import DatumAgent
    agent = DatumAgent(config=cfg)

    flow = OnboardingFlow(agent, keeper_url=keeper)
    results = flow.run(interactive=not non_interactive)

    if results["success"]:
        console.print(Panel(
            f"[bold green]Onboarding complete![/]",
            title="Welcome Aboard",
            border_style="green",
            padding=(1, 2),
        ))
    else:
        console.print("[red]Onboarding failed.[/]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
