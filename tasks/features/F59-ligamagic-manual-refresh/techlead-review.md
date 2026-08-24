# F59 TechLead Review

**Verdict:** APPROVED

## Findings

### 1. Plan Conformance -- PASS

The implementation matches the F59-README spec and all three task definitions (T01, T02, T03) faithfully:

- **Endpoint**: `POST /collection/{entry_id}/refresh-liga` implemented at `collection.py:818` with correct auth, IDOR check, 422 on missing name, graceful error handling, and auto-create card_id logic.
- **Frontend button**: violet `bg-violet-600` button with globe SVG, `refreshingLiga` state, `handleRefreshLiga` handler, 5s auto-dismiss, conditional rendering on `name_en || name_pt`.
- **PriceSourceBadge**: "liga" case renders violet badge with globe icon, using `t("priceSource.liga")`.
- **API client**: `refreshCardPriceLiga` with 45s timeout as specified.

### 2. Security -- PASS

- Auth via `require_auth_or_api_key` dependency (line 824).
- IDOR protection: `entry.user_id != user_id` check returns 404 (line 836-837).
- No secrets exposed; no auth bypass.

### 3. Error Handling -- PASS

- `LigaNotFoundError`, `LigaRateLimitError`, `LigaError`, and bare `Exception` are all caught and return 200 with `ErrorDetail` warnings. No 500 possible from this endpoint.
- The `except Exception` catch-all (line 870-876) with structured logging is a good safety net.

### 4. Provider Lifecycle -- PASS

- `await provider.close()` is in a `finally` block (line 877-878), ensuring Playwright cleanup even on exceptions.
- Test `test_provider_close_on_error` explicitly validates this.

### 5. Frontend UX -- PASS

- Separate `refreshingLiga` state prevents interference with MYP refresh.
- Button disabled during loading with `disabled:opacity-50 disabled:cursor-not-allowed`.
- Spinner via `animate-spin` on the globe SVG.
- Tooltip via `title={t("collection.refreshLigaTooltip")}`.
- Warning/success/error messages correctly color-coded (green/amber/red).
- 5s auto-dismiss (longer than MYP's 3s, matching the plan for slower Liga).

### 6. i18n Keys -- PASS

All 7 keys present in both locale files:

| Key | en.json | pt-BR.json |
|-----|---------|------------|
| `collection.refreshLiga` | "LigaMagic" | "LigaMagic" |
| `collection.refreshLigaTooltip` | "Fetch price from LigaMagic (~10s)" | "Buscar preco na LigaMagic (~10s)" |
| `collection.refreshLigaSuccess` | "Price updated from LigaMagic" | "Preco atualizado via LigaMagic" |
| `collection.refreshLigaNotFound` | "Card not found on LigaMagic" | "Carta nao encontrada na LigaMagic" |
| `collection.refreshLigaError` | "LigaMagic fetch failed" | "Falha ao buscar na LigaMagic" |
| `collection.refreshLigaRateLimit` | "LigaMagic rate limited, try later" | "LigaMagic limitou requisicoes, tente depois" |
| `priceSource.liga` | "LigaMagic" | "LigaMagic" |

### 7. Test Coverage -- PASS

**Backend** (`test_collection_refresh_liga.py`): 13 tests across 6 test classes:
- Happy path (price stored, mid/low/high fallback, name_pt fallback, provider close)
- No price found (warning, no insert)
- Entry not found (404)
- IDOR (wrong user 404)
- No name (422)
- Provider errors (LigaNotFoundError, LigaRateLimitError, LigaError, RuntimeError, close-on-error)
- Auto-create card_id (create_canonical_card + link_collection_entry verified)

**Frontend** (`CollectionCardDetail.liga.test.tsx`): 8 tests:
- Button renders with name_en, name_pt only, hidden when both null
- Click triggers API call with correct ID
- Loading state (button disabled)
- Success/warning/error message display
- MYP refresh independence

**PriceSourceBadge** (`PriceSourceBadge.test.tsx`): 4 new liga-specific tests:
- Violet badge with "LigaMagic" text
- Globe SVG icon
- Tooltip
- Color classes

### 8. Code Quality -- PASS

- No unused imports detected.
- `sourceLabel()` helper in CollectionCardDetail updated with `liga: "LigaMagic"`.
- Consistent patterns: the Liga endpoint mirrors the existing MYP refresh endpoint structure.
- Lazy imports inside the endpoint function (lines 827-833) follow the established pattern in this file.

## Recommendations

1. **Minor observation**: The frontend i18n keys `collection.refreshLigaNotFound` and `collection.refreshLigaRateLimit` are defined but not directly used in the frontend `handleRefreshLiga` handler -- the handler shows the raw `res.errors[0].message` from the backend instead. This is actually fine since the backend messages are human-readable, but the unused keys could be removed or the handler could map `liga_warning` codes to specific i18n keys for full localization. Low priority.

2. **Encoding inconsistency in pt-BR locale**: The `refreshLiga*` keys in pt-BR use accented characters (preco -> "preco" in some places, "preco" with cedilla in others). Lines 127-131 of pt-BR.json show a mix: `"Buscar preco na LigaMagic"` vs `"Preco atualizado via LigaMagic"` -- some have proper accents, some don't. This matches the existing inconsistency in the rest of the file, so not a blocker, but worth a cleanup pass eventually.

3. **No `card_id` linkage to Liga price observation**: The `HistoricalPrice` dataclass stores `external_id=f"liga_{card_name}"` but does not store a `card_id` reference directly in the observation. The price is linked through the card's existing `card_id` (or auto-created one). This is consistent with how MYP prices work, but worth noting that Liga prices are only retrievable via the card_id -> get_latest_prices_batch path.

No blocking issues found. The implementation is solid, well-tested, and matches the plan spec.
