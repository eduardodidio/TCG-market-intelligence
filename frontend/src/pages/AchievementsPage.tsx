import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchAchievements } from "../api/achievements";
import { Breadcrumb } from "../components/Breadcrumb";
import { LoadingSpinner } from "../components/LoadingSpinner";
import type { AchievementItem } from "../types/achievements";

const ICON_MAP: Record<string, string> = {
  card: "M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z",
  deck: "M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z",
  scan: "M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z",
  collection:
    "M20 2H4c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM8 20H4v-4h4v4zm0-6H4v-4h4v4zm0-6H4V4h4v4zm6 12h-4v-4h4v4zm0-6h-4v-4h4v4zm0-6h-4V4h4v4zm6 12h-4v-4h4v4zm0-6h-4v-4h4v4zm0-6h-4V4h4v4z",
  trophy:
    "M19 5h-2V3H7v2H5c-1.1 0-2 .9-2 2v1c0 2.55 1.92 4.63 4.39 4.94.63 1.5 1.98 2.63 3.61 2.96V19H7v2h10v-2h-4v-3.1c1.63-.33 2.98-1.46 3.61-2.96C19.08 12.63 21 10.55 21 8V7c0-1.1-.9-2-2-2z",
  alert:
    "M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z",
  treasure: "M12 2L6 8h12L12 2zm0 4L9.5 8h5L12 6zm-6 4v8h12v-8H6zm2 2h8v4H8v-4z",
  star: "M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z",
};

function AchievementIcon({
  icon,
  unlocked,
}: {
  icon: string;
  unlocked: boolean;
}) {
  const path = ICON_MAP[icon] || ICON_MAP.star;
  return (
    <svg
      className={`w-10 h-10 ${unlocked ? "text-amber-400" : "text-slate-600"}`}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}

function formatDate(isoDate: string): string {
  try {
    return new Date(isoDate).toLocaleDateString();
  } catch {
    return isoDate;
  }
}

export function AchievementsPage() {
  const { t } = useTranslation();
  const [achievements, setAchievements] = useState<AchievementItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchAchievements()
      .then((resp) => {
        if (cancelled) return;
        if (resp.data) {
          setAchievements(resp.data);
        } else if (resp.errors?.length > 0) {
          setError(resp.errors[0].message);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Unknown error");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const unlockedCount = achievements.filter((a) => a.unlocked).length;
  const totalCount = achievements.length;

  if (loading) {
    return <LoadingSpinner message={t("common.loading")} />;
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div data-testid="achievements-page">
      <Breadcrumb
        items={[
          { label: t("nav.dashboard"), to: "/" },
          { label: t("achievements.pageTitle") },
        ]}
      />

      <h1 className="text-2xl font-bold text-white mb-4">
        {t("achievements.pageTitle")}
      </h1>

      {/* Progress bar */}
      <div className="mb-6" data-testid="achievements-progress">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-slate-400">
            {t("achievements.progress", {
              unlocked: unlockedCount,
              total: totalCount,
            })}
          </span>
          <span className="text-sm font-medium text-amber-400">
            {totalCount > 0
              ? `${Math.round((unlockedCount / totalCount) * 100)}%`
              : "0%"}
          </span>
        </div>
        <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-amber-500 to-yellow-400 rounded-full transition-all duration-500"
            style={{
              width: `${totalCount > 0 ? (unlockedCount / totalCount) * 100 : 0}%`,
            }}
            data-testid="achievements-progress-bar"
          />
        </div>
      </div>

      {/* Achievement grid */}
      <div
        className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
        data-testid="achievements-grid"
      >
        {achievements.map((achievement) => (
          <div
            key={achievement.key}
            className={`
              rounded-lg border p-4 transition-all duration-200
              ${
                achievement.unlocked
                  ? "bg-slate-800 border-amber-500/30 shadow-sm shadow-amber-500/10"
                  : "bg-slate-800/50 border-slate-700 opacity-60 grayscale"
              }
            `}
            data-testid={`achievement-card-${achievement.key}`}
          >
            <div className="flex flex-col items-center text-center gap-2">
              {achievement.unlocked ? (
                <AchievementIcon icon={achievement.icon} unlocked={true} />
              ) : (
                <div className="w-10 h-10 flex items-center justify-center text-slate-600 text-2xl font-bold">
                  ?
                </div>
              )}
              <h3
                className={`text-sm font-semibold ${
                  achievement.unlocked ? "text-white" : "text-slate-500"
                }`}
              >
                {achievement.title}
              </h3>
              {achievement.unlocked ? (
                <>
                  <p className="text-xs text-slate-400">
                    {achievement.description}
                  </p>
                  {achievement.unlocked_at && (
                    <p className="text-xs text-amber-400/60 mt-1">
                      {t("achievements.unlockedAt", {
                        date: formatDate(achievement.unlocked_at),
                      })}
                    </p>
                  )}
                </>
              ) : (
                <p className="text-xs text-slate-600">
                  {t("achievements.locked")}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
