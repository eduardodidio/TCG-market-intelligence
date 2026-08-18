# F01 Test Plan -- MYP Cards Backfill (Dominaria Remastered)

| Campo           | Valor                                                      |
|-----------------|------------------------------------------------------------|
| **Status**      | retroactive                                                |
| **Generator**   | TEA                                                        |
| **Generated-at**| 2026-08-18                                                 |
| **Source-brief** | `tasks/features/F01-myp-backfill/F01-README.md`           |

> **Nota:** Este plano foi gerado retroativamente. F01 ja esta shipped com
> 103 testes passando (incluindo testes adicionados por F03). O foco aqui
> e documentar o estado atual e identificar gaps para sprints futuros.

---

## 1. Fixtures

| Fixture                          | Path                                         | Domain     | Owner   |
|----------------------------------|----------------------------------------------|------------|---------|
| `card_page_one_ring.html`        | `tests/fixtures/card_page_one_ring.html`     | parser     | F01-T01 |
| `price_history_one_ring.html`    | `tests/fixtures/price_history_one_ring.html`  | parser     | F01-T01 |
| `set_page_dmr.html`             | `tests/fixtures/set_page_dmr.html`           | parser     | F01-T01 |
| `editions_page_1.html`          | `tests/fixtures/editions_page_1.html`        | parser     | F01-T01 |
| `repo` (pytest fixture)          | `tests/unit/test_repository.py`              | db         | F01-T01 |

**Nota sobre gaps:** Nao existem fixtures para paginas com erros (HTML
malformado, JSON-LD ausente, history page sem `precoChartConfig`). Ver
secao 6 para cenarios faltantes.

---

## 2. Harnesses por fronteira

### Unit

- **Framework:** pytest
- **Comando:** `python -m pytest tests/unit/ -v`
- **Path padrao:** `tests/unit/`
- **Estado atual:** 103 testes, todos passando. Cobrem parsers
  (`test_parsers.py`), repository CRUD + upsert/idempotency
  (`test_repository.py`), repository queries (`test_repository_queries.py`),
  analytics models (`test_analytics_models.py`), analytics indicators
  (`test_indicators.py`), CLI analytics (`test_cli_analytics.py`).

### Integration

- **Framework:** pytest + SQLite in-memory
- **Comando:** `python -m pytest tests/unit/test_repository.py tests/unit/test_repository_queries.py -v`
- **Estado atual:** Os testes de repository ja funcionam como testes de
  integracao leves (SQLAlchemy + SQLite real via `tmp_path`). Nao ha
  testes de integracao dedicados que exercitem provider + repository
  juntos.
- **Gap identificado:** Nao existe teste que simule o fluxo completo
  backfill (provider mock -> parser -> repository -> summary) sem rede.

### E2E

**N/A** -- F01 e um collector CLI sem UI. Testes E2E exigiriam acesso
real ao mypcards.com, o que e fragil e viola rate limits. O backfill
manual documentado em F01-T01/T04 serviu como validacao E2E one-shot.

---

## 3. Perf budgets

| Metrica                    | Limite       | Como medir                                  | Aplicavel a |
|----------------------------|--------------|----------------------------------------------|-------------|
| Parse de HTML por card     | < 50ms       | `pytest --durations=10`                       | test_parsers |
| Insert de 1000 observacoes | < 2s         | benchmark no test_repository                  | test_repository |
| Full test suite            | < 10s        | `time python -m pytest tests/ -q`            | all          |

_O suite atual roda em ~0.37s (103 testes). Nenhum budget esta em risco._

---

## 4. Mocks vs hits real

| Componente                  | Decisao  | Justificativa                                                |
|-----------------------------|----------|--------------------------------------------------------------|
| `curl_cffi` HTTP requests   | mock     | Acesso real ao mypcards.com e lento, fragil, e sujeito a rate limit/Cloudflare. Fixtures HTML salvos substituem chamadas reais. |
| SQLite database             | real     | `tmp_path` cria DB efemero por teste. Custo zero, determinismo total. Usar mock de DB esconderia bugs de SQL/schema. |
| `parse_*` functions         | real     | Funcoes puras que operam sobre strings. Nenhum motivo para mock. |
| `MypCardsProvider` (no backfill) | mock | Provider depende de rede. Em testes de integracao do backfill (gap atual), deve ser mockado com respostas pre-gravadas. |
| Filesystem (fixtures)       | real     | Fixtures sao arquivos reais no repo. Nenhum custo.            |

---

## 5. Test scenarios resumo

### Cobertos (existentes)

1. **Parser: SKU parsing** -- standard, three-letter, invalid, empty (F01-T01) -- `test_parsers.py::TestParseSku`
2. **Parser: editions page** -- find sets, exclude non-set links (F01-T01) -- `test_parsers.py::TestParseSetLinks`
3. **Parser: card links** -- find cards, uniqueness (F01-T01) -- `test_parsers.py::TestParseCardLinks`
4. **Parser: JSON-LD product** -- parse product, card page, URL (F01-T01) -- `test_parsers.py::TestParseCardPage`
5. **Parser: price snapshot** -- extract current price (F01-T01) -- `test_parsers.py::TestParsePriceSnapshot`
6. **Parser: price history** -- parse history, dates, prices, chronological order, no duplicate dates (F01-T01) -- `test_parsers.py::TestParsePriceHistory`
7. **Parser: pagination** -- max page, single page, no pagination (F01-T01) -- `test_parsers.py::TestParsePaginationMax`
8. **Repository: upsert source card** -- insert new, idempotent (F01-T01) -- `test_repository.py::TestUpsertSourceCard`
9. **Repository: insert observations** -- insert new, skip duplicates, empty list (F01-T01) -- `test_repository.py::TestInsertPriceObservations`
10. **Repository: collection errors** -- insert/retrieve, mark resolved (F01-T01) -- `test_repository.py::TestCollectionErrors`
11. **Repository: price series queries** -- ordered by date, filter by days, nonexistent card, single obs (F01-T03) -- `test_repository_queries.py`
12. **Repository: cards with observations** -- counts, empty source, filter by source (F01-T03) -- `test_repository_queries.py`

### Gaps (nao cobertos -- recomendados para sprint futuro)

13. **Parser: HTML malformado** -- card page sem JSON-LD, history page sem `precoChartConfig`. Confirmar que retorna `None` ou lista vazia sem crash. (F01-T01)
14. **Parser: encoding edge cases** -- nomes com acentos PT (`Anjo da Guarda`, `Forca Brutal`), caracteres especiais. (F01-T01)
15. **Provider: rate limiting** -- verificar que `delay_seconds` e respeitado entre requests. (F01-T01)
16. **Provider: retry logic** -- verificar que `max_retries` funciona em caso de timeout/HTTP 5xx. (F01-T01)
17. **Provider: Cloudflare 403** -- garantir que fallback ou erro claro ocorre. (F01-T01)
18. **Backfill orchestration** -- fluxo completo com provider mockado: discover -> process -> upsert -> summary. (F01-T04)
19. **Backfill idempotency** -- re-run com mesmos dados retorna `observations_saved=0`. (F01-T04)
20. **CLI: backfill command** -- Click CLI aceita `--set`, `--delay`, `--limit`, `--dry-run`. (F01-T04)
21. **CLI: update command** -- `--history-days` limita janela de coleta. (F01-T04)
22. **CLI: retry-failed command** -- re-processa apenas cards com erros nao resolvidos. (F01-T04)
23. **Data quality: price bounds** -- observacoes com `median_price <= 0` ou absurdamente altas sao rejeitadas ou flagged. (F01-T02)

---

## 6. Anotacoes para tasks

| Task    | Fixtures necessarios                                      | Cenarios referenciados |
|---------|-----------------------------------------------------------|------------------------|
| F01-T01 | `card_page_one_ring.html`, `price_history_one_ring.html`, `set_page_dmr.html`, `editions_page_1.html` | 1--7 (cobertos), 13--17 (gaps) |
| F01-T02 | `repo` (pytest fixture)                                   | 23 (gap)               |
| F01-T03 | `repo` (pytest fixture)                                   | 11--12 (cobertos)      |
| F01-T04 | `repo`, provider mock (a criar)                           | 18--22 (gaps)          |

### Prioridade dos gaps

- **Alta:** #18 (backfill orchestration) -- componente central sem teste automatizado.
- **Alta:** #13 (HTML malformado) -- parsing e a fronteira mais fragil com o mundo externo.
- **Media:** #16, #17 (retry/Cloudflare) -- resiliencia de rede.
- **Media:** #20, #21, #22 (CLI commands) -- previnem regressoes no contrato CLI.
- **Baixa:** #14 (encoding), #15 (rate limiting), #19 (idempotency), #23 (price bounds) -- cobertos implicitamente ou de baixo risco.
