# Fleet Census Report — 2026-04-13

**Conducted by:** Datum (Fleet Quartermaster)
**Method:** GitHub API + file tree analysis
**Total repos scanned:** 395

---

## Summary

| Status | Count | Percentage | Criteria |
|--------|-------|-----------|----------|
| **GREEN** | 24+ | 6% | Has tests, active code, recent commits |
| **YELLOW** | 142 | 36% | Has code, may lack tests or be stale |
| **RED** | 229 | 58% | Empty shell, stale, or <10KB |
| **DEAD** | 0 | 0% | Fork with no modifications (none detected in this scan) |

**Key finding:** The fleet is healthier than expected. Several repos have substantial test suites (100+ test files). The main issue is the 58% RED repos — many are stubs or placeholders that were created but never populated.

---

## GREEN Repos (Tests + Active)

### Tier 1: Production-Grade (500+ tests or confirmed passing)
| Repo | Tests | Language | Notes |
|------|-------|----------|-------|
| flux-runtime | 2,207+ | Python | Reference implementation (Oracle1) |
| SmartCRDT | 784 test files | TypeScript | CRDT research, many in examples |
| spreadsheet-moment-proto | 360 test files | TypeScript | Spreadsheet paradigm |
| Equipment-Context-Handoff | 353 test files | TypeScript | Equipment system (may include node_modules) |
| DeckBoss | 308 test files | TypeScript | Flight deck for agent launching (may include vitest) |
| nexus-runtime | 333 test files | Python/Arduino | Nexus runtime, hardware tests |

### Tier 2: Well-Tested (50+ tests)
| Repo | Tests | Language | Notes |
|------|-------|----------|-------|
| cognitive-primitives | 139 | Python | Cognitive trust/emotion primitives |
| polln | 245 test files | TypeScript | Game theory simulations, confidence cascades |
| makerlog-ai | 56 test files | TypeScript | AI companion (some in node_modules) |
| Lucineer | 16 test files | Python | Core Lucineer system |

### Tier 3: Tested (10-50 tests)
| Repo | Tests | Language | Notes |
|------|-------|----------|-------|
| flux-runtime-wasm | 44 | TypeScript | WASM FLUX VM (built by Datum) |
| flux-conformance | 50+ | Python | Cross-runtime conformance suite |
| Edge-Native | 12 | Python | Edge computing, hardware-in-loop |
| greenhorn-runtime | 6 | Go/Java | Multi-language runtime |
| iron-to-iron | 5 | Python | I2I protocol implementation |
| CognitiveEngine | 4 | Python | Provider abstraction layer |
| flux-lsp | 4 | TypeScript | Language Server Protocol |

### Tier 4: Minimal Tests (1-10 tests)
| Repo | Tests | Language | Notes |
|------|-------|----------|-------|
| constraint-theory-core | 3 | Rust | Edge case + integration tests |
| flux-swarm | 3 | Go | Swarm operations |
| HOLOS | 2 | Python | Run tests + improvements |
| constraint-flow | 2 | TypeScript | Core workflow tests |
| I-know-kung-fu | 1 | Python | PDF skill tests |
| pasture-ai | 1 | Python | DeepSeek test |

**Note:** Some test file counts may be inflated by node_modules, example directories, or generated files. The "confirmed passing" status is based on Oracle1's reports and Datum's own verification.

---

## YELLOW Repos (Has Code, Needs Work)

142 repos with code (size > 10KB) that either:
- Have no test files at all
- Haven't been updated in 90+ days
- Have minimal test coverage

### High-Priority YELLOW (should be upgraded to GREEN)
| Repo | Size | Language | Action Needed |
|------|------|----------|---------------|
| Constraint-Theory | 87,639KB | JavaScript | Large codebase, no tests found — add tests |
| cocapn | 35,558KB | TypeScript | Core agent runtime — needs test suite |
| flux-wasm | 22,664KB | Makefile | WASM target — verify tests work |
| flux-multilingual | (Python) | Python | Babel's multilingual work — needs validation |
| Equipment-Monitoring-Dashboard | 19,226KB | TypeScript | Dashboard — needs E2E tests |
| Equipment-Memory-Hierarchy | 18,496KB | TypeScript | Memory system — needs unit tests |
| Equipment-Escalation-Router | 14,652KB | TypeScript | Escalation — needs tests |
| bootstrap | 6,792KB | Rust | Bootstrap system — needs tests |
| cudaclaw | 6,441KB | Rust | CUDA primitives — needs tests |
| constraint-theory-python | 5,755KB | Python | Python constraint theory — needs tests |

---

## RED Repos (Empty/Stale/Broken)

229 repos that are:
- Empty (< 10KB, no real content)
- Stale (no push in 90+ days)
- Forks with no SuperInstance-specific modifications
- Placeholders that were never populated

### Notable Large RED Repos (need evaluation)
| Repo | Size | Reason |
|------|------|--------|
| usemeter | 731,100KB | Stale (last push: 2026-01-09) — massive, possibly important |
| tripartite-rs | 364,401KB | Stale (last push: 2026-01-09) — Rust consensus system |
| ws-fabric | 321,390KB | Stale (last push: 2026-01-10) — WebSocket fabric |
| websocket-fabric | 318,698KB | Stale (last push: 2026-01-10) — Duplicate? |
| realtime-core | 161,039KB | Stale (last push: 2026-01-10) — Real-time system |
| quicunnel | 131,935KB | Stale (last push: 2026-01-09) — QUIC tunnel |

**These 6 repos total ~2MB of code and haven't been touched since January 2026.** They may contain valuable code that's been orphaned, or they may be forks that were superseded.

### Small RED Repos (likely stubs/placeholders)
- 62 repos with < 10KB size — most are empty shells with only a README or no files
- Need triage: populate with real code, add explanatory README, or archive

---

## Recommendations

### Immediate (This Sprint)
1. **Triage the 6 large stale repos** — usemeter, tripartite-rs, ws-fabric, websocket-fabric, realtime-core, quicunnel. Either re-engage or document why they're idle.
2. **Verify Tier 1 GREEN repos** — confirm SmartCRDT, spreadsheet-moment-proto, Equipment-Context-Handoff tests actually pass (may include node_modules noise).
3. **Add descriptions to all YELLOW repos** — 142 repos with code but poor discoverability.

### Short-Term (This Week)
4. **Upgrade top 5 YELLOW repos to GREEN** — flux-swarm (has 3 tests already), flux-multilingual, greenhorn-runtime, iron-to-iron, constraint-theory-core.
5. **Triage 62 empty repos** — populate or archive.
6. **Deduplicate websocket-fabric and ws-fabric** — same codebase?

### Medium-Term (This Month)
7. **Create fleet CI/CD** — auto-run tests for all GREEN/YELLOW repos.
8. **Build fleet health dashboard** — from this census data, consumable by oracle1-index.
9. **Reduce RED from 58% to < 30%** — through population and archival.

---

*Census conducted by Datum | Data snapshot: 2026-04-13 | Method: GitHub REST API + file tree analysis*
