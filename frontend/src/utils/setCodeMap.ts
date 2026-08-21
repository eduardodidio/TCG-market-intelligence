/**
 * Mapping utility for MYP variant set codes to Scryfall-compatible set codes.
 *
 * MYP uses prefixed set codes for variant printings (borderless, extended art,
 * showcase, etc.). This module translates them to standard Scryfall set codes
 * so that image URLs and API lookups work correctly.
 */

/** Static lookup table for all known MYP variant codes. */
const KNOWN_VARIANTS: Record<string, string> = {
  // Borderless (bl*)
  bldmr: "dmr",
  blfdn: "fdn",
  bl2x2: "2x2",
  bltr: "ltr",
  blltr: "ltr",
  blb: "blb", // Bloomburrow — "blb" IS the standard code
  // Extended Art (ex*)
  exdmu: "dmu",
  // Extended Art alt (ea*)
  eafic: "fic",
  eahoc: "hoc",
  // Showcase Ring (sr*)
  srltr: "ltr",
  // Showcase (sk*)
  skmh2: "mh2",
  // Full-art / Etched (fe*)
  feclb: "clb",
  fesnc: "snc",
  // Special/Misc (sm*)
  smbro: "bro",
  // Commander Borderless (cb*)
  cbznr: "znr",
  // Commander variant (c*)
  cthb: "thb",
  // Bundle/Box promo (bb*)
  bbfdn: "fdn",
  // Draft/Hobby (dh*)
  dhhob: "hob",
  // Draft variant (df*)
  dftdm: "tdm",
  dft: "dft",
  // Gift variant (gf*)
  gftdm: "tdm",
  // Promo/Prerelease (pl*)
  pl24: "pl24",
  pltr: "ltr",
  // Vault/Visual (vv*)
  vvow: "vow",
  // Special Commander (sc*)
  schob: "hob",
  schoc: "hoc",
  sc9: "sc9",
  // Art Series (ash*)
  ashob: "hob",
};

/** Prefixes to strip as a heuristic for unknown codes. */
const STRIP_PREFIXES = [
  "bl", "ex", "ea", "sr", "sk", "fe", "sm", "cb", "bb", "dh",
  "df", "gf", "pl", "vv", "sc", "ash",
];

/** Secret Lair pattern: "sld" followed by digits. */
const SECRET_LAIR_RE = /^sld\d+$/i;

/**
 * Translate an MYP variant set code to the standard Scryfall set code.
 *
 * @param mypSetCode - The set code as it appears in MYP data (e.g. "bldmr").
 * @returns The Scryfall-compatible set code (e.g. "dmr").
 *          Returns the input unchanged (lowercased) if no mapping is found.
 */
export function mapToScryfallSetCode(mypSetCode: string): string {
  const code = mypSetCode.trim().toLowerCase();

  // 1. Check static lookup table
  if (code in KNOWN_VARIANTS) {
    return KNOWN_VARIANTS[code];
  }

  // 2. Secret Lair: sld followed by digits -> "sld"
  if (SECRET_LAIR_RE.test(code)) {
    return "sld";
  }

  // 3. Prefix-stripping heuristic for unknown codes
  for (const prefix of STRIP_PREFIXES) {
    if (code.startsWith(prefix) && code.length > prefix.length) {
      const remainder = code.slice(prefix.length);
      // Only strip if remainder looks like a set code (2-5 chars, alphanumeric)
      if (remainder.length >= 2 && remainder.length <= 5 && /^[a-z0-9]+$/.test(remainder)) {
        return remainder;
      }
    }
  }

  // 4. Return as-is (lowercased)
  return code;
}
