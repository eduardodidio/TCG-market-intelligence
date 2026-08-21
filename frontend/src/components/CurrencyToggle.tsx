import { useCurrency } from "../hooks/useCurrency";
import type { CurrencyCode } from "../contexts/CurrencyContext";
import rsFlag from "../assets/rs-flag.svg";

export function CurrencyToggle() {
  const { currency, setCurrency } = useCurrency();

  const options: { code: CurrencyCode; label: string; icon?: string }[] = [
    { code: "BRL", label: "BRL" },
    { code: "USD", label: "USD" },
    { code: "PILA", label: "Pila", icon: rsFlag },
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
          className={`px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 flex items-center gap-1 ${
            currency === opt.code
              ? "bg-cyan-600 text-white"
              : "bg-slate-700 text-slate-300 hover:bg-slate-600"
          }`}
          aria-pressed={currency === opt.code}
          data-testid={`currency-btn-${opt.code}`}
        >
          {opt.icon && (
            <img
              src={opt.icon}
              alt=""
              width={14}
              height={10}
              className="inline-block"
            />
          )}
          {opt.label}
        </button>
      ))}
    </div>
  );
}
