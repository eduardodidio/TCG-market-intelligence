import { useTranslation } from "react-i18next";

interface QuantityStepperProps {
  value: number;
  onChange: (newValue: number) => void;
  min?: number;
  compact?: boolean;
}

/**
 * Quantity stepper with +/- buttons.
 * Compact mode: smaller, no label (for tile overlay).
 */
export function QuantityStepper({ value, onChange, min = 1, compact = false }: QuantityStepperProps) {
  const { t } = useTranslation();

  const handleDecrement = () => {
    if (value > min) onChange(value - 1);
  };

  const handleIncrement = () => {
    onChange(value + 1);
  };

  const btnBase = compact
    ? "w-6 h-6 text-xs font-bold rounded"
    : "w-8 h-8 text-sm font-bold rounded-md";

  return (
    <div
      className="flex items-center gap-1"
      data-testid="quantity-stepper"
    >
      {!compact && (
        <span className="text-xs text-slate-400 mr-1">{t("inlineEdit.quantity")}</span>
      )}
      <button
        onClick={handleDecrement}
        disabled={value <= min}
        data-testid="qty-minus"
        title={t("inlineEdit.decrease")}
        className={`${btnBase} bg-slate-700 border border-slate-600 text-white hover:bg-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400`}
      >
        -
      </button>
      <span
        className={`${compact ? "text-sm min-w-[1.5rem]" : "text-sm min-w-[2rem]"} text-center font-bold text-white`}
        data-testid="qty-value"
      >
        {value}
      </span>
      <button
        onClick={handleIncrement}
        data-testid="qty-plus"
        title={t("inlineEdit.increase")}
        className={`${btnBase} bg-slate-700 border border-slate-600 text-white hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400`}
      >
        +
      </button>
    </div>
  );
}
