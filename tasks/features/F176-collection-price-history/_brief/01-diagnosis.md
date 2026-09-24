# F176 — Shard 01: Diagnóstico ponta a ponta

## Objetivo

Provar com dados (SQLite local e, quando o usuário rodar, Neon via
`DATABASE_URL`) de onde vêm os pontos do histórico de um card da coleção e
por que não chegam ao gráfico. **Somente leitura** — nenhum INSERT/UPDATE.

## Artefatos

- `scripts/diagnose_collection_history.py` (novo, standalone, `argparse`,
  NÃO registrar em `src/cli/main.py`). Uso:
  ```
  python scripts/diagnose_collection_history.py --entry-id 123
  python scripts/diagnose_collection_history.py --user-id <uid> --sample 20 --json out.json
  python scripts/diagnose_collection_history.py --db sqlite:///tcg_market.db --sample 50
  ```
  `--db` default: `src.config.get_db_url()` (lê `.env`).
- Funções puras testáveis no script (importáveis): `collect_entry_diagnosis(repo, entry_id) -> dict`
  e `summarize(diagnoses) -> dict`.
- Relatório: `tasks/features/F176-collection-price-history/diagnosis.md`.

## O que medir por entrada da coleção

1. `entry_id`, `card_id`, `extras`, `is_foil_entry(extras)`, set/collector.
2. `source_cards` do `card_id`: (source, external_id).
3. Para cada chave candidata — source_cards + `liga_{card_id}`,
   `liga_{card_id}_foil`, `manual_{card_id}` — contagem de
   `price_observations` agrupada por `source` (liga, myp, jsonld_snapshot,
   daily_snapshot, manual, …), 1ª e última `observed_at`, nº de dias distintos
   nos últimos 30/90 dias.
4. O que o endpoint ATUAL devolveria (replicar a lógica de
   `get_collection_history`: source_cards × `[sc.source, 'jsonld_snapshot']`)
   vs. o que existe no total → "pontos perdidos".
5. Nº de datas com >1 observação (H5) e se séries foil e normal coexistem (H4).

## Resumo agregado (summarize)

- % entradas com 0 pontos no endpoint atual; % que teriam ≥2 pontos com o
  resolver novo (T03 ainda não existe — replicar a regra do shard 02 inline).
- Distribuição por source; última data de `daily_snapshot` no banco (H3).
- Nº de entradas foil com série `liga_{id}_foil`.

## diagnosis.md — seções obrigatórias

1. Ambiente (db, data, nº entradas amostradas)
2. Tabela H1–H6: confirmada / refutada / inconclusiva + número que prova
3. Achados novos não previstos
4. Comandos para o usuário rodar contra o Neon (read-only)
5. Recomendação — confirma ou ajusta o contrato do shard 02

Se o banco local estiver vazio, o dev cria um fixture SQLite temporário no
scratch (não commitado) reproduzindo o formato do liga-sweep e documenta que
os números de produção dependem do usuário rodar o script no Neon.
