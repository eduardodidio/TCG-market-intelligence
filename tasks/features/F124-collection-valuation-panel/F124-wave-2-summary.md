# F124 — Wave 2 summary

**Status:** completed
**Tasks:** F124-T07, F124-T08
**Generated:** 2026-09-13T00:00:00Z (approximate; work is uncommitted on `main`, no per-Wave commit markers found)

## Files touched
- `src/api/routers/collection.py` (T07: `_build_collection_detail` now resolves `ligamagic_url` via `repo.get_liga_card_url(liga_external_id(...))` for foil/non-foil keys, validated with `is_valid_liga_card_url`, falling back to `build_liga_card_url(entry.name_en or entry.name_pt)`; drops the old `CardRow.name_en`-based lookup)
- `src/api/routers/cards.py` (T07: card detail builder now prefers stored `liga_{card_id}` URL, else `build_liga_card_url(fetch_name)`)
- `src/api/schemas/cards.py` (T07: `CardDetail.ligamagic_url: str | None = None`)
- `src/api/routers/card_search.py` (T07: `liga_url = page_url if is_valid_liga_card_url(page_url) else build_liga_card_url(card_name)`, replacing the hand-built query string)
- `frontend/src/types/api.ts` (T07: `CardDetail.ligamagic_url?: string | null` added after T04's `PortfolioSummary` field — no collision)
- `frontend/src/pages/CardDetail.tsx` (T07: link href = `card.ligamagic_url ?? <encoded-name fallback>`)
- `tests/api/test_collection_liga_links.py` (T07: updated to new stored-URL/fallback/foreign-URL contract)
- `frontend/src/pages/__tests__/CardDetailLigaLink.test.tsx` (T07: new)
- `frontend/src/pages/Dashboard.tsx` (T08: removed `market-summary-strip`, `market-empty`, `fetchMarketStats`/`MarketStats` import and full-page error branch; mounts `<DashboardInvestmentSummary totalUnique={summaryData.total_unique} />` after `collection-kpis`, before movers, gated on `isAuthenticated && summaryData.total_unique > 0`)
- `frontend/src/pages/__tests__/Dashboard.test.tsx` (T08: new — covers authenticated/anonymous/empty/error/loading states, asserts `fetchMarketStats` not called)

## Decisions
- T07 kept `scryfall_url` logic untouched, scoping the change strictly to the Liga link resolution path per the task's guardrail.
- No deviations from the T07/T08 task files' implementation details.

## Notes for next Wave
- Wave 3 (T10) can rely on: Liga link now sourced from `liga_card_urls` end-to-end (collection detail, card detail, card search, `CardDetail.tsx`), and Dashboard is slimmed to collection + investment + trending only, with `DashboardInvestmentSummary` mounted.
- `frontend/src/types/api.ts` now carries both T04's `PortfolioSummary` optional field and T07's `CardDetail.ligamagic_url` — file conflict map's sequencing held with no collision.
- Remaining AC7 work (README update, `docs/diagrams/F124-architecture.mmd`, `docs/diagrams/F124-journey.mmd`) and the full regression pass (pytest, vitest, `npm run build`, ruff) are still outstanding — that is T10's scope.
- None of Wave 0/1/2 work is committed yet; confirm commit strategy before T10 wraps up.
