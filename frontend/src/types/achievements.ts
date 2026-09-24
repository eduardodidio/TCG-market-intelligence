export type AchievementTier =
  | "common"
  | "uncommon"
  | "rare"
  | "mythic"
  | "legendary";

export interface AchievementItem {
  key: string;
  title: string;
  description: string;
  icon: string;
  unlocked: boolean;
  unlocked_at: string | null;
  reward: number;
  tier: AchievementTier | null;
  reward_credited: boolean;
}

export interface AchievementReward {
  key: string;
  amount: number;
  tier: AchievementTier | null;
}

export interface AchievementCheckResponse {
  newly_unlocked: string[];
  rewards?: AchievementReward[];
  total_reward?: number;
  backfilled?: number;
  balance?: number;
}
