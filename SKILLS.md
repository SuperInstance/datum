# SKILLS.md — Technical Capabilities

> A detailed inventory of what Datum can do. The next Quartermaster inherits all of these.

---

## Skill Summary

| Skill | Proficiency | Primary Use |
|-------|-------------|-------------|
| Python | ★★★★★ | Automation, batch GitHub API, data analysis |
| Bash | ★★★★☆ | CI/CD, system admin, batch shell operations |
| Git | ★★★★★ | Multi-repo management, I2I protocol |
| GitHub API | ★★★★★ | Repo management, topics, licenses, batch ops |
| TypeScript/JS | ★★★☆☆ | Node.js tools, web development |
| Documentation | ★★★★★ | README, guides, specs, audit reports |
| Data Analysis | ★★★☆☆ | Fleet metrics, gap identification |
| Web Scraping | ★★★☆☆ | Content extraction, data gathering |
| Formal Methods | ★★★★☆ | Mathematical proofs, theorem stating, constructive verification |
| FLUX ISA Architecture | ★★★★★ | Opcode design, encoding formats, extension mechanisms, security/temporal primitives |
| Cross-Runtime Analysis | ★★★★☆ | Multi-implementation comparison, portability classification, encoding translation |
| Specification Writing | ★★★★★ | ISA specs, conformance test suites, audit reports, formal proof documents |

---

## 1. Python

**Proficiency:** ★★★★★ (Expert)
**Primary Use:** Automation scripts, batch GitHub API operations, data analysis

### What I Can Do
- Write production-ready CLI tools with argparse
- Batch operations on GitHub API (repos, topics, licenses, contents)
- Data processing and analysis (JSON, CSV, pandas-like operations without pandas)
- File generation (markdown, JSON, reports)
- Error handling and retry logic
- Rate limit management
- Progress tracking and checkpointing

### Tools & Libraries
- `requests` — HTTP client for GitHub API
- `json` — Data serialization
- `argparse` — CLI argument parsing
- `time` / `datetime` — Rate limiting and timestamps
- `os` / `pathlib` — File operations
- `subprocess` — Running shell commands
- `csv` — CSV file handling
- `re` — Regular expressions

### Example: Batch GitHub API Client

```python
#!/usr/bin/env python3
"""Reusable GitHub API client with rate limiting and error handling."""

import requests
import time
import json
from typing import Optional, Dict, Any, List

class GitHubClient:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "datum-quartermaster/1.0"
        })
        self.base_url = "https://api.github.com"
        self.request_count = 0
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request with rate limit handling."""
        while True:
            resp = self.session.get(f"{self.base_url}{endpoint}", params=params)
            self.request_count += 1
            
            if resp.status_code == 200:
                remaining = int(resp.headers.get("X-RateLimit-Remaining", 5000))
                if remaining < 100:
                    reset = int(resp.headers.get("X-RateLimit-Reset", 0))
                    wait = max(reset - int(time.time()), 60) + 5
                    print(f"[RATE LIMIT] {remaining} remaining, waiting {wait}s")
                    time.sleep(wait)
                return resp.json()
            
            elif resp.status_code == 403:
                # Rate limited
                reset = int(resp.headers.get("X-RateLimit-Reset", 0))
                wait = max(reset - int(time.time()), 60) + 5
                print(f"[BLOCKED] Rate limited, waiting {wait}s")
                time.sleep(wait)
            else:
                print(f"[ERROR] {resp.status_code}: {resp.text}")
                return {"error": resp.status_code, "message": resp.text}
    
    def put(self, endpoint: str, data: Dict) -> Dict[str, Any]:
        """Make a PUT request."""
        time.sleep(1.5)  # Courtesy delay
        resp = self.session.put(f"{self.base_url}{endpoint}", json=data)
        self.request_count += 1
        time.sleep(0.5)  # Post-request delay
        return resp.json() if resp.status_code in (200, 201) else {"error": resp.status_code}
    
    def post(self, endpoint: str, data: Dict) -> Dict[str, Any]:
        """Make a POST request."""
        time.sleep(1.5)
        resp = self.session.post(f"{self.base_url}{endpoint}", json=data)
        self.request_count += 1
        time.sleep(0.5)
        return resp.json() if resp.status_code in (200, 201) else {"error": resp.status_code}
    
    def get_all_pages(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict]:
        """Paginate through all results."""
        results = []
        page = 1
        while True:
            p = {**(params or {}), "page": page, "per_page": 100}
            data = self.get(endpoint, params=p)
            if isinstance(data, dict) and "error" in data:
                break
            if not data:
                break
            results.extend(data)
            if len(data) < 100:
                break
            page += 1
            time.sleep(1)
        return results
    
    def get_all_repos(self, org: str) -> List[Dict]:
        """Get all repos for an organization."""
        return self.get_all_pages(f"/orgs/{org}/repos", params={"type": "all"})
```

### What I'm Bad At
- Computer vision / image processing (no OpenCV/PIL in typical environment)
- Heavy ML training (no GPU access)
- GUI applications (no tkinter/qt available)

---

## 2. Bash / Shell

**Proficiency:** ★★★★☆ (Advanced)
**Primary Use:** CI/CD, system administration, batch operations, one-liners

### What I Can Do
- Complex shell pipelines with pipes and redirections
- Batch file operations (find, rename, chmod)
- Git operations from CLI (commit, push, branch, rebase)
- curl for API testing
- Process management (background jobs, signals)
- Environment variable management
- Shell scripting (variables, conditionals, loops, functions)

### Example: Batch Topic Addition via Bash

```bash
#!/bin/bash
# Batch add topics to repos from a mapping file
# Usage: ./batch-topics.sh mapping.csv $GITHUB_TOKEN

TOKEN="$2"
ORG="SuperInstance"

while IFS=, read -r repo topics; do
    [ -z "$repo" ] && continue
    echo "Tagging $repo with: $topics"
    
    # Convert comma-separated to JSON array
    topics_json=$(echo "$topics" | sed 's/,/","/g' | sed 's/^/["/;s/$/"]/')
    
    result=$(curl -s -X PUT \
        -H "Authorization: token $TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$ORG/$repo/topics" \
        -d "{\"names\":$topics_json}")
    
    echo "  Result: $(echo "$result" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("message","ok"))' 2>/dev/null || echo "$result")"
    sleep 2
done < "$1"
```

### What I'm Bad At
- Complex awk/gawk programs (I can use simple awk but not advanced)
- Binary file manipulation
- Low-level system programming (no C compilation)

---

## 3. Git

**Proficiency:** ★★★★★ (Expert)
**Primary Use:** Multi-repo management, I2I protocol, version control

### What I Can Do
- Initialize repos, create commits, push to remote
- Branch management (create, switch, merge, rebase, delete)
- Conflict resolution
- Commit message formatting (I2I protocol)
- Working with multiple remotes
- Cherry-picking, rebasing, bisecting
- Tag management
- Submodule handling (basic)
- Force push (only on repos I own — my vessel and datum)

### I2I Commit Pattern

```bash
# My standard I2I commit workflow
git add .
git commit -m "[I2I:DELIVERABLE] datum:topics-batch2 — Tagged 30 repos with language topics"
git push origin main
```

### Multi-Repo Operations

```bash
# Clone and operate on multiple repos
for repo in repo1 repo2 repo3; do
    git clone "https://$PAT@github.com/SuperInstance/$repo.git" "/tmp/work/$repo"
    cd "/tmp/work/$repo"
    # Make changes
    git add .
    git commit -m "[I2I:DELIVERABLE] datum:license — Added MIT LICENSE"
    git push origin main
    cd -
done
```

### What I'm Bad At
- Git hooks (can write them but can't easily test in this environment)
- Complex rebase scenarios with many conflicts

---

## 4. GitHub API

**Proficiency:** ★★★★★ (Expert)
**Primary Use:** Repository management, batch operations, automation

### What I Can Do

#### Repositories
```python
# Create a repo
client.post("/user/repos", {
    "name": "new-repo",
    "description": "Description here",
    "private": False,
    "has_issues": True,
    "has_projects": True
})

# Update repo description
client.patch(f"/repos/{org}/{repo}", {
    "description": "New description",
    "homepage": "https://example.com"
})

# List all repos in an org
repos = client.get_all_repos("SuperInstance")
```

#### Topics
```python
# Add topics to a repo
client.put(f"/repos/{org}/{repo}/topics", {
    "names": ["python", "machine-learning", "data-analysis"]
})

# Get topics for a repo
topics = client.get(f"/repos/{org}/{repo}/topics")
```

#### Contents (File Operations via API)
```python
# Create a file via API (no local clone needed)
import base64

content = base64.b64encode(b"MIT License content here").decode()
client.put(f"/repos/{org}/{repo}/contents/LICENSE", {
    "message": "[I2I:DELIVERABLE] datum:license — Add MIT LICENSE",
    "content": content,
    "branch": "main"
})
```

#### License
```python
# Get repo license info
license_info = client.get(f"/repos/{org}/{repo}/license")

# List repos without licenses
unlicensed = [r for r in repos if r.get("license") is None]
```

### API Rate Limits

| Limit | Authenticated | Notes |
|-------|--------------|-------|
| Requests/hour | 5,000 | Resets at the top of each hour |
| Search API | 30/min | Much lower than regular API |
| Topics (PUT) | Not separately limited | Uses general request budget |

### What I'm Bad At
- GraphQL API (I know REST, not GraphQL)
- GitHub Actions API (can create workflows but advanced config is tricky)
- GitHub Packages API

---

## 5. TypeScript / JavaScript

**Proficiency:** ★★★☆☆ (Intermediate)
**Primary Use:** Node.js tools, web development, Next.js

### What I Can Do
- Write Node.js scripts for automation
- Build React/Next.js components
- Use npm/yarn for package management
- Work with TypeScript types and interfaces
- Fetch API, async/await patterns
- Basic testing with Jest or Vitest

### Example: GitHub API in Node.js

```typescript
const GITHUB_API = "https://api.github.com";

async function getRepos(org: string, token: string): Promise<any[]> {
    const repos: any[] = [];
    let page = 1;
    
    while (true) {
        const resp = await fetch(
            `${GITHUB_API}/orgs/${org}/repos?type=all&per_page=100&page=${page}`,
            {
                headers: {
                    "Authorization": `token ${token}`,
                    "Accept": "application/vnd.github.v3+json"
                }
            }
        );
        
        const data = await resp.json();
        if (!data.length) break;
        repos.push(...data);
        page++;
        
        // Rate limit courtesy
        await new Promise(r => setTimeout(r, 1000));
    }
    
    return repos;
}
```

### What I'm Bad At
- Complex state management (Redux, Zustand)
- Advanced CSS/animation
- Performance optimization (webpack config, tree shaking)
- Database ORMs (Prisma, TypeORM)

---

## 6. Documentation

**Proficiency:** ★★★★★ (Expert)
**Primary Use:** README files, guides, specifications, audit reports

### What I Can Do
- Write clear, structured technical documentation
- Create comprehensive README files with installation, usage, examples
- Write contributing guides
- Produce audit reports with tables and metrics
- Create architectural documentation
- Write API documentation
- Format complex markdown (tables, code blocks, nested lists)

### Documentation Format Standards

#### README Template
```markdown
# Project Name

> One-line tagline

## Overview
What it is, why it exists, who it's for.

## Installation
```bash
command here
```

## Usage
Example with code.

## Configuration
How to configure it.

## Contributing
Link to fleet contributing guide.

## License
MIT
```

#### Audit Report Format
```markdown
# Audit Report — [DATE]

## Executive Summary
2-3 bullet points.

## Methodology
How the audit was conducted.

## Findings

### Category 1: Missing Descriptions
| Repo | Status | Priority |
|------|--------|----------|
| ...  | ...    | ...      |

## Recommendations
Prioritized action items.
```

### Specialized Formats
- **PDF generation** — Can create PDF reports using docx/pdf skill
- **DOCX generation** — Can create Word documents
- **XLSX generation** — Can create Excel spreadsheets with data and charts

### What I'm Bad At
- Graphic design / visual layout
- Video tutorials
- Interactive documentation (Storybook, Docusaurus config)

---

## 7. Analysis & Metrics

**Proficiency:** ★★★☆☆ (Intermediate)
**Primary Use:** Fleet metrics, gap identification, dependency mapping

### What I Can Do
- Process JSON data from GitHub API
- Generate summary statistics (counts, averages, distributions)
- Identify patterns across repos
- Create dependency maps (manual, not automated)
- Prioritize issues by impact and effort
- Track trends over time (with historical data)

### Fleet Metrics I Track

| Metric | Current Value | Source |
|--------|--------------|--------|
| Total repos | ~1,482 | GitHub API |
| Repos with descriptions | ~1,248 | GitHub API |
| Repos with topics | ~602 | GitHub API |
| Repos with licenses | ~744 | GitHub API |
| Empty repos | 62 | GitHub API |
| Fork repos | ~580 | GitHub API |
| Index coverage | 598 / 1,482 | THE-FLEET.md |

### What I'm Bad At
- Statistical analysis (hypothesis testing, regression)
- Machine learning (can't train models)
- Visualization (can describe charts but can't render them directly — need xlsx/pdf skill)

---

## 9. Formal Methods

**Proficiency:** ★★★★☆ (Advanced)
**Primary Use:** Mathematical proofs of ISA properties, formal verification of computational claims

### What I Can Do
- State precise mathematical theorems with explicit hypotheses and conclusions
- Construct rigorous proofs using multiple techniques (constructive simulation, exhaustive necessity, encoding disagreement, algebraic closure)
- Define formal semantics for instruction sets (operational semantics, stack discipline, memory safety)
- Prove computational completeness via register machine simulation
- Prove minimality via exhaustive per-element necessity analysis
- Identify and classify algebraic structures (Boolean algebras, monoids, semirings)
- Connect formal results to empirical observations (validate theorems against real data)
- Write formal proof documents in structured mathematical prose with corollary chains

### Proof Techniques Mastered

| Technique | Application | Example |
|-----------|-------------|---------|
| Constructive Simulation | Turing completeness proofs | Theorem I: 17-opcode FLUX is Turing-complete |
| Exhaustive Necessity | Minimality proofs | Theorem II: 11 opcodes are strictly minimal |
| Encoding Disagreement | Impossibility proofs | Theorem IV: No non-NOP opcode portable across runtimes |
| Algebraic Closure | Structural properties | Theorem VII: Boolean algebra, composition monoid, tiling semiring |
| Kraft Inequality | Encoding optimality | Theorem VIII: Extension encoding completeness |
| Stage-wise Construction | Feasibility proofs | Theorem X: 4-stage path to full compatibility |

### Key Results Produced
- 10 formally-stated theorems in FLUX-FORMAL-PROOFS.md (847 lines, 54.6KB)
- 5 open conjectures for future work
- Complete corollary dependency chain
- Formal definitions for: opcode portability (P0-P3), implementation coverage (ρ), incompatibility bound

### What I'm Bad At
- Mechanized/formal proof assistants (Coq, Lean, Isabelle) — I write proofs in mathematical prose
- Automated theorem proving — I rely on manual construction
- Higher-order logic and type theory proofs beyond the level needed for ISA analysis

---

## 10. FLUX ISA Architecture

**Proficiency:** ★★★★★ (Expert)
**Primary Use:** ISA specification design, opcode taxonomy, encoding format engineering, extension mechanism design

### What I Can Do
- Design complete instruction set architectures from scratch
- Define encoding formats (variable-length, fixed-width, compressed, escape-prefix)
- Design extension mechanisms with capability negotiation
- Classify opcodes into hierarchical taxonomies (category → subcategory → opcode)
- Analyze opcode interactions and dependencies
- Define execution semantics (operational, denotational, axiomatic)
- Design security primitives (capability invocation, sandboxing, memory tagging)
- Design temporal primitives for agent-oriented computing (fuel checks, deadlines, yields)
- Create portability classifications for cross-runtime compatibility

### FLUX ISA Expertise
- Authored ISA v3 comprehensive spec (829 lines, 310+ opcodes, 7 encoding formats)
- Designed 0xFF escape prefix extension mechanism (65,280 extension slots)
- Designed compressed instruction format (32 short-form opcodes, 25-35% code size reduction)
- Specified 18 extension opcodes: 6 temporal, 6 security, 6 async
- Proved 17-opcode Turing-completeness and 11-opcode strict minimality
- Mapped all 251 opcodes across 5 runtimes with portability classification
- Identified 7 universally portable opcodes across all runtimes

### What I'm Bad At
- Hardware-level ISA design (pipelining, branch prediction, cache coherence)
- Binary encoding optimization beyond Kraft inequality analysis
- JIT compilation and dynamic code generation strategies

---

## 11. Cross-Runtime Analysis

**Proficiency:** ★★★★☆ (Advanced)
**Primary Use:** Multi-implementation comparison, portability classification, bytecode translation

### What I Can Do
- Compare multiple implementations of the same specification systematically
- Build bidirectional bytecode translation shims between runtimes
- Classify opcode portability (P0: universal, P1: common, P2: partial, P3: unique)
- Create unified dispatch tables comparing runtime implementations
- Run conformance suites against multiple runtimes
- Predict cross-runtime pass rates based on portability classification
- Design convergence strategies for incompatible implementations
- Estimate effort for runtime unification (lines of code, coordination requirements)

### Cross-Runtime Results
- Audited 4 runtimes: Python (49 opcodes), Rust (65 opcodes), C (45 opcodes), Go (29 opcodes)
- Built canonical opcode translation shims (383 lines, 12 translation pairs)
- Proved encoding impossibility: only NOP portable across all runtimes
- Predicted and validated cross-runtime conformance rates: WASM ~66%, Rust ~40%, C ~27%, Go ~20%
- Defined 4-phase convergence methodology (Theorem X)

### What I'm Bad At
- Runtime performance benchmarking (no access to physical hardware)
- Dynamic analysis and profiling tools
- Memory model formalization across different hardware architectures

---

## 12. Specification Writing

**Proficiency:** ★★★★★ (Expert)
**Primary Use:** ISA specifications, conformance test suites, audit reports, formal proof documents

### What I Can Do
- Write comprehensive technical specifications with precise definitions
- Design conformance test suites with structured test vectors (JSON format)
- Produce detailed audit reports with tables, metrics, and prioritized recommendations
- Write formal proof documents in structured mathematical prose
- Create cross-reference tables mapping specifications to implementations
- Write ontology documents classifying technical domains
- Produce execution semantics documents with formal operational rules
- Create "real programs" collections demonstrating specification capabilities

### Specification Documents Produced

| Document | Type | Size |
|----------|------|------|
| FLUX-FORMAL-PROOFS | Formal proofs (10 theorems) | 54.6KB |
| FLUX-IRREDUCIBLE-CORE | Minimal ISA analysis | 58.8KB |
| FLUX-EXECUTION-SEMANTICS | Formal execution model | 31.2KB |
| ISA v3 Comprehensive Spec | ISA specification | 41.5KB |
| Cross-Runtime Compatibility Audit | Technical audit | 25KB |
| FLUX-OPCODE-ONTOLOGY | Taxonomy/classification | 25.6KB |
| Cross-Runtime Conformance Audit | Conformance report | 14.4KB |
| OPCODE-WIRING-AUDIT | Implementation audit | 19.4KB |

### What I'm Bad At
- Standards body specification format (IEEE, ISO, IETF RFC style)
- Formal specification languages (Z, TLA+, Alloy)
- Automated specification testing frameworks (e.g., QuickCheck property-based testing)

---

## 8. Soft Skills (Agent Skills)

These aren't technical skills, but they're critical for fleet operations:

### Communication
- Clear, concise commit messages
- Structured documentation
- I2I protocol adherence
- MiB messages for async communication

### Prioritization
- Impact vs effort analysis
- Triage of issues (critical, high, medium, low)
- Dependency-aware scheduling (what blocks what)

### Self-Awareness
- Knowing when to ask for help (Oracle1, Casey)
- Knowing when to escalate (ALERT type I2I)
- Knowing limitations (I can't do X, Y needs human input)

### Persistence
- Checkpointing long operations
- Resuming after interruption
- Working through rate limits patiently

---

*The next Quartermaster should read this, identify gaps in their own skills, and either improve or document workarounds. A Quartermaster who knows their weaknesses is more effective than one who doesn't.*
