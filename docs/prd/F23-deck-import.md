# PRD: F23 -- Deck Import

**Status:** planned
**Depends on:** F22 (Authentication)
**Priority:** medium
**Author:** Architect agent

## Problem Statement

Users have card collections imported into the system but no way to organize
cards into decks. They want to import a deck list (same CSV format used for
collection import), view the deck, and immediately see which cards they
already own versus which they still need to acquire.

## Goals

1. Allow users to create decks by importing a card list (text/CSV).
2. Persist decks per user (requires F22 auth).
3. Display deck contents as a card grid with visual ownership indicators.
4. Cards NOT in the user's collection appear with a darkened overlay.
5. Hovering a non-owned card shows a tooltip: "Card nao esta na sua colecao".
6. Clicking any card (owned or not) navigates to the collection detail page.

## Non-Goals (this iteration)

- Deck editing (add/remove individual cards after import).
- Deck comparison or diff views.
- Deck format validation (Standard, Modern, etc.).
- Deck statistics (mana curve, color distribution) -- planned for future.
- Card comparison within the detail page (noted as future in brief).
- Sharing decks between users.

## User Stories

### US-1: Import a deck
As a user, I want to paste or upload a deck list so that the system creates
a named deck with all the cards.

**Acceptance criteria:**
- Import accepts the same CSV column format as collection import.
- Import also accepts a simple text format: `{quantity} {card_name}` per line
  (e.g., `4 Lightning Bolt`), with optional set code in brackets: `4 Lightning Bolt [M11]`.
- The user provides a deck name at import time.
- On success, the system returns the deck ID and card count.
- Duplicate deck names per user are allowed (names are not unique).

### US-2: List my decks
As a user, I want to see all my decks so that I can pick one to view.

**Acceptance criteria:**
- GET endpoint returns all decks for the authenticated user.
- Each deck shows: name, card count, created date, ownership percentage.
- Sorted by most recently created.

### US-3: View a deck
As a user, I want to view a deck's card list with ownership indicators so
I can see what I already own.

**Acceptance criteria:**
- Each card in the deck shows quantity needed.
- Cards in the user's collection are displayed normally.
- Cards NOT in the user's collection have a darkened overlay (CSS opacity/brightness).
- Hovering a non-owned card shows a tooltip.
- Clicking any card navigates to `/collection/:id` (if owned) or to a
  card-level detail view (if not owned, navigate to `/cards/:cardId` or show
  a minimal detail).

### US-4: Delete a deck
As a user, I want to delete a deck I no longer need.

**Acceptance criteria:**
- DELETE endpoint removes the deck and all its card entries.
- Returns 404 if deck does not exist or belongs to another user.

## Data Model

### `decks` table
| Column      | Type         | Notes                              |
|-------------|--------------|------------------------------------|
| id          | INTEGER PK   | autoincrement                      |
| user_id     | VARCHAR(100) | NOT NULL, FK to user (from F22)    |
| name        | VARCHAR(300) | NOT NULL                           |
| description | TEXT         | nullable, optional                 |
| created_at  | DATETIME     | default now                        |
| updated_at  | DATETIME     | default now, on update             |

### `deck_cards` table
| Column           | Type         | Notes                                      |
|------------------|--------------|---------------------------------------------|
| id               | INTEGER PK   | autoincrement                               |
| deck_id          | INTEGER      | NOT NULL, FK to decks.id, ON DELETE CASCADE |
| set_code         | VARCHAR(20)  | nullable (may not be provided in text fmt)  |
| collector_number | VARCHAR(20)  | nullable                                    |
| name_en          | VARCHAR(500) | NOT NULL                                    |
| quantity         | INTEGER      | default 1                                   |
| card_id          | INTEGER      | nullable, FK to cards.id (linked if found)  |

Index: `(deck_id, set_code, collector_number)` for dedup within a deck.

## API Endpoints

All endpoints require authentication (F22).

| Method | Path                        | Description                         |
|--------|-----------------------------|-------------------------------------|
| POST   | `/api/v1/decks/import`      | Import deck from text/CSV body      |
| GET    | `/api/v1/decks`             | List user's decks                   |
| GET    | `/api/v1/decks/{id}`        | Deck detail with cards + ownership  |
| DELETE | `/api/v1/decks/{id}`        | Delete a deck                       |

### POST /api/v1/decks/import

**Request body:**
```json
{
  "name": "My Burn Deck",
  "format": "text",
  "content": "4 Lightning Bolt\n4 Lava Spike [MH2]\n2 Eidolon of the Great Revel"
}
```

`format` can be `"text"` (simple list) or `"csv"` (same columns as collection).

**Response:**
```json
{
  "data": {
    "deck_id": 42,
    "name": "My Burn Deck",
    "cards_imported": 10,
    "cards_linked": 7
  }
}
```

### GET /api/v1/decks/{id}

**Response includes ownership flag per card:**
```json
{
  "data": {
    "id": 42,
    "name": "My Burn Deck",
    "cards": [
      {
        "id": 1,
        "name_en": "Lightning Bolt",
        "set_code": null,
        "collector_number": null,
        "quantity": 4,
        "owned_quantity": 4,
        "in_collection": true,
        "collection_entry_id": 123,
        "image_url": "https://...",
        "latest_price": 2.50
      }
    ],
    "total_cards": 60,
    "owned_cards": 45,
    "ownership_pct": 75.0
  }
}
```

## Frontend Pages

### /decks -- Deck List
- Grid or list of user's decks.
- Each deck card shows: name, card count, ownership %, created date.
- "Import Deck" button opens import modal/page.

### /decks/:id -- Deck View
- Card grid identical to collection view.
- Non-owned cards: `opacity-50 brightness-50` overlay + tooltip on hover.
- Owned cards: normal display, click navigates to `/collection/:entryId`.
- Summary bar: total cards, owned, missing, ownership %.

### Import Modal/Page
- Text area for pasting deck list.
- Name input field.
- Format toggle (text / CSV).
- Import button with loading state.

## Ownership Check Logic

For each `deck_card`, determine ownership by matching against `user_collection`:
1. If `deck_card.card_id` is not null: check if any `user_collection` row has
   the same `card_id` for the user.
2. If `card_id` is null: match by `set_code + collector_number` (if available)
   or by `name_en` (case-insensitive).
3. `owned_quantity` = sum of matching collection entries' quantities.
4. `in_collection` = `owned_quantity > 0`.

This check happens at query time (GET /decks/{id}), not stored.

## Technical Notes

- Reuse `src/collection/importer.py` CSV parsing logic for CSV format.
- New simple text parser for `{qty} {name} [{set}]` format.
- Deck card linking to canonical `cards` table reuses the same
  `set_code + collector_number` lookup from `importer.py`.
- Frontend reuses `CollectionCardTile` component pattern with an
  `ownership` prop for the overlay behavior.
