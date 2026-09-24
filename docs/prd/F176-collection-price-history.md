# PRD — F176 Histórico de preços dos cards da coleção (correção definitiva)

**Status:** planned · **Data:** 2026-09-24 · **Lote:** F171–F179

## Problema
Na página de detalhe de um card da coleção (`/collection/:id`), o gráfico de
histórico de preço fica vazio ou com 1–2 pontos, mesmo para cards varridos
com frequência pelo Liga sweep. Quatro features anteriores (F33, F34, F112,
F168) não resolveram. Sem histórico, o usuário não consegue avaliar a
tendência de valor dos próprios cards — a proposta central do produto.

## Usuários
Colecionador autenticado que acompanha o valor da própria coleção em BRL.

## Objetivos
- G1: todo card da coleção com preço coletado mostra série diária desde a 1ª coleta.
- G2: a série é da **variante possuída** (foil vs normal).
- G3: o histórico cresce sozinho todo dia, sem ação manual além das rotinas `.bat` existentes.
- G4: nunca exibir dado fabricado antes da 1ª coleta real.

## Não-objetivos
Novas fontes de preço; migração de schema; sparkline de listas; agendador in-process no Render.

## Requisitos funcionais
- RF1 Diagnóstico read-only reprodutível (script) com relatório.
- RF2 Resolução de chaves de histórico por variante (Liga `liga_{card_id}[_foil]`, `manual_{card_id}`, source_cards MYP/catálogo, `jsonld_snapshot`, `daily_snapshot`).
- RF3 1 ponto/dia com prioridade de fonte `manual > liga > jsonld_snapshot > myp > daily_snapshot`.
- RF4 Snapshot diário automático ao fim do liga-sweep + `bats/daily-snapshot.bat`; carry-forward limitado a 30 dias sem coleta real.
- RF5 Backfill por forward-fill a partir de observações reais, com `--dry-run`.
- RF6 Endpoints `/collection/{id}/history`, `/collection/{id}/metrics`, `/cards/{id}/history` usam a mesma resolução; resposta com `meta` (variante, fontes, desde, pontos reais/snapshot).
- RF7 UI com badge de variante, fontes, "histórico desde", tooltip para pontos repetidos e estado vazio explicativo.

## Requisitos não funcionais
SQLite + Neon PostgreSQL; histórico em ≤1 query de observações por request; sem dependências novas; cobertura ≥90% nos módulos novos.

## Métricas de sucesso
% de entradas da coleção com ≥2 pontos em 30d (medido pelo script de diagnóstico antes/depois) — alvo ≥90% das entradas com preço.

## Riscos
- Dados antigos de backfill "plano" (F168) continuam no banco → documentado no ADR com limpeza opcional (decisão do usuário).
- MYP pode não distinguir foil → série foil fica só com Liga/manual.
- Conflitos com outras features do lote em `collection.py`, i18n e `types/api.ts` → mudanças aditivas e localizadas.
