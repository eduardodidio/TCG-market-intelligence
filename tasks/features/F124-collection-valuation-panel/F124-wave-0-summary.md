# F124 — Wave 0 summary

**Status:** completed
**Tasks:** F124-T01, F124-T02, F124-T03, F124-T05
**Generated:** 2026-09-13T00:00:00Z (approximate, no per-Wave commit markers found; work is uncommitted on `main`)

## Files touched
- `src/providers/liga/urls.py` (T01: new — `build_liga_card_url`, `is_valid_liga_card_url`, `liga_external_id`)
- `src/providers/liga/provider.py` (T01: captures `page.url` as `_last_page_url`, sets `prices["page_url"]`)
- `tests/unit/test_liga_urls.py`, `tests/providers/test_liga_provider.py` (T01: new/updated tests)
- `src/database/models.py` (T02: new `LigaCardUrlRow`)
- `src/database/repository.py` (T02: `upsert_liga_card_url`, `get_liga_card_url`)
- `tests/database/test_liga_card_urls.py` (T02: new)
- `src/api/routers/collection.py` (T03: acquisition fields in list/detail, foil-aware `portfolio_summary`, `unpriced_card_count`)
- `src/api/schemas/collection.py` (T03: `PortfolioSummary.unpriced_card_count`)
- `tests/api/test_collection_portfolio.py`, `tests/api/test_collection_acquisition_fields.py`, `tests/api/test_collection_patch.py` (T03: new/updated)
- `frontend/src/components/PaidPriceQuickEdit.tsx` (T05: new component)
- `frontend/src/components/AcquisitionPriceInput.tsx` (T05: clear-to-null fix for price and date)
- `frontend/src/api/collection.ts` (T05: `patchCollectionEntry` type allows `null`)
- `frontend/src/i18n/locales/en.json`, `pt-BR.json` (T05: `collection.paidPrice*` + `dashboard.investment*` keys, sole owner)
- `frontend/src/components/__tests__/PaidPriceQuickEdit.test.tsx`, `AcquisitionPriceInput.test.tsx` (T05: new)

## Decisions
- T03 `portfolio_summary`: pct denominator is `invested_priced` (priced entries only), not `total_invested` — matches PRD semantics noted as a breaking change in F124-README risks.
- T05 added `dashboard.investment*` i18n keys in Wave 0 even though only consumed by T04 in Wave 1, per the file conflict map (T05 is sole i18n owner).

## Notes for next Wave
- Wave 1 (T04, T06, T09) can rely on `dashboard.investment*` i18n keys already existing in both locale files — do not re-add them.
- T06 (Liga URL writers) should build on `urls.py`/`LigaCardUrlRow`/repository methods from T01/T02, already present and tested.
- None of this Wave's work is committed yet (git status shows all as modified/untracked on `main`); confirm commit strategy before Wave 1 starts.
- `docs/adr/0012-liga-fetched-url-persistence.md` and `docs/prd/F124-collection-valuation-panel.md` exist as untracked files — not part of this Wave's code scope, leave for T10/docs pass.
