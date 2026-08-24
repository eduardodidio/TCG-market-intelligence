# F59 LigaMagic Manual Refresh -- Readiness Report

**Date:** 2026-08-24
**Auditor:** Claude (Opus 4.6)

---

## Verdict: READY

No blocking issues found. All task files are well-structured, dependencies
exist and are accessible, API design follows established patterns, and test
plans are feasible.

---

## Checklist

- [x] All task files present and well-formed (User Story, Dev Notes, Testing)
- [x] Dependencies exist (LigaMagicProvider, collection router, etc.)
- [x] No file conflicts between tasks in same Wave
- [x] API design is consistent with existing patterns
- [x] Test plan is feasible

---

## Detailed Findings

### 1. Task Files

| File | Present | Sections | Notes |
|------|---------|----------|-------|
| F59-README.md | Yes | Summary, Context, User Story, AC, Non-Goals, Architecture, Tasks | Complete and clear |
| F59-T01.md | Yes | User Story, Dev Notes, Testing | Endpoint spec, error handling, test plan all present |
| F59-T02.md | Yes | User Story, Dev Notes, Testing | API client code, UI placement, visual design, 9 test cases |
| F59-T03.md | Yes | User Story, Dev Notes, Testing | Badge mapping, i18n keys (7 keys, both locales), 3 test cases |

### 2. Dependency Verification

| Dependency | Path | Status |
|------------|------|--------|
| LigaMagicProvider | `src/providers/liga/provider.py` | Exists, implements CardSourceProvider ABC |
| Liga exceptions | `src/providers/liga/exceptions.py` | Exists: LigaError, LigaNotFoundError, LigaRateLimitError, LigaServerError |
| Liga config | `src/providers/liga/config.py` | Exists |
| Liga parser | `src/providers/liga/parser.py` | Exists |
| Collection router | `src/api/routers/collection.py` | Exists, already has `refreshCardPrice` endpoint to mirror |
| CollectionCardDetail page | `frontend/src/pages/CollectionCardDetail.tsx` | Exists, already imports PriceSourceBadge |
| Collection API client | `frontend/src/api/collection.ts` | Exists, has `refreshCardPrice()` to mirror for Liga variant |
| PriceSourceBadge | `frontend/src/components/PriceSourceBadge.tsx` | Exists, currently only handles "manual" source |
| apiPost (with timeoutMs) | `frontend/src/api/client.ts` | Exists, supports `{ timeoutMs }` option (line 96-100) |

### 3. File Conflict Analysis (Wave 1)

All three tasks touch different primary files with minimal overlap:

| File | T01 | T02 | T03 | Conflict? |
|------|-----|-----|-----|-----------|
| `src/api/routers/collection.py` | ADD endpoint | -- | -- | No |
| `frontend/src/api/collection.ts` | -- | ADD function | -- | No |
| `frontend/src/pages/CollectionCardDetail.tsx` | -- | ADD button+handler | ADD sourceLabel entry | Low risk -- different sections |
| `frontend/src/components/PriceSourceBadge.tsx` | -- | -- | MODIFY | No |
| `frontend/src/i18n/locales/en.json` | -- | -- | ADD keys | No |
| `frontend/src/i18n/locales/pt-BR.json` | -- | -- | ADD keys | No |

T02 and T03 both touch `CollectionCardDetail.tsx` but in different areas
(button+handler vs. sourceLabel map). No conflict expected if T01 is done
first (as specified by dependency chain).

### 4. API Design Consistency

The proposed `POST /collection/{entry_id}/refresh-liga` follows the exact
pattern of the existing `POST /collection/{entry_id}/refresh`:

- Same auth: `require_auth_or_api_key`
- Same query params: `currency`
- Same response schema: `ApiResponse[CollectionCardDetail]`
- Same graceful degradation (200 + warnings instead of 500)
- Same IDOR check pattern

This is consistent and appropriate.

### 5. Test Plan Feasibility

- **T01 backend tests:** 7 cases covering happy path, no-price, 404, IDOR,
  no-name, provider error, auto-card-creation. All mockable (LigaMagicProvider
  is async, standard mock patterns apply). Feasible.
- **T02 frontend tests:** 9 RTL cases for button render/hide, click, loading,
  success/warning/error, disabled state. Standard patterns already used in
  existing CollectionCardDetail tests. Feasible.
- **T03 frontend tests:** 3 cases for badge rendering and i18n. Trivial. Feasible.

### 6. Minor Observations (Non-blocking)

1. **T02 timeout (45s) vs README AC (30s):** The README says "timeout is
   generous (30s)" but T02 code sample uses `timeoutMs: 45000`. This is a
   minor inconsistency; 45s is the safer choice given Playwright latency.
   Recommend using 45s and updating the README AC if desired.

2. **PriceSourceBadge currently returns null for non-manual sources:** T03
   needs to change the component from "only render for manual" to "render for
   manual OR liga". The current early-return (`if (priceSource !== "manual")
   return null`) will need restructuring. This is straightforward but the dev
   should be aware.

3. **Task ordering:** README says "all sequential due to backend->frontend dep"
   but T03 only depends on T01 (not T02). T02 and T03 could theoretically run
   in parallel after T01. Not a problem either way.
