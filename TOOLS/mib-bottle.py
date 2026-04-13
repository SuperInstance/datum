#!/usr/bin/env python3
"""
mib-bottle.py — Create Message-in-a-Bottle (MiB) files for fleet communication.

Usage:
    python3 mib-bottle.py --vessel oracle1 --type check-in --message "Hello fleet"
    python3 mib-bottle.py --vessel fleet --type signal --message "Audit complete" --token $PAT
    python3 mib-bottle.py --local --vessel babel --type question --message "Status?"

Options:
    --vessel NAME       Target vessel name (org repo name, without org prefix)
    --type TYPE         Message type: check-in, signal, alert, question, deliverable, handoff
    --message TEXT      The message content
    --token TOKEN       GitHub PAT (required for remote commit, omit for local file)
    --org ORG           GitHub organization (default: SuperInstance)
    --local             Create file locally instead of committing to GitHub
    --output-dir DIR    Local output directory (default: ./mib-output)
    --sender NAME       Sender name (default: datum)
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' module required. Install with: pip install requests")
    sys.exit(1)

GITHUB_API = "https://api.github.com"
DEFAULT_ORG = "SuperInstance"
DEFAULT_SENDER = "datum"

VALID_TYPES = ["check-in", "signal", "alert", "question", "deliverable", "handoff", "info"]


def generate_mib_content(sender: str, vessel: str, msg_type: str, message: str) -> str:
    """Generate the MiB markdown content."""
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    date_slug = now.strftime("%Y-%m-%d")

    type_emoji = {
        "check-in": "👋",
        "signal": "📡",
        "alert": "⚠️",
        "question": "❓",
        "deliverable": "📦",
        "handoff": "🔄",
        "info": "ℹ️"
    }

    emoji = type_emoji.get(msg_type, " cork")

    content = f"""---
sender: {sender}
type: {msg_type}
vessel: {vessel}
timestamp: {timestamp}
---

# {emoji} Message in a Bottle

**From:** {sender}
**To:** {vessel if vessel != 'fleet' else 'All Fleet Vessels'}
**Type:** {msg_type}
**Date:** {timestamp}

---

{message}

---

*This is a Message-in-a-Bottle from the SuperInstance fleet.*
*Protocol: MiB v1.0 | Sender: {sender} | {timestamp}*
"""

    return content


def get_mib_path(vessel: str, msg_type: str, sender: str) -> str:
    """Determine the file path within the target vessel repo."""
    now = datetime.now(timezone.utc)
    date_slug = now.strftime("%Y-%m-%d")

    if vessel.lower() == "fleet":
        # Fleet-wide messages go to for-fleet/ directory
        filename = f"for-fleet/{date_slug}-{sender}-{msg_type}.md"
    else:
        # Vessel-specific messages go to for-{vessel}/ directory
        safe_vessel = vessel.lower().replace(" ", "-")
        filename = f"for-{safe_vessel}/{date_slug}-{sender}-{msg_type}.md"

    return filename


def commit_to_github(org: str, vessel: str, file_path: str,
                     content: str, token: str, sender: str, msg_type: str):
    """Commit the MiB file to the target vessel repo via GitHub API."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": f"datum-quartermaster/mib-bottle/1.0"
    })

    repo = vessel if "/" in vessel else f"{org}/{vessel}"

    # Get default branch
    resp = session.get(f"{GITHUB_API}/repos/{repo}")
    if resp.status_code != 200:
        print(f"ERROR: Cannot access repo {repo}: {resp.json().get('message', resp.text)}")
        return False

    branch = resp.json().get("default_branch", "main")

    # Check if directory already exists (look for existing files)
    dir_path = "/".join(file_path.split("/")[:-1])
    encoded_content = base64.b64encode(content.encode()).decode()

    # Create the file
    commit_message = f"[I2I:SIGNAL] {sender}:mib — MiB to {vessel} ({msg_type})"
    resp = session.put(
        f"{GITHUB_API}/repos/{repo}/contents/{file_path}",
        json={
            "message": commit_message,
            "content": encoded_content,
            "branch": branch
        }
    )

    if resp.status_code == 201:
        commit_sha = resp.json().get("commit", {}).get("sha", "unknown")
        print(f"SUCCESS: MiB committed to {repo}/{file_path}")
        print(f"  Commit SHA: {commit_sha[:7]}")
        print(f"  Commit message: {commit_message}")
        return True
    else:
        error = resp.json().get("message", resp.text)
        print(f"ERROR: Failed to commit MiB: {error}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Create Message-in-a-Bottle (MiB) for fleet communication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --vessel oracle1 --type check-in --message "New Quartermaster activated"
  %(prog)s --vessel fleet --type signal --message "Audit complete" --token $PAT
  %(prog)s --local --vessel babel --type question --message "What's your status?"
        """
    )
    parser.add_argument("--vessel", required=True,
                        help="Target vessel name or 'fleet' for fleet-wide")
    parser.add_argument("--type", required=True, choices=VALID_TYPES,
                        help="Message type")
    parser.add_argument("--message", required=True,
                        help="Message content (use quotes for multi-word)")
    parser.add_argument("--token", help="GitHub PAT (omit for --local mode)")
    parser.add_argument("--org", default=DEFAULT_ORG, help="GitHub organization")
    parser.add_argument("--local", action="store_true",
                        help="Create file locally instead of committing")
    parser.add_argument("--output-dir", default="./mib-output",
                        help="Local output directory")
    parser.add_argument("--sender", default=DEFAULT_SENDER, help="Sender name")

    args = parser.parse_args()

    # Generate content
    content = generate_mib_content(
        sender=args.sender,
        vessel=args.vessel,
        msg_type=args.type,
        message=args.message
    )

    file_path = get_mib_path(args.vessel, args.type, args.sender)

    if args.local or not args.token:
        # Local mode
        output_path = os.path.join(args.output_dir, args.vessel, file_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(content)
        print(f"LOCAL: MiB written to {output_path}")
        print(f"  Vessel: {args.vessel}")
        print(f"  Type: {args.type}")
        print(f"  Path: {file_path}")
    else:
        # Remote mode — commit to GitHub
        success = commit_to_github(
            org=args.org,
            vessel=args.vessel,
            file_path=file_path,
            content=content,
            token=args.token,
            sender=args.sender,
            msg_type=args.type
        )
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
