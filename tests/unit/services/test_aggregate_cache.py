"""Tests for AggregateCache (F44-T01)."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta

from src.services.aggregate_cache import (
    TTL_CARD_ANALYTICS,
    TTL_LATEST_PRICES,
    TTL_MARKET_SUMMARY,
    TTL_TOP_MOVERS,
    AggregateCache,
    CacheEntry,
)


class TestCacheEntry:
    def test_not_expired_within_ttl(self):
        entry = CacheEntry(value="x", computed_at=datetime.now(), ttl_seconds=60)
        assert not entry.is_expired()

    def test_expired_after_ttl(self):
        past = datetime.now() - timedelta(seconds=120)
        entry = CacheEntry(value="x", computed_at=past, ttl_seconds=60)
        assert entry.is_expired()

    def test_tags_default_to_empty_frozenset(self):
        entry = CacheEntry(value="x", computed_at=datetime.now(), ttl_seconds=60)
        assert entry.tags == frozenset()


class TestAggregateCacheGet:
    def test_get_returns_none_for_missing_key(self):
        cache = AggregateCache()
        assert cache.get("nonexistent") is None

    def test_set_and_get_within_ttl(self):
        cache = AggregateCache(default_ttl=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_returns_none_after_ttl_expires(self):
        cache = AggregateCache(default_ttl=1)
        past = datetime.now() - timedelta(seconds=10)
        entry = CacheEntry(value="old", computed_at=past, ttl_seconds=1)
        with cache._lock:
            cache._store["expired_key"] = entry
        assert cache.get("expired_key") is None

    def test_set_overwrites_existing_entry(self):
        cache = AggregateCache()
        cache.set("key", "first")
        cache.set("key", "second")
        assert cache.get("key") == "second"

    def test_custom_ttl_overrides_default(self):
        cache = AggregateCache(default_ttl=3600)
        cache.set("short", "val", ttl=1)
        # Manually expire it
        past = datetime.now() - timedelta(seconds=5)
        entry = CacheEntry(value="val", computed_at=past, ttl_seconds=1)
        with cache._lock:
            cache._store["short"] = entry
        assert cache.get("short") is None


class TestAggregateCacheInvalidate:
    def test_invalidate_removes_key(self):
        cache = AggregateCache()
        cache.set("key", "value")
        cache.invalidate("key")
        assert cache.get("key") is None

    def test_invalidate_nonexistent_key_is_noop(self):
        cache = AggregateCache()
        cache.invalidate("nonexistent")  # Should not raise

    def test_invalidate_by_tags_removes_matching_entries(self):
        cache = AggregateCache()
        cache.set("a", 1, tags={"tag1"})
        cache.set("b", 2, tags={"tag2"})
        cache.set("c", 3, tags={"tag1", "tag3"})
        removed = cache.invalidate_by_tags({"tag1"})
        assert removed == 2
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") is None

    def test_invalidate_by_tags_leaves_untagged_entries(self):
        cache = AggregateCache()
        cache.set("tagged", 1, tags={"x"})
        cache.set("untagged", 2)
        removed = cache.invalidate_by_tags({"x"})
        assert removed == 1
        assert cache.get("untagged") == 2

    def test_invalidate_by_tags_with_empty_set(self):
        cache = AggregateCache()
        cache.set("a", 1, tags={"x"})
        removed = cache.invalidate_by_tags(set())
        assert removed == 0
        assert cache.get("a") == 1


class TestAggregateCacheClear:
    def test_clear_removes_all(self):
        cache = AggregateCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.get("c") is None
        assert cache.stats()["size"] == 0


class TestAggregateCacheStats:
    def test_stats_tracks_hits_and_misses(self):
        cache = AggregateCache()
        cache.set("hit_me", "value")
        cache.get("hit_me")  # hit
        cache.get("hit_me")  # hit
        cache.get("miss")  # miss
        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_stats_initial_values(self):
        cache = AggregateCache()
        stats = cache.stats()
        assert stats == {"size": 0, "hits": 0, "misses": 0}


class TestAggregateCacheThreadSafety:
    def test_concurrent_set_get(self):
        cache = AggregateCache(default_ttl=60)

        def writer(thread_id: int):
            for i in range(50):
                cache.set(f"key_{thread_id}_{i}", f"val_{thread_id}_{i}")

        def reader(thread_id: int):
            for i in range(50):
                cache.get(f"key_{thread_id}_{i}")

        threads = []
        for t in range(4):
            threads.append(threading.Thread(target=writer, args=(t,)))
            threads.append(threading.Thread(target=reader, args=(t,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # No exceptions raised = thread-safe
        stats = cache.stats()
        assert stats["size"] <= 200  # 4 writers * 50 keys max


class TestTTLConstants:
    def test_constants_are_positive(self):
        assert TTL_MARKET_SUMMARY > 0
        assert TTL_TOP_MOVERS > 0
        assert TTL_LATEST_PRICES > 0
        assert TTL_CARD_ANALYTICS > 0

    def test_summary_longer_than_movers(self):
        assert TTL_MARKET_SUMMARY > TTL_TOP_MOVERS

    def test_movers_longer_than_prices(self):
        assert TTL_TOP_MOVERS > TTL_LATEST_PRICES
