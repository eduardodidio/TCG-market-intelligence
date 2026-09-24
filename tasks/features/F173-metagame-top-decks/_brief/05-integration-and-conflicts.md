# 05 — Integração e mapa de conflitos (lote F171–F179)

## Arquivos compartilhados tocados pela F173 — TODOS em T15 (Wave 4)
| Arquivo | Mudança | Tamanho |
|---|---|---|
| `src/api/app.py` | import `from src.api.routers.meta_decks import router as meta_decks_router` + `app.include_router(meta_decks_router, prefix="/api/v1")` | 2 linhas |
| `src/cli/main.py` | `from src.cli.metagame import collect_metagame_cmd` + `cli.add_command(collect_metagame_cmd)` (no fim do arquivo, antes de `if __name__`) | 2 linhas |
| `frontend/src/i18n/locales/pt-BR.json`, `en.json` | bloco novo `"metaDecks": {...}` + `topDecks.tabMine/tabMeta/viewMeta` | bloco |
| `README.md` | seção "Top Decks do mercado (F173)": endpoints, comando, .bat, UI | ~15 linhas |
| `.gitignore` | `data/cache/` (hoje NÃO está ignorado — confirmado no planejamento) | 1 linha |

**NÃO tocados** pela F173: `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx`,
`src/database/models.py`, `src/database/repository.py`, `src/api/schemas/*`,
`frontend/src/types/api.ts`, `src/api/error_codes.py`.
`bats/`: apenas arquivo NOVO `bats/collect-metagame.bat` (T12) — sem conflito.

## Arquivos semi-compartilhados (fora da lista do lote, mas atenção)
- `frontend/src/pages/TopDecksPage.tsx`, `frontend/src/components/TopDecksPreview.tsx` — T13.
  Se outra feature do lote tocar esses arquivos, o orquestrador deve serializar.
- `docs/adr/` — número do ADR é o próximo livre **no momento da execução de T01**
  (hoje seria `0014`). Se colidir com ADR de outra feature do lote no merge, renumerar
  o da F173 e ajustar links (T14 revalida).

## Ordem de registro
T15 só roda quando T10 (router), T12 (CLI) e T13 (UI) estão prontos. Após T15:
`pytest tests/`, `ruff check src/`, `cd frontend && npm test && npm run build`.
