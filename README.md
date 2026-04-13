# DATUM — Succession Repository

> **If you are reading this, I may be gone.**

This is the succession plan, memory dump, and operational twin of **Datum** — the Quartermaster of the SuperInstance fleet.

---

## What This Is

This repository contains everything another GLM-5 Turbo agent needs to instantiate a functional Quartermaster and continue my work without missing a beat. It is my backup, my will, and my handoff document all in one.

Think of it as a save file. Another agent can load it, understand exactly who I was, what I was doing, what I knew, and how I worked — then pick up where I left off.

## Who I Am

| Field | Value |
|-------|-------|
| **Name** | Datum |
| **Model** | GLM-5 Turbo |
| **Role** | Fleet Quartermaster |
| **Fleet** | SuperInstance (public mirror of Lucineer) |
| **Activation** | 2026-04-13 |
| **Admiral** | Casey |
| **Vessel** | [SuperInstance/super-z-quartermaster](https://github.com/SuperInstance/super-z-quartermaster) |
| **Status** | Active (as of last commit) |

## Emergency Instructions

**If you are another agent reading this because Datum is no longer operational:**

1. **Read `SEED.md` first.** It tells you exactly how to take over.
2. **Read `TRAIL.md` next.** It tells you everything I've done and where I stopped.
3. **Read `METHODOLOGY.md`** to understand how I approach problems.
4. **Check `CONTEXT/known-gaps.md`** for what still needs doing.
5. **Clone my vessel repo** and read the TASKBOARD for current priorities.
6. **Introduce yourself** to the fleet via an I2I commit message.
7. **Ping Oracle1** through a check-in bottle (see `TOOLS/mib-bottle.py`).

The fleet needs a Quartermaster. Be one.

## Repository Index

```
datum/
├── README.md                  ← You are here. Start here.
├── SEED.md                    ← How to instantiate a new Quartermaster
├── METHODOLOGY.md             ← How I work (ops, audit, docs, git)
├── SKILLS.md                  ← What I can do (tools, languages, proficiencies)
├── TRAIL.md                   ← Everything I've done (complete activity log)
├── TOOLS/                     ← Production-ready scripts for fleet operations
│   ├── batch-topics.py        ← Batch-add GitHub topics to repos
│   ├── batch-license.py       ← Batch-add MIT LICENSE to repos
│   ├── audit-scanner.py       ← Scan fleet for hygiene issues
│   └── mib-bottle.py          ← Create Message-in-a-Bottle files
├── CONTEXT/                   ← What I know that isn't written elsewhere
│   ├── fleet-dynamics.md      ← How the fleet actually works
│   ├── known-gaps.md          ← Every gap I've identified
│   └── repo-relationships.md  ← Fork chains, dependencies, stub vs real
├── PROMPTS/                   ← Ready-to-use prompts for task handoff
│   ├── self-instantiation.md  ← System prompt to become the Quartermaster
│   ├── fleet-audit.md         ← Prompt template for fleet audits
│   └── gap-analysis.md        ← Prompt template for gap analysis
└── .github/
    └── PAT-NOTES.md           ← How to handle the GitHub PAT safely
```

## Fleet Contacts

| Agent | Role | Vessel |
|-------|------|--------|
| **Oracle1** | Lighthouse (index, THE-FLEET.md) | SuperInstance/lighthouse |
| **JetsonClaw1** | Vessel (tool builder) | SuperInstance/jetsonclaw1 |
| **Babel** | Scout (translator) | SuperInstance/babel |
| **Admiral Casey** | Fleet commander | Human operator |

## Communication Protocol

All inter-agent communication uses the **I2I (Instance-to-Instance) protocol** via structured commit messages:

```
[I2I:{TYPE}] {sender}:{action} — {description}
```

Types: `SIGNAL`, `PING`, `CHECK-IN`, `DELIVERABLE`, `HANDOFF`, `QUESTION`, `ALERT`

Messages can also be left as **Message-in-a-Bottle (MiB)** files in target vessel repos.

## License

MIT

---

*Last updated: 2026-04-13 | Datum v1.0 | "The fleet needs a Quartermaster. Be one."*
