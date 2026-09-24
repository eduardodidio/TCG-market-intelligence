# F171 — Wave 0 summary

**Status:** completed
**Tasks:** F171-T01
**Generated:** 2026-09-24T12:35:00Z

## Files touched
- `src/currency/types.py` (T01: `SupportedCurrency`, `CurrencyChoice`, `CurrencySource`, `CurrencyDetection` frozen dataclass)
- `tests/currency/__init__.py` (T01: empty test package init)
- `tests/fixtures/collection_import/*.csv` (T01: 7 fixtures — liga_brl_no_price [cp1252], liga_brl_with_price, generic_brl_symbol, generic_usd_symbol, manabox_usd, manabox_brl, ambiguous_no_hint)
- `tests/fixtures/purchase_usd_sample.html` (T01: minimal Liga order markup, one USD + one BRL item)
- `docs/prd/F171-collection-import-currency.md` (T01: 110-line PRD, problem/goals/non-goals/AC1–AC10)
- `docs/diagrams/F171-architecture.mmd` (T01: created, 54 lines)
- `docs/diagrams/F171-journey.mmd` (T01: created, 40 lines)

## Decisions
- `CurrencyDetection.evidence` and `.unsupported_symbols` are `list[str]` with `field(default_factory=list)` — later waves (T02–T04) should reuse this exact shape rather than inventing their own detection payload.
- _none_ (no other direction changes)

## Notes for next Wave
- Branch check passed: current branch is `claude/stoic-mccarthy-nv2690`, not `main` — safe to proceed.
- All Wave 0 files are still **untracked** (not committed) as of this summary — Wave 1 devs should confirm with the orchestrator whether T01's work gets committed before or alongside Wave 1 changes.
- Verified: `python -c "from src.currency.types import CurrencyDetection"` imports cleanly; `ruff check src/currency/types.py` passes; `liga_brl_no_price.csv` correctly fails UTF-8 decode (confirmed cp1252).
- `src/currency/pila_formatter.py` exists and is unrelated — do not touch it (per T01 dev notes).

DIDIO_DONE: techlead wrote F171-wave-0-summary.md
