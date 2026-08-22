# Orchestration Plan — P2 Market Intelligence (F32-F44)

> Renumerado de F14-F26 (BACKLOG.md) para F32-F44 (evitar conflito com F16-F31 shipped).

## Feature Map

| New ID | Old ID | Titulo | Deps (new) | Status |
|--------|--------|--------|------------|--------|
| F32 | F14 | Varredura em tempo real (streaming progress) | F13 (done) | planned |
| F33 | F15 | Historico de precos (snapshots por coleta) | F13 (done) | planned |
| F34 | F16 | Metricas de historico (var%, tendencia, volatilidade) | F33 | planned |
| F35 | F17 | Top Decks por valor (ranking, filtros, evolucao) | F34 | planned |
| F36 | F18 | Cards em alta e em baixa (trending engine) | F34 | planned |
| F37 | F19 | Varredura global rotineira (scheduler automatico) | F13 (done) | planned |
| F38 | F20 | Landing Page — Em Alta / Em Baixa | F36, F37 | planned |
| F39 | F21 | Ticker estilo Bolsa (animacao topo) | F36, F37 | planned |
| F40 | F22 | Pagina global de Mercado | F35, F36, F37 | planned |
| F41 | F23 | Lista de banimentos (por formato) | — | planned |
| F42 | F24 | Motor de banidas em My Collection | F41 | planned |
| F43 | F25 | Historico de banimentos | F41 | planned |
| F44 | F26 | Arquitetura compartilhada de dados (core engine) | F33, F34 | planned |

## Dependency Graph

```
                    F13 (done)
                   /    |      \
                 F32   F33    F37 -----.
                        |              |
                       F34             |
                      / |  \           |
                   F35 F36  F44        |
                    |   |    |         |
                    |   +----+---> F38 |
                    |   |         F39  |
                    +---+-------> F40 -'

          F41
         /    \
       F42    F43
```

## Parallel Waves

### Wave 0 — No pending deps (all parallel)
- **F32** Varredura em tempo real
- **F33** Historico de precos
- **F37** Varredura global rotineira
- **F41** Lista de banimentos

### Wave 1 — Deps on Wave 0
- **F34** Metricas de historico (needs F33)
- **F42** Motor de banidas (needs F41)
- **F43** Historico de banimentos (needs F41)

### Wave 2 — Deps on Wave 1
- **F35** Top Decks por valor (needs F34)
- **F36** Cards em alta e em baixa (needs F34)
- **F44** Arquitetura compartilhada (needs F33, F34) — consolidates shared core before consumer features

### Wave 3 — Deps on Wave 2
- **F38** Landing Page trending (needs F36, F37)
- **F39** Ticker estilo Bolsa (needs F36, F37)
- **F40** Pagina global de Mercado (needs F35, F36, F37)

## Planning Summary

| Feature | Tasks | Internal Waves | Key Decisions |
|---------|-------|----------------|---------------|
| F32 Real-time Scan | 8 | 5 | SSE (not WebSocket), in-memory event bus, zero new deps |
| F33 Price History | 5 | 3 | No new tables, query-time aggregation, shared response shape |
| F34 History Metrics | 5 | 3 | Pure functions, reuses F33 infra, 6 metric cards |
| F35 Top Decks Value | 7 | 5 | Batch price loading, user-scoped ranking, sparklines |
| F36 Trending Cards | 6 | 4 | Composite scoring (4 factors), anti-false-trending filters |
| F37 Scheduled Scans | 9 | 6 | APScheduler 3.x, SQLite job store, auto-pause on failure |
| F38 Landing Trending | 3 | 2 | Pure reuse of F36 components, replaces MoversPreview |
| F39 Stock Ticker | 5 | 4 | Pure CSS animation, frontend-only, reduced-motion support |
| F40 Market Page | 5 | 4 | Composition page, graceful degradation, public access |
| F41 Banlist | 8 | 5 | Scryfall bulk NDJSON sync, 2 tables, public endpoints |
| F42 Ban Engine | 8 | 5 | Collection JOIN legalities, session-scoped dismiss |
| F43 Ban History | 6 | 4 | No new tables, price impact stub, lazy-load on detail |
| F44 Shared Data Arch | 7 | 5 | MarketDataService facade, TTL cache, scan hooks |
| **TOTAL** | **82** | — | — |

## Notes

- F44 (shared architecture) is cross-cutting. Backlog note says "deve ser planejada antes de F17-F22" (F35-F40). Placed in Wave 2 so shared core is ready before Wave 3 consumer features.
- Within each wave, all features are independent and can be developed in parallel.
- Max parallelism: 4 features (Wave 0), 3 features (Wave 1), 3 features (Wave 2), 3 features (Wave 3).
- Total: 82 tasks across 13 features, organized in 4 orchestration waves.
- All task files are under `tasks/features/F{32-44}-*/`.
