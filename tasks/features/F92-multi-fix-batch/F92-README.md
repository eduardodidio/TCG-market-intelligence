# F92 Multi-Fix Batch

**Status:** done
**Created:** 2026-08-29

## Summary
4 independent fixes/improvements shipped as a single feature batch. All tasks
run in parallel (Wave 1) since they touch completely different files with no
dependencies between them.

## Tasks

| Task | Title | Wave | Files |
|------|-------|------|-------|
| T01 | Refresh All Token Cost Display | 1 | MyCollection.tsx, pt-BR.json |
| T02 | MYP Search Fallback on Render | 1 | card_search.py |
| T03 | Credit Balance Stale on Card Nav | 1 | CollectionCardDetail.tsx |
| T04 | Simplify CreditConfirmModal Art | 1 | CreditConfirmModal.tsx |

## Waves

### Wave 1 (all parallel)
- T01, T02, T03, T04

## Acceptance Criteria
- [x] T01: Refresh All modal shows actual token cost (not hardcoded 5), PT-BR labels say "token(s)" not "ficha(s)"
- [x] T02: Card search works on Render via MYP fallback when Liga is unavailable
- [x] T03: Credit balance refreshes when navigating between card detail pages
- [x] T04: CreditConfirmModal shows clean card art image (no card frame/header/footer)
