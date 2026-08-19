# F08 Test Plan -- Data Enrichment

**Feature:** F08 -- Data Enrichment
**Author:** TEA (Test Architect)
**Date:** 2026-08-19
**Status:** planned

---

## 1. Scope

F08 addresses three data quality issues discovered during manual testing of the F07 dashboard:

1. **Encoding fix (T01):** Double-encoded UTF-8 card names display as mojibake (e.g., "Contram\u00c3\u00a1gica" instead of "Contram\u00e1gica"). The fix targets two layers: the provider's `_fetch()` method (force UTF-8 decoding of `resp.content` instead of relying on `resp.text`) and a one-time DB migration script (`scripts/fix_encoding.py`) to repair existing corrupted rows.

2. **Movers tuning (T02):** Dashboard and Market Movers pages default to `period: "7d"`, which produces 0% changes because price observations are approximately weekly. The default changes to `"30d"`.

3. **Collection expansion (T03):** The database currently contains only 30 cards from 1 set (DMR). Backfill 5-8 additional popular sets using existing infrastructure to provide meaningful data variety.

4. **Validation and documentation (T04):** End-to-end walkthrough, diagrams, and README update.

**Out of scope:** No new API endpoints, no schema changes, no new frontend pages.

---

## 2. Test Strategy

| Layer | Tool | Scope | Automation |
|-------|------|-------|------------|
| Unit | pytest (Python) | Encoding fix logic, migration script roundtrip, provider `_fetch` UTF-8 | Fully automated |
| Unit | Vitest (Frontend) | Updated default period assertions in Dashboard and MarketMovers tests | Fully automated |
| Integration | pytest + FastAPI TestClient | API responses return correctly encoded card names | Fully automated |
| E2E / Manual | Browser + curl | Dashboard walkthrough, encoding spot-checks, movers non-zero | Manual checklist |
| Regression | pytest + Vitest | All 390 backend + 165 frontend tests pass without modification (except T02 assertion updates) | Fully automated |

**Guiding principles:**
- Encoding fix tests use mocked `curl_cffi` responses -- no network calls.
- Migration script tests operate on in-memory or temp SQLite databases.
- Frontend tests update existing assertions; no new test files needed for T02.
- T03 (collection expansion) has no automated tests -- it is operational, verified via API spot-checks.

---

## 3. Unit Tests

### 3.1 Provider encoding fix (`tests/unit/test_provider.py`)

| ID | Test Case | Input | Expected |
|----|-----------|-------|----------|
| U-01 | `_fetch` returns correct UTF-8 when HTTP header says latin-1 | Mock response: `content` = `"Contram\u00e1gica".encode("utf-8")`, `encoding` = `"iso-8859-1"` | Returned string equals `"Contram\u00e1gica"` |
| U-02 | `_fetch` returns correct UTF-8 when HTTP header says UTF-8 | Mock response: `content` = `"Contram\u00e1gica".encode("utf-8")`, `encoding` = `"utf-8"` | Returned string equals `"Contram\u00e1gica"` |
| U-03 | `_fetch` returns correct ASCII for non-accented names | Mock response: `content` = `b"Lightning Bolt"`, `encoding` = `"iso-8859-1"` | Returned string equals `"Lightning Bolt"` |
| U-04 | `_fetch` handles empty response body | Mock response: `content` = `b""`, `encoding` = `"utf-8"` | Returned string equals `""` |

### 3.2 Migration script roundtrip logic (`tests/unit/test_fix_encoding.py` -- new file)

| ID | Test Case | Input | Expected |
|----|-----------|-------|----------|
| U-05 | Fixes double-encoded accent (latin-1 re-encode) | `"Contram\u00c3\u00a1gica"` | `"Contram\u00e1gica"` |
| U-06 | Fixes double-encoded circumflex | `"Rel\u00c3\u00a2mpago H\u00c3\u00a9lice"` | `"Rel\u00e2mpago H\u00e9lice"` |
| U-07 | Fixes double-encoded tilde | `"Neg\u00c3\u00a3o"` | `"Nega\u00e7\u00e3o"` (or equivalent mojibake -> correct mapping) |
| U-08 | Skips already-correct name (no mojibake) | `"Contram\u00e1gica"` | `"Contram\u00e1gica"` (no change) |
| U-09 | Skips pure ASCII name | `"Lightning Bolt"` | `"Lightning Bolt"` (no change) |
| U-10 | Idempotent: running fix twice produces same result | Apply fix to `"Contram\u00c3\u00a1gica"`, then apply again | Same output both times |
| U-11 | Handles `UnicodeDecodeError` gracefully | String that raises on `.encode('latin-1')` | Returns original string unchanged |

### 3.3 Migration script DB integration (`tests/unit/test_fix_encoding.py`)

| ID | Test Case | Description |
|----|-----------|-------------|
| U-12 | Fixes rows in `source_cards` table | Seed temp DB with mojibake `name_pt`, run migration, verify corrected |
| U-13 | Fixes rows in `cards` table | Seed temp DB with mojibake `name_en`/`name_pt`, run migration, verify corrected |
| U-14 | Prints summary count | Capture stdout, verify "X rows fixed" message |
| U-15 | No-op on clean database | Run migration on DB with no mojibake, verify 0 rows changed |

### 3.4 Frontend default period (`frontend/tests/components/Dashboard.test.tsx`, `frontend/tests/components/MarketMovers.test.tsx`)

| ID | Test Case | Description |
|----|-----------|-------------|
| U-16 | Dashboard fetches movers with `period=30d` | Assert fetch URL contains `period=30d` (update existing assertion from `7d`) |
| U-17 | MarketMovers page defaults to `30d` | Assert initial fetch URL contains `period=30d` (update existing assertion from `7d`) |
| U-18 | MarketMovers period selector still works | Select `"7d"` manually, verify fetch URL changes to `period=7d` |

---

## 4. Integration Tests

### 4.1 API encoding correctness (`tests/api/test_cards_router.py` or new `tests/api/test_encoding.py`)

| ID | Test Case | Method | Expected |
|----|-----------|--------|----------|
| I-01 | Cards endpoint returns correct Portuguese names | `GET /api/v1/cards?limit=5` | Response body contains properly encoded accented characters (no `\u00c3` sequences) |
| I-02 | Card detail returns correct name | `GET /api/v1/cards/{id}` for card with accented name | `name_pt` field has correct UTF-8 |
| I-03 | Search works with accented query | `GET /api/v1/cards?search=magica` | Returns matching cards, names are correctly encoded |
| I-04 | Sets endpoint returns after expansion | `GET /api/v1/sets` | Returns at least 6 sets |
| I-05 | Market stats reflect expanded data | `GET /api/v1/market/stats` | `total_cards` and `total_sets` values increased from pre-F08 baseline |

### 4.2 API movers default behavior

| ID | Test Case | Method | Expected |
|----|-----------|--------|----------|
| I-06 | Movers with 30d period returns non-zero changes | `GET /api/v1/market/movers?period=30d&limit=5` | At least some entries have `change_pct != 0` (data-dependent, best-effort) |

---

## 5. E2E / Manual Tests

Manual walkthrough checklist to be executed during T04 validation. Each item must be verified with backend (`make serve`) and frontend (`cd frontend && npm run dev`) running.

| ID | Page | Check | Pass? |
|----|------|-------|-------|
| E-01 | Dashboard | KPI cards show updated totals (more cards, more sets, more observations) | |
| E-02 | Dashboard | Market Movers section shows non-zero price changes | |
| E-03 | Dashboard | No garbled/mojibake text visible anywhere | |
| E-04 | Cards | Cards from multiple sets appear (filter by set if available) | |
| E-05 | Cards | Card names with accented characters display correctly (e.g., search "magica") | |
| E-06 | Cards | Pagination works across the expanded dataset | |
| E-07 | Card Detail | Select a card with accented Portuguese name, verify name renders correctly | |
| E-08 | Card Detail | Price chart renders with data points | |
| E-09 | Market Movers | Default period shows as 30d (not 7d) | |
| E-10 | Market Movers | Switching period selector to 7d/90d works correctly | |
| E-11 | Market Movers | Gainers and losers tables populate with data | |
| E-12 | API (curl) | `curl localhost:8000/api/v1/cards?limit=5` -- names are correct UTF-8 | |
| E-13 | API (curl) | `curl localhost:8000/api/v1/sets` -- shows 6+ sets | |
| E-14 | API (curl) | `curl localhost:8000/api/v1/market/movers?period=30d` -- non-zero changes | |

---

## 6. Regression

All existing test suites must pass without regressions after F08 changes.

### 6.1 Backend (pytest)

| Suite | File | Count (approx) | Notes |
|-------|------|-----------------|-------|
| Unit - Parsers | `tests/unit/test_parsers.py` | ~30 | Must pass unchanged -- parser receives `str`, encoding handled upstream |
| Unit - Parser Edge | `tests/unit/test_parsers_edge.py` | ~10 | Must pass unchanged |
| Unit - Provider | `tests/unit/test_provider.py` | ~25 | Mock adjustments may be needed if `_fetch` signature changes |
| Unit - Repository | `tests/unit/test_repository.py` | ~20 | Must pass unchanged |
| Unit - Indicators | `tests/unit/test_indicators.py` | ~30 | Must pass unchanged |
| Unit - Backfill | `tests/unit/test_backfill.py` | ~15 | Must pass unchanged |
| Unit - CLI | `tests/unit/test_cli_collector.py`, `test_cli_analytics.py` | ~25 | Must pass unchanged |
| API | `tests/api/test_*.py` | ~100 | Must pass unchanged |
| Integration | `tests/integration/test_collector_pipeline.py` | ~10 | Must pass unchanged |
| Database | `tests/database/test_repository_api.py` | ~15 | Must pass unchanged |

**Total backend:** ~390 tests, target 96%+ coverage maintained.

**Command:** `python -m pytest --tb=short`

### 6.2 Frontend (Vitest)

| Suite | File | Notes |
|-------|------|-------|
| Dashboard | `frontend/tests/components/Dashboard.test.tsx` | Assertions updated for `30d` default |
| MarketMovers | `frontend/tests/components/MarketMovers.test.tsx` | Assertions updated for `30d` default |
| All other components | `frontend/tests/components/*.test.tsx` | Must pass unchanged |
| Pages | `frontend/tests/pages/*.test.tsx` | Must pass unchanged |
| API client | `frontend/tests/api/client.test.ts` | Must pass unchanged |
| Utilities | `frontend/tests/utils/format.test.ts` | Must pass unchanged |
| Hooks | `frontend/tests/hooks/useDebounce.test.ts` | Must pass unchanged |

**Total frontend:** ~165 tests.

**Command:** `cd frontend && npm run test`

---

## 7. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Encoding fix misdiagnosis:** The mojibake root cause might not be latin-1 re-encoding (could be double UTF-8 encode, Windows-1252, or other) | Medium | High | T01 dev notes prescribe a diagnostic step: inspect `resp.headers['Content-Type']`, `resp.encoding`, and compare `resp.text` vs `resp.content.decode('utf-8')`. Diagnosis MUST happen before coding the fix. |
| **Migration script corrupts already-correct data:** The `encode('latin-1').decode('utf-8')` roundtrip could mangle names that contain valid latin-1 characters | Low | High | Migration must catch `UnicodeDecodeError` and `UnicodeEncodeError` and skip those rows (idempotency requirement). Unit tests U-08, U-09, U-11 verify this. |
| **Provider mock in existing tests breaks:** Existing `test_provider.py` mocks `resp.text`; if `_fetch` changes to use `resp.content.decode()`, mocks need `content` attribute | Medium | Medium | Update `_mock_response()` helper in `test_provider.py` to include both `.text` and `.content` attributes. Run full suite before committing. |
| **Collection expansion network failures:** Backfill for 5-8 sets depends on MYP Cards availability and Cloudflare behavior | Medium | Low | Existing resume capability handles interrupted runs. Rate limiting (1s delay) avoids bans. Can retry individual sets. Not a code risk. |
| **Collection expansion runtime:** 5-8 sets could take 1-3 hours with rate limiting | High | Low | Operational concern, not a test concern. Developer should run sets sequentially and verify each completes before starting the next. |
| **Frontend test flakiness with new default:** Tests that assert on fetch URL parameters could be brittle if URL construction changes | Low | Low | Search for ALL occurrences of `"7d"` in frontend test files and update systematically. |
| **Movers still show 0% with 30d:** Even with 30d window, if data has no price variation the movers will still be flat | Medium | Low | This is a data quality issue, not a code bug. T03 collection expansion mitigates by adding more data variety. E2E check E-02 is best-effort. |
| **Encoding varies by card/set on MYP:** Different pages might use different encodings | Low | Medium | The UTF-8 force-decode is safe because MYP consistently uses `<meta charset="utf-8">` in HTML. If a page genuinely uses a different encoding, `decode('utf-8')` will raise, which surfaces the issue immediately rather than silently corrupting data. |

---

## Appendix: Test File Mapping

| Task | New Test Files | Modified Test Files |
|------|---------------|-------------------|
| T01 | `tests/unit/test_fix_encoding.py` | `tests/unit/test_provider.py` (mock updates) |
| T02 | (none) | `frontend/tests/components/Dashboard.test.tsx`, `frontend/tests/components/MarketMovers.test.tsx` |
| T03 | (none) | (none -- operational, verified manually) |
| T04 | (none) | (none -- validation and docs only) |
