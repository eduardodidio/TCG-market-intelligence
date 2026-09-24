# F172 — Test Plan

- **status:** drafted
- **generator:** TEA
- **generated-at:** 2026-09-24
- **source-brief:** `tasks/features/F172-deck-builder-suggestions/_brief/00-overview.md`

## 1. Fixtures

| Fixture | Path | Domain | Owner |
|---|---|---|---|
| `_fake_commander_rows` (builder of `FakeCardRow`-style legendary creatures incl. a DFC `"Legendary Creature — X // Y"`, a NULL `type_line` row, and rows with/without `CardLegalityRow`) | inline in `tests/unit/decks/test_commander_search.py`, following `FakeCardRow` in `tests/unit/decks/test_builder.py` | decks | F172-T02 |
| `_fake_price_batch` (dict `card_id -> median_price` stub for `get_latest_prices_batch`) | inline in `tests/unit/decks/test_builder.py` | decks | F172-T02 |
| `deck_suggestions` in-memory engine (`create_engine("sqlite:///:memory:")` + `ensure_table`, pattern from `tests/unit/database/test_repository_decks.py`) | inline in `tests/unit/deck_suggestions/test_repository.py` | deck_suggestions | F172-T03 |
| `_sample_owned_cards` (list of `OwnedCard` covering colored/colorless/duplicate/basic-land) | inline in `tests/unit/deck_suggestions/test_prompt.py`, reused by `tests/unit/deck_suggestions/test_processor.py` | deck_suggestions | F172-T04 (pattern), reused by T09 |
| `_claude_envelope_json` (sample CLI stdout envelope `{"result": "...", "is_error": false}`) and `_claude_api_response_json` (sample Messages API body with `content:[{type:"text",...}]`) | inline in `tests/unit/deck_suggestions/test_claude_runner.py` | deck_suggestions | F172-T05 |
| `mockCommanderSearchResponse` (`ApiResponse<CommanderSearchResult[]>` incl. one row with `name_pt`) | `frontend/src/components/decks/__tests__/CommanderSearch.test.tsx` | frontend | F172-T06 |
| `mockDeckSuggestion` / `mockDeckSuggestionList` (`DeckSuggestion` fixtures covering each `status`, one `done` with a full `SuggestionResult` incl. owned/missing/unresolved/warnings) | `frontend/src/components/decks/__tests__/SuggestionRequestList.test.tsx`, `SuggestionResultView.test.tsx`, `DeckSuggestionPanel.test.tsx` | frontend | F172-T12 (pattern), reused by T13/T14 |

Per `feedback_no_ceremony_specs.md`, no shared fixture module is introduced: every fixture above is a
small task-local builder (dataclass/dict/mock), matching the existing pattern in
`tests/unit/decks/test_builder.py` (`FakeCardRow`) and `frontend/src/pages/__tests__/DeckBuildWizard.test.tsx`
(inline mocked API responses). The feature has no binary/CSV/HTML fixture files to author (unlike
F171) — all inputs are in-memory Python objects, JSON dicts, or TS mock objects.

## 2. Harnesses por fronteira

### Unit
- **Framework:** pytest (backend, pure functions and mocked-Repository services) / Vitest (frontend, pure TS helpers — none in this feature beyond typed API wrappers, covered under Integration below).
- **Comando:** `pytest tests/unit/decks/test_builder.py tests/unit/decks/test_commander_search.py tests/unit/deck_suggestions/test_prompt.py tests/unit/deck_suggestions/test_claude_runner.py -v`
- **Path padrão:** `tests/unit/decks/test_builder.py`, `tests/unit/decks/test_commander_search.py`, `tests/unit/deck_suggestions/test_prompt.py`, `tests/unit/deck_suggestions/test_claude_runner.py`

### Integration
- **Framework:** pytest + in-memory SQLite `Engine` (pattern from `tests/unit/database/test_repository_decks.py`) for T03/T09; pytest + FastAPI `TestClient` with `app.dependency_overrides` (pattern from `tests/unit/api/test_deck_endpoints.py`) for T02/T08/T17; `click.testing.CliRunner` (pattern from existing `tests/cli/*`) for T15; Vitest + React Testing Library with mocked API modules (pattern from `frontend/src/pages/__tests__/DeckBuildWizard.test.tsx`) for T06/T07/T10–T14.
- **Comando (backend):** `pytest tests/unit/deck_suggestions/test_repository.py tests/unit/deck_suggestions/test_processor.py tests/unit/api/test_deck_endpoints.py tests/unit/api/test_deck_suggestions_endpoints.py tests/unit/api/test_deck_suggestions_wiring.py tests/cli/test_deck_suggestions_cli.py -v`
- **Comando (frontend):** `cd frontend && npx vitest run src/components/decks/__tests__ src/pages/__tests__/DeckBuildWizard.test.tsx src/api/__tests__/deckSuggestions.test.ts src/i18n/__tests__/deckSuggestKeys.test.ts`
- **Path padrão:** `tests/unit/deck_suggestions/*.py`, `tests/unit/api/test_deck_*.py`, `tests/cli/test_deck_suggestions_cli.py`, `frontend/src/components/decks/__tests__/*.test.tsx`, `frontend/src/api/__tests__/deckSuggestions.test.ts`, `frontend/src/i18n/__tests__/deckSuggestKeys.test.ts`

### E2E
- **N/A.** The project has no browser-level E2E harness (Playwright is used only by the Liga Magic
  provider for scraping, not for frontend flows — same conclusion as F171/F175). The full user
  journey (mode chooser → commander search or color/archetype form → registered request → daily
  `process-deck-suggestions` run → result view → "Salvar como deck") is covered end-to-end at the
  API layer by T08's `TestClient` tests plus T09's processor tests and T15's `CliRunner` tests, and
  at the UI layer by T14's `DeckSuggestionPanel` integration test with a mocked API — that
  combination is the project's existing substitute for browser E2E.

## 3. Perf budgets

_Sem perf budgets aplicáveis._ This feature is a correctness fix (commander search, budget/legality
wiring) plus an async, once-a-day background flow (deck suggestions are explicitly *not* real-time —
the brief states results land on the next daily run). The only bounded-work rules are correctness
caps, not latency budgets, and are already covered as scenarios: `limit * 10` capped at 500 rows in
commander search (T02), `max_cards=300` owned-card cap and 150-card response cap in `prompt.py`
(T04), and the `DECK_SUGGEST_TIMEOUT` subprocess timeout (T05, tested as a config/error-handling
boundary, not a perf target).

## 4. Mocks vs hits real

| Componente | Decisão | Justificativa |
|---|---|---|
| `get_commander_candidates` / `_query_candidates` / `is_commander_eligible` (T02) | real, against a mocked `Session`/`Repository` returning `FakeCardRow` rows | The soft-legality filter and dedupe/sort logic is exactly what's under test; SQL construction is exercised via the mocked session's `.execute()` capturing the statement, matching the existing `test_builder.py` pattern — a real DB isn't needed to prove the query shape and Python-side post-filter. |
| `generate_deck` price wiring (T02) | real function; `repo.get_latest_prices_batch` mocked to return a fixed dict | The bug (`prices` never filled) is a wiring bug, not a pricing-computation bug — a fixed price map is the simplest way to prove `total_value`/budget now use real numbers, per `feedback_no_ceremony_specs.md` (seeding a real price history table would be ceremony for a wiring test). |
| `deck_suggestions.repository` functions (T03) | real, against an in-memory SQLite `Engine` | `claim_pending`'s conditional-UPDATE race protection and `ensure_table`'s `checkfirst` behavior are DB side effects that a mocked session would hide entirely — this is the same reasoning F171 used for its importer/DB round trips. |
| `prompt.py` (`filter_owned_for_request`, `build_prompt`, `parse_response`) (T04) | real | Pure functions with no I/O; mocking would defeat the point of testing the parsing/prompt-shaping logic itself. |
| `ClaudeCliRunner.run` (T05) | `subprocess.run` mocked (`patch("subprocess.run")`); `shutil.which` mocked for the "binary missing" case | Never invoke a real `claude` CLI subprocess in unit tests (slow, non-deterministic, requires a live login) — the contract under test is argument construction, stdin, timeout, and envelope parsing, all observable via the mock's call args and a crafted return value. |
| `ClaudeApiRunner.run` (T05) | `httpx.post` mocked (`respx` or `unittest.mock.patch`, matching existing `httpx`-based provider tests, e.g. MYP Cards tests) | Never hit the real Anthropic API in tests (cost, network flakiness, key requirement) — status-code branching (429/5xx transient vs 4xx non-transient) and text-block concatenation are what's under test. |
| `processor.process_pending_suggestions` (T09) | real orchestration logic; `ClaudeRunner` is a fake/mock (`run` returns canned JSON or raises `ClaudeRunnerError`); DB via in-memory SQLite `Engine` (real) | The retry/mark_failed/mark_done state machine and per-row exception isolation ("one bad request never aborts the batch") are the actual behavior under test and need a real DB to prove committed state; the Claude call itself is already covered by T05, so faking it here keeps the test deterministic and fast. |
| Prices in `load_owned_cards`/`enrich` (T09) | `Repository.get_latest_prices_batch` mocked to a fixed dict | Same reasoning as T02 — the enrichment math (`missing_cost = unit_price * missing_quantity`) is what's under test, not the price-history query itself (covered elsewhere in the existing `test_repository.py` suite). |
| FastAPI `TestClient` + `app.dependency_overrides` (T08, T17) | real router + schema validation; `get_db`/`require_auth_or_api_key` overridden with a `MagicMock` repo / fixed user id | Matches the existing `test_deck_endpoints.py` pattern — validates real Pydantic validation and real route wiring without needing a live Postgres/SQLite-backed app. |
| `CommanderSearch` / `SuggestionRequestForm` / `SuggestionRequestList` / `SuggestionResultView` / `DeckSuggestionPanel` (T06, T10–T14) | mock (`vi.mock`) of the `decks`/`deckSuggestions` API modules | Component tests, not network integration tests; matches the existing `DeckBuildWizard.test.tsx` pattern of mocking the API layer so assertions target UI state transitions (loading/empty/error, form validation, race-guard) rather than fetch plumbing. |
| `bats/deck-suggestions.bat` (T17) | not executed by any automated test | It's a Windows batch script invoking a local Task Scheduler routine; T17's test scenarios only assert the file exists and documents the required env vars (grep-based), consistent with how `bats/process-queue.bat` is treated elsewhere in the suite. |

## 5. Test scenarios resumo

1. `get_commander_candidates("atra")` (EN partial) and `("voz dos")` (PT partial via `name_pt`) both return matches; an exact-name match sorts before a prefix match — **F172-T02** (AC1).
2. Empty `card_legalities` table → commander search still returns eligible creatures (soft filter); a row with an explicit `banned`/`not_legal` commander-legality row is excluded; a row with no legality row at all passes — **F172-T02** (AC1, H1).
3. Duplicate printings of the same commander (same `name_en`, different `id`) are deduped, preferring the row with `image_uri` — **F172-T02** (H3).
4. `type_line` NULL is excluded; a DFC `"Legendary Creature — X // Y"` is included — **F172-T02** (H4).
5. Search string `"%"` / `"_"` is escaped and does not match everything; a 1-character (post-strip) search returns `[]` — **F172-T02** (AC1).
6. `limit=1` returns exactly 1; with 600 eligible candidates, the `limit * 10` fetch is capped at 500 rows before the Python post-filter and slice — **F172-T02** (Boundary).
7. Colorless commander (`color_identity` `""` or `None`) still matches a colors filter — **F172-T02** (Boundary).
8. `_query_candidates` (used by `generate_deck`) applies the same soft-legality rule: with an empty legality table, `generate_deck` produces non-land cards (not just lands) — **F172-T02** (AC1/AC3, H6).
9. `generate_deck` with a real (mocked) price map: `total_value` reflects the sum of selected cards' `median_price`; a `0.01` budget yields only zero/unknown-priced cards plus a warning — **F172-T02** (AC3, H7).
10. `is_commander_eligible(type_line)` returns True only for `"Legendary" in tl and "Creature" in tl`; `None`/non-matching type lines return False — **F172-T02**.
11. `create_request` → `list_requests` (newest first) → `get_request` → `claim_pending` (status `processing`, `attempts` 1) → `mark_done` → the row's `result_json` round-trips — **F172-T03** (AC5, AC6).
12. `list_requests(status="done")` filters correctly; `limit` is respected; `count_open_requests` counts only `pending`+`processing`, not `done`/`failed` — **F172-T03** (AC5).
13. `delete_pending_request` on a `processing` row returns `False`; a corrupted `result_json` yields `None` on load rather than raising; `mark_failed` truncates `error_message` to 1000 chars — **F172-T03**.
14. `claim_pending(limit=0)` → `[]`; a stale `processing` row exactly at `stale_after` is not re-claimed, one strictly past it is; `release_for_retry` returns the row to `pending` while keeping `attempts` — **F172-T03** (Boundary).
15. Concurrency simulation: two claims where the second's conditional UPDATE affects 0 rows because the first already changed `status` → the second claim does not include that row — **F172-T03** (AC6, concurrency safety).
16. `build_prompt` for a Commander request with 3 owned cards includes the commander name, colors, archetype, and the owned-card lines; `parse_response` on a valid `{"cards": [...]}` (99 entries) returns no warnings — **F172-T04** (AC6).
17. `filter_owned_for_request`: cards whose `color_identity` is not a subset of the requested colors are dropped; colorless owned cards are always kept; a `["C"]` request keeps only colorless cards; duplicate names are merged with summed quantity — **F172-T04**.
18. A notes string containing `</observacoes_do_usuario>` is neutralised (escaped/stripped) before being embedded in the prompt; `notes=None` produces no notes block — **F172-T04** (prompt-injection guard).
19. `parse_response` raises `SuggestionParseError` for: empty string, non-JSON text, `{"cards": []}`, `cards` not a list, and a card entry missing `name` — **F172-T04**.
20. Boundary: a response with 151 cards is either rejected or truncated to 150 with a warning (implementation picks one, test asserts that one consistently); `quantity=0` clamps to 1; `quantity=5` for a non-basic card in `modern` clamps to 4; `quantity=3` for a non-basic card in `commander` clamps to 1; 30× `Island` in commander is kept as-is; a 500-char `deck_name` truncates to 120; `max_cards=300` with 1000 owned cards yields exactly 300 prompt lines — **F172-T04**.
21. `ClaudeCliRunner.run`: a mocked `subprocess.run` returning a JSON envelope `{"result": "...", "is_error": false}` yields the `result` string; `DECK_SUGGEST_MODEL` set adds `--model` to the argv — **F172-T05**.
22. `ClaudeApiRunner.run`: a mocked `httpx.post` response with `content:[{type:"text","text":"..."}]` (possibly multiple text blocks, concatenated) returns the joined text; a non-text block is ignored — **F172-T05**.
23. Error paths: `shutil.which` returning `None` → `ClaudeRunnerError(transient=False)`; non-zero returncode → `transient=True` with `stderr[:500]` in the message; `subprocess.TimeoutExpired` → transient; non-JSON stdout → transient error; API 401 → non-transient; API 429/503 → transient; missing `ANTHROPIC_API_KEY` → non-transient; `get_runner("xyz")` raises/errors on an unknown provider — **F172-T05**.
24. Boundary: a 10 KB stderr is truncated to 500 chars in the raised message; `DECK_SUGGEST_TIMEOUT="abc"` falls back to the default `300` — **F172-T05**.
25. Security: a sentinel value `sk-test-SECRET` used as `ANTHROPIC_API_KEY` never appears in `str(exc)` for any raised `ClaudeRunnerError`, nor in captured logs (`structlog.testing.capture_logs`) — **F172-T05** (secrets-never-logged guardrail).
26. `CommanderSearch`: typing "atr" triggers exactly one API call after the 300 ms debounce; the returned options render and clicking one calls `onSelect` — **F172-T06** (AC1, AC2).
27. `CommanderSearch`: a 1-character (trimmed) query triggers no call; rapid typing ("a","at","atr") triggers a single call; `name_pt` renders under `name_en` when present and different; selecting then clearing calls `onClear` — **F172-T06**.
28. `CommanderSearch`: an `{errors:[...]}` response and a rejected promise both render the inline error and reset `loading` (via `try/finally`) — **F172-T06** (AC2, H5).
29. `CommanderSearch`: 0 results renders the empty state; an older in-flight response resolving after a newer one does not overwrite the newer result (request-sequence guard) — **F172-T06** (AC2, H5).
30. `DeckBuildWizard`: selecting `pioneer` (added to `FORMAT_INFO`) proceeds to the colors step like other 60-card formats — **F172-T06** (H8).
31. `deckSuggestions.ts` API wrappers: each of `createDeckSuggestion`, `listDeckSuggestions`, `getDeckSuggestion`, `saveDeckSuggestion`, `deleteDeckSuggestion` calls the correct HTTP helper with the correct path/body — **F172-T07**.
32. `listDeckSuggestions()` with no status argument sends no query param; `saveDeckSuggestion(1)` with no name sends body `{}`; an `errors` envelope from the helper passes through unchanged; id `0` and a large id interpolate correctly into the path — **F172-T07**.
33. `POST /deck-suggestions` for a commander request (legendary creature with `color_identity="WUBG"`) → 201, `status="pending"`, `colors=["W","U","B","G"]` derived from the card, ignoring any client-sent colors — **F172-T08** (AC5).
34. `POST /deck-suggestions` for a `modern` request with `colors=["r","R","g"]` + `archetype="aggro"` → normalized, deduped, WUBRG-ordered `["R","G"]` — **F172-T08**.
35. `GET /deck-suggestions` returns newest first; `GET /deck-suggestions/{id}` after `mark_done` includes `result`; `POST .../save` creates a deck with the commander plus cards; `DELETE` on a pending request returns 204 — **F172-T08** (AC5, AC7).
36. Validation errors: unknown `format_name`; commander request missing `commander_card_id`; a non-existent card id; a non-legendary card; a non-commander format missing colors/archetype; invalid color letters (`["X"]`, `["C","W"]` mixed); unknown `archetype`; `notes` of 1001 chars — all rejected (400 or 422, whichever is implemented, asserted consistently) — **F172-T08** (AC5).
37. Rate limit: exactly 5 open requests → a 6th is rejected with 429 `VALIDATION_LIMIT_EXCEEDED`; a `failed` or `done` request does not count toward the 5 — **F172-T08** (open-request limit decision #4).
38. `save` on a request not yet `done` → 409; `save` twice on the same `done` request is idempotent (returns the existing `saved_deck_id`); `delete` on a `done` request → 409 — **F172-T08** (AC7).
39. `process_pending_suggestions`: a commander request with 3 of 5 suggested cards owned and 2 priced → `summary.owned_cards=3`, `missing_cards=2`, `missing_cost_brl` = sum of the 2 known prices — **F172-T09** (AC6, AC7).
40. Owned quantity 1 vs. a suggested quantity of 4 (modern) → `missing_quantity=3`; a basic land is always treated as owned (cost 0); a card name returned in PT resolves via `name_pt`; a DFC front-face name resolves; when two printings are owned, the owned `card_id` is preferred over other printings — **F172-T09**.
41. A `ClaudeRunnerError(transient=True)` raised 3 times across 3 processing attempts on the same request → `failed` on the 3rd attempt (`attempts` reaches the cap); a non-transient error → `failed` immediately (no retry); a `SuggestionParseError` → `failed` with a "Resposta inválida do Claude" message; an unexpected exception inside `enrich` → that request is `failed`, and the next pending request in the batch is still processed — **F172-T09** (AC6, resilience).
42. `limit=1` with 3 pending requests processes only the oldest; no pending requests → `ProcessSummary.total == 0`; when every suggested name is unresolved, the request still completes as `done` with `missing_cost_brl=None` and a warning — **F172-T09**.
43. `DeckBuildModeChooser`: clicking the manual card calls `onChoose("manual")`; clicking the suggestion card calls `onChoose("suggestion")`; neither is called on initial render; both buttons have an accessible name — **F172-T10** (AC4).
44. `SuggestionRequestForm`: a commander submission body contains `commander_card_id` and the notes text; a modern submission with colors `["R","G"]` + `archetype="aggro"` produces the matching body — **F172-T11** (AC4).
45. `SuggestionRequestForm`: switching `format_name` resets format-specific fields; toggling colorless `"C"` clears the WUBRG toggles; whitespace-only notes are sent as `null`; the character counter updates as notes are typed — **F172-T11**.
46. `SuggestionRequestForm`: an `errors:[{message:"Too many open requests"}]` response and a rejected promise both render inline and leave the form submittable again; the submit button is disabled until the format-specific required fields (commander selection, or colors + archetype) are present — **F172-T11** (AC5, 429 case).
47. `SuggestionRequestList`: 4 items (one per status: pending/processing/done/failed) render 4 rows with the matching status badges; clicking a row calls `onSelect`; a failed row shows the error in a tooltip; a `done` row with a summary shows the owned/total text — **F172-T12** (AC5, AC7).
48. `SuggestionRequestList`: `confirm()` returning `false` on delete does not call `onDelete`; an empty list shows the empty state; `loading=true` with existing items keeps the items visible (no flicker to empty) — **F172-T12**.
49. `SuggestionResultView`: a `done` fixture with 3 cards (owned, missing-priced, missing-unpriced) renders the correct totals, and clicking "Salvar como deck" calls `saveDeckSuggestion` then navigates to `/decks/{id}` — **F172-T13** (AC7).
50. `SuggestionResultView`: `missing_cost_brl=null` renders "—"; an empty `unresolved` list hides that section; `warnings` are listed; a non-commander result renders without a commander section; a save-error response shows the message with no navigation — **F172-T13**.
51. `DeckSuggestionPanel` (via `DeckBuildWizard?mode=suggestion`): the list loads on mount, a new request from the form is prepended, selecting a `done` row fetches and shows its detail — **F172-T14** (AC4, AC5, AC7).
52. `DeckBuildWizard`: `?mode=bogus` renders the chooser (not a crash); "Trocar modo" clears the param back to the chooser; deleting the currently selected suggestion clears the selection; rapid selection changes only render the last-selected detail (request-id guard, same pattern as T06) — **F172-T14** (AC4).
53. `process-deck-suggestions` CLI: 2 pending requests with a fake runner → exit code 0, summary reports 2 done; `--limit 1` with 2 pending processes 1, leaves 1 pending; `--provider api` is forwarded to `get_runner` — **F172-T15** (AC6).
54. `process-deck-suggestions` CLI: `get_runner` raising a non-transient `ClaudeRunnerError` → exit code 2 with the message printed; a fake runner that always fails → exit 0, summary reports 1 failed (batch does not abort) — **F172-T15**.
55. `process-deck-suggestions` CLI: `--limit 0` processes nothing; `--db` omitted resolves via a patched `get_db_url()` — **F172-T15** (Boundary).
56. Diagrams (`F172-architecture.mmd`, `F172-journey.mmd`) render without a Mermaid syntax error; node labels containing `?`, `/`, or `:` are quoted — **F172-T16** (AC10).
57. Wiring: `/api/v1` includes the `deck_suggestions` router (a request to `/api/v1/deck-suggestions` reaches the router) and `process-deck-suggestions` is registered on the CLI group; importing `src.cli.main` does not raise a circular-import error — **F172-T17** (AC6, AC8).
58. Wiring boundary: `/api/v1/deck-suggestions` does not shadow `/api/v1/decks/{deck_id}` — `GET /api/v1/decks/ranking` (an existing literal-path route) still resolves correctly alongside the new prefix — **F172-T17**.
59. i18n: every `deckBuild.*` and `deckSuggest.*` key present in `en.json` is also present in `pt-BR.json` (and vice versa), including nested keys like `deckSuggest.status.pending`; interpolation placeholders (e.g. `{{query}}`) match exactly between the two locales; deliberately removing one key locally fails the test (then restore it) — **F172-T18** (AC10, H9).

## 6. Anotações para tasks

- (F172-T01, none — docs/infra task, no fixture obligation)
- (F172-T02, `_fake_commander_rows`, `_fake_price_batch`)
- (F172-T03, `deck_suggestions` in-memory engine)
- (F172-T04, `_sample_owned_cards`)
- (F172-T05, `_claude_envelope_json`, `_claude_api_response_json`)
- (F172-T06, `mockCommanderSearchResponse`)
- (F172-T07, none — pure API wrapper functions, mocked HTTP helpers only)
- (F172-T08, `_fake_commander_rows` pattern reused via a mocked `Repository`/`get_card_by_id`)
- (F172-T09, `_sample_owned_cards`, `_fake_price_batch`, fake `ClaudeRunner`)
- (F172-T10, none — presentational component, no fixture needed)
- (F172-T11, `mockCommanderSearchResponse` reused for the embedded `CommanderSearch`)
- (F172-T12, `mockDeckSuggestion` / `mockDeckSuggestionList`)
- (F172-T13, `mockDeckSuggestion` (a `done` variant with full `SuggestionResult`))
- (F172-T14, `mockDeckSuggestionList`, `mockDeckSuggestion`)
- (F172-T15, fake `ClaudeRunner`, `CliRunner`)
- (F172-T17, none — wiring/import assertions only)
- (F172-T18, none — key-parity assertions read the locale JSON files directly)

T16 is a docs task with no `## Test scenarios` code obligation of its own beyond "the diagrams
render"; it is annotated in the scenarios list (56) but needs no reusable fixture.

## Riscos para QA

- **The soft-legality filter (H1/H6) is the single highest-impact behavior in this feature and is
  duplicated in two places** — `get_commander_candidates` (search) and `_query_candidates` (deck
  generation) in `builder.py`. Both must apply the identical `~CardRow.id.in_(select(...banned/not_legal...))`
  rule. QA should diff the two query-building functions after T02 lands and confirm neither one
  silently reverted to a hard `IN legal` filter, since a test passing for one function would not
  catch a regression in the other.
- **The `claim_pending` conditional-UPDATE race guard (T03) is safety-critical for the daily batch
  job** but is only exercised by a single-process simulation in unit tests (updating a row between
  a mocked "select" and "update" step). QA should manually verify with two concurrent
  `process-deck-suggestions --limit 5` invocations against the same SQLite/Postgres DB that no
  request is processed twice (check `attempts` and `result_json` for duplication), since a
  simulated race in pytest is not proof against real DB-level concurrency semantics differing
  between SQLite and Neon Postgres.
- **The Claude CLI runner's `--disallowedTools` flag name is unverified in the brief itself**
  ("verify the flag with `claude --help` in the task"). If T05 ships with a wrong or no-op flag,
  every unit test (which mocks `subprocess.run`) will still pass while the real daily job runs
  Claude with full tool access (Bash/Edit/Write) — a real security exposure the automated suite
  cannot catch. QA must manually run `claude --help` against the actual installed CLI and confirm
  the exact flag used in `claude_runner.py` disables tool use, then do one live dry run of
  `process-deck-suggestions` against a real pending request.
- **`ANTHROPIC_API_KEY` must never be logged (AC8, T05 security scenario 25).** The unit test only
  checks the exception message and `structlog` capture; QA should additionally grep any real log
  output from a manual `--provider api` run for the key value before this ships, since production
  logging configuration (e.g. request/response middleware) is not exercised by the unit tests.
- **`DeckBuildWizard.tsx` is edited twice (T06 in Wave 1, T14 in Wave 3) and both existing test
  files (`DeckBuildWizard.test.tsx`) must be updated to render with `?mode=manual`.** QA should
  re-run the full existing wizard test suite after Wave 3 lands (not just after T06) to confirm T14
  didn't reintroduce the old no-mode-param rendering path that the T06 update removed.
- **Price wiring (H7) changes `generate_deck`'s budget behavior for every existing caller of manual
  deck generation**, not just new suggestion-mode code. QA should re-run
  `pytest tests/unit/decks/test_builder.py tests/unit/api/test_deck_endpoints.py -v` in full after
  T02 and manually build one real commander deck with a low budget in the UI, since a previously
  "always None" `total_value` becoming a real number could newly trip budget-based UI states that
  were never exercised before this feature.
