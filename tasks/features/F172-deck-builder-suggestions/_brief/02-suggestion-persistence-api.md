# 02 — Suggestion request persistence + REST API

## Table `deck_suggestion_requests` (new module `src/deck_suggestions/models.py`)

```python
from src.database.models import Base  # shared declarative Base — do NOT edit models.py

class DeckSuggestionRequestRow(Base):
    __tablename__ = "deck_suggestion_requests"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    format_name: Mapped[str] = mapped_column(String(30), nullable=False)
    commander_card_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cards.id", ondelete="SET NULL"))
    commander_name: Mapped[str | None] = mapped_column(String(500))   # denormalized, survives card deletion
    colors: Mapped[str | None] = mapped_column(String(10))            # "WUB" sorted in WUBRG order; "C" = colorless
    archetype: Mapped[str | None] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text)                   # <= 1000 chars (validated at API)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # status: pending | processing | done | failed
    result_json: Mapped[str | None] = mapped_column(Text)             # json.dumps(SuggestionResult)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saved_deck_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("decks.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    __table_args__ = (
        Index("ix_deck_sugg_req_user", "user_id"),
        Index("ix_deck_sugg_req_status", "status"),
        Index("ix_deck_sugg_req_created", "created_at"),
    )
```

Follow the pattern of `PriceUpdateRequestRow` (`src/database/models.py:602`).

## Repository (new module `src/deck_suggestions/repository.py`)

Plain functions that take a SQLAlchemy `Engine` (use `repo.engine`) and use `Session(engine)`, like `builder.py` does.

```python
ensure_table(engine) -> None      # DeckSuggestionRequestRow.__table__.create(engine, checkfirst=True); memoized per engine id
create_request(engine, *, user_id, format_name, commander_card_id, commander_name, colors, archetype, notes) -> DeckSuggestionRequestRow
count_open_requests(engine, user_id) -> int          # pending + processing
list_requests(engine, user_id, *, status=None, limit=20) -> list[Row]   # newest first
get_request(engine, request_id, user_id) -> Row | None                  # ownership enforced
delete_pending_request(engine, request_id, user_id) -> bool             # only when status == pending
claim_pending(engine, limit, *, stale_after=timedelta(hours=2)) -> list[Row]
    # selects status=='pending' OR (status=='processing' AND started_at < now-stale_after),
    # ordered by created_at, and for each row: status='processing', started_at=now, attempts+=1; commit.
    # Use conditional UPDATE ... WHERE id=:id AND status=:old_status (rowcount==1) so concurrent runners never double-claim.
mark_done(engine, request_id, result: dict) -> None      # status done, result_json=json.dumps(result, ensure_ascii=False), processed_at, error_message=None
mark_failed(engine, request_id, error: str) -> None      # status failed, error_message=error[:1000], processed_at
release_for_retry(engine, request_id, error: str) -> None  # status pending, error_message kept (transient failure)
set_saved_deck(engine, request_id, deck_id) -> None
```

Every public function calls `ensure_table(engine)` first (cheap after memoization).
Rows returned are detached. Use `expire_on_commit=False` or copy them into dataclasses before the session closes.

## API (new router `src/api/routers/deck_suggestions.py`, `APIRouter(prefix="/deck-suggestions", tags=["decks"])`)

Mounted under `/api/v1` by F172-T17. Auth: `user_id: str = Depends(require_auth_or_api_key)` (`src/api/deps.py`), same as the `decks.py` router.
Envelope: `ApiResponse[...]` + `success_response` (`src/api/schemas/envelope.py`). Errors: `api_error(status, ErrorCode.X, msg)` (`src/api/error_codes.py`).

| Method | Path | Body / query | Response | Errors |
|---|---|---|---|---|
| POST | `/deck-suggestions` | `DeckSuggestionCreate` | 201 `ApiResponse[DeckSuggestionSchema]` | 400 VALIDATION_ERROR, 429 VALIDATION_LIMIT_EXCEEDED (≥5 open) |
| GET | `/deck-suggestions` | `?status=&limit=20 (1..50)` | `ApiResponse[list[DeckSuggestionSchema]]` (`result` omitted, `summary` included) | 400 bad status |
| GET | `/deck-suggestions/{id}` | — | `ApiResponse[DeckSuggestionSchema]` with `result` | 404 RESOURCE_NOT_FOUND (also when owned by another user) |
| POST | `/deck-suggestions/{id}/save` | `{ "deck_name"?: str (1..300) }` | `ApiResponse[{deck_id:int}]` | 404, 409 RESOURCE_CONFLICT when status ≠ done. Idempotent: return the existing `saved_deck_id` if set and the deck still exists |
| DELETE | `/deck-suggestions/{id}` | — | 204 | 404, 409 when not pending |

### Schemas (`src/api/schemas/deck_suggestions.py`)

```python
SUGGESTION_FORMATS = {"commander","standard","pioneer","modern","legacy","vintage","pauper","casual"}
SUGGESTION_ARCHETYPES = {"aggro","control","midrange","combo","tempo","ramp"}

class DeckSuggestionCreate(BaseModel):
    format_name: str
    commander_card_id: int | None = None
    colors: list[str] = []            # subset of W,U,B,R,G or ["C"]
    archetype: str | None = None
    notes: str | None = Field(default=None, max_length=1000)

class SuggestionSummary(BaseModel):
    total_cards: int; owned_cards: int; missing_cards: int
    missing_cost_brl: float | None; unresolved_count: int

class DeckSuggestionSchema(BaseModel):
    id: int; format_name: str; commander_card_id: int | None; commander_name: str | None
    colors: list[str]; archetype: str | None; notes: str | None
    status: Literal["pending","processing","done","failed"]
    error_message: str | None; saved_deck_id: int | None
    created_at: datetime; processed_at: datetime | None
    summary: SuggestionSummary | None = None
    result: dict | None = None        # full SuggestionResult (detail endpoint only)
```

### Validation rules (POST)

- `format_name.lower()` ∈ `SUGGESTION_FORMATS`, else 400.
- `commander`: `commander_card_id` is required. The card must exist (`repo.get_card_by_id`) and pass
  `is_commander_eligible(card.type_line)` (from `src/decks/builder.py`, added by F172-T02), else 400.
  `colors` = derived from `card.color_identity` (ignore client colors). `commander_name = card.name_en`. `archetype` is optional.
- other formats: `colors` must be non-empty and made of WUBRG letters, or exactly `["C"]`. Uppercase and dedupe them, then store in WUBRG order.
  `archetype` is required and must be in `SUGGESTION_ARCHETYPES`. `commander_card_id` must be None (ignore/strip it).
- `notes`: strip, empty → None, max 1000 characters.
- Rate limit: `count_open_requests(user) >= 5` → 429 `VALIDATION_LIMIT_EXCEEDED`.

### Save as deck

`result["cards"]` → `repo.create_deck(user_id, name)` + `repo.add_deck_cards(deck.id, cards)` exactly like
`generate_deck_endpoint` in `src/api/routers/decks.py:~323` (dict keys `name_en,set_code,collector_number,quantity,card_id`).
The commander (if any) is included as a card. Unresolved cards are included with `card_id=None`.
Default name = `result["deck_name"]`. Then `set_saved_deck`.

## Result contract (`SuggestionResult`, stored in `result_json`)

```json
{
  "deck_name": "Atraxa Superfriends",
  "strategy": "texto pt-BR 2-4 frases",
  "format_name": "commander",
  "commander": {"name_en": "Atraxa, Praetors' Voice", "card_id": 123} ,
  "cards": [
    {"name_en": "Sol Ring", "quantity": 1, "category": "Ramp", "reason": "…",
     "card_id": 55, "set_code": "cmr", "collector_number": "472", "image_uri": "…",
     "is_owned": true, "owned_quantity": 2, "missing_quantity": 0,
     "unit_price": 12.5, "missing_cost": 0.0}
  ],
  "summary": {"total_cards": 100, "owned_cards": 61, "missing_cards": 39,
              "missing_cost_brl": 842.3, "unresolved_count": 2},
  "unresolved": ["Nome Inventado"],
  "warnings": ["Deck has 98 cards (expected 100)"],
  "provider": "cli", "model": "claude-sonnet-5", "generated_at": "2026-09-25T03:00:12"
}
```
