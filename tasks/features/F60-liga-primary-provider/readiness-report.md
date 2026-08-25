# F60 Readiness Report

**Feature:** F60 — LigaMagic Primary Provider Migration
**Audited:** 2026-08-25
**Verdict:** READY

## Checklist

### Prerequisites — Backend Modules
- [x] `src/providers/liga/provider.py` exists with `LigaMagicProvider` class (implements `CardSourceProvider` ABC)
- [x] `src/providers/liga/exceptions.py` exists with `LigaError`, `LigaNotFoundError`, `LigaRateLimitError`, `LigaServerError`
- [x] `src/providers/liga/config.py` exists (`LigaConfig` dataclass)
- [x] `src/providers/liga/parser.py` exists (`parse_card_prices`)
- [x] `src/collectors/scan.py` exists with `run_scan()` function (MYP-hardcoded, target of T01 refactor)
- [x] `src/database/repository.py` exists with `get_cards_for_scan()` method (line 1187)
- [x] `src/database/cleanup.py` exists (target of T03 `clear_prices_by_source` addition)
- [x] `src/cli/main.py` exists (Click CLI, target of T03/T05/T06 commands)
- [x] `src/api/routers/scans.py` exists (target of T06 provider flag)
- [x] `src/api/routers/collection.py` exists, includes `POST /{entry_id}/refresh-liga` (F59, used by T08)
- [x] `src/scheduler/service.py` exists (APScheduler integration, target of T10)
- [x] `src/domain/models.py` exists with `ScanType` enum (currently: COLLECTION, SET, FORMAT, CUSTOM — T01 adds LIGA_FULL, LIGA_PARTIAL)

### Prerequisites — Frontend Modules
- [x] `frontend/src/api/scans.ts` exists (target of T06 provider param)
- [x] `frontend/src/hooks/useCollectionRefresh.ts` exists (target of T06 default provider change)
- [x] `frontend/src/pages/CollectionCardDetail.tsx` exists (target of T08 button hierarchy)
- [x] `frontend/src/components/PriceSourceBadge.tsx` exists (target of T08 liga color)
- [x] `frontend/src/i18n/locales/en.json` exists (target of T09)
- [x] `frontend/src/i18n/locales/pt-BR.json` exists (target of T09)

### Task Files
- [x] F60-README.md — well-structured with 4 waves, 10 tasks, clear acceptance criteria
- [x] F60-T01.md — scan orchestrator refactor (Wave 0)
- [x] F60-T02.md — Liga repo method + price priority (Wave 0)
- [x] F60-T03.md — clear prices CLI (Wave 0)
- [x] F60-T04.md — Liga scan orchestrator end-to-end (Wave 1, depends T01+T02)
- [x] F60-T05.md — Liga sweep CLI (Wave 1, depends T01+T02)
- [x] F60-T06.md — scan API + CLI provider flag (Wave 1, depends T01+T04)
- [x] F60-T07.md — admin link monitor page (Wave 2, depends T02+T06)
- [x] F60-T08.md — card detail Liga/MYP button priority (Wave 2, depends T01)
- [x] F60-T09.md — i18n keys (Wave 2, parallel with T07+T08)
- [x] F60-T10.md — scheduled Liga scans (Wave 3, depends T04+T06)

### Dependency Chain Validity
- [x] Wave 0 tasks (T01, T02, T03) are independent — can run in parallel
- [x] Wave 1 tasks (T04, T05, T06) correctly depend on Wave 0
- [x] Wave 2 tasks (T07, T08, T09) correctly depend on Wave 0/1
- [x] Wave 3 task (T10) correctly depends on Wave 1
- [x] No circular dependencies detected

## Blockers

None.

## Notes

1. **ScanType enum gap:** `ScanType` currently has 4 values (COLLECTION, SET, FORMAT, CUSTOM). T01 correctly identifies the need to add `LIGA_FULL` and `LIGA_PARTIAL`. No conflict with existing values.

2. **`get_cards_for_liga_scan()` does not exist yet:** This is expected — T02 creates it. The existing `get_cards_for_scan()` is MYP-specific (requires source_card linkage). T02's approach of querying by `card_id + name` without MYP source_cards is sound.

3. **`clear_prices_by_source()` does not exist yet:** Expected — T03 creates it in `cleanup.py`. The existing cleanup module has the right patterns (backup, dry_run, VACUUM) that T03 will follow.

4. **F59 `refresh-liga` endpoint already exists:** T08 references `POST /collection/{entry_id}/refresh-liga` which is already implemented (line 818 of collection.py). T08 only changes frontend button hierarchy and default refresh action — no backend changes needed for that endpoint.

5. **LigaMagicProvider has both `get_current_price()` (ABC) and `search_card()` (convenience):** T01/T04 reference `provider.search_card(name)` for the Liga fetch strategy. The method exists on the provider (line 323) and returns parsed price dicts. The task descriptions correctly use this API.

6. **Scan orchestrator is fully MYP-hardcoded:** `src/collectors/scan.py` imports `MypCardsProvider`, `NotFoundError`, `RateLimitError` directly. T01's refactor scope is accurate and well-defined. The T04 approach of creating a separate `src/collectors/liga_scan.py` as a thin wrapper is a reasonable alternative to a full generic refactor.

7. **Estimated sweep time (~79 min for 349 cards):** T05 documents this clearly. The batch-pause approach with resume support via `max_age_days` is well-designed for overnight operation.

8. **No contradictions found** between task files. All file paths, method names, and API contracts are internally consistent across the 10 tasks.
