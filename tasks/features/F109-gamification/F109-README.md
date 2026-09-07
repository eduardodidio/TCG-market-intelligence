# F109 — Gamification & Engagement

## Summary

Achievement system that rewards users for key milestones: adding cards,
creating decks, completing scans, setting alerts, claiming bonuses, and
completing sets. Includes backend persistence, REST API, a dedicated
achievements page, and celebratory toast notifications.

## What was delivered

### Backend (T01)

- **AchievementRow** model in `src/database/models.py` — stores unlocked
  achievements per user with `(user_id, achievement_key)` unique constraint
  and FK cascade to users.
- **Achievement service** at `src/services/achievements.py`:
  - 11 hardcoded achievement definitions (not in DB)
  - `check_achievements(user_id, repo)` — lightweight stat queries, INSERT
    OR IGNORE for idempotency, returns newly unlocked keys
  - `grant_set_master(user_id, repo)` — callable from set-completion endpoint
  - `get_user_achievements(user_id, repo)` — returns all definitions with
    unlock status
  - Graceful handling of optional models (PriceAlertRow)
- **API router** at `src/api/routers/achievements.py`:
  - `GET /api/v1/achievements` — list all with unlock status (auth required)
  - `POST /api/v1/achievements/check` — trigger check, returns newly unlocked
  - Language-aware: returns title/description in user's preferred_language

### Frontend (T02, T03, T04)

- **AchievementToast** component — gold/amber slide-in notification with
  icon, title, description, auto-dismiss (5s), progress bar animation
- **useAchievementNotifier** hook — calls check endpoint, queues toasts for
  newly unlocked achievements
- **AchievementsPage** at `/achievements` — responsive grid (2/3/4 cols),
  progress bar, unlocked vs locked states (grayscale + "?" icon)
- **Nav link** added to primary sidebar (requires auth)
- **i18n** — all 11 achievement keys in both `en.json` and `pt-BR.json`,
  plus UI keys (pageTitle, progress, unlocked, locked, unlockedAt, toastTitle)

## Achievement definitions

| Key             | EN Title          | Icon       | Condition                    |
|-----------------|-------------------|------------|------------------------------|
| first_card      | First Card        | card       | 1+ card in collection        |
| deck_builder    | Deck Builder      | deck       | 1+ deck created              |
| scanner         | Scanner           | scan       | 1+ completed scan            |
| collector_10    | Collector         | collection | 10+ unique cards             |
| collector_50    | Avid Collector    | collection | 50+ unique cards             |
| collector_100   | Serious Collector | collection | 100+ unique cards            |
| collector_500   | Master Collector  | collection | 500+ unique cards            |
| set_master      | Set Master        | trophy     | 100% set completion          |
| price_watcher   | Price Watcher     | alert      | 1+ price alert               |
| treasure_hunter | Treasure Hunter   | treasure   | 5+ bonus claims              |
| early_adopter   | Early Adopter     | star       | Account before 2027-01-01    |

## Files created/modified

### New files
- `src/services/achievements.py`
- `src/api/routers/achievements.py`
- `frontend/src/api/achievements.ts`
- `frontend/src/types/achievements.ts`
- `frontend/src/components/AchievementToast.tsx`
- `frontend/src/hooks/useAchievementNotifier.ts`
- `frontend/src/pages/AchievementsPage.tsx`
- `tests/services/test_achievements.py`
- `tests/api/test_achievements_router.py`
- `frontend/src/components/__tests__/AchievementToast.test.tsx`
- `frontend/src/hooks/__tests__/useAchievementNotifier.test.ts`
- `frontend/src/pages/__tests__/AchievementsPage.test.tsx`
- `tasks/features/F109-gamification/F109-README.md`

### Modified files
- `src/database/models.py` — added AchievementRow
- `src/database/repository.py` — import AchievementRow for create_all
- `src/api/app.py` — registered achievements router
- `frontend/src/App.tsx` — lazy import + /achievements route
- `frontend/src/components/Layout.tsx` — nav link
- `frontend/src/i18n/locales/en.json` — nav + achievements keys
- `frontend/src/i18n/locales/pt-BR.json` — nav + achievements keys

## Test counts
- Backend: 19 tests (service + router)
- Frontend: 17 tests (toast + hook + page)
