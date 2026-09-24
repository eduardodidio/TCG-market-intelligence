"""Metagame source registry (F173)."""

from __future__ import annotations

from src.metagame.sources.base import MetaSource

# populated by F173-T12
SOURCE_FOR_FORMAT: dict[str, str] = {}


def get_sources(fetcher) -> dict[str, MetaSource]:
    # populated by F173-T12
    return {}
