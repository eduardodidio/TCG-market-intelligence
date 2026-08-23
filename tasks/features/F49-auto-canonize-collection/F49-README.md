# F49 Auto-Canonize Collection

**Status:** planned
**Feature:** Auto-Canonize Collection — vincular automaticamente todas as cartas da colecao ao canonico (rastreamento de preco MYP)

## Summary

Ao inserir uma carta na colecao, o sistema deve automaticamente buscar e vincular ao produto MYP correspondente (canonize). Inclui:
1. Endpoint/CLI para canonizar em massa todas as cartas existentes sem vinculo
2. Integracao automatica no fluxo de import CSV para canonizar na insercao
3. Retry para cartas que falharam canonizacao

## Current State

- Canonize endpoint existe: `POST /collection/{id}/canonize` (single card)
- CSV import cria `CardRow` mas NAO busca MYP (sem SourceCard, sem preco)
- `sync-collection` faz o fluxo completo MYP mas e um comando separado
- Nenhum mecanismo de auto-canonize no fluxo de insercao

## Global Acceptance Criteria

- **AC1:** User can canonize all unlinked cards via API endpoint (POST /collection/canonize-all)
- **AC2:** CSV import automatically triggers background canonization for new entries
- **AC3:** CLI command `canonize-all` runs bulk canonization with dry-run support
- **AC4:** Frontend shows "Canonize All" button when unlinked cards exist, with progress feedback
- **AC5:** All canonize UI strings are translated in EN and PT-BR

## Tasks

| Task | Description | Wave | Depends | AC |
|------|-------------|------|---------|-----|
| F49-T01 | Bulk canonize service + endpoint | 0 | - | AC1 |
| F49-T02 | Auto-canonize hook on CSV import | 1 | T01 | AC2 |
| F49-T03 | Bulk canonize CLI command | 1 | T01 | AC3 |
| F49-T04 | Frontend bulk canonize UI | 1 | T01 | AC4 |
| F49-T05 | i18n keys for canonize UI | 1 | T04 | AC5 |

## Waves

- **Wave 0:** T01 (bulk canonize service + endpoint)
- **Wave 1:** T02, T03, T04, T05 (depend on Wave 0)

## Architecture Notes

- Bulk canonize reuses existing `canonize_card` logic in a loop with concurrency control
- Auto-canonize on import triggers async background canonization after CSV rows inserted
- Rate limiting: respect MYP rate limits (existing backoff in provider)
- Orphan re-canonization: reuse existing orphan logic from F46
