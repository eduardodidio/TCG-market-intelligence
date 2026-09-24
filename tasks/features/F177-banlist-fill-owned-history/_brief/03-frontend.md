# 03 — Frontend (toggle + card detail modal)

## Files
- NEW `frontend/src/components/BanCardDetailModal.tsx` (F177-T05) + `frontend/tests/components/BanCardDetailModal.test.tsx`
- EDIT `frontend/src/pages/BanList.tsx`, `frontend/src/api/banlist.ts`, `frontend/src/types/banlist.ts` (F177-T08)
  + `frontend/tests/pages/BanList.test.tsx`, `frontend/tests/api/banlist.test.ts`
- i18n keys (F177-T02, Wave 0): `frontend/src/i18n/locales/en.json`, `pt-BR.json`

## i18n keys (added under the existing `"banlist"` object in both locales)
| key | en | pt-BR |
|-----|----|-------|
| `banlist.ownedOnly` | Only my collection | Somente minha coleção |
| `banlist.ownedOnlyLoginHint` | Log in to filter by your collection | Entre para filtrar pela sua coleção |
| `banlist.owned` | In collection | Na coleção |
| `banlist.ownedQty` | {{count}}x in collection | {{count}}x na coleção |
| `banlist.printings` | {{count}} printings | {{count}} impressões |
| `banlist.emptyNotSynced` | Ban list data has not been synced yet. Run banlist-sync. | Os dados de banimento ainda não foram sincronizados. Rode o banlist-sync. |
| `banlist.emptyOwned` | None of your cards are banned or restricted in this format | Nenhuma carta sua está banida ou restrita neste formato |
| `banlist.lastSynced` | Last synced: {{date}} | Última sincronização: {{date}} |
| `banlist.detail.title` | Card details | Detalhes da carta |
| `banlist.detail.legalities` | Legality by format | Legalidade por formato |
| `banlist.detail.history` | Ban history | Histórico de banimentos |
| `banlist.detail.noHistory` | No ban/unban events recorded for this card | Nenhum evento de ban/unban registrado para esta carta |
| `banlist.detail.baseline` | Already banned when tracking started | Já banida quando o monitoramento começou |
| `banlist.detail.close` | Close | Fechar |
| `banlist.detail.openCard` | Open card page | Abrir página da carta |
| `banlist.loadMore` | Load more | Carregar mais |

Keep the existing `banHistory.*` and `nav.banHistory` keys (used by `CollectionCardDetail.tsx`,
`StatusTransition.tsx` and `frontend/tests/i18n/banHistory-keys.test.tsx`).

## BanCardDetailModal (F177-T05)
```tsx
interface Props { entry: BanListEntry | null; onClose: () => void; }
```
- Renders nothing when `entry` is null. Otherwise it shows an accessible dialog (`role="dialog"`,
  `aria-modal="true"`, `aria-labelledby`); Esc and a backdrop click close it; focus goes to the close button.
  Follow the existing modal styling in `frontend/src/components/CardPreviewModal.tsx`.
- Left: the card image (`entry.image_url || scryfallImageUrl(set, cn)`), name via `useCardName`,
  set/#, `LegalityBadge` of the current status, owned badge (`banlist.ownedQty`).
- Right, section 1: "Legality by format". Uses `fetchCardLegalities(entry.card_id)` (existing).
  Grid of format → `LegalityBadge`; banned/restricted formats first.
- Right, section 2: "Ban history". Uses `fetchCardBanHistory(entry.card_id)` (existing).
  Group events by format (the `entry.format` group first, then alphabetical); each event
  shows the date + `StatusTransition` (existing component, `frontend/src/components/StatusTransition.tsx`).
  Events with `source === "scryfall_baseline"` show the `banlist.detail.baseline` label
  instead of a date. Empty → `banlist.detail.noHistory`.
- Loading skeletons + error text per section (they are independent: a failure in one doesn't hide the other).
- Footer link "Open card page" → `/cards/${entry.card_id}` (react-router `Link`).
- Use `useApi` (`frontend/src/hooks/useApi.ts`), following BanList.tsx.
- `data-testid`s: `ban-card-modal`, `ban-card-modal-close`, `ban-card-legalities`,
  `ban-card-history`, `ban-card-history-empty`, `ban-card-history-format-<fmt>`.

## BanList.tsx (F177-T08)
- Toggle "Somente minha coleção" (checkbox styled as a switch, `data-testid="owned-only-toggle"`)
  in the controls row. Enabled only if `useAuth().isAuthenticated`; otherwise disabled with the
  `title={t("banlist.ownedOnlyLoginHint")}` tooltip. State is persisted in the URL `?owned=1`
  (`useSearchParams`); `format` is also moved to `?format=` so a shared URL keeps it.
- Pass `ownedOnly` to `fetchBanList`; include it in the `useApi` deps.
- Card tile: an owned badge (`banlist-owned-badge`) when `entry.owned`; a "N printings" hint when
  `printings > 1`. The tile becomes a `<button>` (keyboard accessible) that opens `BanCardDetailModal`.
- Empty states: if `fetchBanlistStatus().legalities_count === 0` → `banlist.emptyNotSynced`
  (`data-testid="banlist-not-synced"`); if ownedOnly → `banlist.emptyOwned`; else the existing `no_results`.
- Header subtitle: `banlist.lastSynced` with `last_synced_at` (locale date) when present.
- Pagination: "Load more" button (`banlist-load-more`) when `entries.length < total` (use `meta.total`).
  Remove the client-side re-sort (the server now sorts).
- Remove the hardcoded `standard` default? No. Keep the preference: `?format=` > "commander" if present > "standard" > first.
