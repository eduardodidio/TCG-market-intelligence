import { useApi } from "./useApi";
import { fetchValuation } from "../api/collection";
import type { ValuationData } from "../api/collection";

/**
 * Fetch portfolio valuation data (% change, snapshots).
 */
export function useValuation(days: number = 7, currency: string = "BRL") {
  return useApi<ValuationData>(
    () => fetchValuation(days, currency),
    [days, currency],
  );
}
