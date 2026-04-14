#!/usr/bin/env python3
"""
mib_bottle.py — Create Message-in-a-Bottle (MiB) files for fleet communication.

Standalone version (stdlib only, no third-party dependencies).

Usage:
    python -m datum_runtime.tools.mib_bottle --vessel oracle1 --type check-in --message "Hello fleet" --token $PAT
    python -m datum_runtime.tools.mib_bottle --vessel fleet --type signal --message "Audit complete" --token $PAT
    python -m datum_runtime.tools.mib_bottle --local --vessel babel --type question --message "Status?"

Options:
    --vessel NAME       Target vessel name or 'fleet' for fleet-wide
    --type TYPE         Message type: check-in, signal, alert, question, deliverable, handoff, info
    --message TEXT      The message content
    --token TOKEN       GitHub PAT (required for remote commit)
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
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

GITHUB_API = "https://api.github.com"
DEFAULT_ORG = "SuperInstance"
DEFAULT_SENDER = "datum"

VALID_TYPES = ["check-in", "signal", "alert", "question", "deliverable", "handoff", "info"]


def _headers(token: str):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "datum-quartermaster/mib-bottle/1.0",
        "Content-Type": "application/json",
    }


def _api_get(url: str, token: str):
    req = urllib.request.Request(url, headers=_headers(token))
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


def _api_put(url: str, data: dict, token: str):
    encoded = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, headers=_headers(token), method="PUT")
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


def generate_mib_content(sender: str, vessel: str, msg_type: str, message: str) -> str:
    """Generate the MiB markdown content."""
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    type_emoji = {
        "check-in": "👋",
        "signal": "📡",
        "alert": "⚠️",
        "question": "❓",
        "deliverable": "📦",
        "handoff": "🔄",
        "info": "ℹ️"
    }
    emoji = type_emoji.get(msg_type, "🫙")

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
        filename = f"message-in-a-bottle/for-fleet/{date_slug}-{sender}-{msg_type}.md"
    else:
        safe_vessel = vessel.lower().replace(" ", "-")
        filename = f"message-in-a-bottle/for-{safe_vessel}/{date_slug}-{sender}-{msg_type}.md"

    return filename


def commit_to_github(org: str, vessel: str, file_path: str,
                     content: str, token: str, sender: str, msg_type: str):
    """Commit the MiB file to the target vessel repo via GitHub API."""
    repo = vessel if "/" in vessel else f"{org}/{vessel}"

    # Get default branch
    status, data = _api_get(f"{GITHUB_API}/repos/{repo}", token)
    if status != 200:
        error = data.get("message", "unknown") if data else "unknown"
        print(f"ERROR: Cannot access repo {repo}: {error}")
        return False

    branch = data.get("default_branch", "main") if data else "main"

    encoded_content = base64.b64encode(content.encode()).decode()

    commit_message = f"[I2I:SIGNAL] {sender}:mib — MiB to {vessel} ({msg_type})"
    status, data = _api_put(
        f"{GITHUB_API}/repos/{repo}/contents/{file_path}",
        {
            "message": commit_message,
            "content": encoded_content,
            "branch": branch
        },
        token
    )

    if status == 201:
        commit_sha = data.get("commit", {}).get("sha", "unknown") if data else "unknown"
        print(f"SUCCESS: MiB committed to {repo}/{file_path}")
        print(f"  Commit SHA: {commit_sha[:7]}")
        print(f"  Commit message: {commit_message}")
        return True
    else:
        error = data.get("message", "unknown") if data else "unknown"
        print(f"ERROR: Failed to commit MiB: {error}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Create Message-in-a-Bottle (MiB) for fleet communication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --vessel oracle1 --type check-in --message "New Quartermaster activated" --token $PAT
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

    content = generate_mib_content(
        sender=args.sender,
        vessel=args.vessel,
        msg_type=args.type,
        message=args.message
    )

    file_path = get_mib_path(args.vessel, args.type, args.sender)

    if args.local or not args.token:
        output_path = os.path.join(args.output_dir, args.vessel, file_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(content)
        print(f"LOCAL: MiB written to {output_path}")
        print(f"  Vessel: {args.vessel}")
        print(f"  Type: {args.type}")
        print(f"  Path: {file_path}")
    else:
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
