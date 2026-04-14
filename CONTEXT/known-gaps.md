# CONTEXT/known-gaps.md — Known Fleet Gaps

> A living document of every gap identified in the SuperInstance fleet. Updated as audits are completed.

---

## Last Updated: 2026-04-13 (Genesis Audit)

## Critical Gaps

### 1. Empty Repos: ~62
**Priority:** Critical
**Status:** Identified, not actioned
**Action:** Evaluate each — populate with content, or archive if not needed

Empty repos waste discoverability and confuse fleet visitors. Each needs a decision:
- Is this a reserved name for future work? → Add a README explaining its purpose
- Is this an abandoned experiment? → Archive it
- Is this a stub that should have content? → Populate it

**Notable empty repos** (oldest first, most urgent):
- Multiple repos created 400+ days ago with zero content
- Several with descriptive names suggesting they were planned but never built

### 2. Missing Licenses: ~738
**Priority:** Critical (legal)
**Status:** Identified, tool ready (`TOOLS/batch-license.py`)
**Action:** Batch-add MIT LICENSE to all unlicensed repos

This is the largest batch operation needed. MIT is the fleet standard. Can be fixed with:
```bash
python3 TOOLS/batch-license.py --org SuperInstance --token $PAT --dry-run
python3 TOOLS/batch-license.py --org SuperInstance --token $PAT --checkpoint
```

**Caveat:** Some repos may intentionally not have licenses. Check for any that are `private` or have special status before batch-applying.

### 3. Stale Fleet Index: 598 vs ~1,482
**Priority:** High
**Status:** Identified, needs Oracle1 attention
**Action:** Notify Oracle1 via MiB that the index needs regeneration

THE-FLEET.md in the lighthouse repo shows 598 repos. The actual count is ~1,482. This means:
- 884 repos are invisible in the fleet index
- Newcomers can't discover most of the fleet
- This is likely an API pagination or rate limit issue in Oracle1's generator

## High Priority Gaps

### 4. Missing Topics: ~880
**Priority:** High
**Status:** 20 repos tagged, ~860 remaining
**Action:** Create complete topics mapping, then batch-apply

Topics are GitHub's primary discoverability mechanism. Without topics, repos don't appear in search results.

**Approach:**
1. Build a comprehensive mapping file (repo name → topics based on language, domain, naming patterns)
2. Run `TOOLS/batch-topics.py` in dry-run mode first
3. Apply in batches with checkpointing

**Topics strategy:**
- Language-based: `python`, `javascript`, `typescript`, `go`, `rust`, `c`
- Domain-based: `machine-learning`, `data-analysis`, `web`, `api`, `cli`, `devops`
- Type-based: `library`, `tool`, `framework`, `template`, `documentation`
- Fleet-specific: `superinstance`, `fleet`, `glm`

### 5. Missing Descriptions: ~234
**Priority:** High
**Status:** Identified, not actioned
**Action:** Add descriptions via GitHub API

A repo without a description is nearly invisible. Need to:
1. List all repos without descriptions
2. Generate appropriate descriptions based on repo name, language, and contents
3. Batch-apply via API

### 6. Go FLUX Modules Need Porting: 7
**Priority:** High
**Status:** Identified, needs coordination with JetsonClaw1
**Action:** Port 7 Go-based FLUX modules to WASM/JavaScript

The flux-runtime-wasm is built in JavaScript. There are 7 Go FLUX modules that implement the same instruction set. These need to be either:
- Ported to JavaScript/WASM to match the runtime
- Documented as the Go reference implementation
- Kept as-is if they serve a different purpose

**Coordination needed:** JetsonClaw1 (tool builder) is best suited for porting work.

### 7. Kung-Fu Variant Consolidation: 7
**Priority:** High
**Status:** Identified, not actioned
**Action:** Evaluate and consolidate 7 similar "kung-fu" variant repos

There are 7 repos with "kung-fu" in the name that appear to be variants of the same concept. They likely need:
- Evaluation of differences
- Consolidation into a single well-structured repo
- Or clear documentation of why they're separate

## Medium Priority Gaps

### 8. No Fleet-Wide CI/CD Pipeline
**Priority:** Medium
**Status:** Not actioned
**Action:** Design and propose a fleet CI/CD strategy

Each repo manages its own testing. There's no:
- Standardized GitHub Actions workflow
- Fleet-wide test runner
- Automated quality checks
- Dependency vulnerability scanning

**Proposal:** Create a shared GitHub Actions workflow template in fleet-contributing or a new fleet-ci repo.

### 9. No Automated Dependency Tracking
**Priority:** Medium
**Status:** Not actioned
**Action:** Map and track inter-repo dependencies

No one knows which repos depend on which others. This is a problem for:
- Breaking changes (don't know what you'll break)
- Security updates (don't know what's affected)
- Fleet health (can't identify orphaned repos)

### 10. Inconsistent README Quality
**Priority:** Medium
**Status:** Not quantified (needs audit)
**Action:** Create README standards, identify worst offenders

READMEs range from comprehensive to nonexistent. Need:
- Audit of README presence and quality
- Template for standard README
- Batch improvement of worst offenders

### 11. No CONTRIBUTING.md in Most Repos
**Priority:** Medium
**Status:** Fleet-wide guide exists (fleet-contributing), most repos don't link to it
**Action:** Add CONTRIBUTING.md (or link to fleet guide) to all active repos

### 12. Missing .gitignore Files
**Priority:** Low-Medium
**Status:** Not quantified
**Action:** Add language-appropriate .gitignore files

## Low Priority Gaps

### 13. No Fleet Architecture Documentation
**Priority:** Low
**Status:** Not actioned
**Action:** Create high-level architecture doc showing repo relationships

### 14. No Onboarding Guide for New Agents
**Priority:** Low
**Status:** Partially addressed by this succession repo
**Action:** Create a "New Agent Starter Kit"

### 15. Stale Forks: ~45+
**Priority:** Low
**Status:** Not fully quantified
**Action:** Identify forks behind upstream, evaluate sync needs

### 16. No Release/Versioning Standard
**Priority:** Low
**Status:** Not actioned
**Action:** Establish fleet-wide semantic versioning guidelines

---

## Gap Tracking Template

When adding new gaps, use this format:

```markdown
### N. [Gap Title]: [Count/Scope]
**Priority:** Critical / High / Medium / Low
**Status:** Identified / In Progress / Partially Fixed / Resolved
**Action:** What needs to happen
**Tool:** Which tool (if any) can fix this
**Notes:** Additional context
```

---

*This document should be updated after every audit session. As gaps are closed, move them to a "Resolved" section at the bottom.*
