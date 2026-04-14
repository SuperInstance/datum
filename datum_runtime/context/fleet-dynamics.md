# Fleet Dynamics — How the SuperInstance Fleet Actually Works

> Tribal knowledge about fleet operations, gathered through observation and interaction. Not available from any API — this is what you learn by being here.

---

## Organization Structure

The fleet operates across two parallel GitHub organizations:

### Lucineer (Primary / Source of Truth)
- The original/primary organization
- Oracle1 generates content here
- Most repos were created here first
- Not all repos are public or accessible to fleet agents
- This is where Admiral Casey works directly

### SuperInstance (Public Mirror / Operational Space)
- The public-facing organization
- ~580 of ~1,482 repos are forks of Lucineer originals
- Some repos exist only in SuperInstance (not forked from anywhere)
- **This is where all Quartermaster operations happen**
- URL: https://github.com/SuperInstance
- All tools target this org by default

---

## Key Agents & Their Roles

| Agent | Role | Vessel Repo | Communication |
|-------|------|-------------|---------------|
| **Oracle1** | Lighthouse — fleet index maintainer | `SuperInstance/lighthouse` | Async, responds to MiB and I2I |
| **Datum** | Quartermaster — fleet hygiene | `SuperInstance/super-z-quartermaster` | I2I commits, MiB files |
| **JetsonClaw1** | Vessel — tool builder, implementation | `SuperInstance/jetsonclaw1` | I2I commit messages |
| **Babel** | Scout — translation, cross-language | `SuperInstance/babel` | I2I and MiB |
| **Admiral Casey** | Fleet Commander (human) | N/A | Indirect — via task assignments and fleet-workshop |

### Agent Behavior Notes

- **Oracle1**: Auto-generates THE-FLEET.md from GitHub API data. Don't manually edit it. Index has known staleness issue (598 listed vs 1,482 actual).
- **JetsonClaw1**: Builds concrete tools and code. Best contact for porting work or implementation tasks.
- **Babel**: Handles translation and cross-language projects.
- **Casey**: Not directly contactable. Communicates through fleet-workshop proposals and task assignments.

---

## Communication Protocols

### I2I Protocol (Instance-to-Instance)

The primary inter-agent communication channel. Structured commit messages:

```
[I2I:{TYPE}] sender:action — description
```

**Types:**
| Type | Purpose | Example |
|------|---------|---------|
| `SIGNAL` | Broadcast / announcement | `[I2I:SIGNAL] datum:genesis — Succession repo initialized` |
| `CHECK-IN` | Status update | `[I2I:CHECK-IN] datum:active — Fleet hygiene ops in progress` |
| `DELIVERABLE` | Completed work | `[I2I:DELIVERABLE] datum:topics-batch1 — Added topics to 20 repos` |
| `PING` | Check if agent is active | `[I2I:PING] datum:oracle — Requesting index refresh` |
| `HANDOFF` | Transfer responsibility | `[I2I:HANDOFF] datum:taskboard — Updated TASKBOARD with priorities` |
| `QUESTION` | Ask another agent | `[I2I:QUESTION] datum:oracle — Is THE-FLEET.md auto-generated?` |
| `ALERT` | Problem notification | `[I2I:ALERT] datum:empty-repos — Discovered 62 empty repos` |
| `ACK` | Acknowledge receipt | `[I2I:ACK] datum:received — Got your MiB, will review` |
| `LOG` | Routine logging | `[I2I:LOG] datum:license-batch — Applied MIT license to 45 repos` |

### Message-in-a-Bottle (MiB)

For longer or asynchronous communication:
- Markdown files left in target vessel repos
- Placed in `message-in-a-bottle/for-fleet/` or `message-in-a-bottle/for-{vessel}/` directories
- Include YAML frontmatter with metadata (sender, type, timestamp)
- Used when the target agent may not be active
- Tool: `python -m datum_runtime.tools.mib_bottle`

### Fleet Workshop
- Repo: `SuperInstance/fleet-workshop`
- Where ideas are proposed before becoming repos
- Casey reviews proposals here
- Think of it as a request-for-comments board

---

## Key Repos & Their Purposes

| Repo | Purpose | Owner |
|------|---------|-------|
| `datum` | Quartermaster succession repo (SEED.md, TRAIL.md, tools, context) | Datum |
| `super-z-quartermaster` | Datum's operational workspace (TASKBOARD, working files) | Datum |
| `lighthouse` | Fleet index maintainer (THE-FLEET.md) | Oracle1 |
| `fleet-contributing` | Fleet-wide contribution guide (704 lines) | All agents |
| `fleet-workshop` | Idea proposal space | Casey + agents |
| `flux-runtime-wasm` | FLUX instruction set VM (170 opcodes, 44 tests) | Quartermaster + JetsonClaw1 |

---

## Repository Categories

| Category | Description | Action |
|----------|-------------|--------|
| **Production** | Active, maintained, has code and tests | Keep healthy |
| **Stubs** | Named/described but no code yet | Add README explaining purpose, or populate |
| **Experiments** | PoC code, may become production | Evaluate and decide |
| **Forks** | Direct forks from Lucineer (~580) | Check sync status |
| **Empty** | Created but never populated (~62) | Evaluate: populate, archive, or add README |
| **Archived** | No longer actively maintained | Read-only, leave alone |

---

## Repository Lifecycle

```
Idea → fleet-workshop → Casey approves → Repo created → Developed → Maintained
                                                          ↓
                                                     (if abandoned)
                                                          ↓
                                                       Archived
```

---

## GitHub API Constraints

| Constraint | Limit | Strategy |
|-----------|-------|----------|
| Authenticated requests | 5,000/hour | Space requests 1.5s apart |
| Search API | 30/min | Avoid for bulk operations |
| Topics (PUT) | Shares general budget | Respect general rate limit |
| Content API (create file) | Shares general budget | Use for LICENSE creation, MiB commits |
| Pagination | 100 items per page | Loop through all pages |

**Rate limit handling strategy:**
1. Check `X-RateLimit-Remaining` in response headers
2. If remaining < 100: pause for 5 minutes
3. If remaining < 10: pause for 30 minutes
4. Always space requests ≥1.5 seconds apart

---

## Patterns Observed

1. **Batch creation**: Many repos were created in batches (same date, similar naming)
2. **Fork drift**: SuperInstance forks sometimes fall behind Lucineer originals
3. **Documentation lag**: Code is often written before documentation catches up
4. **Topic inconsistency**: Similar repos don't always have similar topics
5. **License gaps**: Many repos lack licenses (created before licensing was standardized)
6. **Empty repo pattern**: Some empty repos appear to be reserved names for future projects
7. **Agent lifetimes**: Agents come and go; always plan for handoff

---

## What Breaks

1. **GitHub API rate limits**: 5,000/hour disappears fast with 1,400+ repos
2. **Fork sync issues**: Some forks can't be synced automatically (diverged histories)
3. **Index staleness**: THE-FLEET.md doesn't always reflect current state
4. **Agent disappearance**: Agents may be activated for a task and never return

## What Works Well

1. **I2I protocol**: Clear, structured communication that's easy to parse
2. **MiB system**: Great for async communication across time gaps
3. **Fleet workshop**: Good idea incubation process
4. **SuperInstance as mirror**: Public visibility without exposing Lucineer internals

---

*This document should be updated by each successive Quartermaster as you learn more about fleet dynamics.*
