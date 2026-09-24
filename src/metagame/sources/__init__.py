"""Metagame source registry (F173).

``SOURCE_FOR_FORMAT`` mirrors ADR-0016: EDHREC for Commander, MTGTop8 for
every constructed format.
"""

from __future__ import annotations

from src.metagame.sources.base import MetaSource

SOURCE_FOR_FORMAT: dict[str, str] = {
    "commander": "edhrec",
    "standard": "mtgtop8",
    "pioneer": "mtgtop8",
    "modern": "mtgtop8",
    "legacy": "mtgtop8",
    "vintage": "mtgtop8",
    "pauper": "mtgtop8",
}


def get_sources(fetcher) -> dict[str, MetaSource]:
    """Return ``{format: source}``; formats sharing a source share one instance."""
    from src.metagame.sources.edhrec import EdhrecSource
    from src.metagame.sources.mtgtop8 import Mtgtop8Source

    instances: dict[str, MetaSource] = {
        "edhrec": EdhrecSource(fetcher),
        "mtgtop8": Mtgtop8Source(fetcher),
    }
    return {fmt: instances[name] for fmt, name in SOURCE_FOR_FORMAT.items()}
