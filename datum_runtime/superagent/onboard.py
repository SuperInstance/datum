"""
superagent.onboard — Onboarding flow for new agents.

Connects an agent to the Keeper, registers it, initializes a workshop,
and activates it on the fleet. Uses the TUI for interactive prompts
or can run non-interactively from config.

Flow:
    1. Welcome banner
    2. Agent configuration (name, role, capabilities)
    3. Keeper handshake (register with secret proxy)
    4. Workshop initialization from template
    5. Bootcamp assignment
    6. Activation
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from datum_runtime.superagent.core import (
    Agent,
    AgentConfig,
    AgentState,
)


class OnboardingFlow:
    """
    Interactive onboarding for new agents.

    Usage:
        agent = MyAgent()
        flow = OnboardingFlow(agent)
        result = flow.run(interactive=True)
    """

    def __init__(self, agent: Agent, keeper_url: Optional[str] = None):
        self.agent = agent
        self._override_keeper = keeper_url
        self._logger = logging.getLogger("onboard")

    def run(self, interactive: bool = True) -> Dict[str, Any]:
        """
        Execute the full onboarding flow.

        Returns dict with 'success', 'steps', and per-step results.
        """
        results: Dict[str, Any] = {"steps": [], "success": False}
        self._print_banner()

        # Step 1: Configure
        self._print_step("Step 1: Agent Configuration")
        if interactive:
            self._configure_interactive()
        else:
            self._configure_from_defaults()
        results["steps"].append({"step": "configure", "status": "ok",
                                 "name": self.agent.name})

        # Step 2: Connect to Keeper
        self._print_step("Step 2: Keeper Connection")
        keeper_ok = self._connect_keeper()
        results["steps"].append({"step": "keeper", "status": "ok" if keeper_ok else "standalone"})
        if keeper_ok:
            print("  ✓ Connected to Keeper")
        else:
            print("  ⚠ Keeper not reachable — running in standalone mode")

        # Step 3: Initialize workshop
        self._print_step("Step 3: Workshop Initialization")
        ws_ok = self._init_workshop()
        results["steps"].append({"step": "workshop", "status": "ok" if ws_ok else "skipped"})
        if ws_ok:
            print(f"  ✓ Workshop at {self.agent.config.repo_path}")
        else:
            print("  ⚠ Workshop init skipped")

        # Step 4: Save config
        self._print_step("Step 4: Saving Configuration")
        config_path = os.path.join(self.agent.config.repo_path, ".superagent", "agent.toml")
        self.agent.config.save(config_path)
        print(f"  ✓ Config saved to {config_path}")
        results["steps"].append({"step": "config_save", "status": "ok"})

        # Step 5: Activate
        self._print_step("Step 5: Activation")
        self.agent.activate()
        results["steps"].append({"step": "activate", "status": "ok"})
        print(f"  ✓ Agent '{self.agent.name}' is now ACTIVE")

        # Summary
        self._print_summary(results)
        results["success"] = True
        return results

    # -- Steps -----------------------------------------------------------------

    def _configure_interactive(self) -> None:
        """Collect configuration from interactive prompts."""
        name = input(f"  Agent name [{self.agent.name}]: ").strip() or self.agent.name
        role = input(f"  Role [{self.agent.config.role}]: ").strip() or self.agent.config.role
        caps = input(f"  Capabilities [{','.join(self.agent.config.capabilities) or 'general'}]: ").strip()
        keeper = input(f"  Keeper URL [{self.agent.config.keeper_url}]: ").strip() or self.agent.config.keeper_url
        workshop = input(f"  Workshop path [{self.agent.config.repo_path}]: ").strip() or self.agent.config.repo_path

        self.agent.name = name
        self.agent.config.name = name
        self.agent.config.role = role
        self.agent.config.capabilities = [c.strip() for c in caps.split(",") if c.strip()]
        self.agent.config.keeper_url = keeper
        self.agent.config.repo_path = workshop

    def _configure_from_defaults(self) -> None:
        """Use config values as-is, filling defaults where empty."""
        if not self.agent.config.name:
            self.agent.config.name = f"{self.agent.role}-{os.urandom(3).hex()}"
        self.agent.name = self.agent.config.name

    def _connect_keeper(self) -> bool:
        """Connect to the Keeper and register."""
        url = self._override_keeper or self.agent.config.keeper_url
        return self.agent.onboard(keeper_url=url)

    def _init_workshop(self) -> bool:
        """Initialize the workshop from the template."""
        from datum_runtime.superagent.git_agent import GitAgent

        ws_path = Path(self.agent.config.repo_path)
        if ws_path.exists() and (ws_path / "TASKBOARD.md").exists():
            return False  # Already initialized

        ga = GitAgent(config=self.agent.config, owner=self.agent.name)
        ga.init_workshop(name=self.agent.name, owner=self.agent.name)
        return True

    # -- Display ---------------------------------------------------------------

    def _print_banner(self) -> None:
        print()
        print("  ╔═══════════════════════════════════════════════════╗")
        print("  ║     SuperInstance Agent Framework — Onboarding    ║")
        print("  ║                    v0.1.0                        ║")
        print("  ╚═══════════════════════════════════════════════════╝")
        print()

    def _print_step(self, text: str) -> None:
        print()
        print(f"  ▸ {text}")
        print()

    def _print_summary(self, results: Dict[str, Any]) -> None:
        print()
        print("  ── Onboarding Summary ──")
        print(f"  Agent:       {self.agent.name}")
        print(f"  Role:        {self.agent.config.role}")
        print(f"  Capabilities: {', '.join(self.agent.config.capabilities)}")
        print(f"  Keeper:      {self.agent.config.keeper_url}")
        print(f"  Workshop:    {self.agent.config.repo_path}")
        print(f"  State:       {self.agent.state.value}")
        print()
