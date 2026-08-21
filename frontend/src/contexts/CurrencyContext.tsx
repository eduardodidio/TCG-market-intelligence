import { createContext, useCallback, useEffect, useState, type ReactNode } from "react";

export type CurrencyCode = "BRL" | "USD";

export interface CurrencyContextValue {
  currency: CurrencyCode;
  setCurrency: (c: CurrencyCode) => void;
  toggle: () => void;
}

const STORAGE_KEY = "tcg_currency";

function loadCurrency(): CurrencyCode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "USD" || stored === "BRL") return stored;
  } catch {
    // localStorage unavailable (SSR, privacy mode)
  }
  return "BRL";
}

export const CurrencyContext = createContext<CurrencyContextValue>({
  currency: "BRL",
  setCurrency: () => {},
  toggle: () => {},
});

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [currency, setCurrencyState] = useState<CurrencyCode>(loadCurrency);

  const setCurrency = useCallback((c: CurrencyCode) => {
    setCurrencyState(c);
    try {
      localStorage.setItem(STORAGE_KEY, c);
    } catch {
      // ignore
    }
  }, []);

  const toggle = useCallback(() => {
    setCurrency(currency === "BRL" ? "USD" : "BRL");
  }, [currency, setCurrency]);

  // Sync if localStorage changes in another tab
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY && (e.newValue === "BRL" || e.newValue === "USD")) {
        setCurrencyState(e.newValue);
      }
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  return (
    <CurrencyContext.Provider value={{ currency, setCurrency, toggle }}>
      {children}
    </CurrencyContext.Provider>
  );
}
