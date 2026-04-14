"""
superagent.tui — Minimal terminal UI components for agents.

Uses the `rich` library when available for pretty output, falls back to
plain text when not. Provides:
    - Colored status messages
    - Simple progress bar
    - Panel/border displays
    - Interactive prompts (input, confirm)
    - Table display for structured data
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich import box

    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


class TUI:
    """Terminal UI wrapper. Uses rich when available, plain text otherwise."""

    def print(self, text: str = "") -> None:
        if HAS_RICH:
            console.print(text)
        else:
            print(text)

    def print_info(self, text: str) -> None:
        if HAS_RICH:
            console.print(f"[bold blue]ℹ[/] {text}")
        else:
            print(f"[INFO] {text}")

    def print_success(self, text: str) -> None:
        if HAS_RICH:
            console.print(f"[bold green]✓[/] {text}")
        else:
            print(f"[OK] {text}")

    def print_warning(self, text: str) -> None:
        if HAS_RICH:
            console.print(f"[bold yellow]⚠[/] {text}")
        else:
            print(f"[WARN] {text}")

    def print_error(self, text: str) -> None:
        if HAS_RICH:
            console.print(f"[bold red]✗[/] {text}")
        else:
            print(f"[ERROR] {text}")

    def print_panel(self, title: str, content: str, style: str = "blue") -> None:
        if HAS_RICH:
            console.print(Panel(content, title=title, border_style=style,
                                padding=(1, 2)))
        else:
            width = max(len(line) for line in content.split("\n")) + 4
            print(f"┌─ {title} {'─' * (width - len(title) - 4)}┐")
            for line in content.split("\n"):
                print(f"│ {line:<{width - 2}} │")
            print(f"└{'─' * width}┘")

    def prompt(self, label: str, default: str = "") -> str:
        if HAS_RICH:
            return str(Prompt.ask(f"  {label}", default=default))
        else:
            default_str = f" [{default}]" if default else ""
            return input(f"  {label}{default_str}: ").strip() or default

    def confirm(self, question: str, default: bool = True) -> bool:
        if HAS_RICH:
            return Confirm.ask(f"  {question}", default=default)
        else:
            hint = "Y/n" if default else "y/N"
            answer = input(f"  {question} [{hint}]: ").strip().lower()
            if not answer:
                return default
            return answer.startswith("y")

    def table(self, title: str, columns: List[str], rows: List[List[str]]) -> None:
        """Display a table."""
        if HAS_RICH:
            t = Table(title=title, box=box.ROUNDED)
            for col in columns:
                t.add_column(col)
            for row in rows:
                t.add_row(*[str(c) for c in row])
            console.print(t)
        else:
            # Plain text table
            col_widths = [len(c) for c in columns]
            for row in rows:
                for i, cell in enumerate(row):
                    col_widths[i] = max(col_widths[i], len(str(cell)))

            header = " | ".join(c.ljust(col_widths[i]) for i, c in enumerate(columns))
            sep = "-+-".join("-" * w for w in col_widths)
            print(f"  {title}")
            print(f"  {header}")
            print(f"  {sep}")
            for row in rows:
                line = " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(row))
                print(f"  {line}")

    def status_line(self, agent_name: str, state: str, role: str,
                    extra: str = "") -> None:
        """Print a one-line status."""
        if HAS_RICH:
            text = f"[bold]{agent_name}[/] — {state} ({role})"
            if extra:
                text += f" | {extra}"
            console.print(text)
        else:
            extra_str = f" | {extra}" if extra else ""
            print(f"  {agent_name} — {state} ({role}){extra_str}")


class ProgressDisplay:
    """Simple progress indicator."""

    def __init__(self, tui: Optional[TUI] = None):
        self._tui = tui or TUI()
        self._progress: Optional[Progress] = None

    def start(self, description: str) -> None:
        if HAS_RICH:
            self._progress = Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                console=console,
            )
            self._progress.start()
            self._task = self._progress.add_task(description, total=None)
        else:
            print(f"  ... {description}")

    def update(self, description: str) -> None:
        if HAS_RICH and self._progress:
            self._progress.update(self._task, description=description)

    def stop(self) -> None:
        if HAS_RICH and self._progress:
            self._progress.stop()


def show_banner(tui: Optional[TUI] = None, version: str = "0.1.0") -> None:
    """Display the framework banner."""
    tui = tui or TUI()
    tui.print_panel(
        "SuperInstance Agent Framework",
        f"Version {version}\nStandalone CLI Agents for Distributed Work",
        style="cyan",
    )
