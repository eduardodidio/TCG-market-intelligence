# 05 — Documentação

- PRD: `docs/prd/F175-trending-market-mode.md` (siga `docs/prd/template.md`). Inclua a
  análise de causa raiz de `_brief/01-root-cause.md` de forma resumida.
- `docs/diagrams/F175-architecture.mmd`: flowchart Trending.tsx → TrendingSection →
  `/market/trending/*` → TrendingService (cache: só grava sucesso) → Repository →
  {`trending_queries.load_market_trending_prices` [source_cards ∪ liga_/manual_ direto] |
  `get_trending_price_data_for_user`} → analytics.rank_trending.
  Templates: `docs/diagrams/templates/architecture.mmd`, `user-journey.mmd`.
- `docs/diagrams/F175-journey.mmd`: `flowchart LR` com swimlanes Usuário / Frontend / API:
  abre Tendências → vê coleção → desmarca → vê mercado; caminhos de erro: timeout → estado
  vazio (sem cache) → recarregar tenta de novo; sem histórico → "sem tendências".
- `README.md`: nota curta (seção de changelog/features que já existe): "F175 — Tendências
  mostram o mercado inteiro (incluindo preços do Liga sweep) quando 'minha coleção' está
  desmarcado; falhas de query não ficam mais 30 min em cache."
