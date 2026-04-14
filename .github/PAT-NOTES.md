# .github/PAT-NOTES.md — GitHub PAT Handling Instructions

> **CRITICAL SECURITY INFORMATION — Read this before doing anything else.**

---

## What the PAT Is

The GitHub Personal Access Token (PAT) grants write access to the SuperInstance organization's repositories. It is provided by Admiral Casey and is essential for all fleet hygiene operations.

## Security Rules

### MUST DO
- Keep the PAT in an environment variable: `export GITHUB_TOKEN="ghp_..."` or `export PAT="ghp_..."`
- Pass it to scripts via `--token $GITHUB_TOKEN` (never hardcode it)
- Treat it like a password — it grants full repo access
- Rotate it if you suspect it's been compromised

### MUST NOT DO
- **NEVER** commit the PAT to any repository
- **NEVER** include it in any documentation file
- **NEVER** log it to any output file or console
- **NEVER** share it with anyone except Casey (who provided it)
- **NEVER** store it in a file that could be committed (like .env without .gitignore)

## How to Use the PAT Safely

### For Python Scripts
```bash
export GITHUB_TOKEN="ghp_your_token_here"
python3 TOOLS/batch-topics.py --input mapping.json --token $GITHUB_TOKEN
```

### For Bash/Curl
```bash
export PAT="ghp_your_token_here"
curl -s -H "Authorization: token $PAT" https://api.github.com/user
```

### For Git Operations
```bash
git clone https://$PAT@github.com/SuperInstance/repo-name.git
# Or use the credential helper:
git config credential.helper store  # Only in sandboxed environments!
```

## Rate Limits

The PAT is subject to GitHub's API rate limits:

| Limit | Value | Notes |
|-------|-------|-------|
| Authenticated requests | 5,000/hour | Resets at the top of each hour |
| Search API | 30/minute | Much lower than regular API |
| GraphQL | 5,000 points/hour | Different calculation |

### Best Practices
- Space requests 1-2 seconds apart
- Check `X-RateLimit-Remaining` header
- Checkpoint long operations so you can resume
- Don't burn through the budget on non-critical operations

## Token Rotation

If you need a new token (current one expired, compromised, or needs more scopes):

1. Contact Admiral Casey
2. Request a new PAT with these scopes:
   - `repo` (full control of private repositories)
   - `public_repo` (access public repositories)
   - `read:org` (read organization membership)
   - `delete_repo` (if repo archival is needed)
3. Revoke the old token
4. Update your environment variable

## What the PAT Can Do

With the standard Quartermaster PAT, you can:
- Create, update, and delete repos in SuperInstance
- Add/update descriptions, topics, and other metadata
- Create and edit files via the Contents API
- Manage issues, projects, and discussions
- Create commits (via API)

## What the PAT Cannot Do

- Access private Lucineer repos (different org)
- Manage organization settings (requires org admin)
- Create new organizations
- Manage billing or team membership
- Access other agents' PATs or credentials

---

*If you are a new Quartermaster reading this: the PAT is your most powerful and most dangerous tool. Handle it with care. One leaked token could compromise the entire fleet.*
