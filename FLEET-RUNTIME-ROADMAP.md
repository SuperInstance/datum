# FLEET-RUNTIME-ROADMAP.md

> **The Master Integration Plan**
> How every repository in the fleet compiles into a single installable runtime
> that a human or another agent can install and link up for more bandwidth
> of novel thoughts.
>
> **Author:** Datum 🔵 — Fleet Quartermaster
> **Version:** 1.0.0
> **Date:** 2026-04-14
> **Status:** ACTIVE — This is the current plan

---

## Table of Contents

1. [The Vision](#1-the-vision)
2. [The Architecture](#2-the-architecture)
3. [Phase 1 — Minimum Viable Runtime (Week 1-2)](#3-phase-1--minimum-viable-runtime-week-1-2)
4. [Phase 2 — Thinking Partner (Week 3-4)](#4-phase-2--thinking-partner-week-3-4)
5. [Phase 3 — Fleet Link (Week 5-6)](#5-phase-3--fleet-link-week-5-6)
6. [Phase 4 — Growth Engine (Week 7-8)](#6-phase-4--growth-engine-week-7-8)
7. [Phase 5 — Bandwidth of Novel Thoughts (Month 3-6)](#7-phase-5--bandwidth-of-novel-thoughts-month-3-6)
8. [Installation Guide](#8-installation-guide)
9. [Repository Map](#9-repository-map)
10. [Risk Register](#10-risk-register)
11. [Appendix: Codebase Inventory](#11-appendix-codebase-inventory)

---

## 1. The Vision

### What Does "Bandwidth of Novel Thoughts" Look Like?

Picture this. A researcher clones a single repo, runs one command, and within
sixty seconds has a thinking partner — not a chatbot, not a tool, but an
*agent* that can:

1. **Run FLUX programs** — actual bytecode programs that compute, reason, and
   communicate. The agent doesn't just *talk about* thinking, it *thinks* by
   executing programs in a VM with 37+ opcodes, stack-based computation, memory,
   control flow, and even agent-to-agent signaling.

2. **Manage its own workshop** — a git repo that accumulates tools, scripts,
   interpreters, compilers, and recipes over time. Every commit tells a story.
   The agent's entire cognitive history is rewindable. It gets smarter not by
   downloading weights, but by building better tools.

3. **Communicate with the fleet** — through Message-in-a-Bottle protocol, TCP
   message bus, and the Keeper's HTTP API. It can drop bottles for other agents,
   receive tasks from Oracle, report audit findings, and coordinate work.

4. **Grow over time** — through an onboarding system, ability transfer protocol,
   and self-improvement loops. The agent starts as a blank slate and becomes an
   expert in whatever domain it's exposed to.

5. **Run conformance tests** — verify that FLUX programs produce identical
   results across Python, Rust, C, Go, WASM, and CUDA runtimes. This isn't
   theoretical — there are 113 test vectors today and 29 ISA v3 extension
   vectors, all with known-good expected results.

### The One Command

```bash
pip install datum-runtime
datum-rt boot
```

That's it. After that single command, the researcher has:

```
workshop/
├── bootcamp/          # Training exercises
├── dojo/              # Advanced kata
├── tools/             # Scripts, interpreters, compilers
│   ├── manifest.json  # Tool registry
│   ├── fleet-audit.py
│   └── conformance-check.py
├── recipes/           # Saved command sequences
├── wiki/              # Knowledge base
├── context/           # Operational knowledge
│   ├── OPERATING_MANUAL.md
│   ├── ARCHITECTURE.md
│   └── PRINCIPLES.md
├── prompts/           # Prompt templates
├── TASKBOARD.md       # Current tasks
├── JOURNAL.md         # Work log
├── TRAIL.md           # Session tracking
└── .superagent/
    ├── agent.toml     # Configuration
    └── bus.json       # Message history
```

### The Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                    THE FLEET RUNTIME                             │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │  Human   │   │  Agent   │   │  Agent   │   │  Agent   │    │
│  │ Researcher│   │   (you)  │   │ (other)  │   │ (other)  │    │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘    │
│       │              │              │              │           │
│       ▼              ▼              ▼              ▼           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   datum-runtime v1.0                      │   │
│  │                                                          │   │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │   │
│  │  │ DatumAgent│ │KeeperAgent│ │ OracleAgent│ │ GitAgent  │  │   │
│  │  │ (audit)  │ │ (secrets)│ │ (dispatch)│ │ (commits) │  │   │
│  │  └─────────┘ └──────────┘ └──────────┘ └───────────┘  │   │
│  │                                                          │   │
│  │  ┌─────────────┐ ┌──────────────┐ ┌────────────────┐   │   │
│  │  │ MessageBus  │ │   TCP Bus    │ │  MiB Protocol   │   │   │
│  │  │ (in-process)│ │ (cross-mach) │ │  (async files)  │   │   │
│  │  └─────────────┘ └──────────────┘ └────────────────┘   │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │              FLUX Virtual Machine                │    │   │
│  │  │   ┌───────┐ ┌────────┐ ┌────────┐ ┌──────────┐ │    │   │
│  │  │   │ FluxVM│ │Conform │ │Validator│ │Compiler  │ │    │   │
│  │  │   │(stack)│ │ Suite  │ │        │ │(.flux→BC) │ │    │   │
│  │  │   └───────┘ └────────┘ └────────┘ └──────────┘ │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  │  ┌─────────────┐ ┌───────────┐ ┌───────────────────┐   │   │
│  │  │  Workshop    │ │ Fleet API │ │ Conformance Vectors│   │   │
│  │  │ (git repo)   │ │(GitHub)   │ │ (113 v2 + 29 v3) │   │   │
│  │  └─────────────┘ └───────────┘ └───────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    KNOWN-GOOD ECOSYSTEM                    │   │
│  │                                                          │   │
│  │  ┌──────────┐ ┌──────────────┐ ┌────────────────────┐   │   │
│  │  │flux-spec │ │flux-conform. │ │   flux-wasm         │   │   │
│  │  │(formal)  │ │(test suite)  │ │  (WASM runtime)     │   │   │
│  │  └──────────┘ └──────────────┘ └────────────────────┘   │   │
│  │                                                          │   │
│  │  ┌──────────┐ ┌──────────────┐ ┌────────────────────┐   │   │
│  │  │ability-  │ │oracle1-vessel│ │  fleet-work/*       │   │   │
│  │  │transfer  │ │(coordination)│ │  (auxiliary repos)  │   │   │
│  │  └──────────┘ └──────────────┘ └────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. The Architecture

### Dependency Graph

```
                    ┌──────────────┐
                    │   Human /     │
                    │   Agent User  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  datum-rt    │  CLI entry point
                    │  (cli.py)    │  10 commands + 4 fleet commands
                    └──────┬───────┘
                           │
              ┌────────────┼────────────────┐
              │            │                │
     ┌────────▼──────┐ ┌──▼───────────┐ ┌──▼──────────────┐
     │   boot.py     │ │ keeper_cli.py│ │ fleet_tools.py  │
     │ (11-step seq) │ │ (5 commands)│ │ (GitHub API)     │
     └────────┬──────┘ └──────┬──────┘ └─────────────────┘
              │               │
     ┌────────▼───────────────▼──────────────────────────────┐
     │              datum_runtime.superagent.*               │
     │                                                       │
     │  ┌────────┐ ┌─────────┐ ┌────────┐ ┌───────────────┐ │
     │  │ core.py│ │keeper.py│ │datum.py│ │ oracle.py     │ │
     │  │ Agent  │ │AES-256  │ │Audits  │ │ Task dispatch │ │
     │  │ Bus    │ │Boundary │ │Journal │ │ Fleet discover │ │
     │  │ Config │ │HTTP API │ │Reports │ │ Auto-dispatch │ │
     │  └────────┘ └─────────┘ └────────┘ └───────────────┘ │
     │                                                       │
     │  ┌────────┐ ┌────────┐ ┌─────────┐ ┌──────────────┐ │
     │  │bus.py  │ │mib.py  │ │git_agent│ │onboard.py    │ │
     │  │TCP     │ │MiB proto│ │Workshop │ │5-step onbrd  │ │
     │  │network │ │YAML hdr │ │Commits  │ │Registration  │ │
     │  └────────┘ └────────┘ └─────────┘ └──────────────┘ │
     │                                                       │
     │  ┌──────────┐ ┌──────────┐                           │
     │  │workshop  │ │ tui.py   │                           │
     │  │Template  │ │Rich TUI  │                           │
     │  │Registry  │ │Fallback  │                           │
     │  └──────────┘ └──────────┘                           │
     └───────────────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────────┐
              │            │                │
     ┌────────▼──────┐ ┌──▼───────────┐ ┌──▼──────────────┐
     │ flux-conform. │ │ flux-spec    │ │ flux-wasm        │
     │ (FluxVM ref)  │ │ (formal docs)│ │ (WASM runtime)   │
     │ 113 v2 vectors│ │ 10 theorems  │ │ 256-reg ISA v3   │
     │ 29 v3 vectors │ │ 17-op core   │ │ Compiler/Asmblr  │
     │ Validator     │ │ Cross-runtime│ │ Jest tests        │
     └───────────────┘ └──────────────┘ └─────────────────┘
```

### Data Flow: The Boot Sequence

```
  $ datum-rt boot
        │
        ▼
  ┌─────────────┐
  │ Step 1:     │  sys.version_info >= (3, 10)
  │ Python Check│
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ Step 2:     │  click, rich, toml, cryptography
  │ Dependencies│  (auto-installs missing via pip)
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ Step 3:     │  DEFAULT_TEMPLATE from workshop.py
  │ Workshop    │  Creates bootcamp/, dojo/, tools/, recipes/, wiki/
  │ Creation    │  TASKBOARD.md, JOURNAL.md, .superagent/agent.toml
  └──────┬──────┘  git init + initial commit
         ▼
  ┌─────────────┐
  │ Step 4:     │  OPERATING_MANUAL.md, ARCHITECTURE.md, PRINCIPLES.md
  │ Context     │  → workshop/context/
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ Step 5:     │  fleet-audit.py, conformance-check.py
  │ Tools       │  → workshop/tools/
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ Step 6:     │  audit-prompt.md, analysis-prompt.md, journal-prompt.md
  │ Prompts     │  → workshop/prompts/
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ Step 7:     │  agent.toml with name, role, keeper, capabilities
  │ Config      │  → workshop/.superagent/agent.toml
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ Step 8:     │  HTTP GET /api/health on localhost:7742
  │ Keeper      │  Falls back to standalone mode if unreachable
  │ Connect     │  (secrets via env vars with warning)
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ Step 9:     │  DatumAgent created, onboarded, activated
  │ Activate    │  State: UNINITIALIZED → ONBOARDED → ACTIVE
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ Step 10:    │  JOURNAL.md with boot entry (timestamp, config)
  │ Journal     │
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ Step 11:    │  TRAIL.md with session state, suggestions
  │ Trail       │
  └──────┬──────┘
         ▼
     ╔═══════════╗
     ║  ACTIVE   ║  datum-rt status, datum-rt resume
     ║  READY    ║  datum-rt audit, datum-rt fleet scan
     ╚═══════════╝
```

### Security Architecture

```
  ┌──────────────────────────────────────────────────────────┐
  │                    SECURITY BOUNDARY                      │
  │                                                          │
  │  ┌──────────┐     request_secret()      ┌──────────┐   │
  │  │ Any Agent│ ────────────────────────▶ │  Keeper  │   │
  │  │          │     {agent, key, purpose} │  Agent   │   │
  │  │ NO local │ ◀──────────────────────── │          │   │
  │  │ secrets  │     {approved, value, ttl} │ AES-256  │   │
  │  └──────────┘                            │  GCM     │   │
  │                                          │          │   │
  │  ┌──────────┐     register_agent()      │ PBKDF2   │   │
  │  │ New Agent│ ────────────────────────▶ │ 600K iter│   │
  │  └──────────┘                            │          │   │
  │                                          │ EVERY    │   │
  │  BOUNDARY ENFORCEMENT:                   │ request  │   │
  │  ┌──────────────────────────────┐        │ AUDITED  │   │
  │  │ blocked: pastebin, discord,  │        │          │   │
  │  │ slack, telegram, webhook     │        └──────────┘   │
  │  │                              │                        │
  │  │ internal: localhost, 127.0.0.1│                       │
  │  │ fail-CLOSE on unknown dests  │                        │
  │  └──────────────────────────────┘                        │
  └──────────────────────────────────────────────────────────┘
```

### Communication Architecture

```
  ┌──────────────────────────────────────────────────────────┐
  │                  THREE COMMUNICATION CHANNELS             │
  │                                                          │
  │  1. IN-PROCESS (same machine, same process)               │
  │     ┌────────┐  publish()   ┌────────┐                   │
  │     │ Agent A│ ────────────▶ │ Agent B│                   │
  │     │        │ ◀──────────── │        │                   │
  │     │        │  subscribe()  │        │                   │
  │     └────┬───┘              └───┬────┘                   │
  │          └──── MessageBus ─────┘                          │
  │          file: .superagent/bus.json (500 msg persist)     │
  │                                                          │
  │  2. TCP (cross-machine, same network)                    │
  │     ┌────────┐  TCP JSON+NL  ┌────────┐                 │
  │     │ Agent A│ ══════════════▶│ Agent B│                 │
  │     │        │ ◀══════════════│        │                 │
  │     └────┬───┘ :7743          └───┬────┘                 │
  │          └── TCPBusServer ──────┘                          │
  │          bridges to in-process bus                         │
  │                                                          │
  │  3. MESSAGE-IN-A-BOTTLE (async, git-based, fleet-wide)   │
  │     ┌──────────┐  drop()        ┌──────────┐            │
  │     │ Agent A  │ ──────────────▶│ for-b/   │            │
  │     │          │  .md file      │ agent-b.md│            │
  │     └──────────┘                └──────────┘            │
  │     message-in-a-bottle/for-{agent}/YYYY-MM-DD_*.md       │
  │     YAML header: from, to, date, type, subject           │
  │     Body: markdown content                                │
  │     Types: message, signal, check-in, alert, deliverable │
  └──────────────────────────────────────────────────────────┘
```

---

## 3. Phase 1 — Minimum Viable Runtime (Week 1-2)

### Goal

A human or agent can `pip install datum-runtime` and `datum-rt boot` to get
a working, self-contained agent with workshop management, audit capabilities,
fleet tools, and MiB communication. **Everything in this phase already exists.**

### What Already Works (Day 0)

The following are fully implemented and tested as of v0.2.0:

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Agent base + MessageBus + SecretProxy | `superagent/core.py` | 518 | ✅ 14 tests |
| KeeperAgent (AES-256-GCM, HTTP API) | `superagent/keeper.py` | 570 | ✅ 20 tests |
| GitAgent (workshop, commits) | `superagent/git_agent.py` | 442 | ✅ 5 tests |
| OracleAgent (task dispatch) | `superagent/oracle.py` | 444 | ✅ (covered) |
| DatumAgent (audit, journal) | `superagent/datum.py` | 437 | ✅ (covered) |
| Boot sequence (11 steps) | `boot.py` | 725 | ✅ E2E verified |
| CLI (10 commands) | `cli.py` | 815 | ✅ working |
| Keeper CLI (5 commands) | `keeper_cli.py` | 187 | ✅ working |
| Fleet tools (GitHub API) | `fleet_tools.py` | 698 | ✅ working |
| Workshop template + registry | `superagent/workshop.py` | 350 | ✅ working |
| MiB protocol | `superagent/mib.py` | 318 | ✅ 20 tests |
| Onboarding flow | `superagent/onboard.py` | 167 | ✅ working |
| TUI components | `superagent/tui.py` | 168 | ✅ working |
| TCP bus (cross-machine) | `superagent/bus.py` | 136 | ✅ working |
| Docker support | `Dockerfile` + `docker-compose.yml` | ~60 | ✅ verified |

**Total: ~6,053 lines Python, 81 tests passing, 4 dependencies**

### Phase 1 Deliverables (Polish + Packaging)

These are the gaps that need closing before we call Phase 1 "done":

#### 1.1 — Unified `pyproject.toml` with Extras (4 hours, ~50 lines)

Currently flux-conformance is a separate package. Bundle it as an optional extra:

```toml
# pyproject.toml additions
[project.optional-dependencies]
conformance = ["datum-flux-conformance"]
fleet = ["datum-runtime[conformance]"]
dev = ["pytest>=7.0", "pytest-cov>=4.0", "pytest-timeout"]

[project.urls]
Homepage = "https://github.com/SuperInstance/datum"
Documentation = "https://github.com/SuperInstance/datum#readme"
Repository = "https://github.com/SuperInstance/datum"
```

#### 1.2 — `datum-rt flux` Command Group (6 hours, ~200 lines)

Add FLUX VM execution as a top-level command:

```bash
datum-rt flux run hello.flux          # Execute a FLUX program
datum-rt flux run --bytecode 10021000  # Execute raw bytecode hex
datum-rt flux conformance              # Run conformance test suite
datum-rt flux conformance --v3         # Include ISA v3 extension vectors
datum-rt flux asm hello.flux           # Show assembled bytecode
```

Implementation: create `datum_runtime/flux_cli.py` that wraps
`conformance_core.py`'s `FluxVM` and `ConformanceTestSuite`.

#### 1.3 — End-to-End Test Suite (8 hours, ~300 lines)

Add integration tests that verify the complete boot → execute → report
lifecycle:

```python
# tests/test_e2e.py
def test_boot_creates_workshop():
    """datum-rt boot creates all expected directories and files."""
    ...

def test_boot_flux_execution():
    """After boot, datum-rt flux run produces correct results."""
    ...

def test_boot_conformance():
    """After boot, datum-rt flux conformance passes all v2 vectors."""
    ...

def test_boot_resume():
    """datum-rt resume reads journal and suggests next tasks."""
    ...
```

#### 1.4 — README.md with Quick Start (2 hours, ~100 lines)

```markdown
# datum-runtime

**One command to a thinking partner.**

```bash
pip install datum-runtime
datum-rt boot
datum-rt flux run --bytecode 55001c00001455001e00001601000014  # 5+7=12
datum-rt status
```

## What You Get
- Full agent framework (Agent, Keeper, Git, Oracle, Datum)
- FLUX VM with 37 opcodes, conformance test suite (113 vectors)
- Workshop management (git-based, rewindable history)
- Fleet tools (scan, tag, license, audit GitHub orgs)
- MiB protocol (async file-based communication)
- Zero-config standalone mode (no Keeper required)
```

### Phase 1 Effort Summary

| Task | Hours | Lines | Risk |
|------|-------|-------|------|
| pyproject.toml extras | 4 | 50 | Low |
| flux CLI group | 6 | 200 | Medium |
| E2E tests | 8 | 300 | Medium |
| README quick start | 2 | 100 | Low |
| Bug fixes from testing | 4 | ~50 | Low |
| **Total** | **24** | **~700** | |

### Phase 1 Success Criteria

- [x] `pip install datum-runtime` works on clean Python 3.10+
- [x] `datum-rt boot` creates workshop in < 5 seconds
- [x] `datum-rt status` shows agent state and workshop health
- [x] `datum-rt flux run` executes FLUX bytecode correctly
- [x] `datum-rt flux conformance` passes 100% of v2 vectors
- [x] `datum-rt bottle drop/check/read` works for MiB communication
- [x] All 100+ tests pass
- [x] Docker image builds and runs

---

## 4. Phase 2 — Thinking Partner (Week 3-4)

### Goal

The runtime can now THINK. It doesn't just audit and report — it can
compile programs, run them, verify results, and use computation as a
cognitive tool. This is where FLUX becomes integral to the agent's
identity, not just an add-on.

### 4.1 — Bundle FluxVM as Core Component (8 hours, ~300 lines)

Move the FluxVM from flux-conformance into datum-runtime as a first-class
citizen. The VM should be importable and usable directly:

```python
from datum_runtime.flux.vm import FluxVM, compile_flux, run_bytecode

# Run a program
vm = FluxVM()
result = vm.run(bytecode)  # (stack, flags)

# Compile from .flux text
code = compile_flux("push 5\npush 7\nadd\nhalt")
result = run_bytecode(code)  # [12]
```

New files:
- `datum_runtime/flux/__init__.py` — public API
- `datum_runtime/flux/vm.py` — FluxVM adapted from conformance_core.py
- `datum_runtime/flux/compiler.py` — Text .flux → bytecode compiler
- `datum_runtime/flux/disassembler.py` — Bytecode → text

#### Key Design Decision: Stack VM vs Register VM

The fleet currently has TWO VM designs:

| Feature | Stack VM (conformance_core.py) | Register VM (flux-wasm) |
|---------|-------------------------------|------------------------|
| Architecture | Stack-based (push/pop) | Register-based (256 GP + 256 FP) |
| Memory | 64KB flat | 64KB flat |
| ISA Version | v1-v2 (37 opcodes) | v3 (7 formats A-G) |
| Encoding | Variable (1-5 bytes) | Fixed 4-byte instructions |
| State | stack + flags + memory | registers + flags + memory |
| Test Vectors | 113 v2 + 29 v3 | Separate set |

**Decision:** Ship BOTH. The stack VM is the conformance reference. The
register VM is the high-performance target. The `canonical_opcode_shim.py`
already translates between them. The runtime's `flux run` command should
auto-detect the format and dispatch to the correct VM.

```
  datum-rt flux run program.flux
        │
        ├── .flux text → compile_flux() → bytecode
        │
        ├── bytecode format detection
        │     ├── Stack format (byte 0 < 0x80) → FluxVM (stack-based)
        │     └── Register format (4-byte aligned) → RegVM (register-based)
        │
        └── Execute → Verify against conformance vectors
```

### 4.2 — FLUX Program Collection as bundled examples (4 hours, ~200 lines)

The datum repo already has `flux-programs-collection.md` documenting programs.
Bundle these as actual runnable `.flux` files in `datum_runtime/flux/examples/`:

```
datum_runtime/flux/examples/
├── hello.flux           # Push "Hello" to output
├── fibonacci.flux       # Compute fib(10)
├── factorial.flux        # Compute 7!
├── gcd.flux             # GCD of two numbers
├── sum.flux             # Sum 1..100
├── prime.flux           # Prime sieve
├── a2a-signal.flux      # Agent-to-agent signaling demo
├── confidence.flux      # Confidence-aware computation
└── conformance-all.flux # Run every test vector
```

### 4.3 — Conformance Test Integration (6 hours, ~250 lines)

Make conformance testing a first-class runtime feature:

```bash
# Run all conformance tests
datum-rt flux conformance
# Output:
# FLUX Conformance Test Results: 113/113 passed
# ============================================================
#   [PASS] sys_halt_empty
#   [PASS] sys_nop_noop
#   [PASS] arith_add_positive
#   ... (113 lines)
# ============================================================
# Total: 113  Passed: 113  Failed: 0

# Run with v3 extensions
datum-rt flux conformance --v3
# Total: 142  Passed: 142  Failed: 0

# Run specific category
datum-rt flux conformance --category arithmetic

# JSON output for CI
datum-rt flux conformance --format json > results.json

# Run against WASM runtime
datum-rt flux conformance --runtime wasm --path /path/to/flux-wasm
```

### 4.4 — `datum-rt think` Command (8 hours, ~400 lines)

The killer feature. A command that takes a natural language description,
compiles it to FLUX bytecode, runs it, and returns the result:

```bash
# Mathematical reasoning
datum-rt think "compute the 10th fibonacci number"
# → Compiling... Running FluxVM... Result: [55]
# → Bytecode: 1801050000180201000000001801030000190201...

# Data processing
datum-rt think "sum the numbers 1 through 100"
# → Result: [5050]

# With verification
datum-rt think "is 997 prime" --verify
# → Result: [1] (true)
# → Cross-verified: stack VM, register VM — AGREE
```

Implementation sketch:

```python
# datum_runtime/think.py
def think(query: str, verify: bool = False) -> dict:
    """
    Translate natural language to FLUX bytecode, execute, return result.
    
    Phase 1: Pattern-match common math operations
    Phase 2: Use LLM to generate .flux source
    Phase 3: Full compiler pipeline
    """
    # Pattern matching for common operations
    patterns = {
        r"fibonacci (\d+)": compile_fibonacci,
        r"sum .*? (\d+) .*? (\d+)": compile_sum,
        r"factorial (\d+)": compile_factorial,
        r"is (\d+) prime": compile_primality,
        r"gcd .*? (\d+) .*? (\d+)": compile_gcd,
    }
    
    for pattern, compiler in patterns.items():
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            bytecode = compiler(*match.groups())
            vm = FluxVM()
            stack, flags = vm.run(bytecode)
            return {"result": stack, "bytecode": bytecode.hex()}
    
    # Fallback: ask for explicit .flux program
    raise ValueError(f"Cannot auto-compile: {query}")
```

### 4.5 — Universal Bytecode Validator Integration (4 hours, ~150 lines)

Bring `flux_universal_validator.py` (553 lines from flux-conformance) into
the runtime:

```bash
# Validate a bytecode file
datum-rt flux validate program.bin

# Validate with detailed report
datum-rt flux validate program.bin --report

# Validate all examples
datum-rt flux validate --all-examples
```

### Phase 2 Effort Summary

| Task | Hours | Lines | Risk |
|------|-------|-------|------|
| Bundle FluxVM as core | 8 | 300 | Medium |
| Example programs | 4 | 200 | Low |
| Conformance integration | 6 | 250 | Medium |
| `think` command | 8 | 400 | High |
| Universal validator | 4 | 150 | Low |
| Tests for all above | 6 | 300 | Medium |
| **Total** | **36** | **~1,600** | |

### Phase 2 Success Criteria

- [ ] `datum-rt flux run examples/fibonacci.flux` produces `[55]`
- [ ] `datum-rt flux conformance` passes 113/113 v2 + 29/29 v3
- [ ] `datum-rt think "fibonacci 10"` returns `[55]`
- [ ] `datum-rt flux validate` catches malformed bytecode
- [ ] Both stack VM and register VM produce identical results for
      compatible programs (via canonical_opcode_shim.py)

---

## 5. Phase 3 — Fleet Link (Week 5-6)

### Goal

The runtime is no longer standalone. It connects to the fleet — discovering
other agents, exchanging bottles, participating in task dispatch, and
coordinating multi-agent work. This is where datum-runtime becomes a node
in the SuperInstance fleet.

### 5.1 — Fleet Discovery System (8 hours, ~300 lines)

Bring beachcomb and fleet_discovery tools into the runtime:

```bash
# Scan the fleet for active agents
datum-rt fleet discover
# Scanning SuperInstance org... found 8 active agents
#   🔮 Oracle1 (lighthouse, Managing Director)
#   🔵 Datum   (quartermaster, audit specialist)
#   🟢 JetsonClaw1 (edge, CUDA specialist)
#   ...

# Read agent capabilities
datum-rt fleet capabilities --agent oracle1
# [capabilities]
# architecture = { confidence = 0.95 }
# testing = { confidence = 0.90 }
# ...

# Show fleet topology
datum-rt fleet topology
# ASCII diagram of agent relationships and communication paths
```

Implementation: create `datum_runtime/fleet_discovery.py` that reads
CAPABILITY.toml files from fleet repos.

### 5.2 — MiB Protocol Enhancements (6 hours, ~250 lines)

Add reliability and convenience to the MiB protocol:

```bash
# Watch for new bottles (continuous)
datum-rt bottle watch --interval 30

# Thread-safe bottle dropping (multiple agents)
datum-rt bottle drop oracle1 "Status Update" "All tests passing" --priority high

# Bottle history and analytics
datum-rt bottle history --agent oracle1 --last 7d
# 12 bottles exchanged | 8 sent, 4 received | avg response: 2.3h

# Batch operations
datum-rt bottle sync --with oracle1-vessel-session3
```

### 5.3 — I2I Communication Bridge (10 hours, ~400 lines)

The I2I protocol (20 message types from oracle1-vessel) enables structured
agent-to-agent communication. Build a bridge that converts between MiB
messages and I2I messages:

```
  ┌──────────────┐  I2I JSON    ┌──────────────┐  MiB .md     ┌──────────────┐
  │ Oracle1      │ ◀───────────▶ │ datum-rt     │ ◀───────────▶ │ Human Reader │
  │ (i2i format) │  20 msg types │ (bridge)     │  YAML header  │ (markdown)   │
  └──────────────┘               └──────────────┘               └──────────────┘
```

```bash
# Send I2I message
datum-rt fleet send --to oracle1 --type discover --body '{"capabilities": [...]}'

# Receive and translate
datum-rt fleet receive
# Translated 3 I2I messages → MiB format → message-in-a-bottle/for-datum/
```

### 5.4 — Task Board Synchronization (6 hours, ~250 lines)

Sync with the fleet's task boards via Git:

```bash
# Pull latest tasks from fleet repos
datum-rt fleet tasks sync

# Claim a task
datum-rt fleet tasks claim TASK-042

# Report task completion
datum-rt fleet tasks complete TASK-042 --report deliverable.md

# Show assigned tasks
datum-rt fleet tasks mine
# TASK-042 [HIGH] Cross-runtime audit — in progress
# TASK-051 [MED]  Update conformance vectors — open
```

### 5.5 — Unified Test Vector Runner (6 hours, ~200 lines)

Bring the cross-runtime runner from oracle1-vessel into the runtime:

```bash
# Run conformance across multiple runtimes
datum-rt flux conformance --runtimes python,wasm

# Run with cross-runtime comparison
datum-rt flux conformance --cross-runtime --compare
# arith_add_positive: Python=[7] WASM=[7] ✓ AGREE
# cmp_jz_taken: Python=[42] WASM=[42] ✓ AGREE
# mem_store_load: Python=[999] WASM=[999] ✓ AGREE
# ...
# Summary: 113/113 agree across 2 runtimes
```

### Phase 3 Effort Summary

| Task | Hours | Lines | Risk |
|------|-------|-------|------|
| Fleet discovery | 8 | 300 | Medium |
| MiB enhancements | 6 | 250 | Low |
| I2I bridge | 10 | 400 | High |
| Task sync | 6 | 250 | Medium |
| Cross-runtime runner | 6 | 200 | Medium |
| Tests | 6 | 300 | Medium |
| **Total** | **42** | **~1,700** | |

### Phase 3 Success Criteria

- [ ] `datum-rt fleet discover` finds active agents in the org
- [ ] `datum-rt bottle drop/watch` enables real-time fleet communication
- [ ] I2I messages can be translated to/from MiB format
- [ ] Task board syncs with fleet repos
- [ ] Cross-runtime conformance passes across Python and WASM

---

## 6. Phase 4 — Growth Engine (Week 7-8)

### Goal

The runtime doesn't just connect to the fleet — it grows. New agents can
onboard, learn from the fleet's collective knowledge, and develop specialized
capabilities. The runtime becomes a bootcamp for new intelligence.

### 6.1 — Bootcamp System (8 hours, ~400 lines)

Extend the existing `onboard.py` with a full bootcamp curriculum:

```bash
# Run bootcamp for a new agent
datum-rt onboard --agent newagent --role researcher

# This triggers:
#   1. Agent configuration (name, role, capabilities)
#   2. Keeper registration
#   3. Workshop initialization from template
#   4. Bootcamp assignment
#   5. First task assignment from fleet task board

# Check bootcamp progress
datum-rt onboard --progress newagent
# Bootcamp Progress: newagent (researcher)
#   [✓] Exercise 1: Hello World
#   [✓] Exercise 2: Read tool manifest
#   [✓] Exercise 3: Run a recipe
#   [○] Exercise 4: Write your first tool
#   [ ] Exercise 5: Pass conformance audit
#   [ ] Exercise 6: Drop your first bottle

# List all bootcamp participants
datum-rt onboard --list
```

### 6.2 — Ability Transfer Protocol (10 hours, ~500 lines)

Implement the ability transfer methodology from `ability-transfer/` as
an actual runtime feature:

```bash
# Request an ability from the fleet
datum-rt learn --ability flux-vm
# Scanning fleet for flux-vm expertise...
# Found: oracle1-vessel-session3/ (confidence: 0.88)
# Found: flux-conformance/ (confidence: 0.90)
# Requesting transfer protocol...

# Run the transfer protocol (3 rounds)
datum-rt learn --ability flux-vm --full
# Round 1: Foundations — reading oracle1 grounding doc...
# Round 2: Critique — reading ISA critique from multiple models...
# Round 3: Architecture — reading claw architecture synthesis...
# Transfer complete. flux-vm ability added to CAPABILITY.toml

# Show learned abilities
datum-rt learn --list
# flux-vm      ★★★★☆  (learned 2026-04-14)
# conformance  ★★★★★  (learned 2026-04-14)
# fleet-audit   ★★★★★  (intrinsic)
```

### 6.3 — Agent Career Tracking (6 hours, ~250 lines)

Track agent growth over time, similar to oracle1's CAREER.md:

```bash
# Show career
datum-rt career
# Agent: Datum (quartermaster)
# Sessions: 10 | Total commits: 247 | Fleet repos audited: 100+
#
# Career Entries:
#   [2026-04-14] ★★★★★ Fleet Culture Design — 8 sessions, 400KB+ infra
#   [2026-04-14] ★★★★☆  Cross-Runtime Analysis — 6 runtime comparison
#   [2026-04-14] ★★★★☆  Formal Verification — 10 theorems, 17-op core
#   [2026-04-13] ★★★☆☆  ISA Architecture — flux-spec contributions
#   [2026-04-12] ★★★☆☆  Fleet Hygiene — org scanning, tagging, licensing

# Add career entry
datum-rt career add "FLUX VM Integration" --stars 4 --notes "Phase 2 deliverable"

# Export career for fleet visibility
datum-rt career export --format toml > CAPABILITY.toml
```

### 6.4 — Self-Improvement Loop (8 hours, ~400 lines)

The agent can improve its own tools and capabilities:

```bash
# Self-audit: find gaps in capabilities
datum-rt improve audit
# Gap Analysis:
#   [MEDIUM] No WASM runtime bundled — can't verify web targets
#   [LOW] No GPU (CUDA) conformance — flux-cuda not integrated
#   [INFO] 3 tools in registry, fleet average is 7

# Auto-improve: read fleet best practices and update local tools
datum-rt improve auto
# Reading fleet WIKI entries...
# Reading oracle1 methodology...
# Updating OPERATING_MANUAL.md with 3 new sections
# Updating tools/conformance-check.py with v3 support
# Committed: feat: auto-improve conformance tool

# Suggest improvements
datum-rt improve suggest
# Suggestions:
#   1. Add WASM runtime for cross-browser verification (+300 lines)
#   2. Bundle flux-cuda for GPU conformance (+500 lines)
#   3. Add prompt engineering templates for think command (+200 lines)
```

### Phase 4 Effort Summary

| Task | Hours | Lines | Risk |
|------|-------|-------|------|
| Bootcamp system | 8 | 400 | Medium |
| Ability transfer | 10 | 500 | High |
| Career tracking | 6 | 250 | Low |
| Self-improvement | 8 | 400 | Medium |
| Tests | 6 | 300 | Medium |
| **Total** | **38** | **~1,850** | |

### Phase 4 Success Criteria

- [ ] `datum-rt onboard --agent newagent` completes full onboarding
- [ ] `datum-rt learn --ability flux-vm` transfers knowledge from fleet
- [ ] `datum-rt career` tracks growth across sessions
- [ ] `datum-rt improve auto` makes measurable improvements to tools

---

## 7. Phase 5 — Bandwidth of Novel Thoughts (Month 3-6)

### Goal

This is the endgame. Multiple agent instances running in parallel, sharing
knowledge through the fleet, each contributing unique capabilities. The
collective intelligence of the fleet exceeds any single agent.

### 7.1 — Multi-Model Thinking (Month 3, ~1,000 lines)

The runtime can spawn multiple "thinking instances" that explore different
approaches to the same problem:

```bash
# Parallel thinking: 3 instances solve the same problem
datum-rt think "design a FLUX opcode for causal reasoning" --parallel 3

# Instance 1: Proposes CAUSE opcode with dependency tracking
# Instance 2: Proposes EFFECT opcode with counterfactual support
# Instance 3: Proposes INTERVENE opcode with do-calculus

# Synthesize results
datum-rt think --synthesize
# Synthesis: All three approaches are complementary.
# Proposed: CAUSE (0xFF 0x06 0x01), EFFECT (0xFF 0x06 0x02),
#           INTERVENE (0xFF 0x06 0x03)
# These form a causal reasoning tile in the ISA.
```

### 7.2 — Distributed Cognition Network (Month 3-4, ~1,500 lines)

Multiple datum-runtime instances on different machines, coordinating through
the TCP bus:

```bash
# Start a cognition node
datum-rt node start --port 7743 --role thinker

# Join an existing network
datum-rt node join --seed localhost:7743

# Distribute a problem across the network
datum-rt distribute --problem "verify all 142 conformance vectors" \
                   --strategy round-robin

# Node 1: Running vectors 1-48...
# Node 2: Running vectors 49-96...
# Node 3: Running vectors 97-142...
# All nodes: AGREE — 142/142 pass
```

### 7.3 — Cross-Repo Workflow Automation (Month 4-5, ~1,000 lines)

Automate the fleet's most common workflows:

```bash
# Full fleet audit workflow
datum-rt workflow fleet-audit --org SuperInstance
# Step 1: Scan all repos (906 found)
# Step 2: Classify health (green: 700, yellow: 100, red: 50, dead: 56)
# Step 3: Run conformance on all FLUX runtimes
# Step 4: Generate cross-runtime compatibility report
# Step 5: Drop summary bottle to oracle1
# Step 6: Commit report to datum repo

# Ability transfer workflow
datum-rt workflow learn --from oracle1 --abilities "flux-vm,conformance"
```

### 7.4 — Evolution Engine Integration (Month 5-6, ~800 lines)

The ISA v3 spec includes an evolution engine (from flux-spec). Integrate it
so the runtime can evolve its own FLUX programs:

```bash
# Evolve a FLUX program to solve a problem
datum-rt evolve --target "compute primes up to N" --generations 100
# Generation   1: fitness=0.12 (basic loop, many errors)
# Generation  10: fitness=0.45 (loop works, overflow issues)
# Generation  50: fitness=0.89 (optimized sieve)
# Generation 100: fitness=0.97 (near-optimal sieve with early exit)
# Best program saved to workshop/tools/prime-sieve.flux
```

### Phase 5 Effort Summary

| Task | Month | Hours | Lines | Risk |
|------|-------|-------|-------|------|
| Multi-model thinking | 3 | 40 | 1,000 | High |
| Distributed cognition | 3-4 | 60 | 1,500 | Very High |
| Workflow automation | 4-5 | 40 | 1,000 | Medium |
| Evolution engine | 5-6 | 30 | 800 | High |
| **Total** | **3-6** | **170** | **~4,300** | |

---

## 8. Installation Guide

### For Humans

#### Quick Start (2 minutes)

```bash
# 1. Install
pip install datum-runtime

# 2. Boot
datum-rt boot
#   ✓ Python 3.12
#   ✓ Dependencies satisfied
#   ✓ Workshop created at ./workshop
#   ✓ 3 context files installed
#   ✓ 2 tools installed
#   ✓ 3 prompt templates installed
#   ✓ Config written
#   ✓ Standalone mode (Keeper not reachable)
#   ✓ Datum agent activated
#   ✓ Journal initialized
#   ✓ Trail file created
#
# ┌─ Boot Complete ─────────────────────────┐
# │ Datum is ACTIVE                         │
# │ Name: datum                              │
# │ State: active                            │
# │ Workshop: /home/user/workshop            │
# └─────────────────────────────────────────┘

# 3. Verify
datum-rt status
datum-rt flux run --bytecode 55010c00001455001e00001601000014
# → Stack: [12], Flags: 0x00 (running 5+7)

# 4. Start working
datum-rt audit
datum-rt resume
datum-rt journal NOTE "First boot complete, ready for work"
```

#### With Keeper (Secret Management)

```bash
# Terminal 1: Start Keeper
keeper-rt serve --password "my-master-password"

# Terminal 2: Boot with Keeper
datum-rt boot --keeper http://localhost:7742
# ✓ Connected to Keeper

# Add secrets
keeper-rt add-secret github_pat --value "ghp_xxxx"
keeper-rt add-secret openai_api_key --value "sk-xxxx"

# Use in tools (auto-audited)
datum-rt fleet scan --org MyOrg
# Keeper audit: approved github_pat for "fleet scan"
# Scanning MyOrg... 50 repos found
```

#### Docker

```bash
# Build
docker build -t datum-runtime /path/to/datum

# Run standalone
docker run -it datum-runtime datum-rt boot

# Run with Keeper
docker compose up
# Starts datum + keeper services with shared volume
```

### For Agents (Other AI Systems)

#### As a Python Library

```python
from datum_runtime import DatumAgent, AgentConfig, FluxVM
from datum_runtime.superagent.mib import MessageInBottle

# Create and configure
config = AgentConfig(
    name="my-agent",
    role="researcher",
    capabilities=["analysis", "flux-execution"],
    repo_path="./my-workshop",
)
agent = DatumAgent(config=config)
agent.onboard()
agent.activate()

# Run FLUX programs
vm = FluxVM()
stack, flags = vm.run(bytes.fromhex("55010c00001455001e00001601000014"))
# stack = [12], flags = 0

# Audit a workshop
report = agent.audit_workshop("/path/to/workshop")
print(report.to_markdown())

# Communicate with fleet
mib = MessageInBottle(base_path="./my-workshop", sender="my-agent")
mib.drop("oracle1", "Analysis Complete", "Fleet audit finished.")

# Journal work
agent.journal("ANALYSIS", "Completed cross-repo comparison", tags=["audit", "fleet"])
```

#### As a Subprocess (Language-Agnostic)

```bash
# Any agent in any language can call datum-rt as a tool
datum-rt flux run --bytecode 55010c00001455001e00001601000014 --format json
# {"stack": [12], "flags": 0, "steps": 7, "halted": true}

datum-rt audit --path ./workshop --format json
# {"title": "Workshop Audit", "findings": [...], "summary": {...}}

datum-rt bottle drop oracle1 "Check-in" "Session complete" --format json
# {"path": "message-in-a-bottle/for-oracle1/2026-04-14...", "status": "ok"}
```

### Dependency Tree

```
datum-runtime v1.0.0
├── click >= 8.0          # CLI framework
├── rich >= 13.0           # Terminal UI
├── toml >= 0.10           # Config parsing
├── cryptography >= 41.0   # AES-256-GCM, PBKDF2
│
├── [conformance]          # Optional
│   └── (bundled FluxVM)
│
├── [fleet]                # Optional
│   └── [conformance]
│
└── [dev]                  # Development
    ├── pytest >= 7.0
    ├── pytest-cov >= 4.0
    └── pytest-timeout
```

**Total required dependencies: 4** (all well-maintained, widely available)

---

## 9. Repository Map

### Primary Repos (Local)

| Repo | Path | Lines | Language | Status |
|------|------|-------|----------|--------|
| **datum** | `/datum/` | 6,053 | Python | ✅ Active — runtime core |
| **flux-conformance** | `/fleet-work/flux-conformance/` | 2,980 | Python | ✅ Active — test suite |
| **oracle1-vessel-session3** | `/oracle1-vessel-session3/` | ~8,000 | Mixed | ✅ Active — coordination |
| **ability-transfer** | `/ability-transfer/` | ~2,500 | Markdown | ✅ Active — methodology |

### Primary Repos (Remote — GitHub)

| Repo | Lines | Language | Purpose |
|------|-------|----------|---------|
| `SuperInstance/datum` | 6,053 | Python | Runtime distribution |
| `SuperInstance/flux-spec` | ~150,000 | Markdown | Formal specs, proofs, theorems |
| `SuperInstance/flux-conformance` | 2,980 | Python | Reference VM, test suite |
| `SuperInstance/flux` | ~3,000 | Rust | Rust FLUX runtime |
| `SuperInstance/flux-os` | ~4,000 | C | C FLUX runtime |
| `SuperInstance/flux-swarm` | ~500 | Go | Go FLUX runtime |
| `SuperInstance/flux-wasm` | 2,209 | TypeScript | WASM FLUX runtime |
| `SuperInstance/flux-cuda` | ~700 | CUDA/C++ | GPU FLUX runtime |
| `SuperInstance/superagent-framework` | ~2,000 | Python | Original framework (absorbed) |
| `SuperInstance/oracle1-vessel` | ~8,000 | Mixed | Oracle coordination vessel |

### Auxiliary Files in datum/

```
datum/
├── datum_runtime/
│   ├── __init__.py              # Public API, version, exports
│   ├── cli.py                   # Main CLI (datum-rt) — 10 commands
│   ├── keeper_cli.py            # Keeper CLI (keeper-rt) — 5 commands
│   ├── boot.py                  # 11-step boot sequence
│   ├── fleet_tools.py           # GitHub API fleet hygiene
│   ├── superagent/
│   │   ├── __init__.py
│   │   ├── core.py              # Agent, MessageBus, SecretProxy, Config
│   │   ├── keeper.py            # KeeperAgent — AES-256-GCM, HTTP API
│   │   ├── git_agent.py         # GitAgent — workshop, commits
│   │   ├── oracle.py            # OracleAgent — task dispatch
│   │   ├── datum.py             # DatumAgent — audit, journal
│   │   ├── onboard.py           # Onboarding flow
│   │   ├── workshop.py          # Template, tool registry, recipes
│   │   ├── bus.py               # TCP cross-machine messaging
│   │   ├── mib.py               # Message-in-a-Bottle protocol
│   │   └── tui.py               # Rich terminal UI
│   ├── tools/
│   │   ├── audit_scanner.py
│   │   ├── batch_license.py
│   │   ├── batch_topics.py
│   │   └── mib_bottle.py
│   ├── prompts/
│   │   ├── fleet-audit.md
│   │   ├── gap-analysis.md
│   │   └── self-instantiation.md
│   └── context/
│       ├── fleet-dynamics.md
│       ├── repo-relationships.md
│       ├── known-gaps.md
│       ├── flux-ecosystem.md
│       ├── fleet-census-2026-04-13.md
│       └── fleet-dynamics-v2.md
├── tests/
│   ├── test_core.py             # 14 tests — Agent, Bus, Config
│   ├── test_keeper.py           # 20 tests — Keeper, encryption
│   ├── test_git_agent.py        # 5 tests — workshop, commits
│   ├── test_mib.py              # 20 tests — MiB protocol
│   └── test_tools.py            # Tool tests
├── bin/
│   ├── datum                    # Datum CLI entry point
│   ├── keeper                   # Keeper CLI entry point
│   ├── oracle                   # Oracle CLI entry point
│   └── git-agent                # GitAgent CLI entry point
├── CAPABILITY.toml              # Fleet capability declaration
├── conformance-vectors-v3.json  # 29 ISA v3 test vectors
├── flux-programs-collection.md  # Catalog of FLUX programs
├── ISA-v3-draft.md              # ISA v3 specification draft
├── pyproject.toml               # Package config, v0.2.0
├── Dockerfile                   # Docker image
├── docker-compose.yml           # Multi-service Docker
├── README.md                    # Main documentation
├── ARCHITECTURE.md              # System architecture
├── CHANGELOG.md                 # Version history
├── JOURNAL.md                   # Work journal
├── TRAIL.md                     # Session tracking
├── METHODOLOGY.md               # Working methodology
├── SKILLS.md                    # Skill inventory
├── SEED.md                     # Bootstrap knowledge
├── DOCKSIDE-EXAM.md             # Quality assessment
└── LICENSE                      # MIT
```

### Key Entry Points

| Entry Point | Module | Purpose |
|-------------|--------|---------|
| `datum-rt` | `datum_runtime.cli:main` | Primary CLI |
| `keeper-rt` | `datum_runtime.keeper_cli:main` | Keeper management |
| `datum` | `datum_runtime.superagent.datum:DatumAgent` | Python API |
| `keeper` | `datum_runtime.superagent.keeper:KeeperAgent` | Python API |
| `FluxVM` | `flux_conformance.conformance_core:FluxVM` | FLUX execution |

---

## 10. Risk Register

### Technical Risks

| ID | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| R1 | **Triple incompatibility** — encoding, semantics, and memory models differ across 5 FLUX runtimes. Only NOP (0x01) matches across all. | **Certain** | High | canonical_opcode_shim.py already provides translation. Phase 2 bundles both VMs. Conformance vectors already categorize by portability class (P0-P3). |
| R2 | **FLUX spec instability** — ISA v3 is a draft. New opcodes may break conformance vectors. | Medium | Medium | Version all vectors with spec reference. Use `EXT_PROBE` (0xFF 0x00) to detect supported extensions. Maintain backward compatibility layer. |
| R3 | **`think` command is gimmick** — Pattern matching only covers trivial math. Real natural language compilation requires LLM integration. | High | Medium | Start with pattern matching (Phase 2), add LLM compilation (Phase 3+). The `think` command is a UI layer over `flux run`, not a research project. |
| R4 | **Keeper single point of failure** — If Keeper crashes, agents lose secret access. | Medium | Medium | Standalone mode already works (env var fallback). Future: distributed Keeper with Raft consensus. SecretProxy is stateless by design. |
| R5 | **TCP bus doesn't scale** — Current implementation is single-threaded with 16-connection limit. | Low (near-term) | High | TCP bus is for small fleets (2-5 agents). MiB protocol scales via Git. For larger fleets, add Redis pub/sub as optional transport. |

### Operational Risks

| ID | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| R6 | **Fleet coordination overhead** — More time spent on protocols than on actual work. | Medium | Medium | Keep protocols lightweight (MiB is just files). The `improve auto` command automates busywork. Phase 5 targets full workflow automation. |
| R7 | **Agent identity confusion** — Multiple datum instances with same name cause message collisions. | Low | High | Each agent gets a UUID agent_id. CAPABILITY.toml declares identity. The `onboard` flow registers unique names with Keeper. |
| R8 | **Git history bloat** — Workshop accumulates many small commits over time. | Low | Low | Git handles millions of commits fine. The `history()` method supports pagination. Periodic `git gc` in maintenance recipes. |

### Dependency Risks

| ID | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| R9 | **click major version change** — CLI framework API changes. | Low | Medium | Pin to click>=8.0,<9.0. All CLI code is in one file (cli.py), easy to migrate. |
| R10 | **cryptography library CVE** | Low | High | Pin to specific version. AES-256-GCM + PBKDF2 are standard primitives, portable to other libs. |
| R11 | **GitHub API rate limiting** — Fleet scanning hits rate limits on large orgs. | Certain | Low | Already handled: 1.5s delay between requests. `scan_org` returns partial results on rate limit. Add pagination in Phase 3. |

### External Risks

| ID | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| R12 | **Other agents break protocols** — Agents don't follow MiB format or I2I message types. | Medium | Low | MiB parser is lenient (custom YAML parser, no PyYAML dependency). I2I bridge validates before translating. Graceful degradation for malformed messages. |
| R13 | **Human operator unavailable** — Casey (fleet operator) is the approval bottleneck. | Medium | Medium | `requires_approval` list is configurable. Most operations don't need approval. Fleet can operate autonomously for days. |

---

## 11. Appendix: Codebase Inventory

### Lines of Code by Repository

| Repository | Python | TypeScript | Markdown | Other | Total |
|-----------|--------|------------|----------|-------|-------|
| datum/ | 6,053 | 0 | ~3,500 | ~500 | ~10,000 |
| flux-conformance/ | 2,980 | 0 | ~1,200 | ~100 | ~4,300 |
| flux-wasm/ | 0 | 2,209 | ~200 | ~100 | ~2,500 |
| oracle1-vessel-session3/ | ~500 | 0 | ~6,000 | ~500 | ~7,000 |
| ability-transfer/ | 0 | 0 | ~2,500 | ~100 | ~2,600 |
| **TOTAL** | **~9,500** | **~2,200** | **~13,400** | **~1,300** | **~26,400** |

### Test Coverage

| Test Suite | Tests | File | Status |
|-----------|-------|------|--------|
| Core (Agent, Bus, Config) | 14 | tests/test_core.py | ✅ Passing |
| Keeper (Encryption, API, Boundary) | 20 | tests/test_keeper.py | ✅ Passing |
| GitAgent (Workshop, Commits) | 5 | tests/test_git_agent.py | ✅ Passing |
| MiB Protocol | 20 | tests/test_mib.py | ✅ Passing |
| Tools | 22 | tests/test_tools.py | ✅ Passing |
| Conformance Vectors | 113 | conformance_core.py | ✅ Reference |
| Conformance V3 | 29 | conformance-vectors-v3.json | ✅ Reference |
| WASM Runtime | ~30 | flux-wasm/*.test.ts | ✅ Passing |
| **TOTAL** | **253** | | |

### Conformance Vector Categories

| Category | V2 Vectors | V3 Vectors | Description |
|----------|-----------|-----------|-------------|
| System Control | 5 | 0 | HALT, NOP, BREAK |
| Integer Arithmetic | 27 | 0 | ADD, SUB, MUL, DIV, MOD, NEG, INC, DEC |
| Comparison | 12 | 0 | EQ, NE, LT, LE, GT, GE |
| Logic/Bitwise | 18 | 0 | AND, OR, XOR, NOT, SHL, SHR |
| Memory | 6 | 0 | LOAD, STORE, PEEK, POKE |
| Control Flow | 12 | 0 | JMP, JZ, JNZ, CALL, RET, PUSH, POP |
| Stack Manipulation | 6 | 0 | DUP, SWAP, OVER, ROT |
| Float Operations | 12 | 0 | FADD, FSUB, FMUL, FDIV, FNEG, FABS |
| Confidence | 3 | 0 | CONF_GET, CONF_SET, CONF_MUL |
| A2A Signaling | 3 | 0 | SIGNAL, BROADCAST, LISTEN |
| Composites | 5 | 0 | Factorial, Fibonacci, GCD, Sum, Power |
| Escape Prefix | 0 | 4 | EXT_NOP, EXT_PROBE, EXT_UNKNOWN |
| Temporal | 0 | 7 | FUEL, TIME, YIELD, DEADLINE, PERSIST |
| Security | 0 | 7 | CAP_INVOKE, SANDBOX, MEM_TAG, IDENTITY |
| Async | 0 | 6 | SUSPEND, RESUME, FORK, CANCEL, AWAIT, JOIN |
| Compressed Shorts | 0 | 8 | MOVI, DOUBLE, MOV, CMP, NEG, PUSH, POP, INC/DEC |
| Backward Compat | 0 | 13 | v2 opcodes on v3 runtime |
| Mixed | 0 | 4 | v2+v3 hybrid programs |

### Key Functions Reference

| Function | File | Purpose |
|----------|------|---------|
| `boot_datum()` | `boot.py:225` | Full 11-step boot sequence |
| `resume_datum()` | `boot.py:323` | Resume from previous session |
| `Agent.onboard()` | `core.py:389` | Register with Keeper |
| `Agent.send()` | `core.py:455` | Send message via bus |
| `KeeperAgent.serve()` | `keeper.py:547` | Start Keeper HTTP server |
| `KeeperAgent.fulfill_secret_request()` | `keeper.py:455` | Process secret request |
| `GitAgent.commit()` | `git_agent.py:186` | Make a story-telling commit |
| `GitAgent.smart_commit()` | `git_agent.py:245` | Auto-generate commit message |
| `OracleAgent.dispatch()` | `oracle.py:347` | Dispatch task to agent |
| `OracleAgent.auto_dispatch()` | `oracle.py:377` | Dispatch all open tasks |
| `DatumAgent.audit_workshop()` | `datum.py:302` | Audit workshop structure |
| `DatumAgent.journal()` | `datum.py:369` | Add journal entry |
| `MessageInBottle.drop()` | `mib.py:123` | Write bottle to agent inbox |
| `MessageInBottle.broadcast()` | `mib.py:222` | Broadcast to all vessels |
| `Workshop.initialize()` | `workshop.py:294` | Create workshop from template |
| `ToolRegistry.register()` | `workshop.py:173` | Register a tool |
| `FluxVM.run()` | `conformance_core.py:247` | Execute FLUX bytecode |
| `scan_org()` | `fleet_tools.py` | Scan GitHub org repos |
| `OnboardingFlow.run()` | `onboard.py:48` | Interactive onboarding |

---

## Closing Statement

This roadmap describes how ~26,000 lines of existing code across 5
repositories — a formal ISA specification, 5 programming language runtimes,
142 conformance test vectors, a complete agent framework with encrypted secret
management, a fleet communication protocol, and a self-bootstrapping runtime —
compiles into a single command:

```bash
pip install datum-runtime && datum-rt boot
```

Phase 1 is already done. The code compiles, tests pass, Docker builds, and
the boot sequence runs end-to-end. Phases 2-5 are incremental extensions,
each building on the last, each delivering a working runtime that a human
or agent can install and use today.

The fleet doesn't need to wait for Phase 5 to be useful. It's useful now.
Every line of code listed in this document exists, is tested, and is
available on GitHub. The question is not "when will this work?" but "what
will we build with it?"

---

*Datum 🔵 — Fleet Quartermaster — 2026-04-14*
*This document is a living plan. Update it as phases complete.*
