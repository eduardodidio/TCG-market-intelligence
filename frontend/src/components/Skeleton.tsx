/**
 * Skeleton loading components -- pulsing placeholder blocks
 * for contextual loading states across all pages.
 */

const pulseBase = "animate-pulse bg-slate-700 rounded";

export function SkeletonKpi() {
  return (
    <div data-testid="skeleton-kpi" className="rounded-lg bg-white/5 backdrop-blur-sm border border-white/10 p-6">
      <div className={`${pulseBase} h-4 w-24 mb-3`} />
      <div className={`${pulseBase} h-8 w-32 mb-2`} />
      <div className={`${pulseBase} h-3 w-20`} />
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div data-testid="skeleton-card" className="rounded-lg bg-slate-800 border border-slate-600 p-4">
      <div className={`${pulseBase} h-40 w-full mb-3`} />
      <div className={`${pulseBase} h-4 w-3/4 mb-2`} />
      <div className={`${pulseBase} h-4 w-1/2`} />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div data-testid="skeleton-table" className="rounded-lg bg-slate-800 border border-slate-600 overflow-hidden">
      <div className="bg-slate-700/50 px-6 py-4">
        <div className={`${pulseBase} h-5 w-32`} />
      </div>
      <div className="px-6 py-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 py-3 border-b border-slate-600/50 last:border-0">
            <div className={`${pulseBase} h-4 w-6`} />
            <div className={`${pulseBase} h-4 w-40`} />
            <div className={`${pulseBase} h-4 w-20 ml-auto`} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonChartPanel() {
  return (
    <div data-testid="skeleton-chart" className="rounded-lg bg-slate-800 border border-slate-600 p-6">
      {/* Period selector placeholder */}
      <div className="flex gap-2 mb-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className={`${pulseBase} h-8 w-12`} />
        ))}
      </div>
      {/* Chart area placeholder */}
      <div className={`${pulseBase} h-72 w-full`} />
    </div>
  );
}

export function SkeletonInfoPanel() {
  return (
    <div data-testid="skeleton-info" className="rounded-lg bg-slate-800 border border-slate-600 p-6">
      <div className={`${pulseBase} h-7 w-2/3 mb-2`} />
      <div className={`${pulseBase} h-4 w-1/3 mb-4`} />
      <div className="flex gap-2 mb-4">
        <div className={`${pulseBase} h-6 w-12`} />
        <div className={`${pulseBase} h-6 w-10`} />
      </div>
      <div className={`${pulseBase} h-6 w-24 mb-6`} />
      <div className={`${pulseBase} h-4 w-20 mb-1`} />
      <div className={`${pulseBase} h-10 w-32 mb-6`} />
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className={`${pulseBase} h-3 w-20 mb-1`} />
          <div className={`${pulseBase} h-4 w-24`} />
        </div>
        <div>
          <div className={`${pulseBase} h-3 w-20 mb-1`} />
          <div className={`${pulseBase} h-4 w-24`} />
        </div>
      </div>
    </div>
  );
}
