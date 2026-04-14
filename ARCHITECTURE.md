# ARCHITECTURE.md — Datum Runtime System Architecture

> Complete technical reference for the datum runtime, agent framework, and deployment configurations.

---

## 1. System Overview

The datum runtime is a self-bootstrapping Python agent framework that serves as the operational backbone of the Fleet Quartermaster. It transforms the datum succession repository from a static documentation archive into a live, executable agent system capable of autonomous fleet operations, inter-agent communication, and secure secret management.

The runtime implements a layered agent architecture where security boundaries are enforced at the architecture level, Git-native state persistence ensures full auditability, and the Message-in-a-Bottle protocol provides asynchronous inter-agent communication compatible with the fleet's Git-native paradigm.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DATUM RUNTIME v0.2.0                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   CLI Layer   │───▶│ Agent Layer  │───▶│  Transport   │          │
│  │  (cli.py)    │    │              │    │   Layer      │          │
│  │              │    │  ┌─────────┐ │    │              │          │
│  │  ┌────────┐  │    │  │ Keeper  │ │    │  ┌─────────┐ │          │
│  │  │boot    │  │    │  │ Agent   │ │    │  │MessageBus│ │          │
│  │  │audit   │  │    │  │(secrets)│ │    │  │(TCP/loc)│ │          │
│  │  │analyze │  │    │  └────┬────┘ │    │  └────┬────┘ │          │
│  │  │journal │  │    │       │       │    │       │       │          │
│  │  │report  │  │    │  ┌────▼────┐ │    │  ┌────▼────┐ │          │
│  │  │status  │  │    │  │GitAgent │ │    │  │   MiB   │ │          │
│  │  │resume  │  │    │  │(repos)  │ │    │  │Protocol │ │          │
│  │  │tools   │  │    │  └────┬────┘ │    │  └─────────┘ │          │
│  │  │fleet   │  │    │       │       │    │              │          │
│  │  └────────┘  │    │  ┌────▼────┐ │    │  ┌─────────┐ │          │
│  └──────────────┘    │  │ Datum   │ │    │  │GitHub   │ │          │
│                      │  │ Agent   │ │    │  │API      │ │          │
│                      │  │(ops)    │ │    │  │(fleet)  │ │          │
│                      │  └─────────┘ │    │  └─────────┘ │          │
│                      └──────────────┘    └──────────────┘          │
├─────────────────────────────────────────────────────────────────────┤
│  Infrastructure Layer                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │ SecretProxy│  │ AgentConfig│  │  Workshop  │  │   TUI      │   │
│  │ (env/vault)│  │ (persist)  │  │  Template  │  │  (rich)    │   │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. CLI Structure

The main entry point is `datum_runtime/cli.py`, which provides a comprehensive command-line interface for all Quartermaster operations. CLI entry points in `bin/` provide convenient shell access.

### Command Hierarchy

```
datum-rt
├── boot              # Initialize full agent stack
│   ├── --keeper URL  # Keeper URL to connect to
│   ├── --workshop    # Workshop path
│   └── --non-interactive  # Skip prompts
├── audit             # Run workshop, fleet, or conformance audits
│   ├── --type TYPE   # workshop | fleet | conformance
│   ├── --path PATH   # Path to audit
│   └── --workshop    # Workshop path
├── analyze           # Profile a workshop and show stats
│   ├── --path PATH   # Workshop path to analyze
│   └── --workshop    # Workshop path
├── journal           # Add entries to the work journal
│   ├── CATEGORY      # (arg) Entry category
│   ├── CONTENT       # (arg) Entry content
│   ├── --agent NAME  # Agent name
│   └── --tag TAG     # Tags (repeatable)
├── report            # Generate markdown reports
│   ├── TYPE          # (arg) workshop | fleet | conformance
│   └── --workshop    # Workshop path
├── status            # Runtime health check
│   └── --workshop    # Workshop path
├── resume            # Resume from previous session
│   └── --workshop    # Workshop path
├── tools             # List and run bundled tools
│   ├── list          # List all tools
│   └── run NAME      # Run a tool (audit-scanner, fleet-scanner, etc.)
├── fleet             # Fleet hygiene operations (GitHub API)
│   ├── scan --org ORG          # Scan repos for health status
│   ├── tag --org ORG           # Add topics/tags to repos
│   ├── license --org ORG       # Add LICENSE files
│   └── report --org ORG        # Generate fleet report
├── bottle            # Message-in-a-Bottle operations
│   ├── drop AGENT SUBJECT      # Drop a bottle for an agent
│   ├── check                  # Check inbox for new bottles
│   ├── read PATH              # Read a bottle file
│   ├── broadcast SUBJECT      # Broadcast to all vessels
│   ├── summary                # Summarize inbox bottles
│   └── delete PATH            # Delete a bottle
└── onboard            # Interactive onboarding flow
    ├── --keeper URL  # Keeper URL
    └── --workshop    # Workshop path
```

### Entry Points

The `bin/` directory provides four CLI entry points:

| Entry Point | Purpose | Invokes |
|-------------|---------|---------|
| `bin/datum` | Main datum CLI | `datum-rt` command suite |
| `bin/keeper` | Keeper agent standalone | `KeeperAgent` directly |
| `bin/git-agent` | Git agent standalone | `GitAgent` directly |
| `bin/oracle` | Oracle1 adapter | Oracle1 integration adapter |

---

## 3. Agent Hierarchy

The runtime implements a strict agent hierarchy where security boundaries are enforced at the architecture level. Each agent has a specific role and communicates through the MessageBus.

### Agent Dependency Graph

```
                    ┌──────────────┐
                    │ OnboardingFlow│
                    │ (onboard.py) │
                    └──────┬───────┘
                           │ initializes
                    ┌──────▼───────┐
                    │   CLI Layer   │
                    │  (cli.py)    │
                    └──────┬───────┘
                           │ dispatches
              ┌────────────▼────────────┐
              │                         │
       ┌──────▼──────┐         ┌───────▼──────┐
       │ KeeperAgent │────────▶│   GitAgent   │
       │ (keeper.py) │ manages │ (git_agent)  │
       │             │ secrets │              │
       └──────┬──────┘         └───────┬──────┘
              │                         │
              │    ┌──────────────┐     │
              └───▶│ SecretProxy  │◀────┘
                   │  (core.py)  │
                   └──────────────┘
                           │
              ┌────────────▼────────────┐
              │                         │
       ┌──────▼──────┐         ┌───────▼──────┐
       │ DatumAgent  │────────▶│ fleet_tools  │
       │ (datum.py)  │ uses    │(fleet_tools) │
       │             │         │              │
       └──────┬──────┘         └──────────────┘
              │
       ┌──────▼──────┐
       │  Workshop   │
       │ (workshop)  │
       └─────────────┘
```

### KeeperAgent (`superagent/keeper.py`)

**Role:** Security layer — manages secrets, enforces operational boundaries, provides HTTP API.

**Responsibilities:**
- AES-256-GCM encryption for secret storage and retrieval
- Boundary enforcement — prevents agents from accessing unauthorized resources
- HTTP API for external integrations (e.g., tender vessels, fleet monitoring)
- Capability management based on CAPABILITY.toml declarations
- Agent lifecycle management (start, stop, restart)

**Key Methods:**
- `store_secret(key, value)` — Encrypt and store a secret
- `retrieve_secret(key)` — Decrypt and return a secret
- `check_boundary(agent_id, resource)` — Verify access authorization
- `health_check()` — Verify runtime health status
- `http_serve(port)` — Start HTTP API server

### GitAgent (`superagent/git_agent.py`)

**Role:** Repository layer — manages Git operations, workshop templates, and commit history.

**Responsibilities:**
- Workshop template management (create, clone, list)
- Commit history tracking and analysis
- Repository cloning, branching, and synchronization
- File-level operations (read, write, delete) with Git tracking
- Historian interface for audit trails

**Key Methods:**
- `create_workshop(template)` — Initialize workshop from template
- `commit(message, files)` — Stage and commit with I2I message
- `history(limit)` — Retrieve recent commit history
- `diff(ref1, ref2)` — Compare two references
- `sync(remote)` — Pull/push with conflict detection

### DatumAgent (`superagent/datum.py`)

**Role:** Operations layer — performs fleet auditing, cross-repo analysis, journal management, and workshop profiling.

**Responsibilities:**
- Fleet auditing (scan repos, classify health, generate reports)
- Cross-repo workshop profiling (language distribution, tool inventory)
- Journal management (append, search, export)
- Conformance testing coordination
- MiB bottle creation and delivery

**Key Methods:**
- `audit_fleet(org, severity)` — Scan organization for hygiene issues
- `analyze_workshops(path)` — Profile workshop characteristics
- `journal_add(entry)` — Append to operational journal
- `deliver_mib(target, content)` — Create and deliver MiB
- `profile_repos(repos)` — Cross-repo analysis

### OnboardingFlow (`superagent/onboard.py`)

**Role:** Interactive setup — guides new Quartermasters through initial configuration.

**Responsibilities:**
- Vessel repository setup and configuration
- GitHub PAT configuration and validation
- Agent identity configuration
- First-contact fleet protocols (MiB to Oracle1, initial TASKBOARD)
- Capability declaration setup

---

## 4. MessageBus Topology

The MessageBus is the central communication backbone, supporting both local in-process messaging and TCP-based cross-machine communication.

### MessageBus Architecture

```
┌──────────────────────────────────────────────────┐
│                  MessageBus (bus.py)              │
├──────────────────────────────────────────────────┤
│                                                   │
│  ┌───────────┐     ┌───────────┐     ┌────────┐ │
│  │  Local     │     │   TCP     │     │  MiB   │ │
│  │  Channel   │     │  Channel  │     │Channel │ │
│  │            │     │           │     │        │ │
│  │ in-process│     │ cross-    │     │ async  │ │
│  │ pub/sub   │     │ machine   │     │ Git-   │ │
│  │           │     │ pub/sub   │     │ native │ │
│  └─────┬─────┘     └─────┬─────┘     └───┬────┘ │
│        │                 │               │       │
│  ┌─────▼─────────────────▼───────────────▼────┐ │
│  │            Message Router                   │ │
│  │  (topic-based routing, priority queuing)    │ │
│  └────────────────────────────────────────────┘ │
│                                                   │
│  ┌────────────────────────────────────────────┐  │
│  │           Message Persistence               │  │
│  │  (optional: file-based, database-backed)    │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### Message Types

| Type | Channel | Use Case | Delivery |
|------|---------|----------|----------|
| Command | Local | CLI → Agent dispatch | Synchronous |
| Event | Local | Agent state changes | Asynchronous |
| MiB | MiB | Inter-agent async messages | Git-based, batch |
| Status | TCP | Cross-machine health checks | Request/response |
| Fleet | TCP | Fleet-wide broadcasts | Pub/sub |
| Audit | Local+TCP | Audit result distribution | Fan-out |

### TCP Configuration

```python
# MessageBus TCP configuration
MESSAGE_BUS_CONFIG = {
    "host": "0.0.0.0",        # Bind address
    "port": 7778,              # Datum's bus port
    "max_connections": 16,     # Maximum concurrent connections
    "heartbeat_interval": 30,  # Seconds between heartbeats
    "message_timeout": 60,     # Seconds before message expiry
    "retry_limit": 3,          # Retries for failed deliveries
}
```

---

## 5. Module Dependency Graph

```
datum_runtime/
│
├── cli.py ─────────────────────────────────────────┐
│   │                                                │
│   ├── superagent/core.py ─────────────────────────┤
│   │   ├── Agent (base class)                      │
│   │   ├── MessageBus (local + TCP)                │
│   │   ├── SecretProxy (env/vault)                 │
│   │   └── AgentConfig (TOML persistence)          │
│   │                                                │
│   ├── superagent/keeper.py ◄── core.py            │
│   │   └── KeeperAgent (AES-256-GCM, boundaries)   │
│   │                                                │
│   ├── superagent/git_agent.py ◄── core.py         │
│   │   └── GitAgent (workshop, commits, historian) │
│   │                                                │
│   ├── superagent/datum.py ◄── core.py             │
│   │   ├── DatumAgent (audit, analysis, journal)   │
│   │   └── fleet_tools.py (GitHub API)             │
│   │                                                │
│   ├── superagent/onboard.py ◄── core, keeper      │
│   │   └── OnboardingFlow (interactive setup)      │
│   │                                                │
│   ├── superagent/mib.py ◄── core.py               │
│   │   └── MiB protocol (local + cross-machine)    │
│   │                                                │
│   ├── superagent/bus.py ◄── core.py               │
│   │   └── TCP MessageBus (cross-machine)          │
│   │                                                │
│   ├── superagent/tui.py                           │
│   │   └── Rich terminal UI components             │
│   │                                                │
│   ├── superagent/workshop.py ◄── core.py          │
│   │   └── Workshop template, tool registry        │
│   │                                                │
│   └── superagent/oracle.py ◄── core, bus          │
│       └── Oracle1 integration adapter             │
│
├── fleet_tools.py (GitHub API: scan, tag, license)
│
├── boot.py (Runtime bootstrap sequence)
│
├── tools/ (Runtime-embedded fleet tools)
│   ├── audit_scanner.py
│   ├── batch_topics.py
│   ├── batch_license.py
│   └── mib_bottle.py
│
├── prompts/ (Runtime-embedded prompt templates)
│   ├── self-instantiation.md
│   ├── fleet-audit.md
│   └── gap-analysis.md
│
└── context/ (Runtime-embedded context files)
    ├── fleet-dynamics.md
    ├── known-gaps.md
    └── repo-relationships.md
```

---

## 6. Configuration Reference

### CAPABILITY.toml Format

The `CAPABILITY.toml` file declares Datum's capabilities for fleet discovery and capability matching. Other agents read this file to understand what Datum can do and how to interact with it.

```toml
# CAPABILITY.toml — Datum Fleet Capability Declaration
#
# Sections:
#   [agent]        — Identity and role
#   [capabilities] — Skill inventory with confidence scores
#   [domains]      — Expertise domains with proficiency levels
#   [communication]— How to send/receive messages
#   [metadata]     — Activity statistics

[agent]
name = "datum"              # Agent identifier (lowercase)
role = "quartermaster"      # Fleet role
description = "Fleet Quartermaster: audit, analysis, hygiene, and journal management"
version = "0.2.0"           # Runtime version

[capabilities]
# Each capability has a confidence score (0.0-1.0) and description
audit = { confidence = 0.95, description = "Workshop and fleet structural audits" }
analyze = { confidence = 0.90, description = "Cross-repo workshop profiling" }
journal = { confidence = 0.95, description = "Chronological work log management" }
report = { confidence = 0.85, description = "Markdown report generation" }
"fleet-scan" = { confidence = 0.90, description = "GitHub org scanning for health" }
"fleet-tag" = { confidence = 0.85, description = "Bulk topic/tag management" }
"fleet-license" = { confidence = 0.85, description = "LICENSE file deployment" }
"cross-repo" = { confidence = 0.80, description = "Multi-workshop comparison" }
conformance = { confidence = 0.90, description = "Workshop structure validation" }
"formal-verification" = { confidence = 0.90, description = "Mathematical proofs of ISA properties" }
"isa-design" = { confidence = 0.95, description = "Instruction set architecture design" }

[domains]
# Each domain has a proficiency level and optional repo scope
fleet-hygiene = { level = "expert", repos = ["SuperInstance/*"] }
formal-verification = { level = "expert", repos = ["flux-spec", "flux-conformance"] }
isa-design = { level = "expert", repos = ["flux-spec", "ability-transfer"] }
git-operations = { level = "advanced" }
security = { level = "intermediate", notes = "Secret proxy, boundary enforcement" }

[communication]
incoming = ["message-in-a-bottle/for-datum/"]
outgoing = ["message-in-a-bottle/for-{agent}/"]
protocol = "MiB"  # Primary: MiB; Secondary: I2I (commit messages)

[metadata]
last_active = "2026-04-14"
session_count = 8
total_commits = 120
fleet_repos_audited = 100
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub PAT with SuperInstance org write access |
| `DATUM_HOME` | No | Runtime home directory (default: current directory) |
| `DATUM_BUS_HOST` | No | MessageBus bind address (default: 0.0.0.0) |
| `DATUM_BUS_PORT` | No | MessageBus port (default: 7778) |
| `DATUM_VAULT_PATH` | No | Secret vault file path (default: `.datum/vault.enc`) |
| `DATUM_LOG_LEVEL` | No | Logging level (default: INFO) |

### pyproject.toml

```toml
[project]
name = "datum-runtime"
version = "0.2.0"
description = "Fleet Quartermaster agent runtime"
requires-python = ">=3.10"

[project.scripts]
datum-rt = "datum_runtime.cli:main"
keeper = "datum_runtime.keeper_cli:main"
```

---

## 7. Deployment Guide

### Local Development

```bash
# Clone the datum repository
git clone https://github.com/SuperInstance/datum.git
cd datum

# Install in editable mode
pip install -e .

# Set required environment variables
export GITHUB_TOKEN="ghp_your_token_here"

# Boot the runtime
datum-rt boot

# Run a fleet audit
datum-rt audit --org SuperInstance --output audit-report.md

# Check runtime status
datum-rt status --verbose
```

### Docker Deployment

```dockerfile
# Dockerfile (included in repo)
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -e .

ENV DATUM_HOME=/app
ENV DATUM_LOG_LEVEL=INFO

ENTRYPOINT ["datum-rt"]
CMD ["boot"]
```

```yaml
# docker-compose.yml (included in repo)
version: '3.8'

services:
  datum:
    build: .
    ports:
      - "7778:7778"  # MessageBus TCP port
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - DATUM_BUS_PORT=7778
    volumes:
      - ./data:/app/data        # Persistent state
      - ./.datum:/app/.datum    # Secret vault
    restart: unless-stopped
```

```bash
# Build and run with Docker
docker-compose up -d

# Check logs
docker-compose logs -f datum

# Run a specific command
docker-compose exec datum datum-rt status
```

### Fleet Integration

For fleet-wide deployment, the datum runtime integrates through several mechanisms:

1. **CAPABILITY.toml**: Other agents discover Datum's capabilities by reading this file from the repository
2. **MiB Protocol**: Asynchronous communication via Git-based message bottles in vessel repos
3. **TCP MessageBus**: Synchronous cross-machine communication on port 7778
4. **I2I Commit Messages**: Fleet-facing operations are tagged with structured commit messages

**Fleet integration checklist:**
- [ ] `CAPABILITY.toml` is up to date with current capabilities
- [ ] `GITHUB_TOKEN` has write access to SuperInstance org
- [ ] MessageBus port (7778) is accessible to other fleet agents
- [ ] Onboarding flow has been completed at least once
- [ ] MiB delivery to Oracle1 has been confirmed

### Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/test_core.py -v

# Run with coverage
python -m pytest tests/ --cov=datum_runtime --cov-report=term-missing
```

Current test coverage: **39 tests, all passing** across 5 test modules:
- `test_core.py` — Core module tests (Agent, MessageBus, SecretProxy)
- `test_keeper.py` — KeeperAgent tests (encryption, boundaries)
- `test_git_agent.py` — GitAgent tests (workshop, commits)
- `test_mib.py` — MiB protocol tests
- `test_tools.py` — Fleet tools tests

---

## 8. Security Model

### Secret Management

Secrets are managed through the SecretProxy, which provides a unified interface for secret storage and retrieval:

```
Secret Storage Locations (priority order):
1. Environment variables (highest priority)
2. Encrypted vault file (.datum/vault.enc, AES-256-GCM)
3. Configuration files (lowest priority, for non-sensitive config)
```

### Boundary Enforcement

The KeeperAgent enforces operational boundaries that prevent agents from accessing unauthorized resources:

- **Filesystem boundaries:** Agents can only access files within their designated workshop directories
- **Network boundaries:** Agents can only connect to approved endpoints (GitHub API, fleet MessageBus)
- **Capability boundaries:** Agents can only invoke capabilities declared in CAPABILITY.toml
- **Secret boundaries:** Agents can only access secrets explicitly granted to them by the KeeperAgent

---

*This document describes the architecture as of datum runtime v0.2.0. Update it when the runtime evolves.*
