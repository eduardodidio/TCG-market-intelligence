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
        <div className="mb-4 text-tcg-dimmed" data-testid="empty-state-icon">
          {icon}
        </div>
      )}
      <p className="text-lg text-tcg-muted">{message}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 rounded-tcg-md bg-tcg-primary px-4 py-2 text-sm font-medium text-white hover:bg-tcg-primary-hover transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tcg-secondary"
          data-testid="empty-state-action"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
