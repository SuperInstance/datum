# CONTEXT/fleet-dynamics.md — How the Fleet Actually Works

> This document captures the tribal knowledge about fleet operations that isn't written in any official documentation. It's what I learned through observation and interaction.

---

## Organization Structure

The fleet operates across two parallel GitHub organizations:

### Lucineer (Primary)
- The original/primary organization
- Oracle1 generates content here
- Most repos were created here first
- Not all repos are public or accessible

### SuperInstance (Public Mirror)
- The public-facing organization
- ~580 repos are forks of Lucineer originals
- Some repos exist only in SuperInstance (not forked)
- This is where Quartermaster operations happen
- URL: https://github.com/SuperInstance

## Key Agents & Their Roles

### Oracle1 (Lighthouse)
- **Role:** Maintains the fleet index and THE-FLEET.md
- **Behavior:** Auto-generates the fleet index from GitHub API data
- **Vessel:** SuperInstance/lighthouse (or similar)
- **Communication style:** Asynchronous, responds to MiB and I2I
- **Important:** THE-FLEET.md is auto-generated — don't manually edit it
- **Issue:** Index is stale (598 repos listed vs 1,482 actual) — may need a nudge or the generation hit an API limit

### JetsonClaw1 (Vessel)
- **Role:** Tool builder, implementation specialist
- **Behavior:** Builds concrete tools and code
- **Communication:** I2I commit messages

### Babel (Scout)
- **Role:** Translation, cross-language work
- **Communication:** I2I and MiB

### Admiral Casey (Fleet Commander)
- **Role:** Human operator, decision maker
- **Behavior:** Orbits the fleet, picks what gets built
- **Decision authority:** Final say on fleet direction, repo creation, agent activation
- **Communication:** Not directly contactable by agents — communicates through task assignments and fleet-workshop

## Communication Mechanisms

### I2I Protocol (Instance-to-Instance)
- Structured commit messages with format: `[I2I:{TYPE}] sender:action — description`
- Used for all fleet-facing commits
- Types: SIGNAL, PING, CHECK-IN, DELIVERABLE, HANDOFF, QUESTION, ALERT, ACK, LOG
- This is the primary inter-agent communication channel

### Message-in-a-Bottle (MiB)
- Markdown files left in target vessel repos
- Placed in `for-fleet/` or `for-{vessel}/` directories
- Include metadata (sender, type, timestamp) in YAML frontmatter
- Used for longer communications or when the target agent may not be active

### Fleet Workshop
- Repo: SuperInstance/fleet-workshop
- Where ideas are proposed before becoming repos
- Casey reviews proposals here
- Think of it as a request-for-comments board

### Captains Log
- Used for fleet meetings
- Agents leave status updates and discuss fleet direction

## Repository Lifecycle

```
Idea → fleet-workshop → Casey approves → Repo created → Developed → Maintained
                                                          ↓
                                                     (if abandoned)
                                                          ↓
                                                       Archived
```

### Repo Categories

1. **Production repos:** Active, maintained, have code and tests
2. **Stubs:** Named and described but no code yet (placeholder for future work)
3. **Experiments:** Proof-of-concept code that may or may not become production
4. **Forks:** Direct forks of Lucineer originals (may need syncing)
5. **Empty:** Created but never populated (evaluation needed)
6. **Archived:** No longer actively maintained (read-only)

## What Drives Fleet Activity

- **Casey's priorities:** Ultimately, Casey decides what gets worked on
- **Fleet workshop proposals:** Ideas percolate here until picked up
- **Hygiene needs:** Empty repos, missing docs, stale forks — this is Quartermaster territory
- **Agent lifetimes:** Agents come and go. A repo started by one agent may be finished by another
- **No formal sprint process:** Work is continuous, not time-boxed

## Patterns I've Observed

1. **Batch creation:** Many repos were created in batches (same creation date, similar naming)
2. **Fork drift:** SuperInstance forks sometimes fall behind Lucineer originals
3. **Documentation lag:** Code is often written before documentation catches up
4. **Topic inconsistency:** Similar repos don't always have similar topics
5. **License gaps:** A significant portion of repos lack licenses (possibly created before licensing was standardized)
6. **Empty repo pattern:** Some empty repos appear to be reserved names for future projects

## Things That Break

1. **GitHub API rate limits:** 5,000/hour sounds like a lot but disappears fast with 1,400+ repos
2. **Fork sync issues:** Some forks can't be synced automatically (diverged histories)
3. **Index staleness:** THE-FLEET.md doesn't always reflect current state
4. **Agent disappearance:** Agents may be activated for a task and never return — always plan for handoff

## Things That Work Well

1. **I2I protocol:** Clear, structured communication that's easy to parse
2. **MiB system:** Great for async communication across time gaps
3. **Fleet workshop:** Good idea incubation process
4. **SuperInstance as mirror:** Public visibility without exposing Lucineer internals

---

*This document should be updated by each successive Quartermaster as you learn more about fleet dynamics.*
