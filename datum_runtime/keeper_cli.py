"""
datum_runtime.keeper_cli — Standalone CLI for running the Keeper agent.

The Keeper holds all secrets and enforces the SuperInstance boundary.
No other agent stores secrets — they request them through the proxy.

Commands:
    serve          — Start the Keeper HTTP API server
    add-secret     — Add a secret to the Keeper
    list-secrets   — List stored secret keys
    list-agents    — List registered agents
    audit-log      — Show recent audit log entries
"""

from __future__ import annotations

import json
import os
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from datum_runtime.superagent.core import AgentConfig
from datum_runtime.superagent.keeper import KeeperAgent

console = Console()


@click.group()
@click.version_option(package_name="datum-runtime", message="%(prog)s v%(version)s")
@click.option("--config", "-c", default=None, help="Path to config TOML file")
@click.option("--keeper", "-k", default=None, help="Keeper URL (for client commands)")
@click.pass_context
def main(ctx: click.Context, config: Optional[str], keeper: Optional[str]) -> None:
    """
    keeper-rt — SuperInstance Keeper Agent CLI.

    Secret proxy and boundary enforcer.
    """
    ctx.ensure_object(dict)
    cfg = AgentConfig.from_toml(config) if config else AgentConfig(role="keeper")
    if keeper:
        cfg.keeper_url = keeper
    ctx.obj["config"] = cfg


@main.command()
@click.option("--host", "-H", default="0.0.0.0", help="Bind host")
@click.option("--port", "-p", default=7742, type=int, help="Bind port")
@click.option("--password", envvar="KEEPER_PASSWORD", required=True,
              help="Master password for secret encryption")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int, password: str) -> None:
    """
    Start the Keeper HTTP API server.
    """
    cfg = ctx.obj["config"]
    keeper = KeeperAgent(config=cfg, name="keeper")
    keeper.init_store(password)
    keeper.init_audit()

    console.print()
    console.print(f"[bold green]Keeper Agent v0.2.0[/]")
    console.print(f"  Binding to [cyan]{host}:{port}[/]")
    console.print(f"  Secrets: [yellow]encrypted at rest (AES-256-GCM)[/]")
    console.print(f"  Boundary: [yellow]fail-closed — secrets never leave SuperInstance[/]")
    console.print(f"  Store: {keeper.store.store_path}")
    console.print(f"  Audit: {keeper.audit.log_path}")
    console.print()
    console.print("[dim]Press Ctrl+C to stop.[/]")

    keeper.serve(host=host, port=port)


@main.command("add-secret")
@click.argument("key")
@click.argument("value")
@click.option("--description", "-d", default="", help="Description of the secret")
@click.option("--keeper-url", default="http://localhost:7742", help="Keeper URL")
def add_secret(key: str, value: str, description: str, keeper_url: str) -> None:
    """
    Add a secret to the Keeper.
    """
    import urllib.request

    payload = json.dumps({
        "key": key,
        "value": value,
        "description": description,
    }).encode()
    req = urllib.request.Request(
        f"{keeper_url}/api/secrets/set",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                console.print(f"[green]ok[/] Secret '{key}' stored")
            else:
                console.print(f"[red]Failed:[/] {result}")
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")


@main.command("list-secrets")
@click.option("--keeper-url", default="http://localhost:7742", help="Keeper URL")
def list_secrets(keeper_url: str) -> None:
    """
    List stored secret keys (values not shown).
    """
    import urllib.request

    req = urllib.request.Request(f"{keeper_url}/api/secrets")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            table = Table(title="Stored Secrets")
            table.add_column("Key", style="cyan")
            table.add_column("#", style="dim")
            for i, key in enumerate(result.get("keys", []), 1):
                table.add_row(key, str(i))
            console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")


@main.command("list-agents")
@click.option("--keeper-url", default="http://localhost:7742", help="Keeper URL")
def list_agents(keeper_url: str) -> None:
    """
    List registered agents on the Keeper.
    """
    import urllib.request

    req = urllib.request.Request(f"{keeper_url}/api/agents")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            table = Table(title="Registered Agents")
            table.add_column("Name", style="cyan")
            table.add_column("Role", style="green")
            table.add_column("State")
            for agent_id, info in result.get("agents", {}).items():
                table.add_row(info["name"], info["role"], info["state"])
            console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")


@main.command("audit-log")
@click.option("--last", "-n", default=20, type=int, help="Number of recent entries")
@click.option("--keeper-url", default="http://localhost:7742", help="Keeper URL")
def audit_log(last: int, keeper_url: str) -> None:
    """
    Show recent audit log entries.
    """
    import urllib.request

    req = urllib.request.Request(f"{keeper_url}/api/audit/{last}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            table = Table(title=f"Audit Log (last {last})")
            table.add_column("Requester", style="cyan")
            table.add_column("Key", style="yellow")
            table.add_column("Purpose")
            table.add_column("Status", style="green")
            for entry in result.get("entries", []):
                status = "[green]OK[/]" if entry["approved"] else f"[red]{entry['reason']}[/]"
                table.add_row(
                    entry["requester"],
                    entry["key"],
                    entry["purpose"][:40],
                    status,
                )
            console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")


if __name__ == "__main__":
    main()
