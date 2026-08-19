import type { ReactNode } from "react";

interface EmptyStateProps {
  message: string;
  icon?: ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ message, icon, action }: EmptyStateProps) {
  return (
    <div
      data-testid="empty-state"
      className="flex flex-col items-center justify-center py-12 text-center"
    >
      {icon && (
        <div className="mb-4 text-slate-500" data-testid="empty-state-icon">
          {icon}
        </div>
      )}
      <p className="text-lg text-slate-400">{message}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 rounded-md bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          data-testid="empty-state-action"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
