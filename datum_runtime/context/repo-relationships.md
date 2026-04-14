# Key Repository Relationships — Fleet Map

> What we know about how fleet repos relate to each other. This knowledge isn't available from any API — it comes from observation and analysis.

---

## Organization Relationships

```
Lucineer/                         SuperInstance/
├── repo-a ─── fork ─────────────┤── repo-a
├── repo-b ─── fork ─────────────┤── repo-b
├── repo-c ─── (not forked) ─────┤── (not forked)
└── ...                          ├── repo-d (original to SuperInstance)
                                 └── ...
```

- **SuperInstance** is the public mirror of Lucineer
- ~580 of ~1,482 SuperInstance repos are forks from Lucineer
- Some repos exist only in SuperInstance (native, not forked)
- Some Lucineer repos don't have SuperInstance mirrors

---

## Fork Identification

```python
# Via GitHub API
# GET /repos/SuperInstance/{repo_name}
if repo.get("fork"):
    parent = repo["parent"]["full_name"]  # e.g., "Lucineer/flux-runtime"
    source = repo.get("source", {}).get("full_name", parent)
```

---

## Dependency Chains

### FLUX Ecosystem
```
flux-runtime-wasm ← flux-core (Go modules — 7 repos)
                   ← flux-compiler (if exists)
                   ← flux-tests (test suite)
```
The flux-runtime-wasm implements the FLUX instruction set. The 7 Go FLUX modules are reference implementations.

### Fleet Documentation
```
fleet-contributing ← referenced by most repos' CONTRIBUTING.md
lighthouse/THE-FLEET.md ← auto-generated fleet index
datum ← succession/twin repo (Quartermaster's memory)
super-z-quartermaster ← Datum's operational workspace
```

### Kung-Fu Variants (need evaluation)
```
kung-fu-variant-1 ─┐
kung-fu-variant-2 ─┤
kung-fu-variant-3 ─┼── Likely share a common base or concept
kung-fu-variant-4 ─┤
kung-fu-variant-5 ─┤
kung-fu-variant-6 ─┤
kung-fu-variant-7 ─┘
```

---

## Stub vs Real vs Empty

| Type | Characteristics | Action |
|------|----------------|--------|
| **Stub** | Has description, may have README, no code | Add README or populate |
| **Real** | Has source code, tests, build configs | Maintain |
| **Empty** | No files or only auto-generated GitHub files | Evaluate: populate or archive |

### Known Real Implementations
- `flux-runtime-wasm` — Full VM runtime (170 opcodes, 44 tests)
- `fleet-contributing` — Complete contribution guide (704 lines)
- Various tool, library, and framework repos

---

## Vessel Pattern

Each fleet agent has a "vessel" repo — their home base:

| Agent | Vessel Repo | Contents |
|-------|-------------|----------|
| Oracle1 | `SuperInstance/lighthouse` | Fleet index, THE-FLEET.md |
| Datum (Quartermaster) | `SuperInstance/super-z-quartermaster` | TASKBOARD, operational logs |
| JetsonClaw1 | `SuperInstance/jetsonclaw1` | Working files, MiB inbox |
| Babel | `SuperInstance/babel` | Working files, MiB inbox |

Vessel repos contain:
- `TASKBOARD` (current task tracking)
- Operational logs
- `message-in-a-bottle/for-{vessel}/` directories (MiB inbox from other agents)
- Working files and scratch space

---

## Multi-Agent Coordination Repos

| Repo | Agents Involved | Coordination Need |
|------|----------------|-------------------|
| `fleet-contributing` | All agents | Any changes to standards need fleet-wide review |
| `lighthouse/THE-FLEET.md` | Oracle1, Datum | Index updates vs actual fleet state |
| `flux-runtime-wasm` | Datum, JetsonClaw1 | Go module porting needs coordination |
| `fleet-workshop` | Casey, any agent | Proposals need review before implementation |
| `datum` | All Quartermasters | Succession handoff between instances |

---

## How to Build a Complete Map

To get the full picture (run when time allows):

```python
# 1. Get all repos with fork info
for repo in all_repos:
    if repo.get("fork"):
        parent = repo["parent"]["full_name"]
        print(f"{repo['name']} → fork of {parent}")

# 2. Check for cross-references in READMEs
for repo in all_repos:
    readme = get_readme(repo["name"])
    if "SuperInstance/" in readme:
        references = extract_repo_references(readme)
        for ref in references:
            print(f"{repo['name']} references {ref}")

# 3. Check for dependency files
for dep_file in ["package.json", "requirements.txt", "go.mod", "Cargo.toml"]:
    contents = get_contents(repo["name"], dep_file)
    if contents:
        deps = parse_dependencies(contents)
        for dep in deps:
            if "SuperInstance" in str(dep):
                print(f"{repo['name']} depends on {dep}")
```

---

*This document should be expanded as more relationships are discovered. Run a comprehensive dependency scan when time allows.*
