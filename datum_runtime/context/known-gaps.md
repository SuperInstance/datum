# Known Fleet Gaps — Living Document

> Every gap identified in the SuperInstance fleet. Updated as audits are completed. As gaps are resolved, move them to the "Resolved" section at the bottom.

---

## Last Updated: 2026-04-13 (Genesis Audit)

---

## Critical Gaps

### GAP-001: Empty Repos (~62)
- **Priority:** Critical
- **Status:** Identified, not actioned
- **Scope:** ~62 repos
- **Current State:** Repos with zero or near-zero content, some 400+ days old
- **Desired State:** Every repo has at minimum a README explaining its purpose
- **Action:** Evaluate each — populate with content, add README, or archive if not needed
- **Tool:** Manual evaluation required
- **Notes:** Empty repos waste discoverability and confuse fleet visitors

### GAP-002: Missing Licenses (~738)
- **Priority:** Critical (legal risk)
- **Status:** Tool ready, not executed at scale
- **Scope:** ~738 repos
- **Current State:** No LICENSE file; `repo.license` is null in API
- **Desired State:** All repos have MIT LICENSE
- **Action:** Batch-add MIT LICENSE to all unlicensed repos
- **Tool:** `python -m datum_runtime.tools.batch_license --org SuperInstance --token $PAT --dry-run`
- **Notes:** Some repos may intentionally not have licenses (private, special status). Check before batch-applying.

### GAP-003: Stale Fleet Index (598 vs ~1,482)
- **Priority:** High
- **Status:** Identified, needs Oracle1 attention
- **Scope:** 884 repos invisible in fleet index
- **Current State:** THE-FLEET.md shows 598 repos; actual count is ~1,482
- **Desired State:** Complete fleet index
- **Action:** Notify Oracle1 via MiB that the index needs regeneration
- **Tool:** `mib-bottle` tool to contact Oracle1
- **Notes:** Likely an API pagination or rate limit issue in Oracle1's generator

---

## High Priority Gaps

### GAP-004: Missing Topics (~880)
- **Priority:** High
- **Status:** 20 repos tagged, ~860 remaining
- **Scope:** ~880 repos
- **Current State:** No topics assigned; repos don't appear in GitHub search
- **Desired State:** All repos have relevant language, domain, and type topics
- **Action:** Build comprehensive mapping file → batch-apply with checkpointing
- **Tool:** `python -m datum_runtime.tools.batch_topics --input mapping.json --token $PAT --checkpoint`
- **Topics strategy:**
  - Language: `python`, `javascript`, `typescript`, `go`, `rust`, `c`
  - Domain: `machine-learning`, `data-analysis`, `web`, `api`, `cli`, `devops`
  - Type: `library`, `tool`, `framework`, `template`, `documentation`
  - Fleet: `superinstance`, `fleet`, `glm`

### GAP-005: Missing Descriptions (~234)
- **Priority:** High
- **Status:** Identified, not actioned
- **Scope:** ~234 repos
- **Current State:** `repo.description` is null
- **Desired State:** All repos have meaningful descriptions
- **Action:** Generate descriptions based on repo name, language, contents → batch-apply via API
- **Tool:** Needs new tool (PATCH /repos/{org}/{repo} with description)
- **Notes:** Repos without descriptions are nearly invisible on GitHub

### GAP-006: Go FLUX Modules Need Porting (7)
- **Priority:** High
- **Status:** Identified, needs coordination with JetsonClaw1
- **Scope:** 7 Go modules
- **Current State:** Go reference implementations of FLUX instructions; runtime is JS/WASM
- **Desired State:** Either ported to JS/WASM or documented as Go reference
- **Action:** Coordinate with JetsonClaw1 on porting decision
- **Tool:** Manual coordination
- **Notes:** These implement the same instruction set as flux-runtime-wasm

### GAP-007: Kung-Fu Variant Consolidation (7)
- **Priority:** High
- **Status:** Identified, not actioned
- **Scope:** 7 repos with "kung-fu" in name
- **Current State:** 7 similar repos, unclear if duplicates or intentional variants
- **Desired State:** Consolidated into one well-structured repo, or clearly documented as separate
- **Action:** Evaluate differences → consolidate or document
- **Tool:** Manual evaluation
- **Notes:** Repository analysis needed to determine overlap

---

## Medium Priority Gaps

### GAP-008: No Fleet-Wide CI/CD Pipeline
- **Priority:** Medium
- **Status:** Not actioned
- **Current State:** Each repo manages its own testing independently
- **Desired State:** Shared GitHub Actions workflow template
- **Action:** Design and propose a fleet CI/CD strategy
- **Tool:** Create template in fleet-contributing or new fleet-ci repo

### GAP-009: No Automated Dependency Tracking
- **Priority:** Medium
- **Status:** Not actioned
- **Current State:** Unknown which repos depend on which others
- **Desired State:** Mapped and tracked inter-repo dependencies
- **Notes:** Problem for breaking changes, security updates, identifying orphans

### GAP-010: Inconsistent README Quality
- **Priority:** Medium
- **Status:** Not quantified
- **Current State:** READMEs range from comprehensive to nonexistent
- **Desired State:** All active repos have adequate READMEs
- **Action:** Audit README presence/quality → create template → batch improve

### GAP-011: No CONTRIBUTING.md in Most Repos
- **Priority:** Medium
- **Status:** Fleet-wide guide exists (fleet-contributing) but most repos don't link to it
- **Current State:** Missing or non-standard contributing files
- **Desired State:** All active repos reference or include contribution guidelines

### GAP-012: Missing .gitignore Files
- **Priority:** Low-Medium
- **Status:** Not quantified
- **Current State:** Many repos lack appropriate .gitignore
- **Desired State:** All repos have language-appropriate .gitignore

---

## Low Priority Gaps

### GAP-013: No Fleet Architecture Documentation
- **Priority:** Low
- **Status:** Not actioned
- **Action:** Create high-level architecture doc showing repo relationships

### GAP-014: No Onboarding Guide for New Agents
- **Priority:** Low
- **Status:** Partially addressed by datum succession repo and runtime bundle
- **Action:** Create a "New Agent Starter Kit"

### GAP-015: Stale Forks (~45+)
- **Priority:** Low
- **Status:** Not fully quantified
- **Action:** Identify forks behind upstream, evaluate sync needs

### GAP-016: No Release/Versioning Standard
- **Priority:** Low
- **Status:** Not actioned
- **Action:** Establish fleet-wide semantic versioning guidelines

---

## Resolved Gaps

_(None yet — this section fills as work progresses.)_

---

## Gap Tracking Template

When adding new gaps, use this format:

```markdown
### GAP-NNN: [Gap Title] ([Count/Scope])
- **Priority:** Critical / High / Medium / Low
- **Status:** Identified / In Progress / Partially Fixed / Resolved
- **Scope:** [How many repos affected]
- **Current State:** [What exists now]
- **Desired State:** [What it should look like]
- **Action:** [What needs to happen]
- **Tool:** [Which tool, if any, can fix this]
- **Notes:** [Additional context]
```

---

*This document should be updated after every audit session.*
