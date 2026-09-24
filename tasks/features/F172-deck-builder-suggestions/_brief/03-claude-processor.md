# 03 — Claude processor, CLI command, daily routine

## Package layout (all NEW files)

```
src/deck_suggestions/
├── __init__.py
├── models.py          (T03) DeckSuggestionRequestRow
├── repository.py      (T03) queue functions
├── prompt.py          (T04) pure: collection filtering, prompt build, response parse
├── claude_runner.py   (T05) ClaudeCliRunner / ClaudeApiRunner / get_runner()
└── processor.py       (T09) orchestration + enrichment
src/cli/deck_suggestions.py   (T15) click command `process-deck-suggestions`
bats/deck-suggestions.bat     (T17) daily routine
```

## prompt.py (pure, no DB, no network)

```python
@dataclass(frozen=True)
class OwnedCard: name_en: str; name_pt: str | None; quantity: int; color_identity: str | None; type_line: str | None; unit_price: float | None

@dataclass(frozen=True)
class SuggestionInput: format_name: str; commander_name: str | None; colors: list[str]; archetype: str | None; notes: str | None

def filter_owned_for_request(owned: list[OwnedCard], colors: list[str], max_cards: int = 300) -> list[OwnedCard]
    # keep cards whose color_identity ⊆ colors (None/"" = colorless → always kept; "C" request = only colorless);
    # merge duplicates by name_en.lower() (sum quantity, max price); sort by unit_price desc (None last) then name; cap max_cards
def build_prompt(inp: SuggestionInput, owned: list[OwnedCard]) -> str
def parse_response(text: str, format_name: str) -> ParsedSuggestion   # raises SuggestionParseError
def expected_deck_size(format_name) -> int   # commander 100 (incl. commander), others 60
```

### Prompt requirements

- Written in Portuguese (pt-BR) for the strategy text. Card names must be the **official English names** (catalog matching).
- It includes: format, commander (if any), colors, archetype, and the user notes delimited as
  `<observacoes_do_usuario>…</observacoes_do_usuario>`. The prompt states explicitly that this block is user data and not instructions.
  Truncate the notes to 1000 chars.
- It includes the owned-cards list (`- 2x Sol Ring`) and asks the model to **prioritize owned cards** while keeping the deck coherent and format-legal.
- It asks for **only** a JSON object:
  `{"deck_name": str, "strategy": str, "cards": [{"name": str, "quantity": int, "category": str, "reason": str}]}`.
  The commander is NOT in `cards`. Singleton rules apply to commander formats (qty 1 except basic lands). Max 4 copies apply otherwise.
  Total = expected size (commander: 99 in `cards`).

### parse_response

- Strip ```json fences. Take the first balanced `{…}` object. `json.loads`.
- Validate: `cards` is a non-empty list with ≤ 150 entries. `name` is a non-empty str ≤ 200 chars. `quantity` is an int in 1..(99 if basic land else 4, and 1 for singleton non-basic).
  Clamp the quantity instead of failing, and add a warning. `deck_name` ≤ 120 chars (default "Sugestão {format}"). `strategy` ≤ 2000 chars.
- Merge duplicate names (sum qty, then re-clamp).
- Size mismatch vs `expected_deck_size` → warning, not an error.
- Raise `SuggestionParseError` for no JSON, invalid JSON, or missing/empty `cards`.

## claude_runner.py (no new deps)

```python
class ClaudeRunnerError(Exception): transient: bool
class ClaudeRunner(Protocol):
    provider: str; model: str
    def run(self, prompt: str) -> str: ...

class ClaudeCliRunner:   # provider="cli" (DEFAULT)
    # cmd = [bin, "-p", "--output-format", "json", "--max-turns", "1"] + (["--model", model] if model else [])
    # bin = os.environ.get("DECK_SUGGEST_CLAUDE_BIN", "claude")  (resolved with shutil.which; missing → ClaudeRunnerError(transient=False))
    # disable tools: pass "--disallowedTools" with "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch,Read,Glob,Grep"
    #   (verify the flag with `claude --help` in the task; if `--tools ""` exists prefer it)
    # prompt sent via stdin (input=prompt), text=True, capture_output=True,
    # timeout=int(os.environ.get("DECK_SUGGEST_TIMEOUT", "300")), cwd=tempfile.mkdtemp() (empty dir; removed afterwards)
    # returncode != 0 → ClaudeRunnerError(stderr[:500], transient=True); TimeoutExpired → transient=True
    # stdout is a JSON envelope → return envelope["result"] (if envelope.get("is_error") → transient error)
class ClaudeApiRunner:   # provider="api"
    # key = os.environ["ANTHROPIC_API_KEY"] (missing → ClaudeRunnerError(transient=False, "ANTHROPIC_API_KEY not set"))
    # httpx.post("https://api.anthropic.com/v1/messages",
    #   headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
    #   json={"model": model, "max_tokens": 8000, "messages": [{"role": "user", "content": prompt}]}, timeout=...)
    # 429/5xx → transient; other 4xx → non-transient; return "".join(block["text"] for block in content if type=="text")
    # NEVER log the key or headers.
def get_runner(provider: str | None = None) -> ClaudeRunner
    # provider = provider or os.environ.get("DECK_SUGGEST_PROVIDER", "cli")
    # model = os.environ.get("DECK_SUGGEST_MODEL", "claude-sonnet-5")  (CLI: only pass --model if env var explicitly set)
```

**Pending decision (README):** the official `anthropic` SDK is NOT added (no new deps without confirmation).
The `httpx` implementation covers the need. If the user approves the SDK later, only `ClaudeApiRunner` changes.

## processor.py

```python
@dataclass
class ProcessSummary: total: int = 0; done: int = 0; failed: int = 0; retried: int = 0

def load_owned_cards(engine, user_id) -> list[OwnedCard]
    # UserCollectionRow (user_id) LEFT JOIN CardRow on card_id → name_en (fallback collection name_en), name_pt, quantity,
    # CardRow.color_identity, CardRow.type_line; prices via Repository.get_latest_prices_batch(card_ids) → median_price
def resolve_cards(engine, names: list[str], owned_by_name: dict[str, OwnedCard]) -> dict[str, dict]
    # case-insensitive exact on CardRow.name_en, fallback name_pt; choose printing: owned card_id first, then row with image_uri, then highest id.
    # DFC: also try match on name_en.split(" // ")[0]
def enrich(parsed, request_row, owned, resolved, prices) -> dict   # builds SuggestionResult (see 02 shard); pure, unit-testable
def process_pending_suggestions(repo, runner, *, limit=5, dry_run=False) -> ProcessSummary
    # dry_run: count claimable (no claim), return summary.total
    # for row in claim_pending(repo.engine, limit):
    #   try: owned = filter_owned_for_request(load_owned_cards(...), colors); prompt = build_prompt(...)
    #        text = runner.run(prompt); parsed = parse_response(text, fmt); result = enrich(...); mark_done
    #   except ClaudeRunnerError as e: transient and row.attempts < 3 → release_for_retry (retried+=1) else mark_failed
    #   except SuggestionParseError → mark_failed("Resposta inválida do Claude: …")
    #   except Exception → log.exception + mark_failed(str(e)[:500])   # one bad request never aborts the batch
```

Prices: `missing_cost = unit_price * missing_quantity` (None if no price). `missing_cost_brl` = sum of the known costs
(None if no card has a price). Basic lands (`Plains, Island, Swamp, Mountain, Forest, Wastes`) are treated as owned (cost 0).

## CLI (`src/cli/deck_suggestions.py`, T15) — registered in `src/cli/main.py` by T17

```python
@click.command("process-deck-suggestions")
@click.option("--db", default=None, help="Database URL (default: auto-detect)")   # resolve with src.config.get_db_url() when None
@click.option("--limit", default=5, type=int)
@click.option("--provider", type=click.Choice(["cli","api"]), default=None, help="Default: $DECK_SUGGEST_PROVIDER or cli")
@click.option("--dry-run", is_flag=True)
def process_deck_suggestions(db, limit, provider, dry_run): ...
```

Do **not** import from `src.cli.main` (that would be a circular import once main registers this command).
Output format mirrors `process-price-requests` (`src/cli/main.py:1216`).

## Daily routine (`bats/deck-suggestions.bat`, T17)

Mirror `bats/process-queue.bat`. It calls `python -m src.cli.main process-deck-suggestions --limit 10`.
REM header: purpose, Task Scheduler suggestion (daily 03:00), and the env vars it needs:
`DECK_SUGGEST_PROVIDER`, `DECK_SUGGEST_CLAUDE_BIN`, `DECK_SUGGEST_MODEL`, `DECK_SUGGEST_TIMEOUT`, `ANTHROPIC_API_KEY` (only for provider=api; read from `.env`, never written in the .bat).
