"""
datum_runtime.tools — Fleet hygiene CLI tools.

All tools are standalone (stdlib only) and runnable as modules:

    python -m datum_runtime.tools.audit_scanner --org SuperInstance --token $PAT
    python -m datum_runtime.tools.batch_topics --input mapping.json --token $PAT --dry-run
    python -m datum_runtime.tools.batch_license --org SuperInstance --token $PAT --dry-run
    python -m datum_runtime.tools.mib_bottle --vessel fleet --type signal --message "hi" --token $PAT
"""

TOOL_REGISTRY = {
    "audit-scanner": {
        "description": "Scan GitHub org repos for hygiene issues (descriptions, topics, licenses, empty/stale/fork detection)",
        "module": "datum_runtime.tools.audit_scanner",
        "file": "audit_scanner.py",
        "args": {
            "required": ["--org", "--token"],
            "optional": ["--output", "--json", "--stale-days", "--min-size", "--top"],
        },
        "output": "Markdown report or JSON (with --json)",
        "rate_limit": "1.5s between API calls, auto-pauses at <100 remaining",
        "example": "python -m datum_runtime.tools.audit_scanner --org SuperInstance --token $PAT --output audit.json --json",
    },
    "batch-topics": {
        "description": "Batch-add GitHub topics to repos from a JSON/NDJSON mapping file",
        "module": "datum_runtime.tools.batch_topics",
        "file": "batch_topics.py",
        "args": {
            "required": ["--input", "--token"],
            "optional": ["--org", "--dry-run", "--delay", "--checkpoint"],
        },
        "input_format": '{"repo-name": ["topic1", "topic2"]} or NDJSON: {"repo": "name", "topics": ["t1"]}',
        "rate_limit": "1.5s between API calls, auto-pauses at <100 remaining",
        "example": "python -m datum_runtime.tools.batch_topics --input topics.json --token $PAT --dry-run --checkpoint progress.json",
    },
    "batch-license": {
        "description": "Batch-add MIT LICENSE files to unlicensed repos via GitHub Contents API",
        "module": "datum_runtime.tools.batch_license",
        "file": "batch_license.py",
        "args": {
            "required": ["--token"],
            "optional": ["--org", "--license-type", "--owner", "--dry-run", "--delay", "--checkpoint"],
        },
        "rate_limit": "1.5s between API calls, auto-pauses at <100 remaining",
        "example": "python -m datum_runtime.tools.batch_license --org SuperInstance --token $PAT --dry-run",
    },
    "mib-bottle": {
        "description": "Create Message-in-a-Bottle (MiB) files for fleet communication, commit to target vessel repo",
        "module": "datum_runtime.tools.mib_bottle",
        "file": "mib_bottle.py",
        "args": {
            "required": ["--vessel", "--type", "--message"],
            "optional": ["--token", "--org", "--local", "--output-dir", "--sender"],
        },
        "message_types": ["check-in", "signal", "alert", "question", "deliverable", "handoff", "info"],
        "example": "python -m datum_runtime.tools.mib_bottle --vessel fleet --type signal --message 'Audit complete' --token $PAT",
    },
}
