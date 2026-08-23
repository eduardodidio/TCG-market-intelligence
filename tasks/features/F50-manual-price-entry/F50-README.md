# F50 Manual Price Entry

**Status:** planned
**Feature:** Manual Price Entry — permitir insercao manual de preco para qualquer carta da colecao

## Summary

Permitir que o usuario insira manualmente o preco de uma carta. O preco manual deve ser claramente marcado como "informacao manual" no frontend. Preco manual coexiste com preco automatico (MYP) — ambos sao armazenados, manual tem precedencia na exibicao quando mais recente.

## Current State

- Precos armazenados em `PriceObservationRow` com `source` field (valores: "myp", "jsonld_snapshot")
- Latest price selection: busca mais recente por data entre todas as sources
- Nenhum mecanismo para inserir precos manualmente
- Nenhuma indicacao visual de fonte do preco no frontend

## Global Acceptance Criteria

- **AC1:** User can set a manual price via PATCH /collection/{id}/price (stored as source="manual")
- **AC2:** Collection responses include price_source field indicating origin (manual/myp/jsonld_snapshot)
- **AC3:** Frontend shows manual price input on card detail + "Manual Price" badge where applicable
- **AC4:** All manual price UI strings translated in EN and PT-BR

## Tasks

| Task | Description | Wave | Depends | AC |
|------|-------------|------|---------|-----|
| F50-T01 | Manual price backend (endpoint + source="manual") | 0 | - | AC1 |
| F50-T02 | Price source indicator in schemas | 0 | - | AC2 |
| F50-T03 | Frontend manual price input + badge | 1 | T01, T02 | AC3 |
| F50-T04 | i18n keys for manual price UI | 1 | T03 | AC4 |

## Waves

- **Wave 0:** T01, T02 (independent backend — T01 adds endpoint, T02 modifies schemas/queries; no file collision as T01 writes new endpoint handler, T02 modifies price query and response schemas)
- **Wave 1:** T03, T04 (depend on Wave 0)

## Architecture Notes

- Reusa `PriceObservationRow` com `source="manual"` — sem nova tabela
- `external_id` para manual: `"manual_{collection_entry_id}"`
- Schema `CollectionCard` ganha `price_source: str | None` (ex: "manual", "myp", "jsonld_snapshot")
- Frontend: badge amarelo "Preco Manual" quando `price_source == "manual"`
- Preco manual nao substitui historico MYP — ambos coexistem na timeline
