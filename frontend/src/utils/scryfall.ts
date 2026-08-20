/**
 * Build a Scryfall image URL for a card.
 * Uses the redirect endpoint — browser follows 302 to CDN.
 */
export function scryfallImageUrl(
  setCode: string,
  collectorNumber: string,
  version: "small" | "normal" | "large" = "normal",
): string {
  return `https://api.scryfall.com/cards/${setCode.toLowerCase()}/${collectorNumber}?format=image&version=${version}`;
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
