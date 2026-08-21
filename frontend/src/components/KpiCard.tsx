import type { ReactNode } from "react";

interface KpiCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon?: ReactNode;
}

export function KpiCard({ title, value, subtitle, icon }: KpiCardProps) {
  return (
    <div
      data-testid="kpi-card"
      className="rounded-tcg-lg bg-white/5 backdrop-blur-sm border border-white/10 p-6
        hover:border-tcg-primary/30 transition-all duration-200 shadow-tcg-sm"
    >
      <div className="flex items-start justify-between">
        <p className="text-sm text-tcg-muted">{title}</p>
        {icon && <span className="text-tcg-secondary">{icon}</span>}
      </div>
      <p className="mt-2 text-2xl font-bold text-white">{value}</p>
      {subtitle && (
        <p className="mt-1 text-xs text-tcg-dimmed">{subtitle}</p>
      )}
    </div>
  );
}
