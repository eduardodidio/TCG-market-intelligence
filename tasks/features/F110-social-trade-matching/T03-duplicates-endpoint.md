# T03 -- Duplicates Detection Endpoint

**Wave:** 1 (Backend)
**Depends on:** T01
**Blocks:** T06

## User Story

As a user, I want to see which cards I have more than one copy of so I know
what is available for trade.

## Dev Notes

### Endpoint

Add to existing `src/api/routers/collection.py` (or a new `trade_match.py`
router -- prefer new router for clean separation).

New router: `src/api/routers/trade_match.py`
Prefix: `/api/v1/trade`, tags: `["trade-match"]`

| Method | Path          | Description                           | Auth |
|--------|---------------|---------------------------------------|------|
| GET    | `/duplicates` | List cards with quantity > 1           | yes  |
| GET    | `/duplicates/count` | Count of duplicate cards         | yes  |

### Query logic

```sql
SELECT uc.card_id, uc.name_en, uc.set_code, uc.collector_number,
       uc.quantity, uc.quality, uc.extras,
       c.image_uri, c.rarity
FROM user_collection uc
LEFT JOIN cards c ON uc.card_id = c.id
WHERE uc.user_id = :user_id
  AND uc.quantity > 1
  AND uc.card_id IS NOT NULL
ORDER BY uc.quantity DESC, uc.name_en
LIMIT :limit OFFSET :offset
```

### Response schema

```python
class DuplicateCard(BaseModel):
    card_id: int
    name_en: str
    name_pt: str | None
    set_code: str | None
    collector_number: str | None
    quantity: int
    surplus: int  # quantity - 1 (available for trade)
    quality: str | None
    image_uri: str | None
    current_price: float | None
```

### Repository method

`get_user_duplicates(user_id, limit, offset)` -- returns list of
UserCollectionRow entries where quantity > 1, joined with CardRow for
image_uri.

Also: `get_user_duplicate_card_ids(user_id)` -- returns dict of
`{card_id: surplus_quantity}` for the trade matcher to use.

## Testing

- Test with user who has no duplicates (empty list)
- Test with quantity=2 returns surplus=1
- Test with quantity=5 returns surplus=4
- Test entries with card_id=NULL are excluded
- Test pagination
- Test auth required
