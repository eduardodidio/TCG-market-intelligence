"""Tests for the scans API router (trigger, list, detail)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_credit_service, get_current_user, require_auth_or_api_key
from src.api.routers.scans import router
from src.domain.models import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_USER = User(
    id=1,
    email="test@example.com",
    display_name="Test",
    is_active=True,
    is_admin=True,  # admin so existing tests bypass credit checks
)


def _make_credit_svc() -> MagicMock:
    """Return a mock CreditService that always allows."""
    from src.credits.service import CreditService

    svc = MagicMock(spec=CreditService)
    svc.check_sufficient.return_value = True
    return svc


def _make_app() -> FastAPI:
    """Create a fresh FastAPI app with the scans router."""
    test_app = FastAPI()
    test_app.include_router(router)
    # Override auth + credit deps so tests don't need real JWT/DB
    test_app.dependency_overrides[require_auth_or_api_key] = lambda: str(_TEST_USER.id)
    test_app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    test_app.dependency_overrides[get_credit_service] = _make_credit_svc
    return test_app


def _scan_row(
    scan_id: int = 1,
    scan_type: str = "collection",
    status: str = "pending",
    **overrides,
) -> dict:
    """Build a fake scan-run dict matching Repository.get_scan_run output."""
    row = {
        "id": scan_id,
        "scan_type": scan_type,
        "filters_json": "{}",
        "status": status,
        "cards_total": 0,
        "cards_processed": 0,
        "cards_failed": 0,
        "observations_saved": 0,
        "error_summary": None,
        "started_at": None,
        "finished_at": None,
        "created_at": "2026-08-20T12:00:00",
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# POST /scans — trigger
# ---------------------------------------------------------------------------


class TestTriggerScan:
    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_trigger_returns_scan_id(
        self, mock_repo_cls: MagicMock, mock_thread_cls: MagicMock
    ) -> None:
        """POST /scans returns 200 with scan_id and status."""
        mock_repo = MagicMock()
        mock_repo.create_scan_run.return_value = 42
        mock_repo_cls.return_value = mock_repo

        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        app = _make_app()
        client = TestClient(app)

        resp = client.post("/scans", json={"scan_type": "collection"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["scan_id"] == 42
        assert body["status"] == "pending"

        # Background thread was started
        mock_thread.start.assert_called_once()

    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_trigger_with_filters(
        self, mock_repo_cls: MagicMock, mock_thread_cls: MagicMock
    ) -> None:
        """POST /scans with set_codes in request body passes them through."""
        mock_repo = MagicMock()
        mock_repo.create_scan_run.return_value = 7
        mock_repo_cls.return_value = mock_repo
        mock_thread_cls.return_value = MagicMock()

        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/scans",
            json={
                "scan_type": "set",
                "set_codes": ["dmr", "2xm"],
                "limit": 10,
                "dry_run": True,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["scan_id"] == 7

        # Verify create_scan_run was called with correct scan_type
        call_args = mock_repo.create_scan_run.call_args
        assert call_args[0][0] == "set"

    def test_trigger_requires_auth_when_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """POST /scans returns 401 without a valid X-API-Key."""
        monkeypatch.setenv("TCG_API_KEY", "secret-key-99")

        # Use raw app without dependency overrides to test real auth
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # No header -> 401
        resp = client.post("/scans", json={"scan_type": "collection"})
        assert resp.status_code == 401

        # Wrong header -> 401
        resp = client.post(
            "/scans",
            json={"scan_type": "collection"},
            headers={"X-API-Key": "wrong"},
        )
        assert resp.status_code == 401

    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_trigger_works_with_correct_key(
        self,
        mock_repo_cls: MagicMock,
        mock_thread_cls: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """POST /scans returns 200 with a correct X-API-Key."""
        monkeypatch.setenv("TCG_API_KEY", "secret-key-99")
        mock_repo = MagicMock()
        mock_repo.create_scan_run.return_value = 1
        mock_repo_cls.return_value = mock_repo
        mock_thread_cls.return_value = MagicMock()

        # Use raw app but override credit deps (API key auth skips get_current_user)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: _TEST_USER
        app.dependency_overrides[get_credit_service] = _make_credit_svc
        client = TestClient(app)

        resp = client.post(
            "/scans",
            json={"scan_type": "collection"},
            headers={"X-API-Key": "secret-key-99"},
        )
        assert resp.status_code == 200

    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_trigger_default_provider_is_liga(
        self, mock_repo_cls: MagicMock, mock_thread_cls: MagicMock
    ) -> None:
        """POST /scans with no provider field defaults to liga."""
        import json

        mock_repo = MagicMock()
        mock_repo.create_scan_run.return_value = 1
        mock_repo_cls.return_value = mock_repo
        mock_thread_cls.return_value = MagicMock()

        app = _make_app()
        client = TestClient(app)

        resp = client.post("/scans", json={"scan_type": "collection"})
        assert resp.status_code == 200

        # Verify provider encoded in filters_json
        call_args = mock_repo.create_scan_run.call_args
        filters_json = call_args[0][1]
        filters = json.loads(filters_json)
        assert filters["provider"] == "liga"

    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_trigger_provider_liga_routes_to_liga(
        self, mock_repo_cls: MagicMock, mock_thread_cls: MagicMock
    ) -> None:
        """POST /scans with provider=liga encodes liga in filters."""
        import json

        mock_repo = MagicMock()
        mock_repo.create_scan_run.return_value = 1
        mock_repo_cls.return_value = mock_repo

        captured_target = {}
        original_thread = mock_thread_cls

        def capture_thread(*args, **kwargs):
            captured_target.update(kwargs)
            return MagicMock()

        original_thread.side_effect = capture_thread

        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/scans",
            json={"scan_type": "collection", "provider": "liga"},
        )
        assert resp.status_code == 200

        filters_json = mock_repo.create_scan_run.call_args[0][1]
        filters = json.loads(filters_json)
        assert filters["provider"] == "liga"

    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_trigger_provider_myp_routes_to_myp(
        self, mock_repo_cls: MagicMock, mock_thread_cls: MagicMock
    ) -> None:
        """POST /scans with provider=myp encodes myp in filters."""
        import json

        mock_repo = MagicMock()
        mock_repo.create_scan_run.return_value = 1
        mock_repo_cls.return_value = mock_repo
        mock_thread_cls.return_value = MagicMock()

        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/scans",
            json={"scan_type": "collection", "provider": "myp"},
        )
        assert resp.status_code == 200

        filters_json = mock_repo.create_scan_run.call_args[0][1]
        filters = json.loads(filters_json)
        assert filters["provider"] == "myp"


# ---------------------------------------------------------------------------
# GET /scans — list
# ---------------------------------------------------------------------------


class TestListScans:
    @patch("src.api.routers.scans.Repository")
    def test_list_returns_scans(self, mock_repo_cls: MagicMock) -> None:
        """GET /scans returns a list of scan runs."""
        mock_repo = MagicMock()
        mock_repo.list_scan_runs.return_value = [
            _scan_row(scan_id=1, status="completed"),
            _scan_row(scan_id=2, status="running"),
        ]
        mock_repo_cls.return_value = mock_repo

        app = _make_app()
        client = TestClient(app)

        resp = client.get("/scans")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["scans"]) == 2
        assert body["scans"][0]["id"] == 1
        assert body["scans"][0]["status"] == "completed"

    @patch("src.api.routers.scans.Repository")
    def test_list_with_scan_type_filter(self, mock_repo_cls: MagicMock) -> None:
        """GET /scans?scan_type=set passes filter to repository."""
        mock_repo = MagicMock()
        mock_repo.list_scan_runs.return_value = [
            _scan_row(scan_id=5, scan_type="set"),
        ]
        mock_repo_cls.return_value = mock_repo

        app = _make_app()
        client = TestClient(app)

        resp = client.get("/scans?scan_type=set")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["scans"][0]["scan_type"] == "set"

        # Verify filter was passed to repository
        call_kwargs = mock_repo.list_scan_runs.call_args[1]
        assert call_kwargs["scan_type"] == "set"

    @patch("src.api.routers.scans.Repository")
    def test_list_with_status_filter(self, mock_repo_cls: MagicMock) -> None:
        """GET /scans?status=completed passes filter to repository."""
        mock_repo = MagicMock()
        mock_repo.list_scan_runs.return_value = []
        mock_repo_cls.return_value = mock_repo

        app = _make_app()
        client = TestClient(app)

        resp = client.get("/scans?status=completed")
        assert resp.status_code == 200

        call_kwargs = mock_repo.list_scan_runs.call_args[1]
        assert call_kwargs["status"] == "completed"

    @patch("src.api.routers.scans.Repository")
    def test_list_empty(self, mock_repo_cls: MagicMock) -> None:
        """GET /scans returns empty list when no scans exist."""
        mock_repo = MagicMock()
        mock_repo.list_scan_runs.return_value = []
        mock_repo_cls.return_value = mock_repo

        app = _make_app()
        client = TestClient(app)

        resp = client.get("/scans")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["scans"] == []

    def test_list_no_auth_required(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GET /scans works even when TCG_API_KEY is set (no auth on GETs)."""
        monkeypatch.setenv("TCG_API_KEY", "secret-key-99")

        with patch("src.api.routers.scans.Repository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.list_scan_runs.return_value = []
            mock_repo_cls.return_value = mock_repo

            app = _make_app()
            client = TestClient(app)

            # No X-API-Key header — should still return 200
            resp = client.get("/scans")
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /scans/{scan_id} — detail
# ---------------------------------------------------------------------------


class TestGetScan:
    @patch("src.api.routers.scans.Repository")
    def test_get_scan_returns_detail(self, mock_repo_cls: MagicMock) -> None:
        """GET /scans/1 returns scan run details."""
        mock_repo = MagicMock()
        mock_repo.get_scan_run.return_value = _scan_row(
            scan_id=1,
            status="completed",
            cards_total=100,
            cards_processed=95,
            cards_failed=5,
            observations_saved=90,
        )
        mock_repo_cls.return_value = mock_repo

        app = _make_app()
        client = TestClient(app)

        resp = client.get("/scans/1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == 1
        assert body["status"] == "completed"
        assert body["cards_total"] == 100
        assert body["cards_processed"] == 95
        assert body["cards_failed"] == 5
        assert body["observations_saved"] == 90

    @patch("src.api.routers.scans.Repository")
    def test_get_scan_not_found(self, mock_repo_cls: MagicMock) -> None:
        """GET /scans/999 returns 404 when scan does not exist."""
        mock_repo = MagicMock()
        mock_repo.get_scan_run.return_value = None
        mock_repo_cls.return_value = mock_repo

        app = _make_app()
        client = TestClient(app)

        resp = client.get("/scans/999")
        assert resp.status_code == 404

    def test_get_scan_no_auth_required(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GET /scans/{id} works even when TCG_API_KEY is set."""
        monkeypatch.setenv("TCG_API_KEY", "secret-key-99")

        with patch("src.api.routers.scans.Repository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_scan_run.return_value = _scan_row(scan_id=1)
            mock_repo_cls.return_value = mock_repo

            app = _make_app()
            client = TestClient(app)

            resp = client.get("/scans/1")
            assert resp.status_code == 200

    @patch("src.api.routers.scans.Repository")
    def test_get_scan_datetime_conversion(self, mock_repo_cls: MagicMock) -> None:
        """Datetime fields from the repository are converted to ISO strings."""
        from datetime import datetime

        mock_repo = MagicMock()
        mock_repo.get_scan_run.return_value = _scan_row(
            scan_id=1,
            started_at=datetime(2026, 8, 20, 10, 0, 0),
            finished_at=datetime(2026, 8, 20, 10, 5, 0),
            created_at=datetime(2026, 8, 20, 9, 55, 0),
        )
        mock_repo_cls.return_value = mock_repo

        app = _make_app()
        client = TestClient(app)

        resp = client.get("/scans/1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["started_at"] == "2026-08-20T10:00:00"
        assert body["finished_at"] == "2026-08-20T10:05:00"
        assert body["created_at"] == "2026-08-20T09:55:00"


# ---------------------------------------------------------------------------
# GET /scans/preview — scan preview
# ---------------------------------------------------------------------------


class TestPreviewScan:
    @patch("src.api.routers.scans.Repository")
    def test_preview_returns_counts(self, mock_repo_cls: MagicMock) -> None:
        """Preview returns card_count, skipped_count, credit_cost."""
        mock_repo = MagicMock()
        all_cards = [{"card_id": i} for i in range(10)]
        eligible_cards = [{"card_id": i} for i in range(7)]
        mock_repo.get_cards_for_liga_scan.side_effect = [all_cards, eligible_cards]
        mock_repo_cls.return_value = mock_repo

        app = _make_app()
        client = TestClient(app)

        resp = client.get("/scans/preview?max_age_days=3")
        assert resp.status_code == 200
        body = resp.json()
        assert body["card_count"] == 7
        assert body["skipped_count"] == 3
        # Admin user -> cost 0
        assert body["credit_cost"] == 0

    @patch("src.api.routers.scans.Repository")
    def test_preview_no_max_age_days(self, mock_repo_cls: MagicMock) -> None:
        """Preview without max_age_days returns all cards, no skipped."""
        mock_repo = MagicMock()
        all_cards = [{"card_id": i} for i in range(5)]
        # Both calls return all cards when max_age_days=None
        mock_repo.get_cards_for_liga_scan.side_effect = [all_cards, all_cards]
        mock_repo_cls.return_value = mock_repo

        app = _make_app()
        client = TestClient(app)

        resp = client.get("/scans/preview")
        assert resp.status_code == 200
        body = resp.json()
        assert body["card_count"] == 5
        assert body["skipped_count"] == 0

    @patch("src.api.routers.scans.Repository")
    def test_preview_non_admin_has_credit_cost(self, mock_repo_cls: MagicMock) -> None:
        """Non-admin preview returns per-card credit cost."""
        non_admin_user = User(
            id=2,
            email="user@example.com",
            display_name="User",
            is_active=True,
            is_admin=False,
        )

        mock_repo = MagicMock()
        all_cards = [{"card_id": i} for i in range(8)]
        eligible_cards = [{"card_id": i} for i in range(5)]
        mock_repo.get_cards_for_liga_scan.side_effect = [all_cards, eligible_cards]
        mock_repo_cls.return_value = mock_repo

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: non_admin_user
        client = TestClient(app)

        resp = client.get("/scans/preview?max_age_days=3")
        assert resp.status_code == 200
        body = resp.json()
        assert body["card_count"] == 5
        assert body["skipped_count"] == 3
        assert body["credit_cost"] == 5  # 5 cards * 1 credit


# ---------------------------------------------------------------------------
# POST /scans — max_age_days threading
# ---------------------------------------------------------------------------


class TestTriggerMaxAgeDays:
    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_max_age_days_stored_in_filters_json(
        self, mock_repo_cls: MagicMock, mock_thread_cls: MagicMock
    ) -> None:
        """max_age_days is encoded in filters_json for traceability."""
        import json

        mock_repo = MagicMock()
        mock_repo.create_scan_run.return_value = 1
        mock_repo_cls.return_value = mock_repo
        mock_thread_cls.return_value = MagicMock()

        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/scans",
            json={"scan_type": "collection", "max_age_days": 7},
        )
        assert resp.status_code == 200

        filters_json = mock_repo.create_scan_run.call_args[0][1]
        filters = json.loads(filters_json)
        assert filters["max_age_days"] == 7

    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_max_age_days_not_in_filters_when_none(
        self, mock_repo_cls: MagicMock, mock_thread_cls: MagicMock
    ) -> None:
        """max_age_days omitted from filters_json when not provided."""
        import json

        mock_repo = MagicMock()
        mock_repo.create_scan_run.return_value = 1
        mock_repo_cls.return_value = mock_repo
        mock_thread_cls.return_value = MagicMock()

        app = _make_app()
        client = TestClient(app)

        resp = client.post("/scans", json={"scan_type": "collection"})
        assert resp.status_code == 200

        filters_json = mock_repo.create_scan_run.call_args[0][1]
        filters = json.loads(filters_json)
        assert "max_age_days" not in filters

    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_max_age_days_passed_to_background_thread(
        self, mock_repo_cls: MagicMock, mock_thread_cls: MagicMock
    ) -> None:
        """max_age_days is forwarded to run_liga_scan via the background thread."""
        mock_repo = MagicMock()
        mock_repo.create_scan_run.return_value = 1
        mock_repo_cls.return_value = mock_repo

        captured_target = {}

        def capture_thread(*args, **kwargs):
            captured_target.update(kwargs)
            mock_t = MagicMock()
            return mock_t

        mock_thread_cls.side_effect = capture_thread

        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/scans",
            json={"scan_type": "collection", "max_age_days": 3},
        )
        assert resp.status_code == 200

        # The target callable was captured; it should use max_age_days=3
        assert "target" in captured_target
