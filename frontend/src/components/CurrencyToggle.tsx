import { useCurrency } from "../hooks/useCurrency";
import type { CurrencyCode } from "../contexts/CurrencyContext";

export function CurrencyToggle() {
  const { currency, setCurrency } = useCurrency();

  const options: { code: CurrencyCode; label: string }[] = [
    { code: "BRL", label: "BRL" },
    { code: "USD", label: "USD" },
  ];

  return (
    <div
      className="flex rounded-lg overflow-hidden border border-slate-600"
      role="group"
      aria-label="Currency selector"
      data-testid="currency-toggle"
    >
      {options.map((opt) => (
        <button
          key={opt.code}
          onClick={() => setCurrency(opt.code)}
          className={`px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
            currency === opt.code
              ? "bg-cyan-600 text-white"
              : "bg-slate-700 text-slate-300 hover:bg-slate-600"
          }`}
          aria-pressed={currency === opt.code}
          data-testid={`currency-btn-${opt.code}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
