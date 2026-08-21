import { useTranslation } from "react-i18next";
import { useCurrency } from "../hooks/useCurrency";
import type { CurrencyCode } from "../contexts/CurrencyContext";
import rsFlag from "../assets/rs-flag.svg";
import brFlag from "../assets/br-flag.svg";
import usFlag from "../assets/us-flag.svg";

export function CurrencyToggle() {
  const { t } = useTranslation();
  const { currency, setCurrency } = useCurrency();

  const options: { code: CurrencyCode; label: string; icon?: string }[] = [
    { code: "BRL", label: "BRL", icon: brFlag },
    { code: "USD", label: "USD", icon: usFlag },
    { code: "PILA", label: "PILA", icon: rsFlag },
  ];

  return (
    <div
      className="flex rounded-md overflow-hidden border border-slate-500"
      role="group"
      aria-label={t("currency.selector")}
      data-testid="currency-toggle"
    >
      {options.map((opt) => (
        <button
          key={opt.code}
          onClick={() => setCurrency(opt.code)}
          className={`px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 flex items-center gap-1 ${
            currency === opt.code
              ? "bg-indigo-500 text-white"
              : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
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
