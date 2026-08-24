"""Tests for provider registry FastAPI dependency (F57-T05).

Covers:
 1. get_provider_registry returns a ProviderRegistry
 2. get_provider_registry returns singleton (same instance on repeated calls)
 3. Registry has MYP provider when configured with myp-only
 4. run_scan accepts provider parameter in its signature
"""

from __future__ import annotations

from unittest.mock import patch

from src.api.deps import get_provider_registry
from src.providers.registry import ProviderRegistry, create_registry_from_env


class TestGetProviderRegistry:
    """Tests for the get_provider_registry dependency."""

    def setup_method(self):
        """Clear singleton cache before each test."""
        if hasattr(get_provider_registry, "_instance"):
            del get_provider_registry._instance

    def teardown_method(self):
        """Clear singleton cache after each test."""
        if hasattr(get_provider_registry, "_instance"):
            del get_provider_registry._instance

    def test_returns_provider_registry(self):
        """get_provider_registry returns a ProviderRegistry instance."""
        with patch.dict("os.environ", {"TCG_PROVIDER_ORDER": "myp"}, clear=False):
            registry = get_provider_registry()

        assert isinstance(registry, ProviderRegistry)

    def test_returns_singleton(self):
        """Repeated calls return the same instance."""
        with patch.dict("os.environ", {"TCG_PROVIDER_ORDER": "myp"}, clear=False):
            r1 = get_provider_registry()
            r2 = get_provider_registry()

        assert r1 is r2

    def test_myp_provider_in_registry(self):
        """Registry includes MYP provider when configured."""
        with patch.dict("os.environ", {"TCG_PROVIDER_ORDER": "myp"}, clear=False):
            registry = get_provider_registry()

        assert "myp" in registry.source_names


class TestCreateRegistryFromEnv:
    """Tests for create_registry_from_env factory."""

    def test_myp_only(self):
        """TCG_PROVIDER_ORDER=myp creates registry with only MYP."""
        with patch.dict("os.environ", {"TCG_PROVIDER_ORDER": "myp"}, clear=False):
            registry = create_registry_from_env()

        assert registry.source_names == ["myp"]

    def test_unknown_provider_ignored(self):
        """Unknown provider names are silently ignored."""
        with patch.dict("os.environ", {"TCG_PROVIDER_ORDER": "unknown,myp"}, clear=False):
            registry = create_registry_from_env()

        assert "myp" in registry.source_names
        assert "unknown" not in registry.source_names

    def test_default_order_includes_liga_and_myp(self):
        """Default order tries liga,myp (liga may be skipped if unavailable)."""
        with patch.dict("os.environ", {}, clear=False):
            # Remove TCG_PROVIDER_ORDER if set
            import os

            old = os.environ.pop("TCG_PROVIDER_ORDER", None)
            try:
                registry = create_registry_from_env()
                # At minimum, myp should be present
                assert "myp" in registry.source_names
            finally:
                if old is not None:
                    os.environ["TCG_PROVIDER_ORDER"] = old


class TestRunScanProviderParam:
    """Tests that run_scan accepts and uses an injected provider."""

    def test_run_scan_signature_accepts_provider(self):
        """run_scan accepts a provider keyword argument."""
        import inspect

        from src.collectors.scan import run_scan

        sig = inspect.signature(run_scan)
        assert "provider" in sig.parameters
        assert sig.parameters["provider"].default is None
