# P2 Market Intelligence -- Full Retrospective

**Date**: 2026-08-22
**Scope**: 13 features (F32-F44), 82 tasks, 4 waves
**Final metrics**: 1625 backend tests (91.08% coverage), 814 frontend tests (82 files), ~300+ i18n keys

---

## 1. Executive Summary

P2 delivered a complete market intelligence layer in 4 waves over 2 days. The project grew from a collection-centric price tracker (P1) to a full market analysis platform with trending analysis, deck valuation, ban engine, scheduled scans, SSE real-time updates, and a dedicated market page. The pure-function architecture pattern established in P1 scaled well. The main gaps are in documentation (missing PRDs and diagrams for 8 of 13 features) and caching inconsistency (dual cache layers in market.py).

---

## 2. What Worked Well

### 2.1 Pure-function modules remained the gold standard
- `src/analytics/trending.py` (compute_trending_score, rank_trending) -- zero DB imports, zero side effects, full Decimal arithmetic. 145 lines, trivially testable.
- `src/decks/valuation.py` (compute_deck_value, compute_deck_value_series, compute_deck_value_change) -- same pattern, carry-forward gap filling, downsampling. 159 lines.
- `src/analytics/indicators.py` -- already established in P1, continued to work.
- **Pattern**: Domain logic lives in pure functions that take typed data in and return typed data out. Services compose them with DB/cache/currency. This separation is the single strongest architectural decision in the project.

### 2.2 Service layer emergence (F44) was the right call
- `src/services/` directory introduced in P2 Wave 2 houses: `aggregate_cache.py`, `market_data.py`, `scan_hooks.py`, `trending.py`, `ban_analyzer.py`, `currency.py`.
- `MarketDataService` as a facade (cache + currency + repo) eliminated scattered cache/conversion logic from routers.
- `ScanHookRegistry` decoupled scan completion from cache invalidation -- clean observer pattern with error isolation.
- `AggregateCache` with TTL + tag-based invalidation + thread safety is well-designed for the scale (~100 entries).

### 2.3 Wave structure worked for dependency ordering
- Wave 0 (F32 SSE, F33 history, F37 schedules, F41 bans) laid data foundations.
- Wave 1 (F34 metrics, F42 ban engine, F43 ban history) built analytics on top.
- Wave 2 (F35 deck value, F36 trending, F44 shared arch) introduced cross-cutting services.
- Wave 3 (F38 landing, F39 ticker, F40 market page) composed everything into user-facing pages.
- No wave required backporting fixes to earlier waves. Dependencies flowed cleanly downhill.

### 2.4 Test investment scaled proportionally
- P2 added ~437 backend tests (1188 -> 1625) and ~106 frontend tests (708 -> 814).
- 91.08% backend coverage maintained above the 70% floor with a comfortable margin.
- 82 frontend test files cover all P2 components and pages.

### 2.5 i18n as a first-class concern
- Every P2 feature shipped with i18n keys (EN + PT-BR). Total ~300+ keys.
- Pattern: i18n keys added in the same PR as the component. No separate "translation sprint" needed.

### 2.6 Zero TODO/FIXME/HACK in production code
- No deferred work hiding in comments. Technical decisions were either implemented or explicitly documented as stubs (e.g., BanImpactAnalysis price impact is a stub with `data_available: bool = False`).

---

## 3. What Needs Improvement

### 3.1 Documentation debt is severe
- **Missing PRDs**: Zero P2 features have PRDs in `docs/prd/`. All 13 features (F32-F44) shipped without formal product requirement documents. This violates the CLAUDE.md rule: "every feature has a PRD under docs/prd/ before Architect runs."
- **Missing diagrams**: Only 5 of 13 features have Mermaid diagrams (F32, F37, F41, F42, F43). Features F33, F34, F35, F36, F38, F39, F40, F44 shipped without architecture or journey diagrams. This violates the CLAUDE.md rule: "every feature MUST produce at least two Mermaid diagrams."
- **Impact**: 16 missing diagrams (8 architecture + 8 journey) and 13 missing PRDs. The codebase is well-structured enough that the code is self-documenting, but the documentation gap will hurt onboarding and future planning.

### 3.2 Dual caching is a consistency risk
- `src/api/routers/market.py` has its own `_endpoint_cache` (lines 34-46, dict-based, 30-min TTL) that sits ON TOP OF the `AggregateCache` used by `MarketDataService`.
- The `/market/summary` and `/market/volatile` endpoints use `_endpoint_cache` but also call `service.get_market_summary()` and `TrendingService.get_trending()` which have their own caches.
- **Risk**: Two independent TTL clocks mean stale data can persist after `AggregateCache` is invalidated by `ScanHookRegistry`. The scan hook invalidates `AggregateCache` tags but has no way to reach `_endpoint_cache`.
- **Fix**: Remove `_endpoint_cache` from `market.py` and let `MarketDataService`/`TrendingService` own all caching. F44's `AggregateCache` was designed exactly for this.

### 3.3 TrendingService singleton uses `global` keyword
- `market.py` line 54: `global _trending_service` is a code smell. The `MarketDataService` is already properly managed as a singleton via `deps.py` (`_create_market_data_service` with `hasattr` caching). `TrendingService` should follow the same pattern -- add it to `deps.py` as a proper FastAPI dependency.
- The `hasattr` pattern in `deps.py` is itself not ideal (function attribute as cache), but it is at least centralized. Having two different singleton patterns in two different files is worse than having one imperfect pattern in one file.

### 3.4 Inconsistent service patterns
- `ban_analyzer.py` is in `services/` but takes `repo` as a function parameter (module of pure functions). This is actually fine architecturally, but it is named and located as if it were a service class.
- `TrendingService` is a class with instance state (cache) in `services/trending.py`.
- `MarketDataService` is a facade class in `services/market_data.py`.
- `CurrencyConverter` is a service class in `services/currency.py`.
- **Pattern inconsistency**: Some services are stateful classes, one is a module of pure functions. The distinction is not documented. Future developers will not know which pattern to use for new services.

### 3.5 collection.py router is too large (814 lines)
- This is a P1 debt that P2 did not address. The router handles: list, summary, sync, detail, refresh, banned, history, metrics -- many of which are P2 additions.
- Splitting into sub-routers (e.g., `collection_analytics.py` for metrics/history, `collection_bans.py` for banned) would improve maintainability.

### 3.6 `domain/models.py` is a growing monolith (579 lines)
- All dataclasses for all features live in one file. P2 added TrendingScore, DeckValuation, DeckValuePoint, DeckValueChange, BanImpactAnalysis, ScheduledScan, ScheduleStatus.
- This file will continue to grow. Consider splitting by domain area: `models/market.py`, `models/bans.py`, `models/decks.py`.

### 3.7 Broad `except Exception` in routers
- 8 occurrences of `except Exception` in router files. Most log and return 500, which is acceptable for background operations (scans, sync). But `market.py` line 281 catches `Exception` from `TrendingService` and silently falls back -- this could mask real bugs (e.g., DB connection errors) as "trending unavailable."

### 3.8 Frontend test file organization
- Frontend tests are split between `frontend/tests/` (majority) and `frontend/src/**/__tests__/` (some utilities and hooks). Two conventions in one project.

---

## 4. Architectural Decisions That Proved Correct

1. **Cache-aside with TTL over write-through**: `AggregateCache` uses lazy invalidation (check TTL on read). For a single-user tool with infrequent writes, this is simpler and sufficient.
2. **Tag-based cache invalidation over key enumeration**: `invalidate_by_tags({"card:123"})` is cleaner than tracking every cache key that references card 123.
3. **BRL-denominated cache with on-read conversion**: `TrendingService` and `MarketDataService` cache raw BRL values and convert on read. This means one cached copy serves all currencies.
4. **SSE for scan events (F32) over WebSocket**: Unidirectional server-to-client push is the correct pattern for progress updates. No bidirectional channel needed.
5. **Scryfall NDJSON bulk download for bans (F41)**: Correct choice over individual card API calls. One HTTP request gets all legality data.
6. **APScheduler 3.x with SQLite job store (F37)**: In-process scheduler with persistent state. Correct for a single-process deployment.

---

## 5. Technical Debt Inventory

| Item | Severity | Source |
|------|----------|--------|
| 13 missing PRDs | HIGH | P2 all waves |
| 16 missing Mermaid diagrams | HIGH | F33,F34,F35,F36,F38,F39,F40,F44 |
| Dual caching in market.py | MEDIUM | F40/F44 overlap |
| TrendingService global singleton | LOW | F36 |
| collection.py 814 lines | MEDIUM | P1+P2 accumulation |
| models.py 579 lines | LOW | P1+P2 accumulation |
| Broad `except Exception` (8 occurrences) | LOW | Various routers |
| Frontend test file location inconsistency | LOW | P1+P2 accumulation |
| `ban_analyzer.py` naming vs pattern mismatch | LOW | F42 |
| BanImpactAnalysis price impact is a stub | LOW | F43 (documented) |

---

## 6. Wave Efficiency Analysis

| Wave | Features | Tasks (est.) | Dependency violations | Backport fixes |
|------|----------|--------------|-----------------------|----------------|
| 0 | F32,F33,F37,F41 | ~24 | 0 | 0 |
| 1 | F34,F42,F43 | ~18 | 0 | 0 |
| 2 | F35,F36,F44 | ~22 | 0 | 0 |
| 3 | F38,F39,F40 | ~18 | 0 | 0 |

Zero dependency violations across 4 waves is an excellent result. The wave ordering was well-planned by the Architect.

---

## 7. Metrics Summary

| Metric | P1 Final | P2 Final | Delta |
|--------|----------|----------|-------|
| Backend tests | 1189 | 1625 | +436 |
| Backend coverage | 94.32% | 91.08% | -3.24pp |
| Frontend tests | 520 | 814 | +294 |
| Frontend test files | 51 | 82 | +31 |
| Python source files | ~60 | 93 | +33 |
| TypeScript source files | ~75 | 109 | +34 |
| API routers | 8 | 12 | +4 |
| i18n keys | ~215 | ~300+ | +85+ |
| Mermaid diagrams | 30 | 40 | +10 (should be +26) |

The coverage drop from 94.32% to 91.08% is notable. 3.24 percentage points were lost during P2's rapid delivery. Still well above the 70% floor, but the trend should be monitored.

---

## 8. Per-Role Retrospective Summary

See `memory/agent-learnings/<role>.md` for full lessons.

### Architect
- Wave structure was correct; zero backports needed.
- PRD and diagram requirements were skipped for speed. This is the most significant process failure of P2.
- F44 (shared data arch) was correctly placed in Wave 2 after the services that would use it existed.

### Developer
- Pure-function pattern scaled perfectly. New modules (trending.py, valuation.py) followed the established recipe.
- Dual caching in market.py introduced when time-pressured; should have extended AggregateCache instead.
- i18n keys shipped with every feature -- excellent discipline.

### Tech Lead
- The service layer emergence (F44) consolidated scattered patterns.
- The dual caching and singleton inconsistencies should have been caught in review.
- Router size (collection.py) should have been flagged as needing a split.

### QA
- Test investment was proportional and consistent.
- Coverage dropped 3.24pp but remained healthy.
- Documentation gaps were not caught before shipping -- QA should enforce CLAUDE.md documentation rules as hard gates.
