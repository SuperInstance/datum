#!/usr/bin/env python3
"""
batch_topics.py — Batch-add GitHub topics to repositories.

Standalone version (stdlib only, no third-party dependencies).

Usage:
    python -m datum_runtime.tools.batch_topics --input mapping.json --token $PAT --dry-run
    python -m datum_runtime.tools.batch_topics --input mapping.json --token $PAT --checkpoint

Input format (JSON):
    {"repo-name": ["topic1", "topic2"], ...}

Each line can also be an NDJSON object:
    {"repo": "name", "topics": ["tag1", "tag2"]}
"""

import argparse
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


class TopicBatcher:
    def __init__(self, token: str, org: str, dry_run: bool = False,
                 delay: float = DEFAULT_DELAY, checkpoint_file: str = None):
        self.token = token
        self.org = org
        self.dry_run = dry_run
        self.delay = delay
        self.checkpoint_file = checkpoint_file
        self.stats = {"success": 0, "failed": 0, "skipped": 0, "total": 0}
        self.checkpoint_data = {"completed": [], "failed": []}

    def _headers(self, accept: str = "application/vnd.github+json"):
        return {
            "Authorization": f"token {self.token}",
            "Accept": accept,
            "User-Agent": "datum-quartermaster/batch-topics/1.0",
            "Content-Type": "application/json",
        }

    def log(self, message: str):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"[{timestamp}] {message}"
        print(line)

    def _api_get(self, url: str, accept: str = "application/vnd.github+json"):
        req = urllib.request.Request(url, headers=self._headers(accept))
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

    def _api_put(self, url: str, data: dict, accept: str = "application/vnd.github+json"):
        encoded = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded, headers=self._headers(accept), method="PUT")
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

    def get_current_topics(self, repo: str):
        url = f"{GITHUB_API}/repos/{self.org}/{repo}/topics"
        status, data = self._api_get(url, accept="application/vnd.github.mercy-preview+json")
        if status == 200 and data:
            return data.get("names", [])
        return None

    def set_topics(self, repo: str, topics: list):
        existing = self.get_current_topics(repo)
        if existing is not None:
            merged = list(set(existing + topics))
            merged = [t.lower().strip() for t in merged[:20]]
        else:
            merged = [t.lower().strip() for t in topics[:20]]

        if self.dry_run:
            self.log(f"[DRY RUN] {repo}: would set topics to {merged}")
            return {"dry_run": True, "topics": merged}

        url = f"{GITHUB_API}/repos/{self.org}/{repo}/topics"
        status, data = self._api_put(url, {"names": merged})

        if status == 200:
            actual_topics = data.get("names", []) if data else []
            self.log(f"  OK: {repo} → {actual_topics}")
            return {"success": True, "topics": actual_topics}
        else:
            error = data.get("message", "unknown") if data else "unknown"
            self.log(f"  FAIL: {repo} → {error}")
            return {"success": False, "error": error}

    def load_mapping(self, filepath: str) -> dict:
        """Load repo→topics mapping from JSON or NDJSON file."""
        with open(filepath) as f:
            content = f.read().strip()

        # Try NDJSON first (array of {repo, topics} objects)
        try:
            items = [json.loads(line) for line in content.splitlines() if line.strip()]
            if items and isinstance(items[0], dict) and "repo" in items[0]:
                return {item["repo"]: item["topics"] for item in items}
        except (json.JSONDecodeError, KeyError):
            pass

        # Try plain JSON dict
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        print("ERROR: Could not parse input file. Expected JSON dict or NDJSON.", file=sys.stderr)
        sys.exit(1)

    def run(self, mapping: dict):
        self.stats["total"] = len(mapping)

        if self.checkpoint_file:
            self.load_checkpoint()
            mapping = {
                k: v for k, v in mapping.items()
                if k not in self.checkpoint_data["completed"]
            }

        self.log(f"Starting batch topic operation: {len(mapping)} repos")
        self.log(f"Organization: {self.org}")
        self.log(f"Dry run: {self.dry_run}")
        self.log(f"Delay: {self.delay}s between requests")
        self.log("-" * 60)

        for i, (repo, topics) in enumerate(mapping.items(), 1):
            self.log(f"[{i}/{len(mapping)}] Processing {repo}...")

            if repo in self.checkpoint_data.get("completed", []):
                self.log(f"  SKIP: {repo} (already completed)")
                self.stats["skipped"] += 1
                continue

            if i % 10 == 0:
                self.check_rate_limit()

            result = self.set_topics(repo, topics)

            if result.get("success") or result.get("dry_run"):
                self.stats["success"] += 1
                self.checkpoint_data["completed"].append(repo)
            else:
                self.stats["failed"] += 1
                self.checkpoint_data["failed"].append({
                    "repo": repo,
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
        self.log(f"  Total:    {self.stats['total']}")
        self.log(f"  Success:  {self.stats['success']}")
        self.log(f"  Failed:   {self.stats['failed']}")
        self.log(f"  Skipped:  {self.stats['skipped']}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch-add GitHub topics to repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input topics.json --token $GITHUB_TOKEN --dry-run
  %(prog)s --input topics.json --token $GITHUB_TOKEN --checkpoint
  %(prog)s --input topics.json --token $GITHUB_TOKEN --delay 3
        """
    )
    parser.add_argument("--input", required=True, help="Path to JSON mapping file")
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token")
    parser.add_argument("--org", default=DEFAULT_ORG, help="GitHub organization (default: SuperInstance)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay between requests in seconds")
    parser.add_argument("--checkpoint", help="Save/load progress from this checkpoint file")

    args = parser.parse_args()

    batcher = TopicBatcher(
        token=args.token,
        org=args.org,
        dry_run=args.dry_run,
        delay=args.delay,
        checkpoint_file=args.checkpoint
    )

    mapping = batcher.load_mapping(args.input)

    if not mapping:
        print("ERROR: No mappings found in input file.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(mapping)} repo mappings from {args.input}")
    batcher.run(mapping)


if __name__ == "__main__":
    main()
