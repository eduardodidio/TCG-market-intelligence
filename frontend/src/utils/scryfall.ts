import { mapToScryfallSetCode } from "./setCodeMap";

/**
 * Build a Scryfall image URL for a card.
 * Uses the redirect endpoint — browser follows 302 to CDN.
 * Applies MYP variant set code mapping before building the URL.
 */
export function scryfallImageUrl(
  setCode: string,
  collectorNumber: string,
  version: "small" | "normal" | "large" = "normal",
): string {
  const mapped = mapToScryfallSetCode(setCode);
  return `https://api.scryfall.com/cards/${mapped}/${collectorNumber}?format=image&version=${version}`;
}

/**
 * Build a Scryfall image URL by exact card name (fallback when set/number fails).
 */
export function scryfallImageByName(
  name: string,
  version: "small" | "normal" | "large" = "normal",
): string {
  return `https://api.scryfall.com/cards/named?exact=${encodeURIComponent(name)}&format=image&version=${version}`;
}

/**
 * Build a Scryfall set icon SVG URL.
 * Applies MYP variant set code mapping before building the URL.
 */
export function scryfallSetIconUrl(setCode: string): string {
  const mapped = mapToScryfallSetCode(setCode);
  return `https://svgs.scryfall.io/sets/${mapped}.svg`;
}
