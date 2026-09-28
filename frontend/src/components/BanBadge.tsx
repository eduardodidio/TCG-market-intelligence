import { useTranslation } from "react-i18next";

interface BanBadgeProps {
  status: "banned" | "restricted";
  recentlyChanged?: boolean;
  formats?: Array<{ format: string; status: string }>;
}

export function BanBadge({ status, recentlyChanged = false, formats }: BanBadgeProps) {
  const { t } = useTranslation();

  const isBanned = status === "banned";
  const colorClasses = isBanned
    ? "bg-red-600 text-white"
    : "bg-yellow-600 text-white";
  const label = isBanned
    ? t("banEngine.badgeBanned")
    : t("banEngine.badgeRestricted");

  const tooltipText = formats?.length
    ? [
        t("banEngine.tooltipHeader"),
        ...formats.map((f) => {
          const formatName = f.format.charAt(0).toUpperCase() + f.format.slice(1);
          const statusLabel = f.status === "banned"
            ? t("banEngine.badgeBanned")
            : t("banEngine.badgeRestricted");
          return `${formatName}: ${statusLabel}`;
        }),
      ].join("\n")
    : undefined;

  return (
    <span
      data-testid={`ban-badge-${status}`}
      title={tooltipText}
      className={`inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded-full ${colorClasses} ${
        recentlyChanged ? "animate-pulse ring-2 ring-red-400/50" : ""
      }`}
    >
      {label}
    </span>
  );
}
