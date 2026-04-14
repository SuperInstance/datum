"""
SuperInstance Agent Framework (bundled within datum-runtime)
=============================================================

A system of standalone CLI agents for the SuperInstance distributed ecosystem.

Core concepts:
    - Keeper: Secret proxy and boundary enforcer. Holds all keys.
    - GitAgent: Repo operator / workshop manager. Leaves a story in commits.
    - Oracle: Fleet coordinator. Dispatches tasks, manages priority.
    - Datum: Research and analysis specialist.

Each agent is a self-contained Python CLI with minimal TUI for iterative work.
Onboard with ``--onboard`` to connect to a Keeper and join the fleet.
"""

__version__ = "0.2.0"
__author__ = "SuperInstance Fleet"

from datum_runtime.superagent.core import (
    Agent,
    AgentConfig,
    AgentState,
    AgentMessage,
    MessageBus,
    SecretProxy,
    SuperagentError,
)

__all__ = [
    "Agent",
    "AgentConfig",
    "AgentState",
    "AgentMessage",
    "MessageBus",
    "SecretProxy",
    "SuperagentError",
]
