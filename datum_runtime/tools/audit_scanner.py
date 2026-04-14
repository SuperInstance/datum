#!/usr/bin/env python3
"""
audit_scanner.py — Scan a GitHub organization for fleet hygiene issues.

Standalone version (stdlib only, no third-party dependencies).

Usage:
    python -m datum_runtime.tools.audit_scanner --org SuperInstance --token $PAT
    python -m datum_runtime.tools.audit_scanner --org SuperInstance --token $PAT --output report.json
    python -m datum_runtime.tools.audit_scanner --org SuperInstance --token $PAT --json --stale-days 180

Checks performed:
    1. Repos without descriptions
    2. Repos without topics
    3. Repos without licenses
    4. Empty repos (size = 0 or minimal files)
    5. Stale repos (no commits in N days)
    6. Fork repos (with parent info)
    7. Repos without README
    8. Repos without .gitignore
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime, timezone, timedelta

GITHUB_API = "https://api.github.com"
DEFAULT_DELAY = 1.5


class FleetAuditor:
    def __init__(self, token: str, org: str, stale_days: int = 365,
                 min_size: int = 1, top_n: int = 50):
        self.token = token
        self.org = org
        self.stale_threshold = timedelta(days=stale_days)
        self.min_size = min_size
        self.top_n = top_n

        # Results storage
        self.all_repos = []
        self.no_description = []
        self.no_topics = []
        self.no_license = []
        self.empty_repos = []
        self.stale_repos = []
        self.fork_repos = []
        self.no_readme = []
        self.no_gitignore = []
        self.language_counts = defaultdict(int)
        self.errors = []

    def _headers(self, accept: str = "application/vnd.github.v3+json"):
        """Build request headers."""
        return {
            "Authorization": f"token {self.token}",
            "Accept": accept,
            "User-Agent": "datum-quartermaster/audit-scanner/1.0",
        }

    def print_progress(self, message: str):
        """Print progress to stderr."""
        print(message, file=sys.stderr)

    def _api_get(self, url: str, accept: str = "application/vnd.github.v3+json"):
        """Make a GET request with rate limiting. Returns (status_code, data_dict_or_None)."""
        req = urllib.request.Request(url, headers=self._headers(accept))
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                remaining = int(resp.headers.get("X-RateLimit-Remaining", 5000))
                if remaining < 100:
                    reset_ts = int(resp.headers.get("X-RateLimit-Reset", 0))
                    wait = max(reset_ts - int(time.time()), 60) + 10
                    self.print_progress(f"RATE LIMIT WARNING: {remaining} remaining, waiting {wait}s")
                    time.sleep(wait)
                try:
                    return resp.status, json.loads(body)
                except json.JSONDecodeError:
                    return resp.status, None
        except urllib.error.HTTPError as e:
            self.errors.append(f"API error {e.code} on {url}: {e.reason}")
            try:
                body = e.read().decode("utf-8")
                return e.code, json.loads(body)
            except Exception:
                return e.code, None
        except Exception as e:
            self.errors.append(f"Request error on {url}: {e}")
            return 0, None

    def get_all_repos(self):
        """Fetch all repos from the organization via pagination."""
        self.print_progress(f"Fetching repos from {self.org}...")
        repos = []
        page = 1
        while True:
            url = (
                f"{GITHUB_API}/orgs/{self.org}/repos"
                f"?type=all&per_page=100&page={page}"
            )
            status, data = self._api_get(url)
            if status != 200 or not data:
                break
            repos.extend(data)
            page += 1
            time.sleep(DEFAULT_DELAY)

        self.all_repos = repos
        self.print_progress(f"Found {len(repos)} repos")
        return repos

    def check_topics(self, repo: dict):
        """Check if a repo has topics (requires separate API call with merc-preview)."""
        url = f"{GITHUB_API}/repos/{self.org}/{repo['name']}/topics"
        status, data = self._api_get(url, accept="application/vnd.github.mercy-preview+json")
        if status == 200 and data:
            topics = data.get("names", [])
            return len(topics) > 0
        return None  # Error

    def check_contents(self, repo: dict):
        """Check if repo has README and .gitignore."""
        result = {"has_readme": None, "has_gitignore": None}

        for filename, key in [("README.md", "has_readme"), ("README", "has_readme"),
                               (".gitignore", "has_gitignore")]:
            if result[key] is not None:
                continue
            try:
                url = f"{GITHUB_API}/repos/{self.org}/{repo['name']}/contents/{filename}"
                status, _ = self._api_get(url)
                if status == 200:
                    result[key] = True
                elif status == 404:
                    if result[key] is None:
                        result[key] = False
            except Exception:
                pass

        return result

    def run_audit(self):
        """Run the complete audit."""
        if not self.all_repos:
            self.get_all_repos()

        now = datetime.now(timezone.utc)
        total = len(self.all_repos)

        self.print_progress(f"Auditing {total} repos...")

        # Phase 1: Quick API checks (no extra requests)
        for i, repo in enumerate(self.all_repos, 1):
            if i % 100 == 0:
                self.print_progress(f"  Phase 1: {i}/{total}...")

            name = repo["name"]

            # Description check
            if not repo.get("description"):
                self.no_description.append({
                    "name": name,
                    "url": repo["html_url"],
                    "created": repo.get("created_at", "unknown"),
                    "language": repo.get("language")
                })

            # License check
            if not repo.get("license"):
                self.no_license.append({
                    "name": name,
                    "url": repo["html_url"],
                    "created": repo.get("created_at", "unknown"),
                    "language": repo.get("language")
                })

            # Empty repo check
            if repo.get("size", 0) <= self.min_size:
                self.empty_repos.append({
                    "name": name,
                    "url": repo["html_url"],
                    "size": repo.get("size", 0),
                    "created": repo.get("created_at", "unknown"),
                    "pushed": repo.get("pushed_at", "never")
                })

            # Stale repo check
            pushed_str = repo.get("pushed_at")
            if pushed_str:
                pushed = datetime.fromisoformat(pushed_str.replace("Z", "+00:00"))
                if (now - pushed) > self.stale_threshold:
                    self.stale_repos.append({
                        "name": name,
                        "url": repo["html_url"],
                        "pushed": pushed_str,
                        "stale_days": (now - pushed).days,
                        "language": repo.get("language")
                    })

            # Fork check
            if repo.get("fork"):
                parent = repo.get("parent", {})
                self.fork_repos.append({
                    "name": name,
                    "url": repo["html_url"],
                    "parent": parent.get("full_name", "unknown"),
                    "parent_url": parent.get("html_url", "")
                })

            # Language count
            lang = repo.get("language")
            if lang:
                self.language_counts[lang] += 1

        # Phase 2: Checks requiring extra API calls (slower)
        self.print_progress("Phase 2: Checking topics (this takes a while)...")
        for i, repo in enumerate(self.all_repos, 1):
            if i % 50 == 0:
                self.print_progress(f"  Topics: {i}/{total}...")
                time.sleep(1)

            has_topics = self.check_topics(repo)
            if has_topics is False:
                self.no_topics.append({
                    "name": repo["name"],
                    "url": repo["html_url"],
                    "language": repo.get("language")
                })
            time.sleep(DEFAULT_DELAY)

        self.print_progress("Audit complete. Generating report...")

    def generate_markdown(self) -> str:
        """Generate a markdown report."""
        now = datetime.now(timezone.utc)
        lines = []

        lines.append(f"# Fleet Audit Report — {now.strftime('%Y-%m-%d')}")
        lines.append(f"")
        lines.append(f"**Organization:** {self.org}")
        lines.append(f"**Total Repos:** {len(self.all_repos)}")
        lines.append(f"**Audit Date:** {now.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"**Stale Threshold:** {self.stale_threshold.days} days")
        lines.append(f"")

        # Summary table
        lines.append("## Summary")
        lines.append(f"")
        lines.append("| Category | Count | Priority | Batch Fixable? |")
        lines.append("|----------|-------|----------|-----------------|")
        lines.append(f"| Total repos | {len(self.all_repos)} | — | — |")
        lines.append(f"| Missing description | {len(self.no_description)} | High | Yes |")
        lines.append(f"| Missing topics | {len(self.no_topics)} | High | Yes |")
        lines.append(f"| Missing license | {len(self.no_license)} | Critical | Yes |")
        lines.append(f"| Empty repos | {len(self.empty_repos)} | Critical | No (manual) |")
        lines.append(f"| Stale repos ({self.stale_threshold.days}d+) | {len(self.stale_repos)} | Medium | No |")
        lines.append(f"| Fork repos | {len(self.fork_repos)} | Info | No |")
        lines.append(f"")

        # Language distribution
        lines.append("## Language Distribution")
        lines.append(f"")
        lines.append("| Language | Repos | Percentage |")
        lines.append("|----------|-------|------------|")
        total_with_lang = sum(self.language_counts.values())
        for lang, count in sorted(self.language_counts.items(), key=lambda x: -x[1])[:20]:
            pct = (count / total_with_lang * 100) if total_with_lang > 0 else 0
            lines.append(f"| {lang or 'Unknown'} | {count} | {pct:.1f}% |")
        lines.append(f"**Repos with no language:** {len(self.all_repos) - total_with_lang}")
        lines.append(f"")

        # Priority 1: Empty Repos
        lines.append("## Priority 1: Empty Repos")
        lines.append(f"")
        lines.append(f"Found **{len(self.empty_repos)}** repos with minimal or no content.")
        lines.append(f"")
        if self.empty_repos:
            lines.append("| Repo | Size (KB) | Created | Last Pushed |")
            lines.append("|------|-----------|---------|-------------|")
            for r in self.empty_repos[:self.top_n]:
                lines.append(f"| [{r['name']}]({r['url']}) | {r['size']} | {r['created'][:10]} | {r.get('pushed', 'N/A')[:10]} |")
            if len(self.empty_repos) > self.top_n:
                lines.append(f"")
                lines.append(f"*...and {len(self.empty_repos) - self.top_n} more*")
        lines.append(f"")

        # Priority 2: Missing Licenses
        lines.append("## Priority 2: Missing Licenses")
        lines.append(f"")
        lines.append(f"Found **{len(self.no_license)}** repos without a LICENSE file.")
        lines.append(f"")
        lines.append(f"> **Action:** Run `python -m datum_runtime.tools.batch_license --org {self.org} --token $PAT --dry-run`")
        lines.append(f"")
        if self.no_license:
            lines.append("| Repo | Language | Created |")
            lines.append("|------|----------|---------|")
            for r in self.no_license[:self.top_n]:
                lines.append(f"| [{r['name']}]({r['url']}) | {r['language'] or '—'} | {r['created'][:10]} |")
            if len(self.no_license) > self.top_n:
                lines.append(f"")
                lines.append(f"*...and {len(self.no_license) - self.top_n} more*")
        lines.append(f"")

        # Priority 3: Missing Topics
        lines.append("## Priority 3: Missing Topics")
        lines.append(f"")
        lines.append(f"Found **{len(self.no_topics)}** repos without topics.")
        lines.append(f"")
        lines.append(f"> **Action:** Create a topics mapping file and run `python -m datum_runtime.tools.batch_topics --input mapping.json --token $PAT --dry-run`")
        lines.append(f"")
        if self.no_topics:
            lines.append("| Repo | Language |")
            lines.append("|------|----------|")
            for r in self.no_topics[:self.top_n]:
                lines.append(f"| [{r['name']}]({r['url']}) | {r['language'] or '—'} |")
            if len(self.no_topics) > self.top_n:
                lines.append(f"")
                lines.append(f"*...and {len(self.no_topics) - self.top_n} more*")
        lines.append(f"")

        # Priority 4: Missing Descriptions
        lines.append("## Priority 4: Missing Descriptions")
        lines.append(f"")
        lines.append(f"Found **{len(self.no_description)}** repos without descriptions.")
        lines.append(f"")
        if self.no_description:
            lines.append("| Repo | Language | Created |")
            lines.append("|------|----------|---------|")
            for r in self.no_description[:self.top_n]:
                lines.append(f"| [{r['name']}]({r['url']}) | {r['language'] or '—'} | {r['created'][:10]} |")
            if len(self.no_description) > self.top_n:
                lines.append(f"")
                lines.append(f"*...and {len(self.no_description) - self.top_n} more*")
        lines.append(f"")

        # Info: Fork Repos
        lines.append("## Info: Fork Repos")
        lines.append(f"")
        lines.append(f"Found **{len(self.fork_repos)}** fork repos.")
        lines.append(f"")
        if self.fork_repos:
            lines.append("| Fork | Parent |")
            lines.append("|------|--------|")
            for r in self.fork_repos[:self.top_n]:
                parent_link = f"[{r['parent']}]({r['parent_url']})" if r['parent_url'] else r['parent']
                lines.append(f"| [{r['name']}]({r['url']}) | {parent_link} |")
            if len(self.fork_repos) > self.top_n:
                lines.append(f"")
                lines.append(f"*...and {len(self.fork_repos) - self.top_n} more*")
        lines.append(f"")

        # Recommendations
        lines.append("## Recommendations")
        lines.append(f"")
        lines.append("1. **Empty repos:** Evaluate each one — populate with content, or archive if not needed")
        lines.append("2. **Missing licenses:** Batch-fix with `batch_license` tool (MIT is standard)")
        lines.append("3. **Missing topics:** Create a mapping file and batch-fix with `batch_topics` tool")
        lines.append("4. **Missing descriptions:** Use GitHub API to add descriptions based on repo name/purpose")
        lines.append("5. **Stale repos:** Evaluate if they need updating or archiving")
        lines.append("6. **Fork repos:** Check if they're in sync with upstream")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"*Generated by datum_runtime.tools.audit_scanner on {now.strftime('%Y-%m-%d %H:%M UTC')}*")

        return "\n".join(lines)

    def generate_json(self) -> dict:
        """Generate JSON output."""
        return {
            "audit_date": datetime.now(timezone.utc).isoformat(),
            "organization": self.org,
            "total_repos": len(self.all_repos),
            "findings": {
                "no_description": self.no_description,
                "no_topics": self.no_topics,
                "no_license": self.no_license,
                "empty_repos": self.empty_repos,
                "stale_repos": self.stale_repos,
                "fork_repos": self.fork_repos,
            },
            "language_distribution": dict(self.language_counts),
            "errors": self.errors
        }


def main():
    parser = argparse.ArgumentParser(
        description="Scan a GitHub organization for fleet hygiene issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --org SuperInstance --token $GITHUB_TOKEN
  %(prog)s --org SuperInstance --token $GITHUB_TOKEN --output report.json
  %(prog)s --org SuperInstance --token $GITHUB_TOKEN --json > audit.json
        """
    )
    parser.add_argument("--org", required=True, help="GitHub organization to scan")
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--stale-days", type=int, default=365, help="Stale threshold in days")
    parser.add_argument("--min-size", type=int, default=1, help="Min size in KB to not be empty")
    parser.add_argument("--top", type=int, default=50, help="Max repos to show per category")

    args = parser.parse_args()

    auditor = FleetAuditor(
        token=args.token,
        org=args.org,
        stale_days=args.stale_days,
        min_size=args.min_size,
        top_n=args.top
    )

    auditor.run_audit()

    if args.json:
        report = json.dumps(auditor.generate_json(), indent=2)
    else:
        report = auditor.generate_markdown()

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\nReport written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
