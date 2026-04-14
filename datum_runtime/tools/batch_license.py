#!/usr/bin/env python3
"""
batch_license.py — Batch-add MIT LICENSE files to repositories via GitHub API.

Standalone version (stdlib only, no third-party dependencies).

Usage:
    python -m datum_runtime.tools.batch_license --org SuperInstance --token $PAT --dry-run
    python -m datum_runtime.tools.batch_license --org SuperInstance --token $PAT --license-type MIT
    python -m datum_runtime.tools.batch_license --org SuperInstance --token $PAT --checkpoint

NOTE: This script creates LICENSE files via the GitHub Contents API (no local clone needed).
"""

import argparse
import base64
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

GITHUB_API = "https://api.github.com"
DEFAULT_ORG = "SuperInstance"
DEFAULT_DELAY = 1.5

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
                 owner: str = "", checkpoint_file: str = None):
        self.token = token
        self.org = org
        self.dry_run = dry_run
        self.delay = delay
        self.license_type = license_type
        self.owner = owner or org
        self.checkpoint_file = checkpoint_file
        self.stats = {"success": 0, "failed": 0, "skipped": 0, "total": 0, "already_licensed": 0}
        self.checkpoint_data = {"completed": [], "failed": []}

    def _headers(self):
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "datum-quartermaster/batch-license/1.0",
            "Content-Type": "application/json",
        }

    def log(self, message: str):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"[{timestamp}] {message}"
        print(line)

    def _api_get(self, url: str):
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body)
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8")
                return e.code, json.loads(body)
            except Exception:
                return e.code, {"message": str(e)}
        except Exception as e:
            return 0, {"message": str(e)}

    def _api_put(self, url: str, data: dict):
        encoded = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded, headers=self._headers(), method="PUT")
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body)
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8")
                return e.code, json.loads(body)
            except Exception:
                return e.code, {"message": str(e)}
        except Exception as e:
            return 0, {"message": str(e)}

    def load_checkpoint(self):
        if self.checkpoint_file and Path(self.checkpoint_file).exists():
            with open(self.checkpoint_file) as f:
                self.checkpoint_data = json.load(f)
            self.log(f"Loaded checkpoint: {len(self.checkpoint_data['completed'])} completed, "
                     f"{len(self.checkpoint_data['failed'])} failed")

    def save_checkpoint(self):
        if self.checkpoint_file:
            with open(self.checkpoint_file, "w") as f:
                json.dump(self.checkpoint_data, f, indent=2)

    def check_rate_limit(self):
        url = f"{GITHUB_API}/rate_limit"
        status, data = self._api_get(url)
        if status == 200 and data:
            remaining = data.get("rate", {}).get("remaining", 0)
            reset_ts = data.get("rate", {}).get("reset", 0)
            if remaining < 10:
                wait = max(reset_ts - int(time.time()), 60) + 10
                self.log(f"RATE LIMIT: {remaining} remaining. Waiting {wait}s...")
                time.sleep(wait)
            elif remaining < 100:
                self.log(f"RATE LIMIT WARNING: {remaining} remaining")
            return remaining
        return 0

    def get_all_repos(self):
        self.log(f"Fetching repos from {self.org}...")
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
        self.log(f"Found {len(repos)} repos total")
        return repos

    def has_license(self, repo: str) -> bool:
        url = f"{GITHUB_API}/repos/{self.org}/{repo}/contents/LICENSE"
        status, _ = self._api_get(url)
        return status == 200

    def get_default_branch(self, repo: str) -> str:
        url = f"{GITHUB_API}/repos/{self.org}/{repo}"
        status, data = self._api_get(url)
        if status == 200 and data:
            return data.get("default_branch", "main")
        return "main"

    def add_license(self, repo: str):
        year = str(datetime.now(timezone.utc).year)
        license_content = MIT_LICENSE_TEMPLATE.format(year=year, owner=self.owner)
        encoded_content = base64.b64encode(license_content.encode()).decode()
        branch = self.get_default_branch(repo)

        if self.dry_run:
            self.log(f"[DRY RUN] {repo}: would add MIT LICENSE to branch '{branch}'")
            return {"dry_run": True}

        url = f"{GITHUB_API}/repos/{self.org}/{repo}/contents/LICENSE"
        status, data = self._api_put(url, {
            "message": "[I2I:DELIVERABLE] datum:license — Add MIT LICENSE",
            "content": encoded_content,
            "branch": branch
        })

        if status == 201:
            commit_sha = data.get("commit", {}).get("sha", "unknown") if data else "unknown"
            self.log(f"  OK: {repo} (commit: {commit_sha[:7]})")
            return {"success": True, "sha": commit_sha}
        else:
            error = data.get("message", "unknown") if data else "unknown"
            self.log(f"  FAIL: {repo} → {error}")
            return {"success": False, "error": error}

    def run(self, repo_list=None):
        if repo_list:
            repos_to_process = [{"name": r, "license": None} for r in repo_list]
        else:
            all_repos = self.get_all_repos()
            repos_to_process = [
                r for r in all_repos if r.get("license") is None
            ]
            self.log(f"Filtered to {len(repos_to_process)} unlicensed repos "
                     f"(from {len(all_repos)} total)")

        self.stats["total"] = len(repos_to_process)

        if self.checkpoint_file:
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

            if self.has_license(repo_name):
                self.log(f"  SKIP: {repo_name} (already has LICENSE)")
                self.stats["already_licensed"] += 1
                continue

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

            if i % 5 == 0 and self.checkpoint_file:
                self.save_checkpoint()

            if not self.dry_run:
                time.sleep(self.delay)

        if self.checkpoint_file:
            self.save_checkpoint()

        self.log("-" * 60)
        self.log("SUMMARY:")
        self.log(f"  Total:             {self.stats['total']}")
        self.log(f"  Success:           {self.stats['success']}")
        self.log(f"  Failed:            {self.stats['failed']}")
        self.log(f"  Skipped (has lic): {self.stats['already_licensed']}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch-add MIT LICENSE files to repositories via GitHub API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --org SuperInstance --token $GITHUB_TOKEN --dry-run
  %(prog)s --org SuperInstance --token $GITHUB_TOKEN --license-type MIT
  %(prog)s --org SuperInstance --token $GITHUB_TOKEN --checkpoint
        """
    )
    parser.add_argument("--org", default=DEFAULT_ORG, help="GitHub organization")
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token")
    parser.add_argument("--license-type", default="MIT", help="License type (default: MIT)")
    parser.add_argument("--owner", default="", help="License copyright owner (default: org name)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay between requests")
    parser.add_argument("--checkpoint", help="Checkpoint file path for resume support")

    args = parser.parse_args()

    batcher = LicenseBatcher(
        token=args.token,
        org=args.org,
        dry_run=args.dry_run,
        delay=args.delay,
        license_type=args.license_type,
        owner=args.owner,
        checkpoint_file=args.checkpoint
    )

    batcher.run()


if __name__ == "__main__":
    main()
