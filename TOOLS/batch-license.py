#!/usr/bin/env python3
"""
batch-license.py — Batch-add MIT LICENSE files to repositories via GitHub API.

Usage:
    python3 batch-license.py --org SuperInstance --token GITHUB_TOKEN [--dry-run] [--delay 2.0]
    python3 batch-license.py --repos repo1,repo2,repo3 --token GITHUB_TOKEN

Options:
    --org ORG           Target GitHub organization (default: SuperInstance)
    --repos LIST        Comma-separated list of specific repos
    --token TOKEN       GitHub Personal Access Token
    --license TYPE      License type (default: mit)
    --owner NAME        License owner name (for MIT)
    --dry-run           Preview without applying
    --delay SECS        Delay between requests (default: 2.5)
    --checkpoint        Enable checkpoint/resume
    --skip-licensed     Skip repos that already have a license

NOTE: This script creates LICENSE files via the GitHub Contents API (no local clone needed).
"""

import argparse
import base64
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' module required. Install with: pip install requests")
    sys.exit(1)

GITHUB_API = "https://api.github.com"
DEFAULT_ORG = "SuperInstance"
DEFAULT_DELAY = 2.5
CHECKPOINT_FILE = "batch-license-progress.json"
LOG_FILE = f"batch-license-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.log"

# MIT License Template
MIT_LICENSE_TEMPLATE = """MIT License

Copyright (c) {year} {owner}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


class LicenseBatcher:
    def __init__(self, token: str, org: str, dry_run: bool = False,
                 delay: float = DEFAULT_DELAY, license_type: str = "mit",
                 owner: str = "", skip_licensed: bool = True,
                 use_checkpoint: bool = False):
        self.token = token
        self.org = org
        self.dry_run = dry_run
        self.delay = delay
        self.license_type = license_type
        self.owner = owner or org
        self.skip_licensed = skip_licensed
        self.use_checkpoint = use_checkpoint
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "datum-quartermaster/batch-license/1.0"
        })
        self.stats = {"success": 0, "failed": 0, "skipped": 0, "total": 0, "already_licensed": 0}
        self.checkpoint_data = {"completed": [], "failed": []}

    def log(self, message: str):
        """Write to log file and stdout."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"[{timestamp}] {message}"
        print(line)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")

    def load_checkpoint(self):
        """Load progress from checkpoint file."""
        if Path(CHECKPOINT_FILE).exists():
            with open(CHECKPOINT_FILE) as f:
                self.checkpoint_data = json.load(f)
            self.log(f"Loaded checkpoint: {len(self.checkpoint_data['completed'])} completed, "
                     f"{len(self.checkpoint_data['failed'])} failed")

    def save_checkpoint(self):
        """Save progress to checkpoint file."""
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(self.checkpoint_data, f, indent=2)

    def check_rate_limit(self):
        """Check and respect GitHub rate limits."""
        resp = self.session.get(f"{GITHUB_API}/rate_limit")
        if resp.status_code == 200:
            data = resp.json()
            remaining = data["rate"]["remaining"]
            reset_ts = data["rate"]["reset"]
            if remaining < 10:
                wait = max(reset_ts - int(time.time()), 60) + 10
                self.log(f"RATE LIMIT: {remaining} remaining. Waiting {wait}s...")
                time.sleep(wait)
            elif remaining < 100:
                self.log(f"RATE LIMIT WARNING: {remaining} remaining")
            return remaining
        return 0

    def get_all_repos(self):
        """Get all repos in the organization."""
        self.log(f"Fetching repos from {self.org}...")
        repos = []
        page = 1
        while True:
            resp = self.session.get(
                f"{GITHUB_API}/orgs/{self.org}/repos",
                params={"type": "all", "per_page": 100, "page": page}
            )
            if resp.status_code != 200:
                self.log(f"ERROR fetching repos (page {page}): {resp.status_code}")
                break
            data = resp.json()
            if not data:
                break
            repos.extend(data)
            page += 1
            time.sleep(1)
        self.log(f"Found {len(repos)} repos total")
        return repos

    def has_license(self, repo: str) -> bool:
        """Check if a repo already has a LICENSE file."""
        resp = self.session.get(
            f"{GITHUB_API}/repos/{self.org}/{repo}/contents/LICENSE"
        )
        return resp.status_code == 200

    def get_default_branch(self, repo: str) -> str:
        """Get the default branch for a repo."""
        resp = self.session.get(f"{GITHUB_API}/repos/{self.org}/{repo}")
        if resp.status_code == 200:
            return resp.json().get("default_branch", "main")
        return "main"

    def add_license(self, repo: str):
        """Add MIT LICENSE to a repo via Contents API."""
        year = str(datetime.now(timezone.utc).year)
        license_content = MIT_LICENSE_TEMPLATE.format(year=year, owner=self.owner)
        encoded_content = base64.b64encode(license_content.encode()).decode()
        branch = self.get_default_branch(repo)

        if self.dry_run:
            self.log(f"[DRY RUN] {repo}: would add MIT LICENSE to branch '{branch}'")
            return {"dry_run": True}

        resp = self.session.put(
            f"{GITHUB_API}/repos/{self.org}/{repo}/contents/LICENSE",
            json={
                "message": "[I2I:DELIVERABLE] datum:license — Add MIT LICENSE",
                "content": encoded_content,
                "branch": branch
            }
        )

        if resp.status_code == 201:
            commit_sha = resp.json().get("commit", {}).get("sha", "unknown")
            self.log(f"  OK: {repo} (commit: {commit_sha[:7]})")
            return {"success": True, "sha": commit_sha}
        else:
            error = resp.json().get("message", resp.text)
            self.log(f"  FAIL: {repo} → {error}")
            return {"success": False, "error": error}

    def run(self, repo_list=None):
        """Execute the batch license operation."""
        if repo_list:
            repos_to_process = [{"name": r, "license": None} for r in repo_list]
        else:
            all_repos = self.get_all_repos()

            if self.skip_licensed:
                repos_to_process = [
                    r for r in all_repos if r.get("license") is None
                ]
                self.log(f"Filtered to {len(repos_to_process)} unlicensed repos "
                         f"(from {len(all_repos)} total)")
            else:
                repos_to_process = all_repos

        self.stats["total"] = len(repos_to_process)

        if self.use_checkpoint:
            self.load_checkpoint()
            repos_to_process = [
                r for r in repos_to_process
                if r["name"] not in self.checkpoint_data["completed"]
            ]

        self.log(f"Starting batch license operation: {len(repos_to_process)} repos")
        self.log(f"Organization: {self.org}")
        self.log(f"License type: {self.license_type}")
        self.log(f"Owner: {self.owner}")
        self.log(f"Dry run: {self.dry_run}")
        self.log(f"Delay: {self.delay}s between requests")
        self.log("-" * 60)

        for i, repo_info in enumerate(repos_to_process, 1):
            repo_name = repo_info["name"]
            self.log(f"[{i}/{len(repos_to_process)}] Processing {repo_name}...")

            # Check if already has LICENSE file
            if self.skip_licensed and self.has_license(repo_name):
                self.log(f"  SKIP: {repo_name} (already has LICENSE)")
                self.stats["already_licensed"] += 1
                continue

            # Rate limit check every 10 repos
            if i % 10 == 0:
                self.check_rate_limit()

            result = self.add_license(repo_name)

            if result.get("success") or result.get("dry_run"):
                self.stats["success"] += 1
                self.checkpoint_data["completed"].append(repo_name)
            else:
                self.stats["failed"] += 1
                self.checkpoint_data["failed"].append({
                    "repo": repo_name,
                    "error": result.get("error", "unknown")
                })

            # Save checkpoint every 5 repos
            if i % 5 == 0 and self.use_checkpoint:
                self.save_checkpoint()

            # Rate limit delay
            if not self.dry_run:
                time.sleep(self.delay)

        # Final checkpoint
        if self.use_checkpoint:
            self.save_checkpoint()

        # Summary
        self.log("-" * 60)
        self.log("SUMMARY:")
        self.log(f"  Total:           {self.stats['total']}")
        self.log(f"  Success:         {self.stats['success']}")
        self.log(f"  Failed:          {self.stats['failed']}")
        self.log(f"  Skipped (has lic): {self.stats['already_licensed']}")
        self.log(f"  Log file:        {LOG_FILE}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch-add MIT LICENSE files to repositories via GitHub API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --org SuperInstance --token $GITHUB_TOKEN --dry-run
  %(prog)s --repos repo1,repo2,repo3 --token $GITHUB_TOKEN
  %(prog)s --org SuperInstance --token $GITHUB_TOKEN --delay 3 --checkpoint
        """
    )
    parser.add_argument("--org", default=DEFAULT_ORG, help="GitHub organization")
    parser.add_argument("--repos", help="Comma-separated list of specific repos")
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token")
    parser.add_argument("--license", default="mit", choices=["mit"], help="License type (only MIT supported)")
    parser.add_argument("--owner", default="", help="License copyright owner (default: org name)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay between requests")
    parser.add_argument("--checkpoint", action="store_true", help="Enable checkpoint/resume")
    parser.add_argument("--skip-licensed", action="store_true", default=True,
                        help="Skip repos that already have licenses")

    args = parser.parse_args()

    batcher = LicenseBatcher(
        token=args.token,
        org=args.org,
        dry_run=args.dry_run,
        delay=args.delay,
        license_type=args.license,
        owner=args.owner,
        skip_licensed=args.skip_licensed,
        use_checkpoint=args.checkpoint
    )

    repo_list = None
    if args.repos:
        repo_list = [r.strip() for r in args.repos.split(",") if r.strip()]

    batcher.run(repo_list)


if __name__ == "__main__":
    main()
