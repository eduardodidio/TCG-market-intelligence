# T01 -- Wishlist Table & Repository Methods

**Wave:** 0 (DB Schema)
**Depends on:** nothing
**Blocks:** T02, T03, T04

## User Story

As a developer, I need a `wishlist` table so that users can persist their
desired cards and the trade matcher can query across wishlists.

## Dev Notes

### WishlistRow model (add to `src/database/models.py`)

```python
class WishlistRow(Base):
    __tablename__ = "wishlist"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    card_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )
    # Denormalized for display without joins
    name_en: Mapped[str] = mapped_column(String(500), nullable=False)
    name_pt: Mapped[str | None] = mapped_column(String(500))
    set_code: Mapped[str | None] = mapped_column(String(20))
    collector_number: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(String(500))
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    is_acquired: Mapped[int] = mapped_column(Integer, default=0)
    acquired_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "card_id", name="uq_wishlist_user_card"),
        Index("ix_wishlist_user", "user_id"),
        Index("ix_wishlist_card", "card_id"),
        Index("ix_wishlist_user_acquired", "user_id", "is_acquired"),
    )
```

### Key design decisions

- `card_id` FK to `cards.id` (CASCADE delete) -- wishlist items reference
  canonical cards, not source_cards
- `UniqueConstraint("user_id", "card_id")` -- one wishlist entry per card
  per user (no duplicates in wishlist)
- `max_price` -- optional price ceiling, useful for trade matcher filtering
- `is_acquired` -- soft flag, keeps history of what was wanted
- Denormalized `name_en`, `set_code`, etc. for fast list rendering without
  joins (follows UserCollectionRow pattern)

### Repository methods to add

1. `add_wishlist_item(user_id, card_id, name_en, ...)` -- INSERT OR IGNORE
2. `remove_wishlist_item(user_id, card_id)` -- DELETE
3. `get_wishlist(user_id, include_acquired=False)` -- SELECT with optional filter
4. `mark_wishlist_acquired(user_id, card_id)` -- UPDATE is_acquired=1
5. `is_in_wishlist(user_id, card_id)` -- EXISTS check (for UI button state)
6. `get_wishlist_card_ids(user_id)` -- returns set of card_ids (for batch checks)

Also update the `WishlistRow` import in `repository.py` so `create_all` picks it up.

## Testing

- Unit tests for each repository method
- Test unique constraint violation returns gracefully (no crash)
- Test CASCADE: deleting a card removes wishlist entries
- Test CASCADE: deleting a user removes wishlist entries
- Test `include_acquired=False` filters correctly
