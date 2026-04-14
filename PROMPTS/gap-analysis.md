# PROMPTS/gap-analysis.md — Gap Analysis Prompt Template

> Use this prompt to perform a comprehensive fleet gap analysis.

---

## Prompt

Copy and use this prompt to initiate a gap analysis session:

````markdown
You are performing a gap analysis for the SuperInstance fleet on GitHub.

## Objective

Identify and categorize all gaps in the fleet's repositories — things that are missing, broken, inconsistent, or could be improved. Produce a prioritized action plan.

## Analysis Framework

### Level 1: Per-Repo Gaps
For each repo, identify missing elements:
- Files: LICENSE, README, CONTRIBUTING.md, .gitignore, CI/CD config
- Metadata: description, topics, homepage, language
- Content: source code, tests, documentation
- Quality: code style config, editor config, build system

### Level 2: Fleet-Level Gaps
Identify patterns across the fleet:
- Inconsistent practices (some repos have X, others don't)
- Missing shared infrastructure (templates, CI/CD, tooling)
- Documentation gaps (no onboarding guide, no architecture docs)
- Communication gaps (stale index, missing MiB channels)

### Level 3: Strategic Gaps
Identify high-level improvements:
- Missing capabilities (monitoring, dependency tracking, automated testing)
- Process gaps (no PR review, no release process, no versioning)
- Scalability issues (manual operations that should be automated)
- Knowledge gaps (undocumented relationships, unknown dependencies)

## Data Sources

1. **GitHub API** — repo metadata, contents, commits, forks
2. **audit-scanner.py** — automated fleet audit (run first)
3. **CONTEXT/known-gaps.md** — previously identified gaps
4. **CONTEXT/repo-relationships.md** — known repo relationships
5. **CONTEXT/fleet-dynamics.md** — fleet operational knowledge

## Previous Known Gaps (2026-04-13)

- 62 empty repos
- 738 unlicensed repos
- ~880 untagged repos
- Stale fleet index (598 vs 1,482)
- 7 Go FLUX modules needing port
- 7 kung-fu variants needing consolidation
- No fleet-wide CI/CD
- No automated dependency tracking

## Output Format

### 1. Gap Inventory
For each gap:
```markdown
### G-{NUMBER}: [Title]
- **Category:** Per-Repo / Fleet-Level / Strategic
- **Priority:** Critical / High / Medium / Low
- **Scope:** [How many repos affected]
- **Current State:** [What exists now]
- **Desired State:** [What it should look like]
- **Effort:** [Low / Medium / High / Very High]
- **Tool Required:** [Which tool, if any, can fix this]
- **Dependencies:** [What must happen first]
```

### 2. Priority Matrix
| Gap | Priority | Effort | Impact | Batch Fixable? |
|-----|----------|--------|--------|-----------------|

### 3. Action Plan
Ordered by priority, with:
- Immediate actions (today/this session)
- Short-term actions (this week)
- Medium-term actions (this month)
- Long-term actions (ongoing)

### 4. Metrics Dashboard
Numbers to track over time:
- Total repos
- Repos with descriptions (%)
- Repos with topics (%)
- Repos with licenses (%)
- Repos with READMEs (%)
- Empty repos (count)
- Forks behind upstream (count)

## Important Context

- The fleet has ~1,482 repos in SuperInstance
- ~580 are forks from Lucineer
- The Quartermaster (you) is responsible for fleet hygiene
- You have production tools in TOOLS/ (batch-topics.py, batch-license.py, audit-scanner.py)
- Communication uses I2I protocol and MiB files
- Always update CONTEXT/known-gaps.md after analysis
````

---

## Integration with Tools

After running the gap analysis:

1. **Update known-gaps.md** with any new findings
2. **Update TASKBOARD** with new priorities from the action plan
3. **Run audit-scanner.py** to get fresh metrics
4. **Create a metrics snapshot** for future comparison
5. **Leave a MiB** for Oracle1 with analysis summary
