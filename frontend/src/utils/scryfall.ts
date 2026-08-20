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
