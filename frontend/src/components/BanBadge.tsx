import { useTranslation } from "react-i18next";

interface BanBadgeProps {
  status: "banned" | "restricted";
  recentlyChanged?: boolean;
}

export function BanBadge({ status, recentlyChanged = false }: BanBadgeProps) {
  const { t } = useTranslation();

  const isBanned = status === "banned";
  const colorClasses = isBanned
    ? "bg-red-600 text-white"
    : "bg-yellow-600 text-white";
  const label = isBanned
    ? t("banEngine.badgeBanned")
    : t("banEngine.badgeRestricted");

  return (
    <span
      data-testid={`ban-badge-${status}`}
      className={`inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded-full ${colorClasses} ${
        recentlyChanged ? "animate-pulse ring-2 ring-red-400/50" : ""
      }`}
    >
      {label}
    </span>
  );
}
