# Fleet Audit Prompt — Comprehensive Audit Guide

> Use this prompt to run a comprehensive fleet hygiene audit. This guide covers what to check, how to categorize repos, what to fix, and how to report.

---

## Audit Prompt

Copy and use this prompt to initiate a fleet audit session:

````markdown
You are running a fleet hygiene audit for the SuperInstance organization on GitHub.

## Objective

Audit all repositories in the SuperInstance organization and produce a prioritized report of issues that need fixing.

## Audit Checklist

For each repo, check the following:

### Phase 1: Metadata (via GitHub API, no clone needed)
- [ ] **Has a description?** — `repo.description` field
- [ ] **Has topics?** — `repo.topics` (requires separate request with merc-preview header)
- [ ] **Has a license?** — `repo.license` field
- [ ] **Has a homepage URL?** — `repo.homepage` field
- [ ] **What language?** — `repo.language` field

### Phase 2: Content (via Contents API)
- [ ] **Has a README?** — Check for README.md, README.rst, README
- [ ] **Has a LICENSE file?** — Check for LICENSE, LICENSE.md
- [ ] **Has a .gitignore?** — Check for .gitignore
- [ ] **Has a CONTRIBUTING.md?** — Check for contributing guide
- [ ] **Has tests?** — Check for test/, tests/, __tests__/, *_test.py, *.test.js

### Phase 3: Health Assessment
- [ ] **Is it a fork?** — `repo.fork` → `repo.parent`
- [ ] **Is it empty?** — `repo.size === 0` or minimal files
- [ ] **Is it stale?** — `repo.pushed_at` — no commits in N days (default: 365)
- [ ] **Is it archived?** — `repo.archived`

## Repo Categorization

After checking, categorize each repo:

| Category | Criteria | Color | Action |
|----------|----------|-------|--------|
| **Green** | Has description, topics, license, README, recent commits | 🟢 | No action needed |
| **Yellow** | Missing 1-2 non-critical items (topics, description, .gitignore) | 🟡 | Batch-fixable |
| **Red** | Missing critical items (license, empty, very stale) | 🔴 | Priority action |
| **Dead** | Archived or intentionally deprecated | ⚫ | Leave alone |

## Output Format

Produce a markdown report with:

### 1. Executive Summary
- Total repos audited
- Total issues found (by category)
- Top 3 priorities for immediate action
- Comparison with previous audit (if available)

### 2. Detailed Findings
For each issue category, a table sorted by priority:

```markdown
## Missing Licenses (N repos)
| Repo | Language | Created | Priority |
|------|----------|---------|----------|
| [repo-name](url) | Python | 2025-03-15 | Critical |
```

### 3. Batch-Fixable Items
What can be fixed with a script:
- Missing licenses → `batch-license` tool
- Missing topics → `batch-topics` tool
- Missing descriptions → API PATCH (needs custom tool)

### 4. Manual Items
What needs human/agent evaluation:
- Empty repos → evaluate each one
- Stale repos → evaluate if still needed
- Fork sync → check upstream divergence

### 5. Recommendations
Prioritized action plan:
1. Immediate (this session)
2. Short-term (this week)
3. Medium-term (this month)
4. Long-term (ongoing monitoring)

## Tool Usage

Run the audit scanner:
```bash
# JSON output for programmatic use
python -m datum_runtime.tools.audit_scanner \
  --org SuperInstance --token $PAT \
  --output audit.json --json

# Markdown report for human reading
python -m datum_runtime.tools.audit_scanner \
  --org SuperInstance --token $PAT \
  --output audit-report.md

# Custom thresholds
python -m datum_runtime.tools.audit_scanner \
  --org SuperInstance --token $PAT \
  --stale-days 180 --top 100 --json
```

## Rate Limiting Protocol

During audit:
- Space requests ≥1.5 seconds apart
- Tool auto-checks X-RateLimit-Remaining
- If remaining < 100: auto-pauses
- If remaining < 10: long pause
- Total budget: 5,000 requests/hour (authenticated)

## Post-Audit Actions

1. Save report to your vessel repo (super-z-quartermaster)
2. Update known-gaps.md with any new findings
3. Update TASKBOARD with prioritized action items
4. Leave a MiB for Oracle1 with summary statistics
5. Run batch fixes starting with highest-priority items

## Fleet Context

- SuperInstance is a public mirror of Lucineer (many repos are forks)
- ~1,482 repos total
- THE-FLEET.md only shows 598 — known stale index issue
- Previous audit (2026-04-13) found: 62 empty, 738 unlicensed, ~880 untagged, ~234 missing descriptions
- Compare new findings with previous to track progress
````

---

## Customization Options

| Flag | Default | Description |
|------|---------|-------------|
| `--stale-days N` | 365 | Days threshold for stale repos |
| `--top N` | 50 | Max repos to show per category |
| `--json` | false | Output as JSON for programmatic processing |
| `--min-size N` | 1 | Min size in KB to not be considered empty |
| `--output FILE` | stdout | Write output to file |

---

## Integration with Tools

After running the audit:

1. **Immediate fixes** — Run batch tools on the findings:
   ```bash
   # Fix licenses
   python -m datum_runtime.tools.batch_license --org SuperInstance --token $PAT --dry-run

   # Fix topics (after creating mapping file)
   python -m datum_runtime.tools.batch_topics --input topics-mapping.json --token $PAT --dry-run
   ```

2. **Update context** — Refresh known-gaps.md with current numbers

3. **Communicate** — Leave MiB for fleet with audit summary

4. **Track** — Create a metrics snapshot for future comparison
