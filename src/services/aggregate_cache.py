"""TTL-based in-memory cache for pre-computed market aggregates."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

# TTL constants (seconds)
TTL_MARKET_SUMMARY = 3600  # 1 hour
TTL_TOP_MOVERS = 1800  # 30 minutes
TTL_LATEST_PRICES = 900  # 15 minutes
TTL_CARD_ANALYTICS = 1800  # 30 minutes


@dataclass(frozen=True)
class CacheEntry:
    """A cached value with expiry metadata."""

    value: Any
    computed_at: datetime
    ttl_seconds: int
    tags: frozenset[str] = field(default_factory=frozenset)

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check if this entry has expired."""
        now = now or datetime.now()
        return (now - self.computed_at) > timedelta(seconds=self.ttl_seconds)


class AggregateCache:
    """Thread-safe in-memory cache with TTL and tag-based invalidation.

    Designed for a small number of entries (< 100). Tag-based invalidation
    is O(n) which is acceptable for this scale.
    """

    def __init__(self, default_ttl: int = 900) -> None:
        self._default_ttl = default_ttl
        self._store: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """Return cached value if present and not expired, else None."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired():
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        tags: set[str] | None = None,
    ) -> None:
        """Store a value with optional custom TTL and tags."""
        entry = CacheEntry(
            value=value,
            computed_at=datetime.now(),
            ttl_seconds=ttl if ttl is not None else self._default_ttl,
            tags=frozenset(tags) if tags else frozenset(),
        )
        with self._lock:
            self._store[key] = entry

    def invalidate(self, key: str) -> None:
        """Remove a specific key."""
        with self._lock:
            self._store.pop(key, None)

    def invalidate_by_tags(self, tags: set[str]) -> int:
        """Remove all entries tagged with any of the given tags.

        Returns count of entries removed.
        """
        frozen_tags = frozenset(tags)
        with self._lock:
            to_remove = [k for k, entry in self._store.items() if entry.tags & frozen_tags]
            for k in to_remove:
                del self._store[k]
            return len(to_remove)

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        """Return cache statistics: size, hits, misses."""
        with self._lock:
            return {
                "size": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
            }
