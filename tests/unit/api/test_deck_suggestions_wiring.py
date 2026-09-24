"""Wiring tests for F172: router and CLI command registration (F172-T17)."""

from __future__ import annotations

import os
from unittest.mock import patch

from src.api.app import create_app


def _openapi_paths() -> dict[str, dict]:
    # FastAPI >= 0.14x wraps included routers (``_IncludedRouter``), so
    # ``app.routes`` no longer lists their paths; the OpenAPI schema (what
    # ``/docs`` renders) is the stable source of registered operations.
    with patch.dict(os.environ, {"TCG_SCHEDULER_DISABLED": "1"}):
        app = create_app()
    return app.openapi()["paths"]


def _route_paths() -> set[str]:
    return set(_openapi_paths())


class TestDeckSuggestionsRouterWiring:
    def test_collection_route_registered(self) -> None:
        assert "/api/v1/deck-suggestions" in _route_paths()

    def test_all_suggestion_routes_registered(self) -> None:
        paths = _route_paths()
        assert "/api/v1/deck-suggestions/{request_id}" in paths
        assert "/api/v1/deck-suggestions/{request_id}/save" in paths

    def test_five_suggestion_operations_registered(self) -> None:
        ops = {
            (method.upper(), path)
            for path, item in _openapi_paths().items()
            if path.startswith("/api/v1/deck-suggestions")
            for method in item
        }
        assert ops == {
            ("POST", "/api/v1/deck-suggestions"),
            ("GET", "/api/v1/deck-suggestions"),
            ("GET", "/api/v1/deck-suggestions/{request_id}"),
            ("POST", "/api/v1/deck-suggestions/{request_id}/save"),
            ("DELETE", "/api/v1/deck-suggestions/{request_id}"),
        }

    def test_does_not_shadow_decks_routes(self) -> None:
        paths = _route_paths()
        assert "/api/v1/decks/{deck_id}" in paths
        assert "/api/v1/decks/ranking" in paths


class TestDeckSuggestionsCliWiring:
    def test_command_registered(self) -> None:
        from src.cli.main import cli

        assert "process-deck-suggestions" in cli.commands

    def test_registered_command_is_the_module_command(self) -> None:
        from src.cli.deck_suggestions import process_deck_suggestions
        from src.cli.main import cli

        assert cli.commands["process-deck-suggestions"] is process_deck_suggestions
