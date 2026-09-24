# F175 — Tendências: mercado quando o filtro "minha coleção" é desmarcado

**Status:** planned
**Created:** 2026-09-24
**Priority:** P1 (bug visível para o usuário: lista vazia em Tendências e no ticker)
**Branch:** `homol` (nunca `main`)

## Objetivo
Em `/trending`, ao desmarcar "Somente minha coleção", devem aparecer as tendências do mercado
inteiro. Hoje aparece uma lista vazia. Causa raiz: a query de mercado
(`Repository.get_trending_price_data`) só junta preços via `source_cards` e ignora as
observações diretas do Liga sweep (`liga_{card_id}`, `liga_{card_id}_foil`) e as manuais
(`manual_{card_id}`), que não têm linha em `source_cards`. Agravante: quando a query falha ou
dá timeout, `TrendingService` guarda a resposta vazia no cache singleton por 30 min. A correção
une as duas fontes num módulo de query novo, deixa de guardar falhas no cache e adiciona testes
de regressão para os dois modos. O ticker do Dashboard (sempre em modo mercado) também passa a funcionar.

Brief detalhado: `_brief/00-overview.md` (escopo e ACs) · `_brief/01-root-cause.md` (diagnóstico).

## Impacto na arquitetura
- **Database / query**: novo `src/database/trending_queries.py`; `repository.py` só delega (1 método).
- **Service**: `src/services/trending.py`, a política de cache só grava resultados de sucesso.
- **API**: nenhuma mudança de contrato (`/api/v1/market/trending/{gainers,losers}`).
- **Frontend**: testes de regressão do toggle; correção mínima só se o teste revelar bug.
- **Analytics** (`src/analytics/trending.py`): sem mudança.
- **Sem** migração, dependência nova ou mudança de CI.

## Waves

- **Wave 0**: F175-T01, F175-T02        (branch/PRD + diagnóstico somente leitura)
- **Wave 1**: F175-T03, F175-T04, F175-T05, F175-T06
- **Wave 2**: F175-T07, F175-T08

## Arquivos tocados por task (para detectar sobreposição no lote F171–F179)

| Task | Wave | Tipo | Arquivos |
|------|------|------|----------|
| F175-T01 | 0 | docs/infra | `docs/prd/F175-trending-market-mode.md` (novo) |
| F175-T02 | 0 | infra | `scripts/diagnose_trending_f175.py` (novo) |
| F175-T03 | 1 | backend | `src/database/trending_queries.py` (novo), `src/database/repository.py` (só o corpo de `get_trending_price_data` + 1 import), `tests/unit/database/test_trending_queries.py` (novo) |
| F175-T04 | 1 | backend | `src/services/trending.py`, `tests/unit/services/test_trending_service_cache_f175.py` (novo) |
| F175-T05 | 1 | frontend | `frontend/src/pages/__tests__/TrendingCollectionToggle.test.tsx` (novo); condicional: `frontend/src/components/TrendingSection.tsx`, `frontend/src/hooks/useApi.ts` |
| F175-T06 | 1 | docs | `docs/diagrams/F175-architecture.mmd`, `docs/diagrams/F175-journey.mmd` (novos) |
| F175-T07 | 2 | test | `tests/unit/api/test_f175_trending_market_mode.py` (novo) |
| F175-T08 | 2 | docs | `README.md` ⚠️ compartilhado pelo lote, task dedicada na última Wave |

Arquivos de alto risco do lote tocados: **só `README.md`** (T08). `repository.py` não está na
lista de alto risco, mas é grande: a edição é mínima e fica isolada em T03.

## Critérios de aceite globais
- [ ] AC1: `GET /market/trending/gainers|losers` sem `collection_only` devolve cards quando só existem observações `source='liga'`/`liga_{id}` suficientes (≥3 datas, preço ≥ R$1, consistência ≥ 0.25).
- [ ] AC2: observações via `source_cards` (MYP/jsonld_snapshot) continuam aparecendo no modo mercado.
- [ ] AC3: `collection_only=true` com usuário autenticado continua restrito à coleção (sem regressão).
- [ ] AC4: exceção/timeout na query → resposta vazia **não** entra no cache; a próxima chamada consulta o repo de novo.
- [ ] AC5: o script de diagnóstico (T02) mostra a query de mercado de 90d em < 12s no Neon.
- [ ] AC6: desmarcar o toggle refaz a busca sem `collection_only` e mostra a lista de mercado (teste frontend).
- [ ] AC7: PRD + `F175-architecture.mmd` + `F175-journey.mmd` + nota no README.
- [ ] `pytest tests/ --cov=src`, `ruff check src/`, `cd frontend && npm test` e `npm run build` passam.

## Diagramas
- `docs/diagrams/F175-architecture.mmd` (dono: T06)
- `docs/diagrams/F175-journey.mmd` (dono: T06)

## Notas
- Gitflow: todo trabalho em `homol` (T01 confirma a branch). Promover para `main` só com aval do usuário.
- Não invalidar o cache em produção à mão: o TTL de 30 min expira sozinho após o deploy (o processo reinicia).
