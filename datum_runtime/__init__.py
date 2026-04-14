"""
datum_runtime — Self-bootstrapping Datum agent runtime.

Clone this repo, run ``./boot.sh`` or build with Docker, and Datum is
up and running with all its knowledge, tools, context, and prompts intact.

This package bundles the SuperInstance Agent Framework with Datum's
specific operational knowledge, tools, context, and prompts.
"""

__version__ = "0.2.0"
__author__ = "SuperInstance Fleet"
__agent__ = "Datum"
__role__ = "Fleet Quartermaster"
__fleet__ = "SuperInstance"

from datum_runtime.superagent.core import (
    Agent,
    AgentConfig,
    AgentState,
    AgentMessage,
    MessageBus,
    SecretProxy,
    SuperagentError,
)
from datum_runtime.superagent.datum import DatumAgent
from datum_runtime.superagent.keeper import KeeperAgent
from datum_runtime.superagent.git_agent import GitAgent
from datum_runtime.superagent.oracle import OracleAgent

__all__ = [
    "__version__",
    "Agent",
    "AgentConfig",
    "AgentState",
    "AgentMessage",
    "MessageBus",
    "SecretProxy",
    "SuperagentError",
    "DatumAgent",
    "KeeperAgent",
    "GitAgent",
    "OracleAgent",
]
