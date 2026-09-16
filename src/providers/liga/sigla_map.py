"""Scryfall set_code -> Liga data-sigla normalization.

Liga Magic sometimes uses different set abbreviations (siglas) than Scryfall.
This module provides a mapping to bridge those differences, ensuring that
edition disambiguation by sigla works correctly.

The mapping is populated incrementally as mismatches are discovered via the
``liga_edition_sigla_no_match`` warning log emitted by ``_select_edition``.
"""

from __future__ import annotations

# Mapping: scryfall_set_code (lowercase) -> liga_sigla (lowercase).
# Populated after validation sweeps reveal actual mismatches.
# Example: "plst": "tlist", "pmbs": "pmyb"
SCRYFALL_TO_LIGA_SIGLA: dict[str, str] = {}


def normalize_sigla(scryfall_set_code: str) -> str:
    """Return the Liga sigla for a Scryfall set code.

    If the code exists in ``SCRYFALL_TO_LIGA_SIGLA``, the mapped value
    is returned.  Otherwise, the input is returned unchanged.

    The input should already be lowercased by the caller.
    """
    return SCRYFALL_TO_LIGA_SIGLA.get(scryfall_set_code, scryfall_set_code)
