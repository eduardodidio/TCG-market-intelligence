import { useTranslation } from "react-i18next";

export interface CostBadgeProps {
  cost: number;
  balance: number | null;
}

export function CostBadge({ cost, balance }: CostBadgeProps) {
  const { t } = useTranslation();
  const insufficient = balance !== null && balance < cost;

  return (
    <span
      className={`text-xs ml-1 ${insufficient ? "text-red-400" : "text-slate-400"}`}
      data-testid="cost-badge"
    >
      {t("credits.costBadge", { cost })}
    </span>
  );
}
