/**
 * Determines whether a card is a promo variant based on set code and extras.
 *
 * Heuristic:
 * - set_code starting with "p" and length >= 4 (e.g. "pone", "pltr", "pmkm")
 *   follows Liga Magic's p{base_set} convention for promo sets.
 *   Short set codes like "pip" (3 chars) are real sets, not promo prefixes.
 * - extras field containing "promo" (case-insensitive)
 */
export function isPromoCard(
  setCode: string | null | undefined,
  extras: string | null | undefined,
): boolean {
  if (
    setCode &&
    setCode.length >= 4 &&
    setCode.charAt(0).toLowerCase() === "p"
  ) {
    return true;
  }

  if (extras && extras.toLowerCase().includes("promo")) {
    return true;
  }

  return false;
}
