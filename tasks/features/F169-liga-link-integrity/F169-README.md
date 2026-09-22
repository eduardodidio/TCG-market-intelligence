# F169 — Liga Link Integrity

**Status:** planned

## User Story

As a user viewing a card detail page, I want the "Conferir na Liga" link to open
the exact Liga Magic page for that card/edition, not a generic name-based search
that may show the wrong edition.

## Problem

The API endpoints that build `ligamagic_url` use `liga_url_for_card_name()` which
produces a name-based search URL. Liga search returns the first matching edition,
which often does not match the card the user is looking at.

Meanwhile, the infrastructure to solve this already exists:

- `liga_sweep` stores the actual page URL in `liga_card_urls` via `record_liga_url()`
- `resolve_liga_card_url()` in `src/providers/liga/urls.py` implements correct
  fallback logic (stored URL first, name-based second)
- `repo.get_liga_card_url(external_id)` retrieves stored URLs

But neither the CardDetail endpoint nor `_build_collection_detail()` calls them.

## Wave Breakdown

### Wave 0 (T01 + T02 in parallel)

Both are backend API fixes in different files with no interdependency.

| Task | Description | File |
|------|-------------|------|
| T01  | CardDetail endpoint: use `resolve_liga_card_url` | `src/api/routers/cards.py` |
| T02  | Collection detail: use `resolve_liga_card_url` | `src/api/routers/collection.py` |

### Wave 1 (T03)

CLI verification command. Depends on understanding the stored URL pattern from Wave 0.

| Task | Description | File |
|------|-------------|------|
| T03  | `liga-verify-links` CLI command | `src/cli/main.py` |

### Wave 2 (T04)

CLI re-linking command. Depends on T03 design for mismatch reporting format.

| Task | Description | File |
|------|-------------|------|
| T04  | `liga-relink` CLI command | `src/cli/main.py` |

## Acceptance Criteria

1. CardDetail endpoint (`GET /api/v1/cards/{id}`) returns a stored Liga URL when
   one exists for that card, falling back to name-based search only when no
   stored URL is available.
2. Collection detail endpoint returns the same improved Liga URL.
3. Foil cards prefer the foil-specific stored URL (`liga_{id}_foil`), then fall
   back to the non-foil URL, then to name-based search.
4. `liga-verify-links` CLI command reads all `liga_card_urls`, visits each via
   Playwright, and reports mismatches (card name on page vs expected name).
5. `liga-relink` CLI command re-fetches the correct URL for cards flagged as
   mismatched by T03, updating `liga_card_urls`.
6. All existing tests pass; new unit tests cover the `resolve_liga_card_url`
   integration in both endpoints.
