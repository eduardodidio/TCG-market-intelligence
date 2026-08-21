import { useContext } from "react";
import { CurrencyContext, type CurrencyContextValue } from "../contexts/CurrencyContext";

export function useCurrency(): CurrencyContextValue {
  return useContext(CurrencyContext);
}
