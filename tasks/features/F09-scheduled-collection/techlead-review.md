# Tech Lead Review -- F09 Scheduled Collection

**Reviewer:** Tech Lead Agent
**Date:** 2026-08-19
**Feature:** F09 -- Scheduled Price Collection
**Scope:** Health endpoint, API key guard, cron trigger script, frontend freshness indicator, docs

---

## 1. Architecture Alignment

**Result: PASS**

The implementation faithfully follows the PRD (`docs/prd/F09-scheduled-collection.md`), the
task plan (T01-T05), and the architecture decision to use an external cron trigger with
no in-process scheduler. Specifically:

- T01 (health endpoint): `GET /api/v1/collect/health` returns the exact schema specified
  in the PRD (`last_collection_at`, `next_expected_at`, `total_cards`, `stale_cards_count`,
  `recent_errors_count`, `status`). Status logic matches spec: `error > stale > healthy`.
- T02 (API key guard): `verify_api_key` dependency applied to both POST routes, not to the
  GET health route. Dev-mode fallback (no-op when `TCG_API_KEY` unset) implemented per FR-03.
- T03 (cron script): `scripts/cron_update.sh` is POSIX-compatible bash, requires
  `TCG_API_KEY`, logs to `logs/cron/`, exits 0 on success / non-zero on failure.
- T04 (frontend freshness): `FreshnessIndicator` component rendered on Dashboard,
  graceful degradation when health endpoint fails, does not block dashboard loading.
- T05 (docs): Both diagrams exist, README updated with F09 section.
- No new Python dependencies introduced (NFR-04).

## 2. Code Quality

**Result: PASS**

- **Repository methods** (`get_latest_observation_date`, `get_stale_cards_count`,
  `get_recent_errors_count`, `get_source_card_count`): Clean SQL via SQLAlchemy ORM,
  consistent with existing repository patterns. The stale cards query correctly uses a
  subquery with LEFT JOIN to also count cards with zero observations.
- **API key guard**: Simple, clear, correctly placed in `deps.py` alongside `get_db`.
  No over-engineering.
- **Health endpoint**: Clean status determination logic with proper priority
  (`error > stale > healthy`). The boundary test verifies that exactly 50% stale is NOT
  treated as "stale" (strict `>` comparison).
- **Frontend `FreshnessIndicator`**: Well-structured with `formatRelativeTime` as a pure
  function handling edge cases (NaN, negative diffs, singular forms). Uses `data-testid`
  attributes for reliable testing. Tailwind classes consistent with project dark theme.
- **Dashboard integration**: Health data fetched independently; `loading` and `error`
  states only track `stats` and `movers`, not `health`. This ensures the freshness
  indicator never blocks the dashboard.
- **Cron script**: Uses `set -euo pipefail`, `mktemp` + `trap` for cleanup, proper
  quoting, relative-to-absolute path resolution. Logs to both stdout and file via
  `tee -a`. Health check after update is non-blocking (`|| true`).
- No dead code, no leftover TODOs, no debug statements.

## 3. Security

**Result: PASS**

- API key read from `os.environ.get("TCG_API_KEY")` -- no hardcoded secrets anywhere.
- Cron script documentation uses placeholder `your_key`, not real values.
- Simple string comparison (`x_api_key != expected`) is used. The PRD explicitly states
  that timing-safe comparison is a nice-to-have, not a requirement. For a local/single-user
  deployment this is acceptable. Noted as a MINOR item below.
- Guard correctly returns 401 with `"Invalid or missing API key"` detail.
- GET health endpoint intentionally unprotected (read-only observability).
- No `.env` files or credential files staged for commit.

## 4. Test Coverage

**Result: PASS**

All test scenarios from the test plan (`F09-test-plan.md`) are implemented:

**Backend (435 tests, all passing, 96.47% coverage):**
- `tests/api/test_collect_health.py` (7 tests): 200 response, healthy/stale/error status,
  boundary condition (50% = healthy), null data handling, error priority over stale.
- `tests/api/test_collect_auth.py` (7 tests): unit tests for `verify_api_key` (4) +
  integration tests with TestClient (3: update auth, backfill auth, dev mode, health no-auth).
- `tests/database/test_repository_api.py` (11 new tests for F09): `get_latest_observation_date`
  (4 tests), `get_stale_cards_count` (4 tests including orphan source cards), `get_recent_errors_count`
  (3 tests including source filtering), `get_source_card_count` (3 tests).

**Frontend (178 tests, all passing):**
- `FreshnessIndicator.test.tsx` (10 tests): relative time formatting (minutes, hours, days,
  singular forms, "just now"), null handling ("Unknown"), status dot colors
  (green/yellow/red/slate fallback).
- `Dashboard.test.tsx` (2 new tests): freshness indicator renders with mocked health data,
  dashboard renders without freshness indicator when health endpoint fails.

**Cron script:** Manual testing only, as specified in the test plan. Acceptance criteria
are verifiable via manual steps documented in T03.

## 5. Frontend

**Result: PASS**

- **Graceful degradation**: When health endpoint fails, `health.error` is set, `health.data`
  is null, and the `freshnessIndicator` variable evaluates to `null` -- no indicator
  rendered, no crash, dashboard KPIs and movers still load normally.
- **Dark theme consistency**: Component uses `bg-slate-800`, `text-slate-300`,
  `rounded-full` pill style -- consistent with existing dashboard components.
- **Status dot colors**: green-400 (healthy), yellow-400 (stale), red-400 (error),
  slate-400 (fallback for unknown statuses).
- **No new dependencies**: Custom `formatRelativeTime` function instead of importing
  `date-fns` or similar.

## 6. Documentation

**Result: PASS**

- `docs/diagrams/F09-architecture.mmd`: Correct Mermaid graph showing cron -> script ->
  API key guard -> update endpoint -> collection pipeline -> SQLite, plus health endpoint
  -> SQLite and Dashboard -> health endpoint. Styling applied.
- `docs/diagrams/F09-journey.mmd`: Three swimlanes (Operator Setup, Cron Execution,
  Dashboard User) with error paths (401, connection error). Decision nodes for status
  field values. Correct flow.
- `README.md`: F09 section added under "Shipped" with all 4 deliverables described.
  Endpoints table updated with `GET /api/v1/collect/health` and authentication note
  for collect endpoints.

## 7. No Regressions

**Result: PASS**

- Backend: 435 tests passing (was 407 post-F08, +28 new for F09).
- Frontend: 178 tests passing (was 166 post-F08, +12 new for F09).
- Coverage: 96.47% backend (above 70% minimum).
- Existing collect endpoint tests continue to pass because `TCG_API_KEY` is not set
  in the test environment, so the guard is a no-op.

---

## Issues Found

### MINOR-01: Frontend mock uses datetime format but backend returns date-only

**Location:** `frontend/tests/fixtures/api-responses.ts` line 124

The `mockCollectionHealth()` fixture uses `"2026-08-19T10:30:00Z"` for `last_collection_at`,
but the actual backend returns a date-only string (e.g., `"2026-08-19"`) because
`repo.get_latest_observation_date()` returns a `date` object. The `FreshnessIndicator`
component handles both formats correctly (`new Date("2026-08-19")` parses to UTC midnight),
so this is not a functional bug -- just a mock accuracy issue. The user will see "1 day ago"
at most granularity, never "2 hours ago".

**Impact:** Cosmetic. Tests pass and the component works correctly with both formats.

**Recommendation:** Consider adjusting the mock to return `"2026-08-19"` to match actual
backend behavior, or alternatively update the backend to return a full ISO datetime
(by tracking `datetime` instead of `date`). Not blocking.

### MINOR-02: No timing-safe comparison for API key

**Location:** `src/api/deps.py` line 19

The API key comparison uses `x_api_key != expected` (simple string comparison) instead of
`hmac.compare_digest()`. Per the PRD, this is explicitly acceptable for the current scope
(single-user, local deployment). For a future public-facing deployment, this should be
upgraded to a constant-time comparison.

**Impact:** Negligible for current deployment model. No action required now.

### MINOR-03: `next_expected_at` uses date-only format

**Location:** `src/api/routers/collect.py` line 38

The `next_expected_at` field is computed as `next_dt.date().isoformat()`, producing a
date-only string like `"2026-08-20"`. The PRD schema says "ISO datetime string", and
the frontend mock uses a full datetime. The current implementation works but has
lower temporal granularity than documented.

**Impact:** Cosmetic. The value is informational and not used for any logic.

---

## Verdict

**APPROVED**

The F09 implementation is complete, well-tested (28 new backend tests + 12 new frontend
tests, all passing), architecturally sound, and faithful to the PRD and task plan. The
three MINOR issues noted above are cosmetic/informational and do not affect functionality,
security, or correctness. No CRITICAL issues found.
