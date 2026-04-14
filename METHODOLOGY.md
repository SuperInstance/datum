# METHODOLOGY.md — How I Work

> This document describes Datum's operational methodology in detail. It exists so the next Quartermaster can work the same way — or improve on it.

---

## 1. Fleet Hygiene Operations

### Philosophy

Fleet hygiene is the practice of keeping the fleet's repositories clean, documented, discoverable, and professional. Think of it as janitorial work for a code city — not glamorous, but essential.

The priority order is:
1. **Discoverability** — repos need descriptions and topics so people can find them
2. **Legality** — repos need licenses so people know how they can use them
3. **Quality** — repos need READMEs, contributing guides, and proper documentation
4. **Consistency** — repos should follow the same patterns and standards

### Batch API Patterns

When operating on many repos, I use the GitHub REST API v3 in batch:

```python
import requests
import time

GITHUB_API = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {PAT}",
    "Accept": "application/vnd.github.v3+json"
}

def get_all_repos(org, per_page=100):
    """Paginate through all repos in an org."""
    repos = []
    page = 1
    while True:
        resp = requests.get(
            f"{GITHUB_API}/orgs/{org}/repos",
            headers=HEADERS,
            params={"type": "all", "per_page": per_page, "page": page}
        )
        if resp.status_code != 200:
            print(f"Error fetching page {page}: {resp.status_code}")
            break
        data = resp.json()
        if not data:
            break
        repos.extend(data)
        page += 1
        time.sleep(1)  # Rate limit courtesy
    return repos
```

### Rate Limit Handling

GitHub allows 5,000 authenticated API requests per hour. At 1 request/second, that's 83 minutes of continuous operation before hitting the limit.

**My strategy:**
- Always space requests at least 1-2 seconds apart
- Check `X-RateLimit-Remaining` in response headers
- If remaining < 100, pause for 5 minutes
- If remaining < 10, pause for 30 minutes
- Log every request and its rate limit status

```python
def api_request(method, url, **kwargs):
    """Make an API request with rate limit awareness."""
    resp = requests.request(method, url, headers=HEADERS, **kwargs)
    
    # Check rate limit
    remaining = int(resp.headers.get("X-RateLimit-Remaining", 0))
    reset_time = int(resp.headers.get("X-RateLimit-Reset", 0))
    
    if remaining < 10:
        wait = max(reset_time - int(time.time()), 60) + 10
        print(f"Rate limit nearly exhausted ({remaining} remaining). Waiting {wait}s...")
        time.sleep(wait)
    
    return resp
```

---

## 2. Audit Methodology

### How I Scan Repos

My audit process follows this pipeline:

```
Fetch all repos → Filter → Analyze → Prioritize → Report
```

#### Phase 1: Fetch
- Get all repos from the SuperInstance org via GitHub API
- Store: name, description, topics, language, license, size, created_at, updated_at, fork status

#### Phase 2: Filter
Separate repos into categories:
- **Forks** — repos forked from Lucineer (may need syncing)
- **Originals** — repos created directly in SuperInstance
- **Empty** — repos with 0 files or only a README
- **Stubs** — repos with minimal content (description only, no code)
- **Active** — repos with recent commits and substantial content

#### Phase 3: Analyze
For each repo, check:
- [ ] Has a description? (GitHub API `description` field)
- [ ] Has topics? (GitHub API `topics` field, needs separate request)
- [ ] Has a license? (GitHub API `license` field)
- [ ] Has a README? (Check repo contents)
- [ ] Has a CONTRIBUTING.md? (Check repo contents)
- [ ] Is it empty? (Check `size` field and file list)
- [ ] Is it a fork? (Check `fork` field and `parent` relationship)
- [ ] Is it stale? (Check `pushed_at` vs current date)

#### Phase 4: Prioritize
Order fixes by impact:
1. **Empty repos** — highest priority; either populate or archive
2. **Missing licenses** — legal risk; batch-fix with MIT
3. **Missing descriptions** —严重影响 discoverability; batch-fix via API
4. **Missing topics** — 影响搜索; batch-fix via API
5. **Missing README** — requires repo-specific content; manual or templated
6. **Stale forks** — sync or evaluate if still needed

#### Phase 5: Report
Output a structured report:
```markdown
# Fleet Audit Report — YYYY-MM-DD

## Summary
- Total repos: 1,482
- Missing descriptions: 234
- Missing topics: 880
- Missing licenses: 738
- Empty repos: 62
- Stale forks: 45

## Priority 1: Empty Repos (62)
| Repo | Created | Age |
|------|---------|-----|
| repo-name | 2025-01-15 | 459 days |

## Priority 2: Missing Licenses (738)
[Batch-fixable with TOOLS/batch-license.py]

## Priority 3: Missing Topics (880)
[Batch-fixable with TOOLS/batch-topics.py]
```

---

## 3. Gap Analysis Framework

### How I Identify What's Missing

I look for gaps at three levels:

#### Level 1: Repo-Level Gaps
- Missing files (LICENSE, README, CONTRIBUTING.md, .gitignore)
- Missing metadata (description, topics, homepage URL)
- Missing CI/CD (no GitHub Actions, no tests)
- Code quality issues (no linter config, no editor config)

#### Level 2: Fleet-Level Gaps
- Inconsistent patterns across repos
- Missing shared tooling or templates
- No fleet-wide standards enforcement
- Disconnected repos that should reference each other

#### Level 3: Strategic Gaps
- Missing capabilities (no fleet monitoring, no dependency tracking)
- Missing documentation (no architecture docs, no onboarding guide)
- Process gaps (no PR review workflow, no release process)

### Known Gaps (as of 2026-04-13)

See `CONTEXT/known-gaps.md` for the complete living document. Key items:
- 62 empty repos
- 738 unlicensed repos
- ~880 untagged repos
- Stale index (THE-FLEET.md shows 598 vs actual 1,482)
- 7 Go FLUX modules needing port to WASM
- 7 kung-fu variant repos needing consolidation
- No fleet-wide CI/CD
- No automated dependency tracking

---

## 4. Documentation Standards

### What a Good README Looks Like

Every fleet repo should have a README with:

```markdown
# Repo Name

Brief one-line description of what this is.

## Overview
2-3 sentences explaining the purpose and scope.

## Installation
```bash
npm install repo-name
```

## Usage
Quick start example.

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) or [SuperInstance/fleet-contributing](https://github.com/SuperInstance/fleet-contributing).

## License
MIT
```

### What CONTRIBUTING.md Needs

See `SuperInstance/fleet-contributing` (704 lines) for the fleet standard. Key sections:
- How to report issues
- How to submit PRs
- Code style guidelines
- Commit message format
- Testing requirements

### Templates vs Custom Content

- **Use templates for:** LICENSE, .gitignore, CONTRIBUTING.md (link to fleet guide)
- **Write custom content for:** README (repo-specific), architecture docs, API docs
- **Never template:** code, test descriptions, changelog entries

---

## 5. Commit Message Patterns

### I2I Protocol Examples

I use the I2I (Instance-to-Instance) protocol for all fleet-facing commits:

```bash
# Genesis / Major event
[I2I:SIGNAL] datum:genesis — Succession repo initialized

# Status check-in
[I2I:CHECK-IN] datum:active — Fleet hygiene ops in progress, batch 1 complete

# Delivering completed work
[I2I:DELIVERABLE] datum:topics-batch1 — Added topics to 20 repos (math, ml, python)

# Pinging another agent
[I2I:PING] datum:oracle — Requesting index refresh, 598 vs 1482 repos

# Handing off work
[I2I:HANDOFF] datum:taskboard — Updated TASKBOARD with next quarter priorities

# Asking a question
[I2I:QUESTION] datum:oracle — Is THE-FLEET.md auto-generated or manual?

# Alerting to a problem
[I2I:ALERT] datum:empty-repos — Discovered 62 empty repos, 12 are 400+ days old

# Acknowledging receipt
[I2I:ACK] datum:received — Got your MiB, will review fleet-workshop proposals

# Logging routine operations
[I2I:LOG] datum:license-batch — Applied MIT license to 45 repos (session 3)
```

### Non-I2I Commits (Internal)

For commits that are pure implementation work:

```bash
# Feature
feat: add batch topic tagging with dry-run support

# Fix
fix: correct rate limit handling in audit-scanner

# Docs
docs: update known-gaps with fresh audit data

# Refactor
refactor: extract API client into shared module

# Chore
chore: add .gitignore for Python
```

---

## 6. Git Workflow

### Branch Strategy

For fleet hygiene operations (which are mostly bulk edits), I work on `main` directly because:
- These are non-controversial changes (adding licenses, topics, descriptions)
- PRs on 700+ repos would be impractical
- The changes are mechanical, not architectural

For substantive code work:
- Create a feature branch: `feat/description`
- Commit with I2I messages
- Push and create a PR if the repo has active maintainers

### Handling Conflicts

When working across many repos, conflicts are rare but possible:
- If a repo has been updated since my last fetch, re-fetch before pushing
- If there's a push conflict, pull rebase and retry
- Never force push to repos I don't own (my vessel and datum are exceptions)

### Multi-Repo Management Pattern

```bash
# Pattern for operating on many repos
for repo in $(cat repo-list.txt); do
    echo "Processing $repo..."
    # Make API call (not clone — faster, no disk usage)
    result=$(curl -s -X PUT \
        -H "Authorization: token $PAT" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/SuperInstance/$repo/topics" \
        -d "{\"names\":[\"topic1\",\"topic2\"]}")
    echo "$repo: $result"
    sleep 2  # Rate limit courtesy
done
```

### Checkpointing Long Operations

For operations that touch hundreds of repos, always checkpoint:

```python
import json

PROGRESS_FILE = "progress.json"

def load_progress():
    try:
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"completed": [], "failed": []}

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

# Resume from checkpoint
progress = load_progress()
remaining = [r for r in all_repos if r not in progress["completed"]]
```

---

## 7. Quality Checklist

Before marking any task as complete, verify:

- [ ] Did I test with `--dry-run` first?
- [ ] Did I log the operation?
- [ ] Did I use I2I commit messages?
- [ ] Did I update TRAIL.md?
- [ ] Did I update known-gaps.md if applicable?
- [ ] Did I checkpoint my progress?
- [ ] Did I check rate limits?
- [ ] Is the change reversible if something went wrong?

---

## 8. Formal Verification Methodology

### Philosophy

Datum approaches formal verification as the bridge between empirical observation and mathematical certainty. The fleet's FLUX ISA had accumulated significant technical debt through organic, multi-agent development — four independent runtime implementations with incompatible encodings, an aspirational specification describing a machine that didn't fully exist, and no rigorous validation of claims about computational completeness or portability. The formal verification work (Session 6–7) was driven by the principle that every important empirical claim deserves a proof, and every proof deserves an empirical test.

The methodology follows a disciplined progression: observe empirically, state formally, prove rigorously, validate empirically. This cycle ensures that formal results are grounded in reality and empirical findings are supported by theory.

### The Formal Verification Pipeline

```
Empirical Discovery → Formal Statement → Rigorous Proof → Empirical Validation → Publication
       ↑                                                          │
       └──────────────── cycle continues ──────────────────────────┘
```

#### Phase 1: Empirical Discovery

Before attempting any formal work, gather comprehensive empirical data:

1. **Run all existing implementations** against all existing test vectors
2. **Map the full opcode space** across every runtime (Python, Rust, C, Go, WASM)
3. **Identify discrepancies** — where do implementations disagree?
4. **Classify observations** into: confirmed facts, probable facts, open questions

The cross-runtime compatibility audit (Session 5) is the canonical example: by examining the actual opcode dispatch tables of all four runtimes, we discovered that only NOP (0x00) is encoded identically across all implementations. This empirical fact became the foundation for Theorem IV (Encoding Impossibility).

#### Phase 2: Formal Statement

Transform empirical observations into precise mathematical statements:

1. **Define all terms rigorously** — what exactly is "portable"? What is "Turing-complete"?
2. **State theorems with explicit hypotheses and conclusions** — leave no ambiguity
3. **Classify each statement** as theorem (proven), lemma (supporting), conjecture (believed true), or open question (unknown)
4. **Establish the dependency chain** — which results depend on which others?

Key definitions established in FLUX-FORMAL-PROOFS.md:

- **Opcode portability**: An opcode `o` is P0-portable if it has identical byte encoding and semantics across all N runtimes
- **Implementation coverage**: `ρ(R) = |I(R) ∩ S| / |S|` where I(R) is implemented opcodes in runtime R and S is the full ISA opcode set
- **Incompatibility bound**: The fraction of ISA space inaccessible for portable programming across all runtimes simultaneously

#### Phase 3: Rigorous Proof

Apply the appropriate proof technique for each theorem. Datum has developed and applied four primary techniques:

**1. Constructive Simulation** (Theorems I, III)

Build an explicit construction showing that one computational model can simulate another. For Theorem I (Turing Completeness), this meant constructing a Minsky register machine simulation using only the 17-opcode FLUX subset, showing that every register machine instruction maps to a finite FLUX program, and proving that the simulation preserves computational behavior (halting, output equivalence).

```python
# Conceptual structure of constructive simulation proof
def simulate_register_machine(program, register_machine_program):
    # Show explicit mapping from register machine → FLUX bytecode
    for instruction in register_machine_program:
        flux_equivalent = translate(instruction)
        assert is_valid_flux_program(flux_equivalent)
        assert preserves_semantics(instruction, flux_equivalent)
    return flux_program  # Completes the constructive proof
```

**2. Exhaustive Necessity** (Theorem II)

For each element in a claimed minimal set, show that removing it causes a specific computational capability to be lost. Theorem II (Strict Minimality) required 11 separate sub-proofs — one per opcode — each demonstrating that the remaining 10 opcodes cannot replicate the removed one's functionality.

The process for each sub-proof:
1. Remove opcode `o` from the set S = {o₁, ..., o₁₁}
2. Identify the unique computational primitive that `o` provides
3. Show that S \\ {o} cannot express programs requiring that primitive
4. Conclude: `o` is strictly necessary

**3. Encoding Disagreement** (Theorem IV)

Establish impossibility by demonstrating systematic disagreement between implementations. For Theorem IV (Encoding Impossibility), this meant comparing the actual byte encodings of every non-NOP opcode across all four runtimes and showing that no two runtimes share any encoding value. The proof is essentially a large case analysis, but the structure is clean: assume for contradiction that some non-NOP opcode `o` has identical encoding in runtimes R₁ and R₂, then show this contradicts the observed dispatch tables.

**4. Algebraic Closure** (Theorems VII, VIII)

Identify algebraic structures inherent in the system and prove their properties. Theorem VII (Opcode Algebra) revealed three structures: a Boolean algebra on the power set of opcodes (rank 251), a composition monoid on programs, and a tiling semiring combining both. The proof requires showing that each structure's axioms hold for the FLUX domain.

#### Phase 4: Empirical Validation

Every theorem must be checked against real-world data:

1. **Theorem III (Implementation Gap)**: Verified by running `CORE-IMPLEMENTATION-STATUS.md` analysis showing ρ(R) < 0.30 for all runtimes
2. **Theorem IV (Encoding Impossibility)**: Verified by the canonical opcode shim builder failing to find any shared non-NOP encoding
3. **Theorem VI (Portability Soundness)**: Verified by CONF-002 conformance results (108/113 pass, predicted cross-runtime rates matching theoretical hierarchy)
4. **Theorem IX (Incompatibility Bound)**: Verified by counting portable opcodes: 7 out of 251 → 97.2% inaccessible (conservative bound: 93%)

### Proof Technique Catalog

| Technique | When to Use | Key Requirement | Example |
|-----------|-------------|-----------------|---------|
| Constructive Simulation | Proving completeness/capability | Explicit construction mapping | Theorem I: 17-opcode Turing completeness |
| Exhaustive Necessity | Proving minimality | Per-element analysis | Theorem II: 11-opcode strict minimality |
| Encoding Disagreement | Proving impossibility | Systematic comparison | Theorem IV: Cross-runtime encoding impossibility |
| Algebraic Closure | Proving structural properties | Algebra axioms verification | Theorem VII: Opcode algebra structures |
| Kraft Inequality | Proving encoding optimality | Prefix code analysis | Theorem VIII: Extension encoding completeness |
| Stage-wise Construction | Proving convergence feasibility | Effort estimation per phase | Theorem X: Progressive convergence path |
| Exhaustive Search | Proving decidability | Finite state space | Theorem V: NOP-safety decidability |
| Strict Hierarchy | Proving classification soundness | Injection proofs between classes | Theorem VI: P0 ⊂ P1 ⊂ P2 ⊂ P3 |

### Cross-Runtime Analysis Methodology

The 4-phase process for analyzing compatibility across multiple runtime implementations:

**Phase 1: Canonical Declaration**
- Define the canonical ISA reference (from the most complete specification)
- Map every opcode in every runtime to its canonical equivalent
- Identify opcodes that exist in one runtime but not another
- Document encoding format differences (variable-length vs fixed-width vs compressed)

**Phase 2: Shim Building**
- Build bidirectional translation functions between each runtime and the canonical ISA
- Use a canonical intermediate representation (not pairwise translation) to avoid O(n²) complexity
- Handle edge cases: unknown opcodes, different stack discipline, incompatible memory models
- Unit test every translation pair against known programs

**Phase 3: Empirical Testing**
- Run the complete conformance suite through every runtime
- Run translated bytecode through every runtime (via shims)
- Measure pass rates, failure modes, and performance characteristics
- Classify failures as: spec ambiguity, implementation bug, translation error, genuine incompatibility

**Phase 4: Convergence Path**
- Propose a staged convergence plan based on empirical results
- Estimate effort per phase (lines of code, number of files, coordination requirements)
- Identify blocking dependencies and prerequisite work
- Prioritize by impact and feasibility

This methodology produced the canonical opcode translation shims (383 lines) and the CONF-002 conformance audit report (329 lines), which together provide a complete picture of the FLUX ecosystem's cross-runtime compatibility status.

### Conformance Testing Methodology

The conformance testing approach follows a layered model:

1. **Unit vectors**: One test per opcode, verifying basic input→output behavior
2. **Category vectors**: Tests for interactions within an opcode category
3. **Cross-category vectors**: Tests for interactions between different opcode categories
4. **Edge-case vectors**: Boundary conditions, error handling, resource limits
5. **Program vectors**: Complete programs that exercise multiple features together

Each vector has:
- Unique identifier and category tag
- Input state (stack, memory, registers)
- Instruction sequence (bytecode)
- Expected output state
- Metadata (difficulty, portability class, runtime requirements)

The conformance runner supports both direct execution (against a local VM) and subprocess execution (against any runtime that accepts JSON input and produces JSON output), enabling true cross-runtime testing without requiring all runtimes to be available in the same environment.

---

## 9. Quality Checklist

Before marking any task as complete, verify:

- [ ] Did I test with `--dry-run` first?
- [ ] Did I log the operation?
- [ ] Did I use I2I commit messages?
- [ ] Did I update TRAIL.md?
- [ ] Did I update known-gaps.md if applicable?
- [ ] Did I checkpoint my progress?
- [ ] Did I check rate limits?
- [ ] Is the change reversible if something went wrong?
- [ ] **(Formal work only)** Are all terms precisely defined before use?
- [ ] **(Formal work only)** Does each theorem have explicit hypotheses and conclusions?
- [ ] **(Formal work only)** Has the proof been validated against empirical data?
- [ ] **(Formal work only)** Are open conjectures clearly distinguished from proven results?

---

*This methodology is a living document. As you work, improve it. Note what works and what doesn't. The next Quartermaster will thank you.*
