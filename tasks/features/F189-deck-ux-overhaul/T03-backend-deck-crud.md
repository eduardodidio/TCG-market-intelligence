# F189-T03 — Backend: create empty deck + update deck endpoints

**Feature:** F191
**Wave:** 1
**Status:** planned
**Parallel:** yes (independent of T04, T05, T06 at the backend level)

## User Story

As a user, I want to create an empty deck with just a name and description, and later rename or update the description, so I can manage my deck metadata without importing cards first.

## Dev Notes

### Files to MODIFY

**`src/api/schemas/decks.py`**
- Add new Pydantic schema `DeckCreateRequest`:
  ```python
  class DeckCreateRequest(BaseModel):
      name: str = Field(min_length=1, max_length=200)
      description: str | None = None
  ```
- Add new Pydantic schema `DeckUpdateRequest`:
  ```python
  class DeckUpdateRequest(BaseModel):
      name: str | None = Field(default=None, min_length=1, max_length=200)
      description: str | None = None
  ```
- Add new response schema `DeckCreateResult`:
  ```python
  class DeckCreateResult(BaseModel):
      deck_id: int
      name: str
      description: str | None = None
  ```

**`src/api/routers/decks.py`**
- Modify existing `POST /decks` endpoint to support TWO modes:
  - If request body contains `format` and `content` fields: use existing `DeckImportRequest` flow (backward-compatible)
  - If request body contains only `name` (and optional `description`): create an empty deck
  - Implementation approach: accept a union body or add a separate endpoint
  - **Recommended approach:** Add a NEW `POST /decks/create` endpoint for the simple create, keeping the existing `POST /decks` for import. This avoids breaking the existing import flow.
  - Alternative: use `POST /decks` with a discriminated union. The developer should pick the cleanest approach.
- Add `PUT /decks/{deck_id}` endpoint:
  ```python
  @router.put("/{deck_id}", response_model=ApiResponse[DeckDetailSchema])
  def update_deck(
      deck_id: int,
      request: DeckUpdateRequest,
      repo: Repository = Depends(get_db),
      user_id: str = Depends(require_auth_or_api_key),
  ):
      deck = repo.get_deck(deck_id)
      if not deck or deck.user_id != user_id:
          raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Deck not found")
      updated = repo.update_deck(deck_id, name=request.name, description=request.description)
      # Return updated deck detail (reuse get_deck logic or return summary)
  ```

**`src/database/repository.py`**
- Add `update_deck()` method (near line 2682, after `create_deck`):
  ```python
  def update_deck(self, deck_id: int, name: str | None = None, description: str | None = None) -> DeckRow | None:
      with Session(self.engine) as session:
          deck = session.execute(
              select(DeckRow).where(DeckRow.id == deck_id)
          ).scalar_one_or_none()
          if not deck:
              return None
          if name is not None:
              deck.name = name
          if description is not None:
              deck.description = description
          session.commit()
          session.refresh(deck)
          session.expunge(deck)
          return deck
  ```

### Key constraints
- The existing `POST /decks` import endpoint MUST remain backward-compatible. The DeckImportModal on DeckList.tsx calls `importDeck()` which sends `{ name, format, content, description }`.
- The new create endpoint should accept `{ name, description }` without requiring `format` or `content`.
- Authorization: both new endpoints must require `require_auth_or_api_key`.
- The `update_deck` should only update fields that are explicitly provided (partial update semantics). A `None` value for `description` in the request means "set description to null" -- the developer needs to decide if this uses a sentinel or if `description` is simply always set. A pragmatic approach: if the field is present in the JSON body, update it.

### Edge cases
- Creating a deck with an empty name should return 422 (Pydantic validation)
- Creating a deck with name exceeding 200 chars should return 422
- Updating a deck that belongs to another user should return 404
- Updating a nonexistent deck should return 404
- Partial update: sending only `name` should not clear `description`, and vice versa

## Testing

- [ ] Unit test: `test_create_empty_deck` — POST with just name returns 200 + deck_id
- [ ] Unit test: `test_create_empty_deck_with_description` — POST with name + description
- [ ] Unit test: `test_create_deck_empty_name_rejected` — POST with empty name returns 422
- [ ] Unit test: `test_update_deck_name` — PUT with new name, verify name changed
- [ ] Unit test: `test_update_deck_description` — PUT with new description
- [ ] Unit test: `test_update_deck_partial` — PUT with only name, description unchanged
- [ ] Unit test: `test_update_deck_not_found` — PUT on nonexistent deck returns 404
- [ ] Unit test: `test_update_deck_wrong_user` — PUT on another user's deck returns 404
- [ ] Unit test: `test_import_deck_still_works` — existing POST /decks import flow unchanged
- [ ] Integration test: repository `update_deck()` method
- [ ] Integration test: repository `create_deck()` with description parameter (already exists but verify)
