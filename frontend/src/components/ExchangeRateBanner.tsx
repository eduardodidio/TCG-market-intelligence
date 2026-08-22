import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useCurrency } from "../hooks/useCurrency";
import { fetchCurrentRate, type ExchangeRate } from "../api/exchangeRates";

export function ExchangeRateBanner() {
  const { currency } = useCurrency();
  const { t } = useTranslation();
  const [rate, setRate] = useState<ExchangeRate | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (currency !== "USD") {
      setRate(null);
      setError(false);
      return;
    }

    let cancelled = false;

    async function load() {
      try {
        const res = await fetchCurrentRate();
        if (cancelled) return;
        if (res.data) {
          setRate(res.data);
          setError(false);
        } else {
          setRate(null);
          setError(true);
        }
      } catch {
        if (!cancelled) {
          setRate(null);
          setError(true);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [currency]);

  if (currency !== "USD") return null;

  if (error) {
    return (
      <div
        className="bg-slate-700/50 text-slate-300 text-xs py-1.5 px-4 text-center"
        data-testid="exchange-rate-banner"
      >
        {t("currency.rateUnavailable")}
      </div>
    );
  }

  if (!rate) return null;

  const formattedRate = Number(rate.rate).toFixed(2);

  return (
    <div
      className="bg-slate-700/50 text-slate-300 text-xs py-1.5 px-4 text-center"
      data-testid="exchange-rate-banner"
    >
      {t("currency.exchangeRate", { rate: formattedRate })}
      {" — "}
      {t("currency.rateDate", { date: rate.rate_date })}
    </div>
  );
}
