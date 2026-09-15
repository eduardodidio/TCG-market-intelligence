# T04 -- Trade Matcher Service & Endpoint

**Wave:** 1 (Backend)
**Depends on:** T01
**Blocks:** T06

## User Story

As a user, I want to see other users who have cards I want (from my wishlist)
available as duplicates, so I can initiate trades with them.

## Dev Notes

### Service: `src/services/trade_matcher.py`

Core function:

```python
def find_trade_matches(
    user_id: int,
    repo: Repository,
    limit: int = 20,
) -> list[TradeMatch]:
    """
    For the given user:
    1. Get their active wishlist card_ids
    2. Find other users who have those card_ids with quantity > 1
       AND whose collection is shared (shared_collections.is_shared=1)
    3. Group by partner user, rank by number of matching cards
    4. Return top matches with card details
    """
```

### SQL approach (single efficient query)

```sql
SELECT
    sc.user_id AS partner_user_id,
    u.display_name AS partner_name,
    sc.share_code,
    COUNT(DISTINCT uc.card_id) AS matching_cards,
    GROUP_CONCAT(DISTINCT c.name_en) AS card_names
FROM wishlist w
JOIN user_collection uc
    ON uc.card_id = w.card_id
    AND uc.quantity > 1
    AND uc.user_id != w.user_id
JOIN shared_collections sc
    ON sc.user_id = uc.user_id
    AND sc.is_shared = 1
JOIN users u ON u.id = uc.user_id
JOIN cards c ON c.id = w.card_id
WHERE w.user_id = :user_id
  AND w.is_acquired = 0
GROUP BY sc.user_id
ORDER BY matching_cards DESC
LIMIT :limit
```

### Privacy rules

- Only match against users who have sharing enabled (`is_shared=1`)
- Do NOT reveal partner's email or user_id directly -- use `share_code`
  as the identifier (same pattern as marketplace)
- Display partner's `display_name` (or "Anonymous" if null)

### Response schema

```python
class MatchedCard(BaseModel):
    card_id: int
    name_en: str
    set_code: str | None
    image_uri: str | None
    partner_quantity: int  # how many the partner has
    your_max_price: float | None  # from wishlist

class TradeMatch(BaseModel):
    partner_name: str
    share_code: str
    matching_card_count: int
    matched_cards: list[MatchedCard]  # detail of matching cards
```

### Endpoint

Add to `src/api/routers/trade_match.py`:

| Method | Path       | Description                    | Auth |
|--------|------------|--------------------------------|------|
| GET    | `/matches` | Find trade partner suggestions | yes  |

Query params: `limit` (default 20)

### Reverse matches (bonus, can defer)

Also expose: "Who wants my duplicates?" -- reverse query where we find
users whose wishlists match my duplicates. Same approach, inverted join.

| Method | Path               | Description                        | Auth |
|--------|--------------------|------------------------------------|------|
| GET    | `/matches/reverse` | Users who want my duplicate cards   | yes  |

## Testing

- Test with no wishlist items (empty result)
- Test with wishlist items but no matching duplicates (empty)
- Test with one matching partner
- Test privacy: non-shared collections are excluded
- Test self-exclusion (don't match own cards)
- Test ranking (partner with more matches ranks higher)
- Test limit parameter
- Test reverse matches
