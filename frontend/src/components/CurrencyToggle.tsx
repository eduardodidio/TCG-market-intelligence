import { useTranslation } from "react-i18next";
import { useCurrency } from "../hooks/useCurrency";
import type { CurrencyCode } from "../contexts/CurrencyContext";
import rsFlag from "../assets/rs-flag.svg";

export function CurrencyToggle() {
  const { t } = useTranslation();
  const { currency, setCurrency } = useCurrency();

  const options: { code: CurrencyCode; label: string; icon?: string }[] = [
    { code: "BRL", label: "BRL" },
    { code: "USD", label: "USD" },
    { code: "PILA", label: "Pila", icon: rsFlag },
  ];

  return (
    <div
      className="flex rounded-tcg-md overflow-hidden border border-tcg-ring"
      role="group"
      aria-label={t("currency.selector")}
      data-testid="currency-toggle"
    >
      {options.map((opt) => (
        <button
          key={opt.code}
          onClick={() => setCurrency(opt.code)}
          className={`px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tcg-secondary flex items-center gap-1 ${
            currency === opt.code
              ? "bg-tcg-primary text-white"
              : "bg-tcg-card text-tcg-muted hover:bg-tcg-card-alt hover:text-white"
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
