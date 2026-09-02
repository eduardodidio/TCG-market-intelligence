import type { ReactNode } from "react";

export interface EmptyStateAction {
  label: string;
  onClick: () => void;
  variant?: "primary" | "secondary";
}

interface EmptyStateProps {
  // Existing (kept for backward compat)
  message?: string;
  icon?: ReactNode;
  action?: EmptyStateAction;

  // New props
  title?: string;
  description?: string;
  actions?: EmptyStateAction[];
  compact?: boolean;
}

export function EmptyState({
  message,
  icon,
  action,
  title,
  description,
  actions,
  compact = false,
}: EmptyStateProps) {
  // actions array takes precedence over singular action
  const resolvedActions = actions ?? (action ? [action] : []);

  return (
    <div
      data-testid="empty-state"
      className={`flex flex-col items-center justify-center ${compact ? "py-6" : "py-12"} text-center`}
    >
      {icon && (
        <div className="mb-4 text-slate-500" data-testid="empty-state-icon">
          {icon}
        </div>
      )}

      {title && (
        <h3
          className="text-lg font-bold text-white mb-1"
          data-testid="empty-state-title"
        >
          {title}
        </h3>
      )}

      {description && (
        <p
          className="text-sm text-slate-400 max-w-md mb-2"
          data-testid="empty-state-description"
        >
          {description}
        </p>
      )}

      {/* Legacy message fallback (backward compat) */}
      {!title && !description && message && (
        <p className="text-lg text-slate-400">{message}</p>
      )}

      {resolvedActions.length > 0 && (
        <div className="mt-4 flex items-center gap-3" data-testid="empty-state-actions">
          {resolvedActions.map((a) =>
            a.variant === "secondary" ? (
              <button
                key={a.label}
                onClick={a.onClick}
                className="rounded-md border border-slate-500 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                data-testid="empty-state-action"
              >
                {a.label}
              </button>
            ) : (
              <button
                key={a.label}
                onClick={a.onClick}
                className="rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                data-testid="empty-state-action"
              >
                {a.label}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}
