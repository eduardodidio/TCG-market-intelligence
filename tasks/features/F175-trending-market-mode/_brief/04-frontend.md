# 04 — Frontend: regressão do toggle

Arquivos: `frontend/src/pages/Trending.tsx`, `frontend/src/components/TrendingSection.tsx`,
`frontend/src/api/trending.ts`, `frontend/src/hooks/useApi.ts`.

## Comportamento esperado
- Autenticado + toggle marcado (default) → as duas seções chamam `fetchTrending(dir, {period,
  currency, limit, collection_only: "true"})`.
- Desmarcar → as duas seções chamam `fetchTrending` de novo **sem** `collection_only` e mostram
  os cards retornados (modo mercado).
- Não autenticado → toggle oculto, modo mercado.

## Investigação
A leitura estática indica que o frontend está correto (`collectionOnly` está nas deps do
`useApi`, o param é omitido quando falso). Confirme com teste. Se o teste revelar um bug (ex.:
o `useApi` não refaz a busca ou uma resposta antiga sobrescreve a nova por race), corrija em
`TrendingSection.tsx` / `useApi.ts` com o mínimo de mudança. Para deixar o contrato explícito,
é aceitável enviar `collection_only: "false"` quando desmarcado (o backend aceita bool).
Se fizer isso, atualize os testes existentes que afirmam a ausência do param.

## Testes
Novo arquivo `frontend/src/pages/__tests__/TrendingCollectionToggle.test.tsx` (Vitest +
Testing Library, siga os mocks de `frontend/src/pages/__tests__/Dashboard.test.tsx`: `vi.mock`
de `../../api/trending`, `../../hooks/useAuth`, `../../hooks/useOwnedCardIds`,
`../../hooks/useCurrency`; wrap em `MemoryRouter`, i18n como os outros testes).
Sem mudança em arquivos de i18n.
