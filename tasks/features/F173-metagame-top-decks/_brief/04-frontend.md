# 04 — Frontend

## Decisão de UX: sem rota nova
Evita tocar `frontend/src/App.tsx` e `Layout.tsx` (alto conflito no lote). A página
existente `/decks/ranking` ganha **abas** controladas por query param:
`/decks/ranking?view=mine` (default, comportamento atual intacto) e
`/decks/ranking?view=meta&format=modern`.

## Tipos + client — novos arquivos (T06)
- `frontend/src/types/metaDecks.ts` (NÃO editar `types/api.ts`, compartilhado):
  `MetaFormat`, `MetaFormatInfo`, `MetaDeckSummary`, `MetaDeckListResponse`,
  `MetaDeckCard`, `MetaDeckDetail` — espelho exato de `03-valuation-api.md`
  (snake_case, dinheiro como `number | null` — backend serializa Decimal como número;
  confirmar com pydantic `float` nos schemas de T10).
- `frontend/src/api/metaDecks.ts`: `fetchMetaFormats()`, `fetchMetaDecks({format, limit, offset})`,
  `fetchMetaDeck(id)` usando `apiGet` de `../api/client` (padrão de `api/deckRanking.ts`).
- `META_FORMATS` const ordenada: commander, standard, pioneer, modern, legacy, pauper, vintage.

## Componentes (T11) — `frontend/src/components/meta/`
- `MetaFormatPills.tsx` — pills (mesmo estilo dos period pills do TopDecksPage:
  `bg-cyan-500 text-white` ativo / `bg-slate-800 text-slate-400` inativo);
  `data-testid="meta-format-<fmt>"`; desabilita formatos sem snapshot (usa `/formats`).
- `MetaDeckRow.tsx` — linha: `#rank`, arquétipo (ou comandante), cores, meta share %
  (ou nº de decks p/ Commander), **valor BRL** (`formatCurrency` de `utils/format`),
  barra "% que você possui" (oculta se `owned_pct === null`, mostra CTA "Entre para ver
  quanto você já tem"), "faltam R$ X", link externo para a fonte (`rel="noopener noreferrer"`,
  `target="_blank"`). Clique expande a decklist (lazy `fetchMetaDeck`).
- `MetaDeckCardList.tsx` — lista de cartas agrupada por board, com preço, possuído
  (✓ / x de y), link para `/cards/:card_id` quando `card_id` existe.
- `MetaDecksPanel.tsx` — compõe: pills + lista + loading skeleton + `EmptyState`
  ("Metagame ainda não coletado para este formato") + `ErrorBanner` com retry +
  rodapé "Fonte: X · atualizado em DD/MM/AAAA".
- i18n: usar chaves `metaDecks.*` SEMPRE com `defaultValue` pt-BR
  (`t("metaDecks.ownedPct", { defaultValue: "Você possui" })`), porque os arquivos
  `frontend/src/i18n/locales/*.json` só recebem as chaves em T15.
- Testes (Vitest + Testing Library, padrão `frontend/src/**/__tests__`): mockar
  `../../api/metaDecks`; asserts por `data-testid` e valores, NÃO por texto traduzido.

## Integração (T13)
- `TopDecksPage.tsx`: tabs `data-testid="topdecks-tab-mine|meta"`; `view=meta` renderiza
  `<MetaDecksPanel format=... onFormatChange=...>` (format no query param, default
  `commander`); `view=mine` mantém exatamente o JSX atual (extrair para função interna
  `MyDecksRanking` se ajudar, sem mudar comportamento).
- `TopDecksPreview.tsx`: adicionar link "Ver metagame" → `/decks/ranking?view=meta`
  no header da seção. Nada mais. (Ele retorna `null` quando o usuário não tem decks —
  manter; o link aparece só quando renderiza.)
