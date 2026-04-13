# PROMPTS/fleet-audit.md — Fleet Audit Prompt Template

> Use this prompt to run a comprehensive fleet hygiene audit.

---

## Prompt

Copy and use this prompt to initiate a fleet audit session:

````markdown
You are running a fleet hygiene audit for the SuperInstance organization on GitHub.

## Objective

Audit all repositories in the SuperInstance organization and produce a prioritized report of issues that need fixing.

## Audit Checklist

For each repo, check:

### Metadata (via GitHub API, no clone needed)
- [ ] Has a description? (API: repo.description)
- [ ] Has topics? (API: repo.topics — requires separate request with merc-preview header)
- [ ] Has a license? (API: repo.license)
- [ ] Has a homepage URL? (API: repo.homepage)

### Content (via Contents API)
- [ ] Has a README? (Check for README.md, README.rst, README)
- [ ] Has a LICENSE file? (Check for LICENSE, LICENSE.md)
- [ ] Has a .gitignore? (Check for .gitignore)
- [ ] Has a CONTRIBUTING.md?
- [ ] Has tests? (Check for test/, tests/, __tests__/, *_test.py, *.test.js)

### Health
- [ ] Is it a fork? (API: repo.fork → repo.parent)
- [ ] Is it empty? (API: repo.size === 0)
- [ ] Is it stale? (API: repo.pushed_at — no commits in 365 days)
- [ ] Is it archived? (API: repo.archived)

## Output Format

Produce a markdown report with:

1. **Executive Summary** — Total repos, total issues, top 3 priorities
2. **Detailed Findings** — Table for each category, sorted by priority
3. **Batch-Fixable Items** — What can be fixed with a script
4. **Manual Items** — What needs human/agent evaluation
5. **Recommendations** — Prioritized action plan

## Tool to Use

Run: python3 TOOLS/audit-scanner.py --org SuperInstance --token $PAT --output audit-report.md

## Rate Limiting

- Space requests 1-2 seconds apart
- Check X-RateLimit-Remaining every 10 requests
- If remaining < 100, pause for 5 minutes
- If remaining < 10, pause for 30 minutes
- Total budget: 5,000 requests/hour

## Additional Notes

- SuperInstance is a public mirror of Lucineer (many repos are forks)
- ~1,482 repos total (but THE-FLEET.md only shows 598 — known stale index issue)
- Previous audit (2026-04-13) found: 62 empty, 738 unlicensed, ~880 untagged
- Compare new findings with previous to track progress
````

---

## Customization Options

- `--stale-days N`: Change the staleness threshold (default: 365)
- `--top N`: Limit output per category (default: 50)
- `--json`: Output as JSON for programmatic processing
- `--min-size N`: Minimum repo size in KB to not be considered empty (default: 1)
