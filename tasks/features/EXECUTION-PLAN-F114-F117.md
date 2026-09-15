# Execution Plan: F114-F117

**Created:** 2026-09-09
**Target branch:** homol

## Features Overview

| Feature | Tasks | Type | Estimated Effort |
|---------|-------|------|-----------------|
| F114 Bugfix Sweep | 3 | Bugfix | Small |
| F115 Default Sort by Price | 2 | Enhancement | Medium |
| F116 3D Card Tilt | 3 | Feature | Medium |
| F117 Clean UI Prototype | 5 | Feature | Large |

**Total: 13 tasks across 4 features**

---

## Global Parallelism Map

### Batch 1 (4 worktrees, fully parallel)

```
Worktree A: F114-T01  Card links fix         (collection.py, CardTile.tsx)
Worktree B: F114-T02  Card art DFC fix       (scryfall.py)
Worktree C: F114-T03  Dashboard resilience   (Dashboard.tsx)
Worktree D: F115-T01  Backend price sort     (repository.py, collection.py sort, cards.py)
```

**Zero file overlap.** All 4 can merge cleanly.

### Batch 2 (3 worktrees, fully parallel)

```
Worktree E: F115-T02  Frontend sort default  (MyCollection.tsx, Cards.tsx)
Worktree F: F116-T01  Card3DTilt component   (new file + package.json)
Worktree G: F117-T01  V2 Layout shell        (new file LayoutV2.tsx)
         + F117-T02  Design tokens           (tailwind.config.ts, index.css)
```

F115-T02 depends on F115-T01 (batch 1). F116-T01 and F117-T01+T02 are
independent new files.

### Batch 3 (3 worktrees, fully parallel)

```
Worktree H: F116-T02  Integrate 3D in tiles  (CardTile, CatalogCardTile, DeckCardTile)
         + F116-T03  Foil shimmer            (Card3DTilt.tsx, foil-shimmer.css)
Worktree I: F117-T03  V2 Collection page     (new CollectionV2.tsx)
Worktree J: F117-T04  V2 Dashboard page      (new DashboardV2.tsx)
```

F116-T02/T03 depend on F116-T01 (batch 2). F117-T03/T04 depend on
F117-T01+T02 (batch 2).

### Batch 4 (1 task)

```
F117-T05  V2 route prefix + toggle  (App.tsx)
```

Depends on all F117 tasks. Final integration.

---

## Timeline (3 batches = 3 dev sessions)

```
Batch 1:  ████████████  (4 parallel)  F114 complete + F115 backend
Batch 2:  ████████████  (3 parallel)  F115 complete + F116/F117 foundations
Batch 3:  ████████████  (3 parallel)  F116 complete + F117 pages
Batch 4:  ████          (1 task)      F117 routes → F117 complete
```

## Merge Order

1. Merge all Batch 1 worktrees → homol
2. Merge all Batch 2 worktrees → homol
3. Merge all Batch 3 worktrees → homol
4. Merge Batch 4 → homol
5. Test end-to-end on homol
6. User validates → promote to main

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| CardTile.tsx touched by F114-T01 and F116-T02 | Scheduled in different batches (1 vs 3) |
| collection.py touched by F114-T01 and F115-T01 | Different sections (Liga URL vs sort params) |
| package.json touched by F116-T01 | Only in batch 2, no conflict |
| App.tsx touched by F117-T05 | Last batch, trivial addition |
