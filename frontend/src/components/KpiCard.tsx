import type { ReactNode } from "react";

interface KpiCardProps {
  title: string;
  value: ReactNode;
  subtitle?: ReactNode;
  icon?: ReactNode;
  extra?: ReactNode;
}

export function KpiCard({ title, value, subtitle, icon, extra }: KpiCardProps) {
  return (
    <div
      data-testid="kpi-card"
      className="rounded-lg bg-white/5 backdrop-blur-sm border border-white/10 p-6
        hover:border-indigo-500/30 transition-all duration-200 shadow-sm"
    >
      <div className="flex items-start justify-between">
        <p className="text-sm text-slate-400">{title}</p>
        {icon && <span className="text-cyan-400">{icon}</span>}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <p className="text-2xl font-bold text-white">{value}</p>
        {extra}
      </div>
      {subtitle && (
        <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
      )}
    </div>
  );
}
