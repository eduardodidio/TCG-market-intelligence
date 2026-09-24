# 04 — Frontend

## Current state (verified)

- `AchievementToast.tsx` and `useAchievementNotifier.ts` exist with tests but are
  **not mounted anywhere** (`grep -rn useAchievementNotifier frontend/src` finds
  only the hook and its test). Toasts therefore never show today.
- `TreasureBalance.tsx` uses `useCredits()` (local state, fetch on mount,
  `refetch` exposed); nothing tells it to refresh when credits change elsewhere.
- i18n: `frontend/src/i18n/locales/{en,pt-BR}.json`, section `"achievements"`
  (keys `pageTitle`, `progress`, `unlocked`, `locked`, `unlockedAt`, `toastTitle`, ...).
- Tests: Vitest + React Testing Library, `cd frontend && npm test`;
  test files under `__tests__/` next to the source.

## Types (`frontend/src/types/achievements.ts`)

```ts
export type AchievementTier = "common" | "uncommon" | "rare" | "mythic" | "legendary";
export interface AchievementItem {
  key: string; title: string; description: string; icon: string;
  unlocked: boolean; unlocked_at: string | null;
  reward: number; tier: AchievementTier | null; reward_credited: boolean;
}
export interface AchievementReward { key: string; amount: number; tier: AchievementTier | null; }
export interface AchievementCheckResponse {
  newly_unlocked: string[];
  rewards?: AchievementReward[]; total_reward?: number; backfilled?: number; balance?: number;
}
```
(`rewards`… optional so the UI tolerates an older backend.)

## Credits refresh event (new `frontend/src/utils/creditsEvents.ts`)

```ts
export const CREDITS_CHANGED_EVENT = "credits:changed";
export function notifyCreditsChanged(): void { window.dispatchEvent(new Event(CREDITS_CHANGED_EVENT)); }
```
`useCredits.ts`: in a `useEffect`, `window.addEventListener(CREDITS_CHANGED_EVENT, fetchBalance)`
with cleanup.

## i18n keys (both locales, inside `"achievements"`)

| key                 | en                                   | pt-BR                                    |
|---------------------|--------------------------------------|------------------------------------------|
| `reward`            | `+{{amount}} Treasures`              | `+{{amount}} Tesouros`                   |
| `rewardEarned`      | `Earned`                             | `Recebido`                               |
| `treasureProgress`  | `{{earned}} / {{total}} Treasures earned` | `{{earned}} / {{total}} Tesouros ganhos` |
| `toastReward`       | `+{{amount}} Treasures added!`       | `+{{amount}} Tesouros adicionados!`      |
| `backfillReward`    | `+{{amount}} Treasures from past achievements` | `+{{amount}} Tesouros de conquistas anteriores` |
| `tier.common` … `tier.legendary` | Common/Uncommon/Rare/Mythic/Legendary | Comum/Incomum/Rara/Mítica/Lendária |

## AchievementsPage

- Each card shows a reward chip (`data-testid="achievement-reward-<key>"`) with
  `t("achievements.reward", {amount})` + tier label, visible for locked AND
  unlocked (locked = motivation, muted color); unlocked+credited shows a check /
  `rewardEarned`.
- Tier colour accent on chip: common slate, uncommon emerald, rare sky, mythic
  orange, legendary amber (Tailwind classes, dark theme like the rest of the page).
- Under the progress bar: `treasureProgress` (earned = sum reward of unlocked,
  total = sum of all rewards), `data-testid="achievements-treasure-progress"`.

## Toast + notifier

- `AchievementToast` gets optional `reward?: number`; when > 0 renders
  `t("achievements.toastReward", {amount})` (`data-testid="achievement-toast-reward"`).
  The component currently doesn't use i18n — add `useTranslation`.
- `useAchievementNotifier`: map `resp.data.rewards` by key into each toast's
  `reward`; if `backfilled > 0` push one extra toast (icon `treasure`,
  title `t("achievements.toastTitle")`, description
  `t("achievements.backfillReward", {amount: backfilled})`); if
  `total_reward + backfilled > 0` call `notifyCreditsChanged()`.
  The early return when `newly_unlocked.length === 0` must still handle `backfilled`.
- New `frontend/src/components/AchievementNotifierHost.tsx`: uses the hook,
  calls `checkAchievements()` on mount and on `location.pathname` change,
  throttled to at most once per 30 s (useRef timestamp); renders the stacked
  toasts (offset each by index, e.g. `style={{ top: 16 + i * 80 }}` or a
  wrapper flex column). Renders nothing (and never calls the API) when
  `!isAuthenticated` or `user?.role === "guest"` — use
  `const { user, isAuthenticated } = useAuth()` from `../hooks/useAuth` (same as
  `Layout.tsx` line ~121).
  Mounting inside `Layout.tsx` is done by T09 only.
