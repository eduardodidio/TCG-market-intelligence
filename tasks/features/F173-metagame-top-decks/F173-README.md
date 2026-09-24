# F173 — Top Decks do mercado por formato (Metagame)

**Status:** planned
**Branch:** `homol` (ou worktree derivada de `homol`) — nunca `main`.
**Brief (sharded):** `_brief/00-overview.md` … `_brief/05-integration-and-conflicts.md`

## Goal
Hoje `/decks/ranking` só ranqueia os decks do próprio usuário. A F173 traz os **top
decks do metagame por formato** (Commander via EDHREC; Standard/Pioneer/Modern/Legacy/
Vintage/Pauper via fonte de torneios decidida no SPIKE), coletados de forma educada
(robots.txt, ToS, rate limit, cache em disco) por um novo comando CLI
`collect-metagame` + `bats/collect-metagame.bat`, persistidos como snapshots datados
(posição no meta, meta share, decklist), e exibidos numa aba "Mercado" do Top Decks
com filtro de formato, **valor do deck em BRL** com os preços que já temos e **% que o
usuário já possui** na coleção (e quanto falta em R$).

## Architecture impact
- **Novo pacote backend** `src/metagame/` (http, sources, models, repository,
  valuation, collector) — sem editar `models.py`/`repository.py` (tabelas novas no
  mesmo `Base`, `create_all(tables=...)` próprio).
- **API:** novo router `src/api/routers/meta_decks.py` (`/api/v1/meta-decks*`).
- **CLI:** novo módulo `src/cli/metagame.py` registrado com 1 linha.
- **Ops:** novo `bats/collect-metagame.bat` (semanal).
- **Frontend:** novos `types/metaDecks.ts`, `api/metaDecks.ts`, `components/meta/*`;
  abas em `TopDecksPage.tsx`; link em `TopDecksPreview.tsx`. Sem rota nova.
- **Docs:** ADR (próximo nº livre, ~0014), PRD, 2 diagramas, README.

## Waves
- **Wave 0**: F173-T01, F173-T02
- **Wave 1**: F173-T03, F173-T04, F173-T05, F173-T06
- **Wave 2**: F173-T07, F173-T08, F173-T09, F173-T10, F173-T11
- **Wave 3**: F173-T12, F173-T13, F173-T14
- **Wave 4**: F173-T15

## Tasks & files touched (para detecção de sobreposição entre features do lote)
| Task | Wave | Type | Título | Arquivos tocados |
|---|---|---|---|---|
| T01 | 0 | docs/spike | SPIKE de fontes + ADR + fixtures + scaffolding | `docs/adr/00NN-metagame-deck-sources.md` (novo), `tests/fixtures/metagame/**` (novo), `src/metagame/__init__.py`, `src/metagame/sources/` (dir), `tests/unit/metagame/__init__.py`, `frontend/src/components/meta/` (dir) |
| T02 | 0 | docs | PRD | `docs/prd/F173-metagame-top-decks.md` (novo) |
| T03 | 1 | backend | Modelos + MetagameRepository | `src/metagame/models.py`, `src/metagame/repository.py`, `tests/unit/metagame/test_repository.py` (novos) |
| T04 | 1 | backend | PoliteFetcher + Protocol de fonte | `src/metagame/http.py`, `src/metagame/sources/base.py`, `src/metagame/sources/__init__.py`, `tests/unit/metagame/test_http.py` (novos) |
| T05 | 1 | backend | Valoração pura BRL / % possuído | `src/metagame/valuation.py`, `tests/unit/metagame/test_valuation.py` (novos) |
| T06 | 1 | frontend | Tipos + API client | `frontend/src/types/metaDecks.ts`, `frontend/src/api/metaDecks.ts`, `frontend/src/api/__tests__/metaDecks.test.ts` (novos) |
| T07 | 2 | backend | Adapter EDHREC (Commander) | `src/metagame/sources/edhrec.py`, `tests/unit/metagame/test_source_edhrec.py` (novos) |
| T08 | 2 | backend | Adapter construídos (MTGTop8 ou escolha do ADR) | `src/metagame/sources/<fonte>.py`, `tests/unit/metagame/test_source_<fonte>.py` (novos) |
| T09 | 2 | backend | Collector service | `src/metagame/collector.py`, `tests/unit/metagame/test_collector.py` (novos) |
| T10 | 2 | backend | Router `/meta-decks` | `src/api/routers/meta_decks.py`, `tests/api/test_meta_decks_router.py` (novos) |
| T11 | 2 | frontend | Componentes MetaDecksPanel & cia | `frontend/src/components/meta/*.tsx` + `__tests__` (novos) |
| T12 | 3 | backend/infra | Comando CLI + .bat + registry de fontes | `src/cli/metagame.py`, `bats/collect-metagame.bat`, `tests/cli/test_cli_metagame.py` (novos), `src/metagame/sources/__init__.py` (editar) |
| T13 | 3 | frontend | Abas no TopDecksPage + link no Preview | `frontend/src/pages/TopDecksPage.tsx`, `frontend/src/components/TopDecksPreview.tsx`, `frontend/src/pages/__tests__/TopDecksPage.test.tsx` (novo) |
| T14 | 3 | docs | Diagramas | `docs/diagrams/F173-architecture.mmd`, `docs/diagrams/F173-journey.mmd` (novos) |
| T15 | 4 | infra | **Integração em arquivos compartilhados** | `src/api/app.py`, `src/cli/main.py`, `frontend/src/i18n/locales/pt-BR.json`, `frontend/src/i18n/locales/en.json`, `README.md`, `.gitignore`, `tests/api/test_meta_decks_registration.py` (novo), `tests/cli/test_cli_metagame_registration.py` (novo) |

**Arquivos compartilhados do lote tocados: apenas em T15** (`src/api/app.py`,
`src/cli/main.py`, `README.md`, locales). **Não tocados:** `App.tsx`, `Layout.tsx`,
`src/database/models.py`, `repository.py`. `bats/`: só arquivo novo.

## Global acceptance criteria
1. ADR aceito com matriz ToS/robots por fonte e fonte escolhida por formato (T01).
2. `python -m src.cli.main collect-metagame --format modern --format commander --limit 10`
   popula `meta_decks`/`meta_deck_cards`; rodar 2x no mesmo dia não duplica.
3. Nenhum request viola robots.txt; intervalo mínimo por host ≥ 3s (ou `Crawl-delay`);
   cache em disco evita refetch dentro do TTL.
4. `GET /api/v1/meta-decks?format=modern` retorna decks ordenados por rank com
   `total_value_brl`, `priced_pct`, `missing_value_brl` e `owned_pct` (null se anônimo).
5. `/decks/ranking?view=meta&format=<fmt>` mostra a aba Mercado com pills de formato,
   valor BRL, % possuído, decklist expansível e fonte/data; `view=mine` inalterado.
6. `bats/collect-metagame.bat` existe e segue o padrão de `bats/process-queue.bat`.
7. PRD, ADR, `F173-architecture.mmd`, `F173-journey.mmd` e README atualizados.
8. `pytest tests/ --cov=src` verde, cobertura ≥ 85% em `src/metagame/*`;
   `ruff check src/` limpo; `cd frontend && npm test && npm run build` verdes.
9. Nenhuma dependência nova (Python ou npm).

## Diagrams
- `docs/diagrams/F173-architecture.mmd` — owner T14
- `docs/diagrams/F173-journey.mmd` — owner T14

## Notes for orchestrator
- Wave 0 T01 é SPIKE com time-box (~15 min de pesquisa). Se a fonte construída escolhida
  não for MTGTop8, T08 usa o nome da fonte escolhida (arquivos `sources/<fonte>.py`).
- Testes backend nunca fazem rede real; usam fixtures de `tests/fixtures/metagame/`.

## ADR number (batch reservation)
This feature's ADR number is **0016**, reserved in `tasks/features/EXECUTION-PLAN-F171-F179.md`. It overrides any "next free number" instruction in the task files.
