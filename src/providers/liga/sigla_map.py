"""Scryfall set_code -> Liga data-sigla normalization.

Liga Magic sometimes uses different set abbreviations (siglas) than Scryfall.
This module provides a mapping to bridge those differences, ensuring that
edition disambiguation by sigla works correctly.

The per-card mapping ``CARD_SIGLA_OVERRIDES`` is keyed by
``(scryfall_set_code, collector_number)`` and provides the exact Liga sigla
for cards whose variant edition (borderless, showcase, etc.) uses a different
sigla prefix on Liga.

Built from the user's Liga collection HTML export (2026-09-16).
"""

from __future__ import annotations

# Mapping: scryfall_set_code (lowercase) -> liga_sigla (lowercase).
# For simple 1:1 set renames (rare).
SCRYFALL_TO_LIGA_SIGLA: dict[str, str] = {}

# Per-card overrides: (set_code, collector_number) -> liga_sigla.
# For variant editions where the same Scryfall set_code maps to different
# Liga siglas depending on the specific card/printing.
# Built from Liga HTML export analysis.
CARD_SIGLA_OVERRIDES: dict[tuple[str, str], str] = {
    # Commander editions
    ("thb", "259"): "cthb",  # Heliod, Sun-Crowned
    ("thb", "264"): "cthb",  # Anax, Hardened in the Forge
    ("znr", "314"): "cbznr",  # Angel of Destiny
    ("cmr", "689"): "cbcmr",  # Arcane Signet
    # Borderless LTR
    ("ltr", "407"): "bltr",  # Boromir, Warden of the Tower
    ("ltr", "414"): "bltr",  # Pippin's Bravery
    ("ltr", "425"): "bltr",  # Barad-dur
    ("ltr", "426"): "bltr",  # Oliphaunt
    ("ltr", "427"): "bltr",  # Rising of the Day
    ("ltr", "445"): "bltr",  # Many Partings
    ("ltr", "344"): "blltr",  # Rivendell
    ("ltr", "404"): "pltr",  # Frodo Baggins (promo)
    ("ltr", "315"): "srltr",  # Peregrin Took (serialized ring)
    # Variant VOW
    ("vow", "279"): "vvow",  # Chandra, Dressed to Kill
    ("vow", "301"): "vvow",  # Belligerent Guest
    ("vow", "310"): "vvow",  # Bloodtithe Harvester
    # Showcase HOC
    ("hoc", "3"): "schoc",  # Thorin, King of Durin's Folk
    ("hoc", "10"): "schoc",  # Bilbo's Burglaring
    ("hoc", "11"): "schoc",  # Dragon's Desire
    # Hobbit variants
    ("hob", "215"): "dhhob",  # Bofur, Reliable Guardian (draft)
    ("hob", "211"): "schob",  # Bolg's Company (showcase)
    ("hob", "44a"): "ashob",  # The Arkenstone (Art Card with Signature)
    # Tarkir Dragonstorm variants
    ("tdm", "401"): "gftdm",  # Elspeth, Storm Slayer (Ghostfire)
    ("tdm", "302"): "dftdm",  # Sarkhan, Dragon Ascendant (draft)
    # Other variant editions
    ("mh2", "328"): "skmh2",  # Esper Sentinel (sketch)
    ("clb", "504"): "feclb",  # Ganax, Astral Hunter (foil etched)
    ("fdn", "496"): "bbfdn",  # Inspiring Overseer (buy-a-box)
    ("2x2", "362"): "bl2x2",  # Monastery Swiftspear (borderless)
    ("brr", "98"): "smbro",  # Mox Amber (set booster BRO)
    ("snc", "443"): "fesnc",  # Sanctuary Warden (foil etched)
    ("sld", "1245"): "sld158",  # Sarkhan, Dragonsoul (Secret Lair)
    ("dbl", "159"): "mid",  # Smoldering Egg (DBL -> MID mapping)
    ("fic", "120"): "eafic",  # Snort (extended art)
    ("dmr", "437"): "bldmr",  # Worldgorger Dragon (borderless)
}


def normalize_sigla(
    scryfall_set_code: str,
    collector_number: str | None = None,
) -> str:
    """Return the Liga sigla for a Scryfall set code.

    Checks ``CARD_SIGLA_OVERRIDES`` first (per-card), then
    ``SCRYFALL_TO_LIGA_SIGLA`` (per-set), then returns the input unchanged.
    """
    sc = scryfall_set_code.lower() if scryfall_set_code else ""
    # Per-card override takes priority
    if collector_number:
        override = CARD_SIGLA_OVERRIDES.get((sc, collector_number))
        if override:
            return override
    # Per-set mapping
    return SCRYFALL_TO_LIGA_SIGLA.get(sc, sc)
