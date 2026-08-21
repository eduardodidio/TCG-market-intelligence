"""Mapping utility for MYP variant set codes to Scryfall-compatible set codes.

MYP uses prefixed set codes for variant printings (borderless, extended art,
showcase, etc.). This module translates them to standard Scryfall set codes
so that image URLs and API lookups work correctly.
"""

from __future__ import annotations

import re

# Static lookup table for all known MYP variant codes.
# Keys are lowercase MYP codes, values are Scryfall base set codes.
_KNOWN_VARIANTS: dict[str, str] = {
    # Borderless (bl*)
    "bldmr": "dmr",
    "blfdn": "fdn",
    "bl2x2": "2x2",
    "bltr": "ltr",  # Note: could be ambiguous, but ltr is the known set
    "blltr": "ltr",
    "blb": "blb",  # Bloomburrow — "blb" IS the standard code, not a prefix
    # Extended Art (ex*)
    "exdmu": "dmu",
    # Extended Art alt (ea*)
    "eafic": "fic",
    "eahoc": "hoc",
    # Showcase Ring (sr*)
    "srltr": "ltr",
    # Showcase (sk*)
    "skmh2": "mh2",
    # Full-art / Etched (fe*)
    "feclb": "clb",
    "fesnc": "snc",
    # Special/Misc (sm*)
    "smbro": "bro",
    # Commander Borderless (cb*)
    "cbznr": "znr",
    # Commander variant (c*)
    "cthb": "thb",
    # Bundle/Box promo (bb*)
    "bbfdn": "fdn",
    # Draft/Hobby (dh*)
    "dhhob": "hob",
    # Draft variant (df*)
    "dftdm": "tdm",
    "dft": "dft",  # Could be a real set code; return as-is
    # Gift variant (gf*)
    "gftdm": "tdm",
    # Promo/Prerelease (pl*)
    "pl24": "pl24",  # Ambiguous — return as-is
    "pltr": "ltr",
    # Vault/Visual (vv*)
    "vvow": "vow",
    # Special Commander (sc*)
    "schob": "hob",
    "schoc": "hoc",
    "sc9": "sc9",  # Ambiguous — return as-is
    # Art Series (ash*)
    "ashob": "hob",
}

# Prefixes to strip as a heuristic for unknown codes.
# Order matters: longer prefixes first to avoid partial matches.
_STRIP_PREFIXES = (
    "bl",
    "ex",
    "ea",
    "sr",
    "sk",
    "fe",
    "sm",
    "cb",
    "bb",
    "dh",
    "df",
    "gf",
    "pl",
    "vv",
    "sc",
    "ash",
)

# Secret Lair pattern: "sld" followed by digits
_SECRET_LAIR_RE = re.compile(r"^sld\d+$", re.IGNORECASE)


def map_to_scryfall_set_code(myp_set_code: str) -> str:
    """Translate an MYP variant set code to the standard Scryfall set code.

    Args:
        myp_set_code: The set code as it appears in MYP data (e.g. "bldmr").

    Returns:
        The Scryfall-compatible set code (e.g. "dmr").
        Returns the input unchanged (lowercased) if no mapping is found.
    """
    code = myp_set_code.strip().lower()

    # 1. Check static lookup table
    if code in _KNOWN_VARIANTS:
        return _KNOWN_VARIANTS[code]

    # 2. Secret Lair: sld followed by digits → "sld"
    if _SECRET_LAIR_RE.match(code):
        return "sld"

    # 3. Prefix-stripping heuristic for unknown codes
    for prefix in _STRIP_PREFIXES:
        if code.startswith(prefix) and len(code) > len(prefix):
            remainder = code[len(prefix) :]
            # Only strip if remainder looks like a set code (2-5 chars, alphanumeric)
            if 2 <= len(remainder) <= 5 and remainder.isalnum():
                return remainder

    # 4. Return as-is (lowercased)
    return code
