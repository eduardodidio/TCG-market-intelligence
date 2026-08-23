# F49 Auto-Canonize Collection -- Tech Lead Review

**Reviewer:** Tech Lead Agent
**Date:** 2026-08-22
**Tests:** 34 backend + 27 frontend = 61 passing

---

## T01 -- Bulk Canonize Service + Endpoint

### Architecture
The service layer (`src/collectors/bulk_canonize.py`) correctly separates query logic (`_get_unlinked_entries`) from processing logic (`_canonize_single`, `bulk_canonize`). The endpoint at `POST /collection/canonize-all` follows the existing router pattern with auth dependency and Pydantic response model. The dataclass-in-service + Pydantic-in-API dual-model approach is consistent with the project pattern (domain models vs. API schemas).

### Code Quality

- **IMPORTANT: `Repository.__new__` bypass (line 208).** When `repo is None`, the code uses `Repository.__new__(Repository)` and manually sets `repo.engine`. This skips `__init__`, which calls `Base.metadata.create_all()` and `_ensure_columns()`. While this follows the precedent set in `src/decks/importer.py`, it is fragile -- if Repository ever adds initialization logic beyond `engine`, `create_all`, and `_ensure_columns`, this pattern will silently break. This should be documented with a comment explaining why `__init__` is bypassed.

- **IMPORTANT: Provider not closed in CLI command (line 732-743).** The CLI `canonize-all` command creates `MypCardsProvider()` but never calls `provider.close()`. If the async run raises an exception, the provider's session is leaked. The API endpoint correctly wraps in `try/finally`, but the CLI does not. The `_run_import_canonize` background task also correctly closes.

- **MINOR: N+1 query in `_get_unlinked_entries` (lines 72-87).** The orphan detection iterates over every entry with `card_id` and issues a separate `SELECT` per entry to check for MYP source cards. For small collections (hundreds of cards) this is acceptable, but it will become a bottleneck at scale. A single LEFT JOIN query would be more efficient. Acceptable for now given collection sizes.

- **MINOR: `provider: object` type annotation (lines 100, 173).** The provider parameter is typed as `object` instead of `MypCardsProvider` or a protocol. This weakens type checking. A `Protocol` with `search_card`, `get_card_details`, `fetch_current_price`, `close` methods would be cleaner.

- **MINOR: Exception catch ordering (line 236).** `except (NotFoundError, ServerError, Exception)` -- `Exception` already subsumes `NotFoundError` and `ServerError`. The explicit listing of specific exceptions is harmless but redundant since the handling is identical for all three.

### Error Handling
Rate limit errors are correctly separated from general failures, matching the F45 provider resilience pattern. The endpoint uses `try/finally` to ensure provider cleanup. The background task `_run_import_canonize` wraps everything in `try/except/finally` -- correct.

### Security
Auth is enforced via `require_auth_or_api_key` dependency. The `user_id` is scoped from the auth token, preventing IDOR. The `limit` query param has `ge=1` validation. No issues.

### Tests (15 tests)
- 8 unit tests for the service cover: empty collection, unlinked entries, orphans, limit, rate limiting, concurrency semaphore, summary counts
- 3 API integration tests: auth required (401), success (200), limit param forwarding
- 4 schema validation tests

Test quality is good. The concurrency test (`test_bulk_canonize_concurrency_semaphore`) actually validates the semaphore bound, which is valuable.

**Missing test:** No test for the `provider: object` path where `repo=None` triggers the `Repository.__new__` fallback. This path is reachable from the API endpoint.

---

## T02 -- Auto-Canonize Hook on CSV Import

### Architecture
The import flow correctly uses FastAPI `BackgroundTasks` to schedule canonization after CSV import. The importer returns `new_entry_ids` so the router can decide whether to schedule. The response includes `canonize_scheduled` boolean for the frontend. Clean separation of concerns.

### Code Quality
- The importer (`src/collection/importer.py`) was modified to call `session.flush()` to populate `row.id` before appending to `new_entry_ids`. This is correct for SQLite.
- The background task `_run_import_canonize` canonizes ALL unlinked entries for the user (not just the newly imported ones). This is intentional -- it catches any previously unlinked entries as well. However, this means re-importing a CSV with 5 new cards could trigger canonization for hundreds of existing unlinked cards. The behavior is documented but could surprise users. Acceptable as designed.

### Tests (14 tests)
- 10 importer tests: new entry IDs returned, single card, empty CSV, re-import clearing, skipped rows, schema fields
- 4 API integration tests: background canonize triggered, skipped when no new entries, non-blocking response, response schema fields

Good coverage of the conditional scheduling logic.

---

## T03 -- CLI Command

### Architecture
Follows existing CLI patterns exactly: Click command with `--db`, `--user-id`, `--limit`, `--concurrency`, `--dry-run`. Dry run queries unlinked entries without processing. Summary printer follows the `_print_*_summary` pattern.

### Code Quality
- **IMPORTANT (repeated from T01): Provider not closed.** The CLI creates `MypCardsProvider()` at line 732 but never closes it. Should wrap in `try/finally` like the API endpoint does. If `asyncio.run()` raises, the provider session leaks.
- Imports `_get_unlinked_entries` (a private function) from `bulk_canonize` for the dry-run path. This creates coupling to an internal API. A public `count_unlinked_entries` would be cleaner, but this is minor given the module is internal.

### Tests (5 tests)
- Dry run, limit forwarding, summary output, required user-id, default concurrency
- Good coverage of CLI contract.

---

## T04 -- Frontend UI

### Architecture
`BulkCanonizeButton` is a self-contained component with clear props (`unlinkedCount`, `onComplete`). It manages its own loading/result/error state. Integration into `MyCollection.tsx` is minimal -- it computes `unlinkedCount` from the summary and passes `handleRefreshComplete` as `onComplete` to trigger a data re-fetch.

### Code Quality
- The API client function `canonizeAll` in `frontend/src/api/collection.ts` sets a generous 120-second timeout, which is appropriate for bulk operations.
- The component correctly hides itself when `unlinkedCount <= 0 && !result && !error`.
- The `onComplete` callback triggers `handleRefreshComplete` which increments `refreshKey`, causing the collection and summary to re-fetch. This is the established pattern from F30.
- `BulkCanonizeResult` type in `frontend/src/types/api.ts` matches the backend schema exactly.

### Tests (13 tests)
- Hidden when 0 or negative, renders when positive, loading state, disabled during loading, result banner, failed text conditional, onComplete callback, error handling for API errors and network exceptions
- Comprehensive coverage of the component's state machine.

---

## T05 -- i18n Keys

### Code Quality
6 keys added to both EN and PT-BR locales:
- `collection.canonizeAll` -- "Canonize All" / "Canonizar Todas"
- `collection.canonizeAllDescription` -- description text
- `collection.unlinkedCount` -- "{{count}} unlinked" / "{{count}} sem vinculo"
- `collection.canonizeResult` -- "Canonized {{canonized}} of {{total}} cards"
- `collection.canonizeFailed` -- "{{failed}} cards failed"
- `collection.canonizeScheduled` -- "Canonization scheduled"

The `canonizing` key already existed from F46. All 6 new keys are present in both locales. The test correctly validates 7 keys (6 new + 1 existing `canonizing`).

### Tests (14 tests)
- 7 keys checked in EN, 7 keys checked in PT-BR via `it.each`.

---

## Cross-Task Consistency

No file collisions between tasks. The shared touchpoints are:
- `src/api/routers/collection.py` -- T01 adds endpoint, T02 modifies import endpoint. No conflicts.
- `src/api/schemas/collection.py` -- T01 adds `BulkCanonizeResult`, T02 extends `ImportResult`. No conflicts.
- `frontend/src/i18n/locales/*.json` -- T04 and T05 both touch these, but T05 is additive and T04 consumes existing keys.

Backend-to-frontend contract alignment verified: `BulkCanonizeResult` fields match exactly between Pydantic schema and TypeScript interface.

---

## Documentation Deliverables

- **BLOCKING: No diagrams created.** CLAUDE.md requires every feature to produce at least two Mermaid diagrams under `docs/diagrams/`: an architecture diagram (`F49-architecture.mmd`) and a user journey diagram (`F49-journey.mmd`). Neither exists.
- **BLOCKING: README.md not updated.** CLAUDE.md states: "every feature that ships MUST update the project README.md with a short note of what was delivered." F49 is not mentioned in README.md.

---

## Summary of Issues

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 1 | BLOCKING | Missing diagrams (F49-architecture.mmd, F49-journey.mmd) | `docs/diagrams/` |
| 2 | BLOCKING | README.md not updated with F49 delivery note | `README.md` |
| 3 | IMPORTANT | CLI `canonize-all` does not close the MYP provider | `src/cli/main.py:732-743` |
| 4 | IMPORTANT | `Repository.__new__` bypass needs a safety comment | `src/collectors/bulk_canonize.py:208` |
| 5 | MINOR | N+1 orphan detection query | `src/collectors/bulk_canonize.py:72-87` |
| 6 | MINOR | `provider: object` type annotation | `src/collectors/bulk_canonize.py:100,173` |
| 7 | MINOR | Redundant exception listing | `src/collectors/bulk_canonize.py:236` |

---

## Verdict

```
Verdict: REJECTED
```

**Reason:** Two BLOCKING documentation deliverables are missing (diagrams and README update), and one IMPORTANT resource leak in the CLI command. The code implementation itself is solid -- the architecture, security, error handling, and test coverage are all good. Fix items 1-3 and this is ready to merge.

---

## Retrospective Seeds

- **Pattern:** CLI commands that create external-service providers (MypCardsProvider) must wrap usage in try/finally with provider.close()
- **Role(s) affected:** developer
- **Lesson:** Add "provider cleanup in CLI" as a checklist item. The API layer consistently uses try/finally, but CLI commands are prone to forgetting cleanup because asyncio.run() returns synchronously and the developer does not think about the async resource lifecycle.

- **Pattern:** Documentation gates (diagrams, README) are consistently missed when features are implemented in a single session
- **Role(s) affected:** developer, architect
- **Lesson:** The architect task manifest should include explicit documentation tasks (e.g., "T06: Create diagrams and update README") rather than relying on developers to remember CLAUDE.md requirements during implementation.
