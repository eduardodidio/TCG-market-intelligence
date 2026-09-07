export interface AchievementItem {
  key: string;
  title: string;
  description: string;
  icon: string;
  unlocked: boolean;
  unlocked_at: string | null;
}

export interface AchievementCheckResponse {
  newly_unlocked: string[];
}
