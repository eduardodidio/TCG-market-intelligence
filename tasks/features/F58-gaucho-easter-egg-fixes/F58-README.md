# F58 — Gaucho Easter Egg Fixes

**Status:** done
**Priority:** low
**Depends on:** none (fully independent)

## Summary

Fix a typo in the gaucho i18n phrase and increase the auto-dismiss
duration for the final dialog response.

## Tasks

| Task | Wave | Description |
|------|------|-------------|
| F58-T01 | 0 | Fix i18n typo + extend dismiss duration |

## Wave Plan

- **Wave 0**: Single task, both changes are trivial and in the same area.

## Acceptance Criteria

1. PT-BR collection message reads "Tchê, tá o luxo do gaúcho esta coleção?"
   (without "que")
2. Dialog reply auto-dismiss takes 4500ms (was 2500ms, +2s)
3. No regression in other gaucho dialogues
