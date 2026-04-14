#!/usr/bin/env python3
"""
batch-topics.py — Batch-add GitHub topics to repositories.

Usage:
    python3 batch-topics.py --input mapping.json --token GITHUB_TOKEN [--dry-run] [--org SuperInstance]
    python3 batch-topics.py --input mapping.csv --token GITHUB_TOKEN --csv [--dry-run]

Input formats:
    JSON: {"repo-name": ["topic1", "topic2"], ...}
    CSV:  repo-name,topic1,topic2,topic3

Options:
    --input FILE    Path to JSON or CSV mapping file
    --token TOKEN   GitHub Personal Access Token
    --org ORG       GitHub organization (default: SuperInstance)
    --dry-run       Preview changes without applying them
    --delay SECS    Delay between requests in seconds (default: 2.0)
    --csv           Treat input as CSV format
    --checkpoint    Save/load progress from checkpoint file
    --verbose       Enable verbose output
"""

import argparse
import csv
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
DEFAULT_DELAY = 2.0
CHECKPOINT_FILE = "batch-topics-progress.json"
LOG_FILE = f"batch-topics-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.log"


class TopicBatcher:
    def __init__(self, token: str, org: str, dry_run: bool = False,
                 delay: float = DEFAULT_DELAY, verbose: bool = False,
                 use_checkpoint: bool = False):
        self.token = token
        self.org = org
        self.dry_run = dry_run
        self.delay = delay
        self.verbose = verbose
        self.use_checkpoint = use_checkpoint
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "datum-quartermaster/batch-topics/1.0"
        })
        self.stats = {"success": 0, "failed": 0, "skipped": 0, "total": 0}
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

    def get_current_topics(self, repo: str):
        """Get current topics for a repo."""
        resp = self.session.get(
            f"{GITHUB_API}/repos/{self.org}/{repo}/topics",
            headers={"Accept": "application/vnd.github.mercy-preview+json"}
        )
        if resp.status_code == 200:
            return resp.json().get("names", [])
        return None

    def set_topics(self, repo: str, topics: list):
        """Set topics for a repo."""
        # Merge with existing topics if possible
        existing = self.get_current_topics(repo)
        if existing is not None:
            merged = list(set(existing + topics))
            # GitHub topics are lowercase and max 20 per repo
            merged = [t.lower().strip() for t in merged[:20]]
        else:
            merged = [t.lower().strip() for t in topics[:20]]

        if self.dry_run:
            self.log(f"[DRY RUN] {repo}: would set topics to {merged}")
            return {"dry_run": True, "topics": merged}

        resp = self.session.put(
            f"{GITHUB_API}/repos/{self.org}/{repo}/topics",
            json={"names": merged}
        )

        if resp.status_code == 200:
            result = resp.json()
            actual_topics = result.get("names", [])
            self.log(f"  OK: {repo} → {actual_topics}")
            return {"success": True, "topics": actual_topics}
        else:
            error = resp.json().get("message", resp.text)
            self.log(f"  FAIL: {repo} → {error}")
            return {"success": False, "error": error}

    def load_mapping_json(self, filepath: str) -> dict:
        """Load repo→topics mapping from JSON."""
        with open(filepath) as f:
            return json.load(f)

    def load_mapping_csv(self, filepath: str) -> dict:
        """Load repo→topics mapping from CSV."""
        mapping = {}
        with open(filepath, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or not row[0].strip():
                    continue
                repo = row[0].strip()
                topics = [t.strip() for t in row[1:] if t.strip()]
                if topics:
                    mapping[repo] = topics
        return mapping

    def run(self, mapping: dict):
        """Execute the batch topic operation."""
        self.stats["total"] = len(mapping)

        if self.use_checkpoint:
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

            # Check if already done
            if repo in self.checkpoint_data.get("completed", []):
                self.log(f"  SKIP: {repo} (already completed)")
                self.stats["skipped"] += 1
                continue

            # Rate limit check every 10 repos
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
        self.log(f"  Total:    {self.stats['total']}")
        self.log(f"  Success:  {self.stats['success']}")
        self.log(f"  Failed:   {self.stats['failed']}")
        self.log(f"  Skipped:  {self.stats['skipped']}")
        self.log(f"  Log file: {LOG_FILE}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch-add GitHub topics to repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input topics.json --token $GITHUB_TOKEN --dry-run
  %(prog)s --input mapping.csv --token $GITHUB_TOKEN --csv
  %(prog)s --input topics.json --token $GITHUB_TOKEN --delay 3 --checkpoint
        """
    )
    parser.add_argument("--input", required=True, help="Path to JSON or CSV mapping file")
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token")
    parser.add_argument("--org", default=DEFAULT_ORG, help="GitHub organization (default: SuperInstance)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay between requests in seconds")
    parser.add_argument("--csv", action="store_true", help="Treat input as CSV format")
    parser.add_argument("--checkpoint", action="store_true", help="Enable checkpoint/resume support")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    batcher = TopicBatcher(
        token=args.token,
        org=args.org,
        dry_run=args.dry_run,
        delay=args.delay,
        verbose=args.verbose,
        use_checkpoint=args.checkpoint
    )

    if args.csv:
        mapping = batcher.load_mapping_csv(args.input)
    else:
        mapping = batcher.load_mapping_json(args.input)

    if not mapping:
        print("ERROR: No mappings found in input file.")
        sys.exit(1)

    print(f"Loaded {len(mapping)} repo mappings from {args.input}")
    batcher.run(mapping)


if __name__ == "__main__":
    main()
