# Orchestration Plan — F29, F30, F31

> Gerado em 2026-08-21. Plano de execucao otimizado para maxima paralelizacao.

## Planning Status

| Feature | Titulo                      | Tasks | Waves | PRD | Plan | Deps |
|---------|-----------------------------|-------|-------|-----|------|------|
| F29     | Single Card Refresh         | 6     | 3     | -   | OK   | -    |
| F30     | Bulk Collection Refresh     | 4     | 2     | -   | OK   | -    |
| F31     | Set Icon Filter Scroll      | 3     | 2     | -   | OK   | -    |

**Total:** 13 tasks, 3 features.

---

## Analise de Conflitos de Arquivo

| Arquivo                              | F29 | F30 | F31 |
|--------------------------------------|-----|-----|-----|
| `src/api/routers/collection.py`      | X   |     |     |
| `frontend/src/pages/MyCollection.tsx` | X   | X   |     |
| `frontend/src/api/collection.ts`     | X   |     |     |
| `frontend/src/components/SetIconFilter.tsx` |  |  | X   |
| `frontend/src/components/DeckCardTile.tsx` | X |  |     |
| `frontend/src/pages/CollectionCardDetail.tsx` | X | |  |
| `frontend/src/i18n/locales/*.json`   | X   | X   |     |

### Conflitos

1. **MyCollection.tsx** — F29 (refresh button on tile) + F30 (RefreshAll button)
   - F29 modifica `CollectionCardTile` (add overlay icon)
   - F30 adds button in header area
   - Areas distintas, mas mesmo arquivo. Serialize F29 Wave 2 before F30 Wave 2.

2. **i18n locales** — F29 + F30 add different keys (additive, low conflict)

---

## Plano de Execucao

### Batch 6 — Todas paralelas (3 features)

```
/create-feature F29   (Single Card Refresh)
/create-feature F30   (Bulk Collection Refresh)     <- paralelas
/create-feature F31   (Set Icon Filter Scroll)
```

**Risco:** Baixo-Medio
- F31 e totalmente isolada (SetIconFilter.tsx)
- F29 e F30 compartilham MyCollection.tsx mas em areas diferentes
- F30 nao tem backend changes (reusa scans existente)

**Mitigacao:**
- F31: executar em worktree isolado, merge independente
- F29 e F30: rodar Wave 1 de ambas em paralelo (nao tocam mesmos arquivos)
- Wave 2: F29 primeiro (CollectionCardTile), depois F30 (header area)
- Merge order: F31 -> F29 -> F30

### Paralelismo Detalhado por Wave

```
Timeline:
                F29              F30              F31
Wave 1:    [T01+T02]        [T01+T02]        [T01+T02]      <- ALL PARALLEL
Wave 2:    [T03+T04+T05]    ---wait---        [T03]          <- F29+F31 parallel
Wave 2b:   ---              [T03+T04]         ---            <- after F29 W2
Wave 3:    [T06]            ---               ---            <- final
```

**Maximo parallelismo em Wave 1:** 6 tasks simultaneas (2+2+2)
**Total waves sequenciais:** 4 (W1 -> W2 -> W2b -> W3)

---

## Diagrama de Dependencias

```
F31 (isolated)          F29                    F30
+-----------+           +-----------+          +-----------+
|T01 + T02  |           |T01 + T02  |          |T01 + T02  |
|(Wave 1)   |           |(Wave 1)   |          |(Wave 1)   |
+-----------+           +-----------+          +-----------+
      |                       |                      |
+-----------+           +-----------+                |
|T03 (Wave2)|           |T03+T04+T05|                |
|(tests)    |           |(Wave 2)   |                |
+-----------+           +-----------+                |
      |                       |                      |
   MERGE                 +-----------+          +-----------+
                         |T06 (Wave3)|          |T03+T04    |
                         |(i18n)     |          |(Wave 2)   |
                         +-----------+          +-----------+
                              |                      |
                           MERGE                  MERGE
```

## Resumo Executivo

| Batch | Features     | Paralelismo   | Pre-req | Risco  |
|-------|-------------|---------------|---------|--------|
| 6     | F29,F30,F31 | 3 paralelas*  | -       | Baixo  |

*F31 totalmente paralela. F29+F30 paralelas em Wave 1, sequenciais em Wave 2.

**Merge order:** F31 -> F29 -> F30

---

## Proximos Passos

1. **Agora:** Revisar este plano e confirmar
2. **Executar:** `/create-feature F31` (isolada, pode rodar independente)
3. **Em paralelo:** `/create-feature F29` e `/create-feature F30` (cuidado com Wave 2)
