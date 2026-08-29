import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

interface SelectableCardTileProps {
  /** The card's id for selection */
  cardId: number;
  /** Whether selection mode is active */
  isSelectable: boolean;
  /** Whether this card is currently selected */
  isSelected: boolean;
  /** Toggle selection for this card */
  onToggle: (id: number) => void;
  /** The original card tile to wrap */
  children: ReactNode;
}

export function SelectableCardTile({
  cardId,
  isSelectable,
  isSelected,
  onToggle,
  children,
}: SelectableCardTileProps) {
  const { t } = useTranslation();

  if (!isSelectable) {
    return <>{children}</>;
  }

  return (
    <div
      className={`relative rounded-lg transition-all ${
        isSelected
          ? "ring-2 ring-cyan-400 ring-offset-1 ring-offset-slate-900"
          : ""
      }`}
      data-testid={`selectable-card-${cardId}`}
    >
      {/* Checkbox overlay */}
      <button
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onToggle(cardId);
        }}
        className={`absolute top-2 left-2 z-20 w-6 h-6 rounded border-2 flex items-center justify-center transition-colors cursor-pointer ${
          isSelected
            ? "bg-cyan-500 border-cyan-400 text-white"
            : "bg-slate-900/70 border-slate-400 hover:border-cyan-400 text-transparent"
        }`}
        aria-label={isSelected ? t("bulk.deselectAll") : t("bulk.select")}
        data-testid={`select-checkbox-${cardId}`}
      >
        {isSelected && (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )}
      </button>
      {children}
    </div>
  );
}
