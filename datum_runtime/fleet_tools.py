"""
datum_runtime.fleet_tools — GitHub API operations for fleet hygiene.

Provides functions for scanning, tagging, licensing, and auditing repos
within a GitHub organization. All HTTP operations use ``urllib.request``
(zero external dependencies) and implement rate limiting with a 1.5s
delay between requests.

Functions:
    scan_org          — Scan all repos, return health stats (green/yellow/red/dead)
    tag_repos         — Add topics to repos
    add_licenses      — Add LICENSE files to repos missing them
    audit_repos       — Find repos missing descriptions, topics, licenses
    repo_stats        — Get overall fleet statistics

All functions support checkpointing progress to a JSON file so long-running
operations can be resumed after interruption.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RATE_LIMIT_DELAY = 1.5  # seconds between API requests
CHECKPOINT_FILE = ".datum_fleet_checkpoint.json"
PER_PAGE = 100

# Standard license templates (simplified text content)
LICENSE_TEMPLATES = {
    "MIT": """MIT License

Copyright (c) {year} {org}

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
""",
    "Apache-2.0": """Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

1. Definitions.

"License" shall mean the terms and conditions for use, reproduction,
and distribution as defined by Sections 1 through 9 of this document.

"Licensor" shall mean the copyright owner or entity authorized by
the copyright owner that is granting the License.

"Legal Entity" shall mean the union of the acting entity and all
other entities that control, are controlled by, or are under common
control with that entity.

"You" (or "Your") shall mean an individual or Legal Entity
exercising permissions granted by this License.

2. Grant of Copyright License. Subject to the terms and conditions of
this License, each Contributor hereby grants to You a perpetual,
worldwide, non-exclusive, no-charge, royalty-free, irrevocable
copyright license to reproduce, prepare Derivative Works of,
publicly display, publicly perform, sublicense, and distribute the
Work and such Derivative Works in Source or Object form.
""",
    "BSD-3-Clause": """BSD 3-Clause License

Copyright (c) {year}, {org}
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
""",
}


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _api_request(url: str, token: str = "", method: str = "GET",
                 data: Optional[bytes] = None) -> Dict[str, Any]:
    """
    Make a GitHub API request using urllib.

    Implements rate limiting (1.5s delay between requests) and
    authentication via the Authorization header.

    Args:
        url: Full GitHub API URL
        token: GitHub personal access token
        method: HTTP method (GET, POST, PUT, DELETE)
        data: Request body bytes

    Returns:
        Parsed JSON response dict

    Raises:
        Exception: On HTTP errors (with status code info)
    """
    time.sleep(RATE_LIMIT_DELAY)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "datum-runtime/0.2.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data:
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise Exception(f"GitHub API {e.code}: {body[:200]}")
    except urllib.error.URLError as e:
        raise Exception(f"GitHub API connection error: {e}")


def _list_repos(org: str, token: str = "") -> List[Dict[str, Any]]:
    """
    List all repos in a GitHub org with pagination.

    Returns a list of repo dicts from the GitHub API.
    """
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{org}/repos?per_page={PER_PAGE}&page={page}&sort=updated"
        result = _api_request(url, token)
        if not isinstance(result, list):
            break
        repos.extend(result)
        if len(result) < PER_PAGE:
            break
        page += 1
    return repos


def _save_checkpoint(data: Dict[str, Any], path: Optional[str] = None) -> None:
    """Save operation checkpoint to JSON file for resumability."""
    cp_path = Path(path or CHECKPOINT_FILE)
    cp_path.write_text(json.dumps(data, indent=2))


def _load_checkpoint(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load operation checkpoint from JSON file."""
    cp_path = Path(path or CHECKPOINT_FILE)
    if cp_path.exists():
        try:
            return json.loads(cp_path.read_text())
        except Exception:
            return None
    return None


def _clear_checkpoint(path: Optional[str] = None) -> None:
    """Remove checkpoint file."""
    cp_path = Path(path or CHECKPOINT_FILE)
    if cp_path.exists():
        cp_path.unlink()


# ---------------------------------------------------------------------------
# Health classification
# ---------------------------------------------------------------------------

def _classify_repo(repo: Dict[str, Any]) -> str:
    """
    Classify a repo's health based on its metadata.

    Returns:
        "green"  — Active, well-maintained repo
        "yellow" — Needs attention (missing description, topics, etc.)
        "red"    — Stale or minimal maintenance
        "dead"   — Archived, empty, or no activity in >2 years
    """
    if repo.get("archived", False):
        return "dead"

    if repo.get("size", 0) == 0 and not repo.get("description"):
        return "dead"

    pushed_at = repo.get("pushed_at", "")
    if pushed_at:
        try:
            from datetime import datetime
            pushed = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - pushed).days
            if age_days > 730:  # 2 years
                return "dead"
            if age_days > 365:  # 1 year
                return "red"
        except (ValueError, TypeError):
            pass

    # Check for basic metadata
    issues = []
    if not repo.get("description"):
        issues.append("no description")
    if not repo.get("topics"):
        issues.append("no topics")
    if not repo.get("license") and not _repo_has_license_file(repo, ""):
        issues.append("no license")

    if len(issues) >= 2:
        return "red"
    elif len(issues) == 1:
        return "yellow"

    return "green"


def _repo_has_license_file(repo: Dict[str, Any], token: str) -> bool:
    """Check if a repo has a LICENSE file (case-insensitive check via API)."""
    name = repo.get("name", "")
    org = repo.get("owner", {}).get("login", "")
    if not org or not name:
        return False
    try:
        url = f"https://api.github.com/repos/{org}/{name}/contents/"
        contents = _api_request(url, token)
        if isinstance(contents, list):
            for item in contents:
                if item.get("name", "").lower().startswith("license"):
                    return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_org(org: str, token: str = "") -> Dict[str, Any]:
    """
    Scan all repos in a GitHub org and return health stats.

    Classifies each repo as green, yellow, red, or dead based on:
    - Activity (pushed_at)
    - Metadata (description, topics, license)
    - Status (archived, empty)

    Args:
        org: GitHub organization name
        token: GitHub personal access token

    Returns:
        Dict with 'stats', 'repos', and 'summary' keys
    """
    try:
        repos = _list_repos(org, token)
    except Exception as e:
        return {"error": str(e), "org": org}

    classified = {"green": [], "yellow": [], "red": [], "dead": []}
    repo_details = []

    for repo in repos:
        status = _classify_repo(repo)
        name = repo.get("full_name", repo.get("name", "unknown"))
        classified[status].append(name)

        issues = []
        if not repo.get("description"):
            issues.append("no description")
        if not repo.get("topics"):
            issues.append("no topics")
        if not repo.get("license") and status != "dead":
            issues.append("no license")

        repo_details.append({
            "name": name,
            "status": status,
            "issues": issues,
            "updated_at": repo.get("updated_at", ""),
            "pushed_at": repo.get("pushed_at", ""),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
        })

    stats = {
        "total": len(repos),
        "green": len(classified["green"]),
        "yellow": len(classified["yellow"]),
        "red": len(classified["red"]),
        "dead": len(classified["dead"]),
        "health_score": (
            (len(classified["green"]) * 100)
            + (len(classified["yellow"]) * 50)
            + (len(classified["red"]) * 25)
        ) // max(len(repos), 1),
    }

    return {
        "org": org,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "repos": sorted(repo_details, key=lambda r: r["name"]),
        "summary": f"{stats['green']} healthy, {stats['yellow']} needs attention, "
                   f"{stats['red']} stale, {stats['dead']} dead out of {stats['total']}",
    }


def tag_repos(org: str, token: str, mapping: Dict[str, List[str]],
              dry_run: bool = False) -> Dict[str, Any]:
    """
    Add topics to repos in a GitHub org.

    Args:
        org: GitHub organization name
        token: GitHub personal access token
        mapping: Dict of repo_name -> list of topics to add
        dry_run: If True, report what would be done without making changes

    Returns:
        Dict with 'actions' list and summary
    """
    actions = []
    errors = []

    # Load checkpoint
    checkpoint = _load_checkpoint()
    if checkpoint and checkpoint.get("operation") == "tag_repos":
        already_tagged = set(checkpoint.get("completed", []))
    else:
        already_tagged = set()

    try:
        repos = _list_repos(org, token)
    except Exception as e:
        return {"error": str(e), "org": org}

    checkpoint_data = {
        "operation": "tag_repos",
        "org": org,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed": list(already_tagged),
    }

    for repo in repos:
        name = repo.get("name", "")
        full_name = repo.get("full_name", "")

        if full_name in already_tagged:
            continue

        topics = mapping.get(name, mapping.get(full_name, []))
        if not topics:
            continue

        if dry_run:
            actions.append(f"[DRY-RUN] Would tag {full_name}: {', '.join(topics)}")
            already_tagged.add(full_name)
            continue

        try:
            # Merge with existing topics
            existing_topics = repo.get("topics", [])
            new_topics = list(set(existing_topics + topics))
            url = f"https://api.github.com/repos/{org}/{name}/topics"
            data = json.dumps({"names": new_topics}).encode()
            _api_request(url, token, method="PUT", data=data)
            actions.append(f"Tagged {full_name}: {', '.join(topics)}")
            already_tagged.add(full_name)
            checkpoint_data["completed"] = list(already_tagged)
            _save_checkpoint(checkpoint_data)
        except Exception as e:
            errors.append(f"Failed to tag {full_name}: {e}")

    _clear_checkpoint() if not dry_run else None

    return {
        "org": org,
        "actions": actions,
        "errors": errors,
        "total_tagged": len([a for a in actions if not a.startswith("[DRY-RUN]")]),
    }


def add_licenses(org: str, token: str, license_type: str = "MIT",
                 dry_run: bool = False) -> Dict[str, Any]:
    """
    Add LICENSE files to repos missing them.

    Args:
        org: GitHub organization name
        token: GitHub personal access token
        license_type: Type of license (MIT, Apache-2.0, BSD-3-Clause)
        dry_run: If True, report what would be done without making changes

    Returns:
        Dict with 'actions' list and summary
    """
    actions = []
    errors = []

    # Load checkpoint
    checkpoint = _load_checkpoint()
    if checkpoint and checkpoint.get("operation") == "add_licenses":
        already_done = set(checkpoint.get("completed", []))
    else:
        already_done = set()

    template = LICENSE_TEMPLATES.get(license_type)
    if not template:
        return {"error": f"Unknown license type: {license_type}. "
                        f"Available: {', '.join(LICENSE_TEMPLATES.keys())}"}

    try:
        repos = _list_repos(org, token)
    except Exception as e:
        return {"error": str(e), "org": org}

    checkpoint_data = {
        "operation": "add_licenses",
        "org": org,
        "license_type": license_type,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed": list(already_done),
    }

    year = datetime.now(timezone.utc).year

    for repo in repos:
        name = repo.get("name", "")
        full_name = repo.get("full_name", "")

        if full_name in already_done:
            continue

        # Skip if already has a license via GitHub API
        if repo.get("license"):
            continue

        # Skip archived repos
        if repo.get("archived", False):
            continue

        content = template.format(year=year, org=org)
        encoded_content = __import__("base64").b64encode(content.encode()).decode()

        if dry_run:
            actions.append(f"[DRY-RUN] Would add {license_type} license to {full_name}")
            already_done.add(full_name)
            continue

        try:
            # Check if LICENSE file already exists
            url = f"https://api.github.com/repos/{org}/{name}/contents/LICENSE"
            try:
                _api_request(url, token)
                # File exists already
                already_done.add(full_name)
                continue
            except Exception:
                pass  # File doesn't exist, proceed to create

            # Create the LICENSE file
            url = f"https://api.github.com/repos/{org}/{name}/contents/LICENSE"
            data = json.dumps({
                "message": f"docs: add {license_type} license",
                "content": encoded_content,
            }).encode()
            _api_request(url, token, method="PUT", data=data)
            actions.append(f"Added {license_type} license to {full_name}")
            already_done.add(full_name)
            checkpoint_data["completed"] = list(already_done)
            _save_checkpoint(checkpoint_data)
        except Exception as e:
            errors.append(f"Failed to add license to {full_name}: {e}")

    _clear_checkpoint() if not dry_run else None

    return {
        "org": org,
        "license_type": license_type,
        "actions": actions,
        "errors": errors,
        "total_licensed": len([a for a in actions if not a.startswith("[DRY-RUN]")]),
    }


def audit_repos(org: str, token: str = "") -> Dict[str, Any]:
    """
    Find repos with missing metadata — descriptions, topics, licenses.

    Args:
        org: GitHub organization name
        token: GitHub personal access token

    Returns:
        Dict with categorized issues per repo
    """
    try:
        repos = _list_repos(org, token)
    except Exception as e:
        return {"error": str(e), "org": org}

    findings = []
    for repo in repos:
        name = repo.get("full_name", repo.get("name", "unknown"))
        issues = []

        if not repo.get("description"):
            issues.append("missing_description")

        if not repo.get("topics"):
            issues.append("missing_topics")

        if not repo.get("license"):
            issues.append("missing_license")

        if not repo.get("homepage"):
            issues.append("missing_homepage")

        # Check for README
        has_readme = False
        try:
            url = f"https://api.github.com/repos/{org}/{repo.get('name', '')}/readme"
            _api_request(url, token)
            has_readme = True
        except Exception:
            pass
        if not has_readme:
            issues.append("missing_readme")

        # Default branch naming
        default_branch = repo.get("default_branch", "")
        if default_branch == "master":
            issues.append("default_branch_is_master")

        if issues:
            findings.append({
                "repo": name,
                "issues": issues,
                "stars": repo.get("stargazers_count", 0),
                "updated_at": repo.get("updated_at", ""),
            })

    # Summary stats
    total = len(repos)
    with_issues = len(findings)
    issue_counts: Dict[str, int] = {}
    for f in findings:
        for issue in f["issues"]:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    return {
        "org": org,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "total_repos": total,
        "repos_with_issues": with_issues,
        "repos_clean": total - with_issues,
        "issue_counts": issue_counts,
        "findings": findings,
        "top_issues": sorted(issue_counts.items(), key=lambda x: -x[1]),
    }


def repo_stats(org: str, token: str = "") -> Dict[str, Any]:
    """
    Get overall fleet statistics for a GitHub org.

    Combines scan, audit, and metadata into a comprehensive overview.

    Args:
        org: GitHub organization name
        token: GitHub personal access token

    Returns:
        Dict with comprehensive fleet statistics
    """
    scan_result = scan_org(org, token)
    if "error" in scan_result:
        return scan_result

    audit_result = audit_repos(org, token)

    # Language distribution
    try:
        repos = _list_repos(org, token)
        language_counts: Dict[str, int] = {}
        for repo in repos:
            lang = repo.get("language") or "Unknown"
            language_counts[lang] = language_counts.get(lang, 0) + 1
    except Exception:
        language_counts = {}

    # Sort by count
    sorted_languages = sorted(language_counts.items(), key=lambda x: -x[1])

    stats = scan_result.get("stats", {})
    return {
        "org": org,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "languages": sorted_languages[:20],
        "top_issues": audit_result.get("top_issues", []),
        "health_summary": scan_result.get("summary", ""),
        "audit": {
            "total_repos": audit_result.get("total_repos", 0),
            "repos_with_issues": audit_result.get("repos_with_issues", 0),
            "repos_clean": audit_result.get("repos_clean", 0),
            "issue_counts": audit_result.get("issue_counts", {}),
        },
        "recommendations": _generate_recommendations(stats, audit_result),
    }


def _generate_recommendations(stats: Dict[str, Any],
                               audit_result: Dict[str, Any]) -> List[str]:
    """
    Generate actionable recommendations based on fleet analysis.
    """
    recs = []

    dead_count = stats.get("dead", 0)
    if dead_count > 0:
        recs.append(f"Archive {dead_count} dead repo(s) to clean up the org")

    missing_desc = audit_result.get("issue_counts", {}).get("missing_description", 0)
    if missing_desc > 0:
        recs.append(f"Add descriptions to {missing_desc} repo(s)")

    missing_topics = audit_result.get("issue_counts", {}).get("missing_topics", 0)
    if missing_topics > 0:
        recs.append(f"Add topics to {missing_desc} repo(s) for discoverability")

    missing_license = audit_result.get("issue_counts", {}).get("missing_license", 0)
    if missing_license > 0:
        recs.append(f"Add licenses to {missing_license} repo(s)")

    yellow_count = stats.get("yellow", 0)
    if yellow_count > 0:
        recs.append(f"Review {yellow_count} repo(s) that need minor attention")

    health = stats.get("health_score", 0)
    if health >= 80:
        recs.append("Fleet health is good — maintain current practices")
    elif health >= 50:
        recs.append("Fleet health is moderate — address the items above")
    else:
        recs.append("Fleet health is low — significant cleanup recommended")

    return recs
