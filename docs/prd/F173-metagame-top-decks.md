# PRD: Top Decks do mercado por formato (Metagame)

**Feature ID:** F173
**Status:** approved
**Owner:** @eduardodidio
**Date:** 2026-09-24
**Branch:** `homol` (nunca `main`)
**Task manifest:** [`tasks/features/F173-metagame-top-decks/`](../../tasks/features/F173-metagame-top-decks/F173-README.md)
**ADR:** [ADR 0016 — Fontes de decks do metagame](../adr/0016-metagame-deck-sources.md) (número reservado; escrito em paralelo por F173-T01)

## Problem

A seção Top Decks (`/decks/ranking`, `TopDecksPage.tsx` / `TopDecksPreview.tsx`) hoje só
ranqueia os decks **do próprio usuário** por valor (`GET /api/v1/decks/ranking`). O jogador
brasileiro não tem como responder, dentro da plataforma, às perguntas:

- "Quais são os decks que estão ganhando/sendo mais jogados no formato X agora?"
- "Quanto custa montar esse deck **no Brasil, em reais**?"
- "Quanto desse deck eu **já tenho** na minha coleção e quanto falta gastar?"

Hoje ele precisa abrir MTGTop8/MTGGoldfish/EDHREC (preços em USD/EUR, sem sua coleção),
copiar a lista e cruzar manualmente com Liga Magic / MYP Cards. Nós já temos preços BRL
(Liga `mid` / mediana MYP) e a coleção do usuário — falta o dado do metagame.

## Goal

O usuário abre `/decks/ranking?view=meta`, escolhe um formato e vê os top decks do metagame
com posição, meta share, data da coleta, **valor do deck em BRL**, **% que já possui** e
**quanto falta em R$** — com dados coletados de forma educada (ToS/robots, rate limit, cache).

## Personas

| Persona | Descrição | Pergunta-chave |
|---|---|---|
| **Jogador competitivo (construído)** | Joga Pioneer/Modern/Pauper em lojas/FNM no Brasil; orçamento limitado. | "Qual deck do meta eu consigo montar mais barato a partir do que já tenho?" |
| **Jogador de Commander** | Joga EDH casual/cEDH; tem coleção grande. | "Quais comandantes populares eu quase completo?" |
| **Colecionador / investidor** | Acompanha preços para compra/venda. | "Quais cartas estão em decks do meta (demanda) e quanto valem?" |
| **Visitante anônimo** | Não logado. | "Quanto custa, em reais, montar o deck #1 de Modern?" (sem % possuído) |

## Scope

### In scope

- **SPIKE de fontes** (EDHREC para Commander; MTGTop8 / MTGGoldfish / mtgdecks para
  construídos) com decisão e matriz ToS/robots registradas no ADR 0016.
- **Camada HTTP educada** (`src/metagame/http.py`): robots.txt, rate limit por host,
  cache em disco com TTL, User-Agent identificado, retry com backoff (429/5xx/timeout).
- **Adapters de fonte** atrás de um Protocol comum (`MetaSource`).
- **Persistência** de snapshots datados: deck (arquétipo/comandante, posição, meta share,
  nº de decks, cores, data do evento, data do snapshot, fonte, URL) + cartas (nome, qtd,
  board, `card_id` resolvido).
- **Resolução nome → `cards.id`** reusando `src/decks/importer._find_card_id`.
- **Coleta local** via novo comando CLI `collect-metagame` + `bats/collect-metagame.bat`
  (agendamento semanal; diário opcional).
- **API** `GET /api/v1/meta-decks/formats`, `GET /api/v1/meta-decks?format=`,
  `GET /api/v1/meta-decks/{deck_id}` com valor BRL, % com preço e % possuído.
- **UI**: aba "Mercado" no `TopDecksPage` (query param `view=meta&format=<fmt>`) com pills
  de formato; link "Ver metagame" no `TopDecksPreview`.
- **Docs**: ADR 0016, este PRD, `F173-architecture.mmd`, `F173-journey.mmd`, README.

Formatos: `commander`, `standard`, `pioneer`, `modern`, `legacy`, `pauper`, `vintage`.

### Out of scope (non-goals)

- **Histórico/gráfico de evolução do meta** — os snapshots ficam guardados por
  `snapshot_date`, mas não há UI de série temporal nesta feature. → *Follow-up*.
- **Importar deck do meta para "Meus decks"** (botão "copiar para meus decks"). → *Follow-up*.
- **Coleta disparada pela API / Render** — a coleta é só local via `.bat`, como o
  `liga-sweep`; o Render apenas lê do Neon.
- **Lista de compras / carrinho** das cartas faltantes (Liga/MYP). → *Follow-up possível*.
- **Rota nova no SPA** (`App.tsx`/`Layout.tsx` não mudam) e novas dependências Python/npm.
- **Fontes que proíbam coleta automatizada** no ToS — descartadas mesmo que o robots permita.

### Follow-ups registrados

| ID | Follow-up | Motivo de ficar fora |
|---|---|---|
| FU1 | Gráfico de evolução do meta share por arquétipo | Precisa de ≥ 4 snapshots semanais para ter valor |
| FU2 | "Importar para Meus decks" a partir de um deck do meta | Toca `src/decks/*` e UI de decks (alto conflito no lote F171–F179) |
| FU3 | Lista de compras das cartas faltantes com link Liga/MYP | Depende de FU2 ou de UI de carrinho |
| FU4 | Coleta diária agendada / alertas "deck do meta ficou mais barato" | Validar custo de requests e estabilidade das fontes primeiro |

## User stories

1. **US1** — Como jogador, quero escolher um formato (pills) e ver os top decks do metagame
   com posição e meta share (ou nº de decks, em Commander), para saber o que está sendo jogado.
2. **US2** — Como jogador, quero ver o **valor do deck em BRL** com os preços que a plataforma
   já coleta, para saber quanto custa montá-lo no Brasil.
3. **US3** — Como usuário logado, quero ver **% que já possuo** e **quanto falta em R$**,
   para decidir qual deck montar.
4. **US4** — Como jogador, quero expandir a decklist e ver cada carta com preço, se possuo
   (x de y) e link para a página da carta.
5. **US5** — Como jogador, quero ver a **fonte e a data da coleta** e um link para a fonte
   original, para confiar no dado.
6. **US6** — Como operador (dono do projeto), quero rodar `collect-metagame` / o `.bat`
   semanalmente na minha máquina, gravando direto no Neon, sem violar ToS/robots das fontes.
7. **US7** — Como usuário anônimo, quero ver valores em BRL mesmo sem login, com um convite
   para entrar e ver quanto já possuo.

## User flows

Diagramas (owner F173-T14):
- Arquitetura / fluxo de dados: [`docs/diagrams/F173-architecture.mmd`](../diagrams/F173-architecture.mmd)
- Jornada do usuário: [`docs/diagrams/F173-journey.mmd`](../diagrams/F173-journey.mmd)

Resumo:
1. **Coleta (local, semanal):** `bats/collect-metagame.bat` → `collect-metagame` →
   para cada formato: `MetaSource.fetch_top_decks` (via `PoliteFetcher`) → resolve cartas
   → `replace_snapshot(format, source, snapshot_date)` no Neon.
2. **Consulta:** usuário abre `/decks/ranking` → aba "Mercado" → pill de formato →
   `GET /meta-decks?format=` → lista com valor/%/faltam → clique expande decklist
   (`GET /meta-decks/{id}`) → link para carta ou para a fonte.

## Functional requirements

### Coleta

| ID | Requisito | Prioridade | AC |
|---|---|---|---|
| R1 | Fonte por formato decidida no ADR 0016, com matriz ToS/robots por candidata. Formato sem fonte viável fica marcado no ADR como "sem fonte" (ver edge case abaixo). | Must | AC1 |
| R2 | `PoliteFetcher`: checa robots.txt por host (URL proibida → `RobotsDisallowed`), intervalo mínimo por host ≥ 3 s (ou `Crawl-delay` maior), cache em disco com TTL (default 24 h), User-Agent identificado, retry com backoff só para 429/5xx/timeout honrando `Retry-After`. | Must | AC3 |
| R3 | Adapters implementam `MetaSource.fetch_top_decks(fmt, limit)` e devolvem `MetaDeckEntry` com rank, arquétipo/comandante, meta share ou nº de decks, cores, URL, data do evento e cartas por board. Parser tolerante: deck malformado é pulado com warning, não aborta o formato. | Must | AC2 |
| R4 | Cada carta é resolvida para `cards.id` (reuso de `_find_card_id`); não resolvidas ficam com `card_id = NULL` e são contadas em `unresolved_cards`. | Must | AC2 |
| R5 | Snapshot persistido em `meta_decks` / `meta_deck_cards` com rank, meta share, data, fonte e decklist; único por (fonte, formato, `external_id`, `snapshot_date`). | Must | AC2 |
| R6 | `collect-metagame` (`--format` múltiplo, `--limit`, `--dry-run`, `--db`, `--no-cache`) é idempotente por dia (rodar 2× não duplica); erro num formato não aborta os demais; exit 1 só se todos falharem. | Must | AC2 |
| R7 | `bats/collect-metagame.bat` segue o padrão de `bats/process-queue.bat` e documenta agendamento semanal (segunda 06:00). | Must | AC6 |

### API

| ID | Requisito | Prioridade | AC |
|---|---|---|---|
| R8 | `GET /api/v1/meta-decks/formats` → `{formats: [{format, latest_snapshot_date, deck_count}]}`. | Must | AC4 |
| R9 | `GET /api/v1/meta-decks?format=<fmt>&snapshot_date?&limit(1–50, 20)&offset` → decks ordenados por rank com `total_value_brl`, `priced_pct`, `missing_value_brl`, `owned_pct` (null se anônimo), `total_copies`, fonte e datas. Formato inválido → 422; sem snapshot → 200 com `decks: []`, `snapshot_date: null`. | Must | AC4 |
| R10 | `GET /api/v1/meta-decks/{deck_id}` → resumo + cartas (`name, quantity, board, card_id, price_brl, owned_qty, image_url?`); inexistente → 404 com `ErrorCode` existente. | Must | AC4 |
| R11 | Valoração pura (`src/metagame/valuation.py`): preços via `get_latest_prices_batch` (BRL, Liga `mid` / mediana MYP); considera `main` + `commander` por padrão; possuído por carta = `min(qty_deck, qty_coleção)`; terrenos básicos contam como possuídos e valor 0; `ROUND_HALF_UP` (2 casas BRL, 1 casa %). | Must | AC4 |
| R12 | Sem N+1: por request, 1 busca de cartas, 1 de preços, 1 de quantidades possuídas. | Must | AC4 |

### UI

| ID | Requisito | Prioridade | AC |
|---|---|---|---|
| R13 | `TopDecksPage` ganha abas `view=mine` (default, **inalterado**) e `view=meta`; formato em query param (default `commander`). | Must | AC5 |
| R14 | Pills de formato; formatos sem snapshot ficam desabilitados. | Must | AC5 |
| R15 | Linha do deck: `#rank`, arquétipo/comandante, cores, meta share % (ou nº de decks em Commander), valor BRL, barra "% que você possui" (anônimo → CTA "Entre para ver quanto você já tem"), "faltam R$ X", link externo para a fonte (`rel="noopener noreferrer"`). | Must | AC5 |
| R16 | Decklist expansível (lazy), agrupada por board, com preço, possuído (✓ / x de y) e link `/cards/:card_id` quando resolvida. | Must | AC5 |
| R17 | Estados: skeleton de loading, `EmptyState` "Metagame ainda não coletado para este formato", `ErrorBanner` com retry, rodapé "Fonte: X · atualizado em DD/MM/AAAA". | Must | AC5 |
| R18 | `TopDecksPreview` ganha link "Ver metagame" → `/decks/ranking?view=meta`. | Should | AC5 |
| R19 | Textos i18n `metaDecks.*` com `defaultValue` pt-BR; chaves em `pt-BR.json`/`en.json` na integração (T15). | Must | AC5 |

### Docs / qualidade

| ID | Requisito | Prioridade | AC |
|---|---|---|---|
| R20 | ADR 0016, este PRD, `F173-architecture.mmd`, `F173-journey.mmd` e README atualizados. | Must | AC7 |
| R21 | Testes backend sem rede real (fixtures em `tests/fixtures/metagame/`); cobertura ≥ 85% em `src/metagame/*`; ruff limpo; frontend test + build verdes. | Must | AC8 |
| R22 | Nenhuma dependência nova (usar `httpx`/`curl_cffi`, `beautifulsoup4`, `tenacity`, `urllib.robotparser`). | Must | AC9 |

### Edge cases

- **Formato sem fonte viável** (ToS proíbe ou fonte indisponível): o ADR 0016 registra o
  formato como "sem fonte"; `collect-metagame` o pula com aviso; `/meta-decks/formats`
  não lista snapshot; a pill fica desabilitada e o `EmptyState` explica.
- **Commander não tem meta share de torneio**: rank = popularidade; exibir `deck_count`
  no lugar do %.
- **Carta não resolvida** (`card_id` null): conta como não possuída e sem preço; reduz
  `priced_pct`, não quebra o valor total.
- **Nenhuma carta com preço**: `total_value_brl = null` (não 0).
- **Terrenos básicos**: possuídos e valor 0, para não distorcer % nem valor.

## Non-functional requirements

| Tema | Requisito |
|---|---|
| **ToS / robots.txt** | Fonte cujo ToS proíbe coleta automatizada é descartada mesmo que robots permita. Toda URL é checada contra robots.txt antes do request. |
| **Rate limit** | ≥ 3 s entre requests ao mesmo host (ou `Crawl-delay`, se maior); retry máximo 3 com backoff exponencial; 429 honra `Retry-After`. |
| **Cache** | Cache em disco (`data/cache/metagame/`, fora do git) com TTL de 24 h; `--no-cache` força refetch. |
| **Volume** | Coleta completa (7 formatos × top 20) deve ficar em ordem de ~150 requests por semana; com rate limit, < 15 min. |
| **Operação** | Coleta **local e semanal** via `.bat` (Task Scheduler), escrevendo direto no **Neon PostgreSQL** (`DATABASE_URL` do `.env`); SQLite local sem `.env`. Render só lê. |
| **Performance da API** | `GET /meta-decks?format=` com 20 decks: 3 queries em lote (sem N+1), p95 < 500 ms em Neon aquecido. |
| **Isolamento** | Tabelas novas em `src/metagame/models.py` com o mesmo `Base` e `create_all(tables=...)` próprio; sem editar `models.py`/`repository.py` compartilhados. |
| **Testabilidade** | Testes nunca fazem rede real; `clock`/`sleep` injetáveis para testar rate limit. |
| **Segurança / privacidade** | `owned_pct` só calculado para usuário autenticado; anônimo recebe `null`. Links externos com `noopener noreferrer`. |

## Success metrics

| Métrica | Meta | Como medir |
|---|---|---|
| % de cartas do meta resolvidas para `card_id` | **≥ 90%** (por cópia, por formato) | `1 − unresolved_cards / cards` do `CollectStats` |
| % de cópias com preço BRL conhecido | **≥ 80%** (média dos decks do formato) | Média de `priced_pct` em `GET /meta-decks?format=` |
| Formatos com snapshot | **≥ 1 construído + Commander** no 1º run; meta de 7/7 | `GET /meta-decks/formats` |
| Idempotência | 0 duplicatas ao rodar 2× no mesmo dia | Contagem em `meta_decks` por (fonte, formato, dia) antes/depois |
| Violações de robots / rate limit | **0** | Testes do `PoliteFetcher` + logs da coleta |
| Latência da API | p95 < 500 ms para 20 decks | Logs de request no Render |
| Cobertura de testes | ≥ 85% em `src/metagame/*` | `pytest --cov=src` |
| Adoção | ≥ 20% das visitas a `/decks/ranking` abrem `view=meta` nas 4 semanas após o deploy | Logs de acesso / analytics |

## Risks

| Risco | Impacto | Mitigação |
|---|---|---|
| **Mudança de HTML/JSON da fonte** quebra o parser | Formato sem dados novos | Parsers tolerantes (pulam deck, logam warning); fixtures de teste; snapshot anterior continua servido; erro por formato não aborta os outros. |
| **Bloqueio / 403 / rate limit da fonte** | Coleta falha | UA identificado, ≥ 3 s entre requests, cache 24 h, coleta semanal; fallback documentado no ADR 0016. |
| **Mudança de ToS** proibindo coleta | Fonte precisa ser descartada | ADR 0016 revisado; adapter desligado no registry `SOURCE_FOR_FORMAT`. |
| **Nomes de cartas divergentes** (split/DFC, acentos, variantes) | `card_id` não resolvido → valor/% subestimados | Reuso de `_find_card_id`; métrica ≥ 90% monitorada; `priced_pct` exibido para transparência. |
| **Preço ausente** para cartas antigas/caras (Legacy/Vintage) | Valor BRL subestimado | Mostrar `priced_pct`; `total_value_brl` null se nenhuma carta tem preço. |
| **Conflito com features paralelas F171–F179** | Merge difícil | Arquivos compartilhados só em T15 (ver `_brief/05-integration-and-conflicts.md`). |
| **Rede bloqueada no ambiente do SPIKE** | Fixtures sintéticas podem divergir do real | ADR marca "fixtures sintéticas — revalidar"; revalidar no 1º run real. |

## Acceptance criteria

Espelho dos critérios globais do manifesto
([`F173-README.md`](../../tasks/features/F173-metagame-top-decks/F173-README.md), mesma
numeração usada nas tasks):

1. **AC1** — ADR 0016 aceito com matriz ToS/robots por fonte e fonte escolhida por formato. *(R1)*
2. **AC2** — `python -m src.cli.main collect-metagame --format modern --format commander --limit 10`
   popula `meta_decks`/`meta_deck_cards` (≥ 1 formato construído e Commander); rodar 2× no
   mesmo dia não duplica. *(R3–R6)*
3. **AC3** — Nenhum request viola robots.txt; intervalo mínimo por host ≥ 3 s (ou `Crawl-delay`);
   cache em disco evita refetch dentro do TTL (testado). *(R2)*
4. **AC4** — `GET /api/v1/meta-decks?format=modern` retorna decks ordenados por rank com
   `total_value_brl`, `priced_pct`, `missing_value_brl` e `owned_pct` (null se anônimo);
   snapshot persistido com rank, meta share, data, fonte e decklist. *(R5, R8–R12)*
5. **AC5** — `/decks/ranking?view=meta&format=<fmt>` mostra a aba Mercado com pills de formato,
   valor BRL, % possuído, decklist expansível e fonte/data; `view=mine` inalterado. *(R13–R19)*
6. **AC6** — `bats/collect-metagame.bat` existe e segue o padrão de `bats/process-queue.bat`. *(R7)*
7. **AC7** — PRD, ADR, `F173-architecture.mmd`, `F173-journey.mmd` e README atualizados. *(R20)*
8. **AC8** — `pytest tests/ --cov=src` verde, cobertura ≥ 85% em `src/metagame/*`;
   `ruff check src/` limpo; `cd frontend && npm test && npm run build` verdes. *(R21)*
9. **AC9** — Nenhuma dependência nova (Python ou npm). *(R22)*

> Nota: `_brief/00-overview.md` lista os mesmos critérios com numeração ligeiramente
> diferente (lá AC4 = snapshot, AC6 = UI, AC7 = `.bat`, AC8 = docs, AC9 = cobertura/ruff).
> O conteúdo está integralmente coberto acima; a numeração canônica é a do manifesto.

## Open questions

- Fonte final para construídos (MTGTop8 vs MTGGoldfish vs mtgdecks) — decidida no ADR 0016 (T01).
- Vintage/Legacy: volume de decks por semana na fonte escolhida pode ser baixo; aceitar
  snapshots com < 20 decks?
- Commander: usar "average deck" do EDHREC como decklist representativa é suficiente, ou
  precisamos de um deck real de torneio (cEDH) como alternativa?
