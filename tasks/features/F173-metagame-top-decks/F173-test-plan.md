# F173 — Top Decks do mercado por formato (Metagame): Test Plan

- **Status:** drafted
- **Generator:** TEA
- **Generated-at:** 2026-09-24
- **Source-brief:** `tasks/features/F173-metagame-top-decks/_brief/00-overview.md`

---

## 1. Fixtures

| Fixture | Path | Domain | Owner |
|---|---|---|---|
| edhrec-top-commanders | `tests/fixtures/metagame/edhrec/top_commanders.json` | Commander source: lista/rank de top comandantes (EDHREC ou fonte escolhida no ADR) | F173-T01 |
| edhrec-decklist | `tests/fixtures/metagame/edhrec/decklist_<slug>.json` (1–2 arquivos) | Commander source: decklist média por comandante | F173-T01 |
| constructed-meta-page | `tests/fixtures/metagame/<fonte>/format_<code>.html` | Formatos construídos: página de meta com arquétipos + meta share | F173-T01 |
| constructed-decklist | `tests/fixtures/metagame/<fonte>/decklist_<slug>.txt` (1–2 arquivos) | Formatos construídos: decklist exportável (main + sideboard) | F173-T01 |

`<fonte>` = nome decidido no ADR 0016 (hipótese: `mtgtop8`); se o ADR escolher outra,
os paths mudam de pasta mas a estrutura da tabela permanece. Cada pasta de fixture
inclui `README.md` com URL de origem e data de captura (exigido por T01 AC).
`PoliteFetcher` (T04) e o registry de fontes (T12) não precisam de fixtures em disco —
seus testes usam `httpx.MockTransport` com corpos sintéticos inline, o que é
suficiente e mais barato que arquivos versionados para simular robots.txt/rate
limit/cache (`feedback_no_ceremony_specs.md`: fixture só se economiza retrabalho real).

## 2. Harnesses por fronteira

### Unit (backend)
- **Framework:** pytest (+ `pytest-cov`)
- **Comando:** `pytest tests/unit/metagame --cov=src/metagame --cov-report=term-missing`
- **Path padrão:** `tests/unit/metagame/`

### Unit (frontend)
- **Framework:** Vitest + React Testing Library
- **Comando:** `cd frontend && npx vitest run src/api/__tests__/metaDecks.test.ts src/components/meta`
- **Path padrão:** `frontend/src/api/__tests__/`, `frontend/src/components/meta/__tests__/`

### Integration
- **Framework:** pytest + `fastapi.testclient.TestClient` (API) e `click.testing.CliRunner` (CLI)
- **Comando:** `pytest tests/api/test_meta_decks_router.py tests/api/test_meta_decks_registration.py tests/cli/test_cli_metagame.py tests/cli/test_cli_metagame_registration.py -q`
- **Path padrão:** `tests/api/`, `tests/cli/`

Frontend também tem uma camada "integration-like": `frontend/src/pages/__tests__/TopDecksPage.test.tsx`
(T13), que monta a página real com `MemoryRouter` e stub de `MetaDecksPanel`/`fetchDeckRanking`.
Comando: `cd frontend && npx vitest run src/pages/__tests__/TopDecksPage.test.tsx`.

### E2E
**N/A** — o repositório não tem harness de E2E de browser (Playwright/Cypress) hoje;
o único arquivo com "e2e" no nome (`tests/integration/test_currency_e2e.py`) é um
teste de integração pytest, não um teste de browser. Cobertura do fluxo do usuário
fica nos testes de integração de API/CLI (acima) + no teste de página do T13
(`TopDecksPage.test.tsx`), que exercita a navegação por query params sem um browser real.

## 3. Perf budgets

| Métrica | Limite | Como medir | Aplicável a |
|---|---|---|---|
| Intervalo mínimo por host | ≥ 3s (ou `Crawl-delay` da fonte, se maior) | `test_http.py`: clock/sleep fake, assert `sleep` chamado com duração ≥ limite entre 2 GETs no mesmo host | `PoliteFetcher` (T04) |
| Requests por coleta (Commander) | 1 (lista) + `limit` (decklists) | `test_source_edhrec.py`: contar chamadas ao `FakeFetcher` para `limit=1` e `limit=N` | `EdhrecSource` (T07) |
| Cache hit | 0 chamadas de rede dentro do TTL | `test_http.py`: 2ª chamada com mesma URL/TTL não incrementa contador do `MockTransport` | `PoliteFetcher` (T04) |
| Retry/backoff | máx. 3 tentativas antes de `FetchError` | `test_http.py`: contar chamadas do transport até a exceção | `PoliteFetcher` (T04) |

Sem budgets de latência de resposta HTTP (ms) ou de renderização de UI — a feature é
coleta local/batch (não é caminho crítico de latência do usuário) e o painel do
frontend já usa skeleton/loading state (T11), então TTI não é um requisito novo desta
feature.

## 4. Mocks vs hits real

| Componente | Decisão | Justificativa |
|---|---|---|
| EDHREC / fonte construída (rede externa) | mock (`FakeFetcher` / `httpx.MockTransport` + fixtures em disco) | Overview e Constraints exigem "testes backend NUNCA fazem rede real"; sites externos são não-determinísticos e podem mudar de estrutura a qualquer momento — mock elimina flakiness (`feedback_no_ceremony_specs.md`). |
| `robots.txt` / rate limit / cache (T04) | mock (`httpx.MockTransport`, clock/sleep injetados) | Testar timing real exigiria dormir de verdade nos testes (lento e flaky); injetar clock é o próprio design pedido pela task — sem isso o teste de rate limit não é determinístico. |
| Banco de dados (SQLite) | real (SQLite em memória) | `MetagameRepository`/router precisam validar SQL, `create_all`, cascatas de delete e joins reais; mock de ORM esconderia bugs de schema. Mesmo padrão já usado no resto do projeto (`tests/conftest.py`). |
| `Repository.get_latest_prices_batch` / `resolve_card_id` (via `src.decks.importer`) | real (chamando a função real sobre dados semeados) | São funções puras/determinísticas do próprio código já testado; mockar duplicaria a lógica de resolução em vez de testá-la — custo de manter o mock supera o benefício. |
| API FastAPI (router T10) | real (`TestClient` sobre app mínima com `dependency_overrides`) | Precisa validar contrato HTTP (schemas Pydantic, envelope `ApiResponse`, status codes) — mockar o framework não testaria isso. |
| CLI Click (T12) | real (`CliRunner` invocando o comando de verdade) | `sources` internas mockadas via `monkeypatch` de `get_sources`, mas o parsing de flags/exit code é real — é justamente o que a task precisa garantir. |
| Componentes React (T11/T13) | mock da camada de API (`vi.mock("../../api/metaDecks")`) | RTL testa comportamento visual/interação, não a rede; mock do módulo de API é o padrão já usado nos outros testes do frontend (`_brief/04-frontend.md`). |
| Valoração (`value_meta_deck`, T05) | real, sem mocks | Função pura, sem I/O — mockar não faria sentido; entradas via `SimpleNamespace`. |

## 5. Test scenarios resumo

1. Escolha de fonte válida por formato registrada no ADR e refletida em `SOURCE_FOR_FORMAT` — F173-T01
2. Formato sem fonte válida marcado como "não suportado" e omitido do registry — F173-T01
3. Modelos criam tabelas automaticamente em engine SQLite em memória — F173-T03
4. `replace_snapshot` idempotente rodando 2x no mesmo dia — F173-T03
5. `list_decks` retorna snapshot mais recente por padrão, ordenado por rank; `snapshot_date` explícito retorna snapshot antigo — F173-T03
6. `resolve_card_id` cobre exato, nome único, carta dupla (`" // "`), não encontrado — F173-T03
7. `owned_quantities` soma quantidades por `card_id`, lista vazia → `{}` — F173-T03
8. URL desautorizada por `robots.txt` levanta `RobotsDisallowed` sem fazer o request — F173-T04
9. Dois GETs no mesmo host respeitam `min_interval_s`/`Crawl-delay` (clock fake) — F173-T04
10. Cache hit dentro do TTL não chama o transport; TTL expirado refaz o request — F173-T04
11. 429/5xx fazem retry (máx. 3) e depois `FetchError`; 404 não tenta de novo — F173-T04
12. `normalize_colors` ordena WUBRG, remove duplicatas, trata vazio/None — F173-T04
13. `value_meta_deck` calcula `total_value_brl`, `priced_pct`, `owned_pct`, `missing_value_brl` no caminho feliz — F173-T05
14. Terrenos básicos contam como precificados (R$0) e possuídos automaticamente — F173-T05
15. Deck vazio não gera `ZeroDivisionError`; `owned=None` (anônimo) → `owned_pct`/`missing_value_brl` `None` — F173-T05
16. `fetchMetaDecks`/`fetchMetaFormats`/`fetchMetaDeck` chamam as URLs e params corretos; `offset:0` não é omitido — F173-T06
17. `EdhrecSource.fetch_top_decks` retorna decks ordenados por rank com o comandante em `board="commander"`, usando fixtures — F173-T07
18. Decklist de um comandante falha (`FetchError`) → deck pulado, coleta continua para os demais — F173-T07
19. `fmt` diferente de `commander` levanta `ValueError` — F173-T07
20. Adapter de formatos construídos retorna arquétipos ordenados por `meta_share_pct` com decklist main+side, usando fixtures — F173-T08
21. Meta share em formatos textuais distintos (`"12.5 %"`, `"12,5%"`, ausente) normalizado para `Decimal`/`None` — F173-T08
22. Formato não suportado pelo adapter levanta `ValueError` — F173-T08
23. `collect_metagame` grava snapshot por formato via `repo.replace_snapshot`, idempotente no mesmo dia — F173-T09
24. Erro isolado por formato (`FetchError`/exceção) não interrompe os demais formatos; registrado em `stats.errors` — F173-T09
25. `dry_run=True` não grava nada, mas preenche `stats` — F173-T09
26. Resolver de carta usa cache por coleta (mesma carta em vários decks resolve 1x) — F173-T09
27. `GET /api/v1/meta-decks?format=` retorna decks com `total_value_brl`, `priced_pct`, `missing_value_brl`, `owned_pct` (null se anônimo) — F173-T10
28. `format` inválido → 422; deck inexistente em `/meta-decks/{id}` → 404 no envelope padrão — F173-T10
29. Sem snapshot para o formato → 200 com lista vazia — F173-T10
30. `MetaDecksPanel`/`MetaDeckRow` renderizam estados loading/vazio/erro/dados; expandir carrega `MetaDeckCardList` — F173-T11
31. `owned_pct === null` esconde a barra de % possuído e mostra CTA de login — F173-T11
32. Trocar pill de formato dispara `onFormatChange`; formato sem snapshot fica desabilitado e não dispara `onChange` — F173-T11
33. CLI `collect-metagame -f modern -f commander --limit 2` grava e imprime totais, exit 0 — F173-T12
34. CLI sem `-f` cobre todos os formatos do registry; `--dry-run` não grava no banco — F173-T12
35. Todas as fontes falhando → exit 1; uma falha isolada → exit 0 com aviso — F173-T12
36. `get_sources` cobre todos os formatos declarados em `SOURCE_FOR_FORMAT` — F173-T12
37. `/decks/ranking` sem params mantém comportamento atual (`view=mine`, `fetchDeckRanking` chamado) — F173-T13
38. `/decks/ranking?view=meta&format=modern` renderiza o painel com o formato correto sem chamar `fetchDeckRanking` — F173-T13
39. Deep-link com `view=meta` sobrevive a refresh (estado vem só da URL) — F173-T13
40. Link `data-testid="top-decks-preview-meta-link"` presente no `TopDecksPreview`, testes existentes de preview continuam verdes — F173-T13
41. Diagramas `.mmd` usam os nomes reais de classes/arquivos entregues (`EdhrecSource`, `Mtgtop8Source` ou equivalente do ADR) — F173-T14
42. `create_app()` real expõe `GET /api/v1/meta-decks/formats` (200) — F173-T15
43. `cli --help` lista `collect-metagame`; `collect-metagame --help` funciona — F173-T15
44. Chaves i18n `metaDecks.*`/`topDecks.tabMine`/`topDecks.tabMeta`/`topDecks.viewMeta` presentes e com mesma estrutura em `pt-BR.json`/`en.json` — F173-T15
45. Suite completa (`pytest tests/ --cov=src`, `ruff check src/`, `npm test && npm run build`) verde após a integração final — F173-T15

## 6. Anotações para tasks

- (F173-T01, fixtures: edhrec-top-commanders, edhrec-decklist, constructed-meta-page, constructed-decklist) — T01 é quem cria as 4 fixtures; nenhum teste automatizado novo consome (é scaffolding), mas os testes de T07/T08 dependem delas existirem no disco.
- (F173-T02, fixtures: none) — task de documentação (PRD), sem fixtures.
- (F173-T03, fixtures: none) — usa `types.SimpleNamespace` + SQLite em memória, sem fixtures de arquivo.
- (F173-T04, fixtures: none) — usa `httpx.MockTransport` com corpos sintéticos inline.
- (F173-T05, fixtures: none) — função pura testada com `SimpleNamespace`.
- (F173-T06, fixtures: none) — mocka `apiGet`, sem fixtures de arquivo.
- (F173-T07, fixtures: edhrec-top-commanders, edhrec-decklist)
- (F173-T08, fixtures: constructed-meta-page, constructed-decklist)
- (F173-T09, fixtures: none) — usa `FakeSource` in-memory.
- (F173-T10, fixtures: none) — semeia dados diretamente no SQLite de teste.
- (F173-T11, fixtures: none) — mocka o módulo `api/metaDecks.ts`.
- (F173-T12, fixtures: none) — `monkeypatch` de `get_sources` com fontes fake.
- (F173-T13, fixtures: none) — stub de `MetaDecksPanel` e mock de `api/deckRanking`.
- (F173-T14, fixtures: none) — documentação; valida nomes via `grep` contra o código entregue.
- (F173-T15, fixtures: none) — testes de registro (`TestClient(create_app())`, `CliRunner`).

### Risks for QA
- **Fonte real ainda não confirmada** (ADR de T01 pode escolher outra fonte que não
  MTGTop8 para os formatos construídos) — QA deve reconferir os nomes de arquivo/
  classe (`src/metagame/sources/<fonte>.py`) antes de validar T08/T12/T14 contra este
  plano; os slugs de fixture (`constructed-meta-page`/`constructed-decklist`) são
  estáveis independentemente da fonte escolhida.
- **Sandbox de nuvem bloqueia rede de saída** para a pesquisa do SPIKE (T01) — se as
  fixtures forem sintéticas ("pending-user" no ADR), QA deve marcar explicitamente a
  necessidade de revalidação com a 1ª coleta real antes de considerar AC1/AC3 fechados.
