# Gap Analysis Prompt — Fleet Gap Identification & Prioritization

> Use this prompt to perform a comprehensive fleet gap analysis. Identifies what's missing, broken, inconsistent, or improvable — and produces a prioritized action plan.

---

## Gap Analysis Prompt

Copy and use this prompt to initiate a gap analysis session:

````markdown
You are performing a gap analysis for the SuperInstance fleet on GitHub.

## Objective

Identify and categorize all gaps in the fleet's repositories — things that are missing, broken, inconsistent, or could be improved. Produce a prioritized action plan.

## Analysis Framework

### Level 1: Per-Repo Gaps
For each repo, identify missing elements:
- **Files:** LICENSE, README, CONTRIBUTING.md, .gitignore, CI/CD config
- **Metadata:** description, topics, homepage, language
- **Content:** source code, tests, documentation
- **Quality:** code style config, editor config, build system

### Level 2: Fleet-Level Gaps
Identify patterns across the fleet:
- **Inconsistent practices:** Some repos have X, others don't
- **Missing shared infrastructure:** Templates, CI/CD, tooling
- **Documentation gaps:** No onboarding guide, no architecture docs
- **Communication gaps:** Stale index, missing MiB channels

### Level 3: Strategic Gaps
Identify high-level improvements:
- **Missing capabilities:** Monitoring, dependency tracking, automated testing
- **Process gaps:** No PR review, no release process, no versioning
- **Scalability issues:** Manual operations that should be automated
- **Knowledge gaps:** Undocumented relationships, unknown dependencies

## Gap Categories to Check

### Missing Repos (should exist but don't)
- Specs/designs that have no implementation
- Tools referenced by other repos that don't exist
- Shared libraries that multiple repos could use

### Duplicate Functionality
- Repos that do the same thing
- Similar tools that could be consolidated
- Overlapping libraries or frameworks

### Orphaned Repos
- No references from any other repo
- No recent activity
- No clear purpose or owner
- Not linked from fleet index

### Implementation Gaps
- Spec/design exists but no code
- README promises features not implemented
- Tests reference unimplemented functionality
- Dependencies that don't exist in the fleet

## Data Sources

1. **audit-scanner results** — Automated fleet audit (run first)
2. **GitHub API** — Repo metadata, contents, commits, forks
3. **context/known-gaps.md** — Previously identified gaps
4. **context/repo-relationships.md** — Known repo relationships
5. **context/fleet-dynamics.md** — Fleet operational knowledge
6. **fleet-contributing** — Fleet standards (what repos should follow)

## Previous Known Gaps (2026-04-13 baseline)

- 62 empty repos
- 738 unlicensed repos
- ~880 untagged repos
- ~234 missing descriptions
- Stale fleet index (598 vs 1,482)
- 7 Go FLUX modules needing port
- 7 kung-fu variants needing consolidation
- No fleet-wide CI/CD
- No automated dependency tracking

## Output Format

### 1. Gap Inventory

For each gap found:
```markdown
### GAP-NNN: [Title] ([Scope])
- **Category:** Per-Repo / Fleet-Level / Strategic
- **Priority:** Critical / High / Medium / Low
- **Scope:** [How many repos affected]
- **Current State:** [What exists now]
- **Desired State:** [What it should look like]
- **Effort:** Low / Medium / High / Very High
- **Tool Required:** [Which tool, if any, can fix this]
- **Dependencies:** [What must happen first]
```

### 2. Priority Matrix

| Gap | Priority | Effort | Impact | Batch Fixable? | Tool |
|-----|----------|--------|--------|-----------------|------|
| GAP-002: Missing Licenses | Critical | Low | High | Yes | batch-license |

### 3. Action Plan

Ordered by priority:

**Immediate (this session):**
- Run audit-scanner for fresh data
- Apply batch-fixable items (licenses, topics)
- Update known-gaps.md

**Short-term (this week):**
- Create topics mapping file for remaining untagged repos
- Evaluate empty repos (populate or archive)
- Contact Oracle1 about stale index

**Medium-term (this month):**
- Design CI/CD template proposal
- Evaluate kung-fu variants for consolidation
- Coordinate Go FLUX module porting with JetsonClaw1

**Long-term (ongoing):**
- Establish regular audit schedule
- Build automated dependency tracking
- Create fleet architecture documentation

### 4. Metrics Dashboard

Numbers to track over time:

| Metric | Baseline | Current | Target |
|--------|----------|---------|--------|
| Total repos | ~1,482 | | |
| Repos with descriptions (%) | ~84% | | >95% |
| Repos with topics (%) | ~41% | | >90% |
| Repos with licenses (%) | ~50% | | >95% |
| Repos with READMEs (%) | | | >90% |
| Empty repos (count) | 62 | | <10 |
| Forks behind upstream (count) | ~45 | | 0 |

## Important Context

- The fleet has ~1,482 repos in SuperInstance
- ~580 are forks from Lucineer
- The Quartermaster (you) is responsible for fleet hygiene
- You have production tools in datum_runtime.tools (all stdlib, no dependencies)
- Communication uses I2I protocol and MiB files
- Always update context/known-gaps.md after analysis
````

---

## Integration with Tools

After running the gap analysis:

1. **Update known-gaps.md** — Add any newly discovered gaps, update counts on existing ones
2. **Update TASKBOARD** — Set priorities from the action plan
3. **Run audit-scanner** — Get fresh metrics for the dashboard
4. **Create a metrics snapshot** — Save current numbers for future comparison
5. **Leave a MiB** for Oracle1 with analysis summary
6. **Execute batch fixes** — Start with the highest-priority, lowest-effort items (licenses first, then topics)
