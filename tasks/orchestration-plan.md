# Orchestration Plan — Backlog F16–F23

> Gerado em 2026-08-21. Plano de execucao otimizado para maxima paralelizacao.

## Planning Status

| Feature | Titulo                   | Tasks | Waves | PRD | Plan | Deps       |
|---------|--------------------------|-------|-------|-----|------|------------|
| F16     | Explore Cards: Sorting   | 5     | 3     | OK  | OK   | —          |
| F17     | Set Symbol Icons         | 3     | 3     | OK  | OK   | —          |
| F18     | Multi-Currency (BRL+USD) | 12    | 5     | OK  | OK   | —          |
| F19     | Moeda "Pila" (RS)        | 7     | 5     | OK  | OK   | F18, F22   |
| F20     | Card Grid Size Control   | 4     | 3     | OK  | OK   | —          |
| F21     | Price Fallback Sources   | —     | —     | —   | —    | brainstorm |
| F22     | Authentication (Login)   | 10    | 7     | OK  | OK   | —          |
| F23     | Deck Import              | 11    | 6     | OK  | OK   | F22        |

**Total planejado:** 52 tasks, 7 features prontas para execucao.
**Pendente:** F21 (brainstorm necessario).

---

## Analise de Conflitos de Arquivo

Antes de paralelizar, mapeei quais features tocam os mesmos arquivos:

| Arquivo                              | F16 | F17 | F18 | F19 | F20 | F22 | F23 |
|--------------------------------------|-----|-----|-----|-----|-----|-----|-----|
| `src/database/repository.py`         | X   |     | X   |     |     |     | X   |
| `src/api/routers/collection.py`      | X   |     | X   |     |     | X   |     |
| `frontend/src/pages/MyCollection.tsx` | X   | X   | X   | X   | X   |     |     |
| `src/database/models.py`             |     |     | X   |     |     | X   | X   |
| `src/api/deps.py`                    |     |     |     |     |     | X   |     |
| All price-displaying pages           |     |     | X   | X   |     |     |     |
| All API routers (auth guards)        |     |     |     |     |     | X   |     |
| Frontend routing                     |     |     |     |     |     | X   | X   |

### Conflitos Criticos

1. **MyCollection.tsx** — tocado por F16, F17, F18, F19, F20 (5 features!)
   - F17: troca FilterChips por SetIconFilter (area do filtro)
   - F20: adiciona GridSizeToggle (area do header da grid)
   - F16: adiciona SortSelect (area do header)
   - F18: altera formatacao de precos (area dos cards)
   - F19: altera formatacao para Pila (mesma area de F18)

2. **collection.py router** — tocado por F16 (sort params), F18 (currency param), F22 (auth guards)

3. **repository.py** — tocado por F16 (sort), F18 (currency), F23 (decks)

4. **models.py (DB)** — tocado por F18 (exchange_rate), F22 (user), F23 (deck)

---

## Plano de Execucao

### Batch 1 — Features Pequenas, Frontend-Focused (3 paralelas)

```
/create-feature F16   (Sorting)
/create-feature F17   (Set Symbol Icons)        ← paralelas
/create-feature F20   (Card Grid Size)
```

**Risco:** Medio — todas tocam MyCollection.tsx, mas em areas distintas:
- F17 mexe no filtro de sets (substitui componente)
- F20 mexe no header da grid (adiciona toggle)
- F16 mexe no header + query params (adiciona sort)

**Mitigacao:** Usar worktrees isolados. Merge na ordem F17 → F20 → F16 (menor → maior impacto).

**Tempo estimado:** Batch completo apos merge das 3 features.

---

### Batch 2 — Features Grandes, Independentes (2 paralelas)

```
/create-feature F18   (Multi-Currency)
/create-feature F22   (Authentication)           ← paralelas
```

**Pre-requisito:** Batch 1 mergeado (para evitar conflitos em collection.py e MyCollection.tsx).

**Risco:** Baixo-Medio — ambas tocam routers mas para concerns diferentes:
- F18 adiciona `?currency=` param nos endpoints de preco
- F22 adiciona auth guards em todos os endpoints

**Mitigacao:** Worktrees isolados. Merge F18 primeiro (menos invasivo nos routers), depois F22 (que toca tudo).

---

### Batch 3 — Features Dependentes (2 paralelas)

```
/create-feature F19   (Moeda Pila)
/create-feature F23   (Deck Import)              ← paralelas
```

**Pre-requisito:** Batch 2 completo (F19 precisa de F18+F22, F23 precisa de F22).

**Risco:** Baixo — F19 e F23 nao se sobrepoem:
- F19 mexe em formatacao de moeda (display layer)
- F23 cria modulo novo de decks (nova area)

---

### Deferred — Brainstorm Necessario

```
/brainstorm F21   (Price Fallback Sources)
/plan-feature F21
/create-feature F21
```

**Quando:** A qualquer momento apos Batch 1. F21 e independente das outras features.
Pode ser planejado durante a execucao dos Batches 2-3.

---

## Diagrama de Dependencias

```
Batch 1 (paralelo)          Batch 2 (paralelo)       Batch 3 (paralelo)
┌──────────┐                ┌──────────┐              ┌──────────┐
│   F16    │──┐             │   F18    │──────────┐   │   F19    │
│ Sorting  │  │             │ Currency │          ├──▶│  Pila    │
└──────────┘  │             └──────────┘          │   └──────────┘
┌──────────┐  ├──merge──▶   ┌──────────┐          │   ┌──────────┐
│   F17    │  │             │   F22    │──────────┼──▶│   F23    │
│ SetIcons │  │             │   Auth   │          │   │  Decks   │
└──────────┘  │             └──────────┘          │   └──────────┘
┌──────────┐  │                                   │
│   F20    │──┘                                   │
│ GridSize │                                      │
└──────────┘                                      │
                            ┌──────────┐          │
                            │   F21    │ (deferred│— brainstorm)
                            │ Fallback │          │
                            └──────────┘──────────┘
```

## Resumo Executivo

| Batch | Features        | Paralelismo | Pre-req          | Risco  |
|-------|-----------------|-------------|------------------|--------|
| 1     | F16, F17, F20   | 3 paralelas | —                | Medio  |
| 2     | F18, F22        | 2 paralelas | Batch 1 mergeado | Baixo  |
| 3     | F19, F23        | 2 paralelas | Batch 2 mergeado | Baixo  |
| —     | F21             | solo        | Brainstorm       | —      |

**Total:** 7 features em 3 batches + 1 deferred.
**Execucao sequencial seria:** 7 features uma a uma.
**Com paralelizacao:** 3 batches (efetivamente ~3 "rodadas" em vez de 7).

---

## Proximos Passos

1. **Agora:** Revisar este plano e confirmar
2. **Batch 1:** Rodar `/create-feature F16`, `/create-feature F17`, `/create-feature F20` em paralelo
3. **Merge Batch 1:** Na ordem F17 → F20 → F16
4. **Batch 2:** Rodar `/create-feature F18` e `/create-feature F22` em paralelo
5. **Merge Batch 2:** Na ordem F18 → F22
6. **Batch 3:** Rodar `/create-feature F19` e `/create-feature F23` em paralelo
7. **A qualquer momento:** `/brainstorm F21` e depois planejar/executar
