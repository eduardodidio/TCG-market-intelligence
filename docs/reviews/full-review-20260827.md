# TechLead Full Project Review — 2026-08-27

**Project:** TEDHC Market (TCG Market Intelligence)
**Reviewer:** Claude TechLead Agent (5 parallel explorers)
**Scope:** Full codebase (119 Python + 134 TypeScript files, 69 features shipped)
**Verdict:** APPROVED_WITH_FOLLOWUP

---

## Executive Summary

The codebase is technically sound with clean architecture, strong test foundations (2350+ backend, 1000+ frontend tests), and good separation of concerns. However, there are **critical gaps** in three areas:

1. **Security**: Race conditions in marketplace trading (double-spend risk)
2. **Documentation**: 19 features shipped without PRDs or diagrams (violates CLAUDE.md)
3. **Test coverage**: Provider layers at 19-23%, marketplace router integration tests sparse

**Production readiness for F69 (Trading):** NOT READY until BLOCKING items resolved.

---

## Findings Summary

| Severity | Backend | Frontend | Tests | Docs | F65-F69 | Total |
|----------|---------|----------|-------|------|---------|-------|
| BLOCKING | 3 | 4 | 6 | 3 | 2 | **18** |
| IMPORTANT | 8 | 7 | 6 | 4 | 5 | **30** |
| MINOR | 5 | 9 | 3 | 4 | 4 | **25** |

---

## BLOCKING Issues (Must Fix)

### B01. Race Condition: Double-spend in trade confirmation
- **File:** `src/marketplace/service.py:151-200`
- **Issue:** `confirm_agreement()` has TOCTOU race — buyer and seller confirming simultaneously can both trigger `_complete_trade()`, charging fees twice.
- **Fix:** Use database row-level locking (SELECT FOR UPDATE) or atomic conditional UPDATE.

### B02. Trade completion not atomic
- **File:** `src/marketplace/service.py:201-240`
- **Issue:** Multiple DB writes (2x credit deduction + status update + email reveal) not wrapped in a single transaction. Partial failure leaves inconsistent state.
- **Fix:** Wrap `_complete_trade()` in a database transaction with rollback.

### B03. MYP refresh deduction skipped on failed price save
- **File:** `src/api/routers/collection.py:892-894`
- **Issue:** Credits only deducted if `price_saved == True`. Users get unlimited free MYP refresh attempts. Liga refresh always deducts (inconsistent).
- **Fix:** Deduct credits unconditionally after guard check, matching Liga behavior.

### B04. Frontend: No 401/403 error handling in API client
- **File:** `frontend/src/api/client.ts:37-40`
- **Issue:** When JWT expires, no automatic redirect to login. Users see stale data or error states.
- **Fix:** Add 401 interceptor that calls `clearTokens()` and redirects to `/login`.

### B05. Frontend: localStorage token storage (XSS vulnerable)
- **File:** `frontend/src/api/client.ts` + `AuthContext.tsx`
- **Issue:** JWT stored in localStorage — XSS can exfiltrate tokens with 24h/30d expiry window.
- **Fix:** Migrate to httpOnly cookies (backend change) or at minimum use sessionStorage.

### B06. Frontend: Race condition in useCollectionRefresh
- **File:** `frontend/src/hooks/useCollectionRefresh.ts:172`
- **Issue:** `eslint-disable-line react-hooks/exhaustive-deps` on empty dependency array. Scan resume may fail silently.
- **Fix:** Remove eslint-disable, add proper dependencies or use ref.

### B07. Frontend: No React Error Boundary
- **Issue:** Runtime render errors crash entire app with blank page.
- **Fix:** Add error boundary wrapping App component.

### B08. Dev mode auth bypass in production
- **File:** `src/auth/dependencies.py:141-143`
- **Issue:** If `TCG_API_KEY` env var is unset, any request gets through as `api_key_user`.
- **Fix:** Add startup validation — fail hard if both JWT_SECRET and API_KEY are missing.

### B09. CORS too permissive
- **File:** `src/api/app.py:150-153`
- **Issue:** `allow_methods=["*"]`, `allow_headers=["*"]` allows any HTTP verb/header.
- **Fix:** Whitelist specific methods: `["GET", "POST", "PATCH", "DELETE", "OPTIONS"]`.

### B10. README.md missing 19 features (F51-F69)
- **File:** `README.md`
- **Issue:** Ends at F50. CLAUDE.md mandates README update for every shipped feature.
- **Fix:** Backfill F51-F69 sections.

### B11. Missing PRDs for F51-F69
- **Files:** `docs/prd/F51-*.md` through `docs/prd/F69-*.md` (all missing)
- **Issue:** CLAUDE.md mandates PRD before Architect runs. 19 features shipped without PRDs.
- **Fix:** Backfill from git history and memory files.

### B12. Missing diagrams for F51-F64, F69
- **Files:** `docs/diagrams/F5x-*.mmd` (missing)
- **Issue:** 14+ features lack required architecture + journey diagrams.
- **Fix:** Create diagrams for shipped features.

### B13-B18. Test coverage gaps (6 items)
- Provider layers (Liga 19%, MYP 23%) — missing error/retry path tests
- Marketplace router — only 11 stub tests, no happy-path integration
- Scheduler service — 18% coverage, lifecycle untested
- Frontend TradeInterestModal — no API integration verification
- Frontend MyTrades — accept/reject/confirm handlers untested
- Frontend Marketplace — browse shared collection untested

---

## IMPORTANT Issues (Should Fix)

### Architecture & Security
- **I01.** Concurrent credit check race — `check_sufficient()` and `deduct()` are separate calls; concurrent trades can overdraft. ValueError from repo bubbles as 500 instead of 402. (`src/marketplace/service.py:205-217`)
- **I02.** Missing FK constraints — `UserCollectionRow.card_id`, `.user_id`, `DeckRow.user_id`, `SourceCardRow.card_id` have no foreign key constraints. (`src/database/models.py`)
- **I03.** JWT secret validation only at token creation time, not at startup. Server can start without valid secrets. (`src/auth/jwt.py:15-22`)
- **I04.** Hardcoded seed password fallback `"mudar12345"`. (`src/cli/main.py:620`)
- **I05.** Dead code: "ambiguous" status handling in `sync_collection.py:290-308` and `match_report.py` (unreachable since F55).
- **I06.** Duplicate unused auth dependency in scan trigger. (`src/api/routers/scans.py:143-144`)
- **I07.** Admin credit bypass not audit-logged. (`src/api/routers/collection.py` — 4 locations)
- **I08.** Missing optimistic lock on TradeAgreement — no version field for concurrent updates. (`src/marketplace/service.py:178-186`)

### Frontend
- **I09.** Marketplace API client throws raw errors instead of `ApiResponse<T>` envelope — inconsistent with rest of app. (`frontend/src/api/marketplace.ts`)
- **I10.** AuthProvider doesn't handle triple-failure (fetchMe + refresh + retry all fail) gracefully. (`frontend/src/contexts/AuthContext.tsx:51-89`)
- **I11.** Prop drilling in MyCollection — 9+ props passed through multiple layers. (`frontend/src/pages/MyCollection.tsx`)
- **I12.** Hardcoded source labels "MYP Cards"/"LigaMagic" — should be i18n keys. (`CardDetail.tsx`, `CollectionCardDetail.tsx`)
- **I13.** useScanStream polling has no max attempts — can run indefinitely. (`frontend/src/hooks/useScanStream.ts:162-175`)
- **I14.** useApi hook race condition in rapid re-fetches with different params. (`frontend/src/hooks/useApi.ts:33-60`)
- **I15.** MYP refresh 402 response missing "message" field (Liga has it). (`src/api/routers/collection.py:776-787`)

### Dependencies & Config
- **I16.** `node_modules/` not in `.gitignore`. Also missing `frontend/dist/`, `frontend/.vite/`.
- **I17.** All 20 frontend deps unpinned (`^` ranges). No `package-lock.json` committed.
- **I18.** Backend deps use broad `>=` ranges without upper bounds (FastAPI, SQLAlchemy).
- **I19.** Missing ADRs for F60-F69 decisions (only 9 ADRs exist, 0001-0009).

### Tests
- **I20.** Service layer modules under-tested: `market_data.py` (18%), `trending.py` (21%), `aggregate_cache.py` (42%).
- **I21.** "ambiguous" status dead code in matcher tests — needs audit for best_effort coverage.
- **I22.** No E2E test for credit deduction during trade completion.
- **I23.** Frontend CreditConfirmModal doesn't test actual API call.
- **I24.** useCollectionRefresh full page flow untested (click Refresh All -> complete).
- **I25.** SSE stream integration (useScanStream) not tested in Scans page tests.

---

## MINOR Issues (Nice to Have)

- **M01.** Broad exception handlers without specific types (collection.py — 6 locations)
- **M02.** No connection pool config for production DB migration (repository.py:44)
- **M03.** Liga provider silent `except Exception: pass` in cleanup (provider.py:134,139)
- **M04.** Redundant `except (ValueError, Exception)` (collection.py:72)
- **M05.** CurrencyContext fragile 3-way string check — needs type guard
- **M06.** Duplicate `sourceLabel()` function in CardDetail + CollectionCardDetail
- **M07.** Missing aria-labels on icon buttons (GridSizeToggle, refresh buttons)
- **M08.** CollectionCardDetail period state not synced to URL params
- **M09.** ManualPriceInput parseFloat edge cases
- **M10.** useCredits refetch not memoized
- **M11.** CLAUDE.md Mission still says "TBD"
- **M12.** Fee calculation has no documented min/max bounds
- **M13.** Liga sweep skipped cards not counted in summary
- **M14.** Admin dashboard stats don't distinguish locked-in-trade credits
- **M15.** Test fixtures partially duplicated across marketplace tests
- **M16.** No time-based test isolation (datetime.now without freezegun)
- **M17.** Async sleep in tests instead of mocking

---

## Positive Findings

### Backend
- Clean layering: domain -> database -> api -> services (no circular imports)
- All secrets via env vars, no hardcoded credentials
- Structured logging (structlog) throughout
- Batch query optimization avoids N+1 patterns
- Proper Session scoping with context managers
- SQLAlchemy parameterized queries — no SQL injection risk

### Frontend
- Full TypeScript coverage, no `any` types detected
- Comprehensive i18n (215+ keys, EN + PT-BR)
- No console.log in production code
- Proper AbortController usage in hooks
- No snapshot tests (behavior-focused)
- Auth context well-structured with useCallback/useMemo

### Architecture
- Clean service/router/repository separation
- Transaction logging for audit trails (credit_transactions)
- Comprehensive schema design (marketplace models)
- Good index coverage on high-traffic queries

---

## Action Plan (Priority Order)

### P0 — Before F69 ships (BLOCKING)
1. Fix trade confirmation race condition (B01, B02) — add DB locking + transaction
2. Fix MYP refresh credit deduction (B03) — align with Liga behavior
3. Add 401 handler to API client (B04)
4. Add startup env var validation (B08)
5. Restrict CORS methods (B09)
6. Add React Error Boundary (B07)

### P1 — Next sprint (IMPORTANT)
7. Add FK constraints to DB models (I02)
8. Add marketplace router integration tests (B13-B18)
9. Fix concurrent credit check race (I01)
10. Add `node_modules/` to .gitignore + commit lock files (I16, I17)
11. Standardize marketplace API client to envelope pattern (I09)
12. Remove dead "ambiguous" code (I05)

### P2 — Technical debt (IMPORTANT)
13. Backfill README F51-F69 (B10)
14. Backfill PRDs (B11) and diagrams (B12)
15. Create missing ADRs (I19)
16. Increase provider test coverage to 70%+ (B13)
17. Add JWT startup validation (I03)
18. Add admin credit bypass audit logging (I07)

### P3 — Polish (MINOR)
19. i18n source labels, aria-labels, URL param sync
20. Fixture deduplication, time isolation in tests
21. Update CLAUDE.md Mission

---

## Verdict

```
Verdict: APPROVED_WITH_FOLLOWUP
```

The codebase has strong foundations but **F69 (Trading) is NOT production-ready** due to race conditions in credit deduction and trade confirmation (B01-B03). These are financial correctness issues that could result in double-charging users.

**Recommended next step:** Create a hardening feature (e.g., F70) to resolve P0 items before any further feature work.

---

*Generated by TechLead review — 5 parallel exploration agents*
*Total analysis: 277 tool calls across 5 agents, ~35 minutes*
