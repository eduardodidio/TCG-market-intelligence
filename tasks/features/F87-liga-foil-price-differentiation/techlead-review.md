# F87 Tech Lead Review -- Liga Foil Price Differentiation

**Reviewer:** Tech Lead
**Date:** 2026-08-28
**Verdict:** APPROVED (with findings to address in follow-up)

---

## Overall Assessment

The feature delivers on its stated goal: foil cards now get foil-specific prices
from LigaMagic, stored with a `_foil` suffix on `external_id`, and the frontend
displays a FoilBadge. The external_id suffix approach is sound -- it avoids
schema migration, naturally leverages the existing unique constraint
`(source, external_id, observed_at)`, and keeps foil and non-foil price
histories cleanly separated. The overlap handling (same card_id appearing as
both foil and non-foil entries) is correctly addressed in both
`list_collection` and `get_collection_total_value`.

Test coverage is solid: 2644 backend + 1237 frontend tests, all green.
The new tests cover the key scenarios (foil refresh, foil price preference,
foil no-price warning, foil badge rendering).

That said, I found one **bug**, one **code quality issue**, and two
**minor observations**.

---

## Per-File Findings

### src/collection/converter.py -- `is_foil_entry()`

**Status:** Clean

Simple, correct implementation. Case-insensitive substring match on `extras`
handles "Foil", "foil", "Foil, Signed", etc. The function is the canonical
source of truth for foil detection and is correctly imported by the API router
and repository.

---

### src/collectors/scan.py -- `_is_foil()` (line 42) and src/collectors/liga_sweep.py -- `_is_foil()` (line 32)

**Issue: Code duplication (LOW)**

There are now **three** copies of the same foil detection logic:
1. `is_foil_entry()` in `src/collection/converter.py` (canonical)
2. `_is_foil()` in `src/collectors/scan.py`
3. `_is_foil()` in `src/collectors/liga_sweep.py`

All three do exactly the same thing: `bool(extras and "foil" in extras.lower())`.

**Recommendation:** The private `_is_foil` functions in `scan.py` and
`liga_sweep.py` should import and use `is_foil_entry` from `converter.py`.
This is a low-risk cleanup -- not blocking, but should be done promptly to
avoid drift.

---

### src/database/repository.py -- `get_latest_prices_batch(foil_card_ids=...)`

**Status:** Correct

The foil lookup logic is sound:
- For foil card_ids, it queries `liga_{card_id}_foil` and, if found, removes
  the normal liga candidate before adding the foil one.
- Manual prices still win regardless of foil status (correct -- manual entry
  means the user set the price explicitly).
- The overlap pattern (same card_id as both foil and non-foil entries) requires
  two separate calls to `get_latest_prices_batch`, which is handled correctly
  in both `list_collection` and `get_collection_total_value`.

---

### src/database/repository.py -- `get_cards_for_liga_scan()` (line 1383)

**Issue: Bug -- max_age_days filter ignores foil external_ids (MEDIUM)**

The `max_age_days` filter constructs the Liga external_id as
`'liga_' || card_id` and checks if a recent observation exists. For foil
entries, the actual external_id stored is `liga_{card_id}_foil`, but the
filter only checks `liga_{card_id}`.

**Impact:** Foil cards will never be excluded by `max_age_days`, even if they
were scanned recently. This means foil cards get re-scanned on every sweep
run, wasting credits and Liga page loads. The data will be correct (the foil
price gets upserted), but it is wasteful.

**Fix:** The filter should check both `liga_{card_id}` and
`liga_{card_id}_foil` -- or, more precisely, it should check the correct
suffix based on the entry's `extras` field. Since the query already selects
`UserCollectionRow.extras`, a `CASE WHEN` expression or an OR condition
could resolve this.

---

### src/api/routers/collection.py -- `refresh_card_price_liga()` (line 1076)

**Issue: Inline foil detection instead of using canonical function (LOW)**

Line 1076 has:
```python
is_foil = bool(entry.extras and "foil" in entry.extras.lower())
```

This is functionally identical to `is_foil_entry(entry.extras)`, which is
already imported in this file (line 53). Should use the canonical function
for consistency.

---

### src/api/routers/collection.py -- `list_collection()` overlap handling

**Status:** Correct but verbose

The overlap handling (lines 118-136) is correct. When the same `card_id`
appears in both foil and non-foil entries, two separate calls to
`get_latest_prices_batch` are made -- one with foil_card_ids set, one without.
The per-row dispatch then picks the right dict.

This works, but is an N+1 risk if overlap grows. Acceptable for now given
typical collection sizes.

---

### src/api/schemas/collection.py -- `is_foil: bool = False`

**Status:** Clean

Default `False` is correct. The field is computed server-side from `extras`,
never set by the client.

---

### src/providers/liga/provider.py -- `get_current_price(is_foil=...)`

**Status:** Clean

The `is_foil` keyword argument is backward-compatible (defaults to False).
When `is_foil=True` and no foil prices are found, it returns `None` (no
fallback to normal prices), which is the correct behavior -- returning a
normal price for a foil entry would be misleading.

The `external_id` is correctly suffixed with `_foil` only when `is_foil=True`.

---

### frontend/src/components/FoilBadge.tsx

**Status:** Clean

Well-structured component with two variants (compact/full), i18n via
`t("card.foil")`, amber gradient styling that fits the dark theme, star
SVG icon, proper `data-testid`, and `aria-hidden` on the decorative SVG.
9 tests cover rendering, variants, and styling.

---

### frontend/src/pages/MyCollection.tsx -- Foil badge overlay

**Status:** Clean

The foil badge is positioned at `bottom-2 left-2` on the card tile image
with `z-10`, which avoids collision with the refresh button (top-right) and
ban badge. Uses `data-testid="foil-badge-overlay"` for testing.

---

### frontend/src/pages/CollectionCardDetail.tsx -- Foil badge on detail page

**Status:** Clean

The badge is placed inline next to the card name (`flex items-center gap-2`).
The price label switches between `t("cardDetail.latestPrice")` and
`t("card.foilPrice")` based on `entry.is_foil`, which is good UX -- the user
knows they are seeing the foil price.

---

### frontend/tests/pages/CollectionCardDetail.test.tsx (line 37-38)

**Observation: Mock data inconsistency (LOW)**

The base mock entry has `extras: "Foil"` but `is_foil: false`. In production
the API always computes `is_foil` from `extras`, so these would never
disagree. This test is not technically wrong (it tests the component renders
based on `is_foil`, not `extras`), but it could confuse future developers.
Consider either:
- Changing `extras` to `null` in the base mock, or
- Setting `is_foil: true` to match `extras: "Foil"`.

---

### frontend/src/types/api.ts

**Status:** Clean

`is_foil: boolean` added to `CollectionCard` interface. Non-optional, which
matches the schema default of `False`.

---

### i18n (en.json, pt-BR.json)

**Status:** Clean

Two new keys: `card.foil` ("Foil"/"Foil") and `card.foilPrice`
("Foil price"/"Preco Foil"). Both locales updated.

---

## Breaking Changes

None. All changes are backward-compatible:
- `get_latest_prices_batch` has an optional `foil_card_ids` parameter
  (defaults to `None`, preserving old behavior).
- `get_current_price` has an optional `is_foil` keyword argument.
- The `is_foil` field on `CollectionCard` schema defaults to `False`.
- Existing `liga_{card_id}` external_ids are unaffected.

---

## Security

No IDOR or auth issues. The `refresh_card_price_liga` endpoint already
validates `entry.user_id == user_id` before proceeding. The `list_collection`
endpoint filters by authenticated user. The `is_foil` field is computed
server-side and cannot be manipulated by the client.

---

## Summary of Findings

| # | Severity | File | Finding |
|---|----------|------|---------|
| 1 | MEDIUM | `repository.py` `get_cards_for_liga_scan` | `max_age_days` filter only checks `liga_{card_id}`, misses `liga_{card_id}_foil` -- foil cards are never skipped by freshness filter |
| 2 | LOW | `scan.py`, `liga_sweep.py` | `_is_foil()` duplicated 2x instead of importing `is_foil_entry` from `converter.py` |
| 3 | LOW | `collection.py` line 1076 | Inline foil detection instead of using the already-imported `is_foil_entry()` |
| 4 | LOW | `CollectionCardDetail.test.tsx` | Mock has `extras: "Foil"` + `is_foil: false` -- inconsistent (cosmetic) |

---

## Verdict: APPROVED

The architecture is sound, the data integrity is preserved (foil and non-foil
prices cannot get mixed up thanks to the external_id suffix), the frontend
integration is clean, and the test coverage is thorough.

Finding #1 (max_age_days) is a real bug but its impact is limited to
unnecessary re-scanning of foil cards -- it does not cause incorrect data.
It should be fixed in a follow-up patch. Findings #2-4 are low-severity
cleanup items.
