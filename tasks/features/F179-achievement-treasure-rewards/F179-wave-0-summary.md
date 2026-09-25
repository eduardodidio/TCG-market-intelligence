# F179 — Wave 0 summary

**Status:** completed
**Tasks:** F179-T01, F179-T02, F179-T03
**Generated:** 2026-09-24T18:20:00Z

## Files touched
- `docs/prd/F179-achievement-treasure-rewards.md` (T01: PRD for tiered treasure rewards)
- `docs/adr/0020-achievement-reward-ledger-idempotency.md` (T01: ADR on ledger idempotency)
- `docs/diagrams/F179-architecture.mmd` (T01: component/data-flow diagram)
- `docs/diagrams/F179-journey.mmd` (T01: unlock→reward user journey)
- `src/services/achievement_rewards.py` (T02: tier table 50/100/250/500/1000, achievement→tier mapping, idempotent in-session crediting, backfill helper)
- `tests/services/test_achievement_rewards.py` (T02: 355 lines covering tier mapping, crediting idempotency)
- `frontend/src/types/achievements.ts` (T03: reward/tier/reward_credited fields)
- `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt-BR.json` (T03: achievements reward copy, additive)
- `frontend/src/utils/creditsEvents.ts` + `__tests__/creditsEvents.test.ts` (T03: new credits-refresh pub/sub event)
- `frontend/src/hooks/useCredits.ts` + `__tests__/useCredits.test.ts` (T03: listens for credits-refresh event)

## Decisions
- _none_ — Wave 0 followed the task files as written; no direction changes observed.

## Notes for next Wave
- T01 and T03 task files still show `Status: planned` in their headers even though their deliverables are present on disk — Wave 1 devs/reviewers should not rely solely on the status field; verify by file presence.
- T02 is the only task file marked `Status: done`; `achievement_rewards.py` exports the tier table and crediting function Wave 1's `achievements.py` (T04) must call inside the same DB transaction as the unlock (`rowcount == 1` pattern per README "Patterns").
- `creditsEvents.ts` is a new pub/sub utility — T06/T07 (AchievementsPage, toast) should dispatch/consume it rather than adding a second mechanism.
- i18n edits were additive inside the existing `"achievements"` object as required — safe to keep extending in Wave 1.
