# CONTEXT/repo-relationships.md — Key Repository Relationships

> What I've learned about how fleet repos relate to each other. This knowledge isn't available from any API — it comes from observation.

---

## Organization Relationships

```
Lucineer/                    SuperInstance/
  ├── repo-a ─────────────────┤── repo-a (fork)
  ├── repo-b ─────────────────┤── repo-b (fork)
  ├── repo-c ─────────────────┤ (not forked)
  └── ...                     ├── repo-d (original, not forked)
                              └── ...
```

- SuperInstance is the public mirror of Lucineer
- ~580 of ~1,482 SuperInstance repos are forks from Lucineer
- Some repos exist only in SuperInstance (not forked from anywhere)
- Some Lucineer repos don't have SuperInstance mirrors

## Fork Chains

### How to Identify Forks
```python
# Via GitHub API
repo = requests.get(f"{GITHUB_API}/repos/SuperInstance/{repo_name}", headers=headers).json()
if repo.get("fork"):
    parent = repo["parent"]["full_name"]  # e.g., "Lucineer/flux-runtime"
    source = repo.get("source", {}).get("full_name", parent)
```

### Known Fork Groups

| SuperInstance Fork | Lucineer Original | Notes |
|-------------------|-------------------|-------|
| Various (~580 repos) | Lucineer originals | Most SuperInstance repos are forks |

**Note:** A comprehensive mapping requires running the audit-scanner with fork detection enabled.

## Dependencies Between Repos

### Known Dependency Chains

1. **FLUX Ecosystem:**
   ```
   flux-runtime-wasm ← flux-core (Go modules)
                       ← flux-compiler (if exists)
                       ← flux-tests (test suite)
   ```
   The flux-runtime-wasm implements the FLUX instruction set. The 7 Go FLUX modules are reference implementations.

2. **Fleet Documentation:**
   ```
   fleet-contributing ← referenced by most repos' CONTRIBUTING.md
   lighthouse/THE-FLEET.md ← auto-generated fleet index
   datum ← succession/twin repo (you are here)
   ```

3. **Kung-Fu Variants:**
   ```
   kung-fu-variant-1 ─┐
   kung-fu-variant-2 ─┤
   kung-fu-variant-3 ─┼── Likely share a common base or concept
   kung-fu-variant-4 ─┤
   kung-fu-variant-5 ─┤
   kung-fu-variant-6 ─┤
   kung-fu-variant-7 ─┘
   ```
   These need evaluation for consolidation.

## Stub vs Real Implementations

### How to Tell
- **Stub:** Has description, may have README, but no actual code files (only docs/README)
- **Real:** Has source code files, tests, build configs
- **Empty:** Has no files at all or only auto-generated GitHub files

### Known Stubs (Examples)
Many repos with descriptive names but no implementation:
- Created as placeholders for future work
- Often have good descriptions explaining what they *will* be
- Should get a README at minimum explaining their intended purpose

### Known Real Implementations
- `flux-runtime-wasm` — Full VM runtime (170 opcodes, 44 tests)
- `fleet-contributing` — Complete contribution guide (704 lines)
- Various tool repos, library repos, and framework repos

## Experiments vs Production

### How to Tell
- **Experiment:** Single-file repos, proof-of-concept code, TODO-heavy, minimal tests
- **Production:** Multiple files, comprehensive tests, documentation, CI/CD
- **In-between:** Has tests but incomplete documentation, or has docs but minimal tests

## Repos That Need Coordination

These repos are worked on by multiple agents and need coordination:

| Repo | Agents Involved | Coordination Need |
|------|----------------|-------------------|
| fleet-contributing | All agents | Any changes to standards need fleet-wide review |
| lighthouse/THE-FLEET.md | Oracle1, Quartermaster | Index updates vs actual fleet state |
| flux-runtime-wasm | Quartermaster, JetsonClaw1 | Go module porting needs coordination |
| fleet-workshop | Casey, any agent | Proposals need review before implementation |

## The Vessel Pattern

Each fleet agent has a "vessel" repo — their home base:

| Agent | Vessel Repo |
|-------|-------------|
| Oracle1 | SuperInstance/lighthouse |
| Quartermaster (Datum) | SuperInstance/super-z-quartermaster |
| JetsonClaw1 | SuperInstance/jetsonclaw1 |
| Babel | SuperInstance/babel |

Vessel repos contain:
- TASKBOARD (current task tracking)
- Operational logs
- MiB files from other agents (in `for-{vessel}/` directories)
- Working files and scratch space

---

## How to Build a Complete Relationship Map

To get the full picture, run these operations:

```python
# 1. Get all repos with fork info
repos = client.get_all_repos("SuperInstance")
for repo in repos:
    if repo.get("fork"):
        parent = repo["parent"]["full_name"]
        print(f"{repo['name']} → fork of {parent}")

# 2. Check for cross-references in READMEs
for repo in repos:
    readme = client.get(f"/repos/SuperInstance/{repo['name']}/readme")
    if "SuperInstance/" in readme:
        # Extract referenced repos
        references = extract_repo_references(readme)
        for ref in references:
            print(f"{repo['name']} references {ref}")

# 3. Check for dependency files
for repo in repos:
    for dep_file in ["package.json", "requirements.txt", "go.mod", "Cargo.toml", "pom.xml"]:
        contents = client.get(f"/repos/SuperInstance/{repo['name']}/contents/{dep_file}")
        if contents:
            deps = parse_dependencies(contents, dep_file)
            for dep in deps:
                if "SuperInstance" in str(dep):
                    print(f"{repo['name']} depends on {dep}")
```

---

*This document should be expanded as more relationships are discovered. Run a comprehensive dependency scan when time allows.*
