"""Tests for the news feed API router (F166)."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.api.routers.news import router
from src.database.models import NewsItemRow
from src.database.repository import Repository
from src.domain.models import User


def _make_user(user_id: int = 1, is_admin: bool = False) -> User:
    return User(
        id=user_id,
        email="test@example.com",
        display_name="Test User",
        auth_provider="email",
        is_active=True,
        is_admin=is_admin,
    )


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_news.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def user():
    return _make_user()


@pytest.fixture()
def test_app(repo, user):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: user
    return app


@pytest.fixture()
def client(test_app):
    return TestClient(test_app)


def _seed_news(repo, count=5):
    """Seed news items and return their IDs."""
    ids = []
    categories = ["ban", "release", "event", "reprint", "other"]
    with Session(repo.engine) as session:
        for i in range(count):
            item = NewsItemRow(
                title=f"News Item {i + 1}",
                summary=f"Summary for item {i + 1}",
                source_url=f"https://example.com/news/{i + 1}",
                source_name="Test Source",
                category=categories[i % len(categories)],
                published_at=datetime(2026, 9, 21, 12, 0, i),
                fetched_at=datetime.now(),
            )
            session.add(item)
            session.flush()
            ids.append(item.id)
        session.commit()
    return ids


class TestListNews:
    def test_list_empty(self, client):
        resp = client.get("/api/v1/news")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_with_items(self, client, repo):
        _seed_news(repo, 3)
        resp = client.get("/api/v1/news")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) == 3
        assert data["total"] == 3

    def test_list_filter_unread(self, client, repo, user):
        ids = _seed_news(repo, 3)
        # Mark first item as read
        repo.mark_news_read(user.id, ids[0])
        resp = client.get("/api/v1/news?filter=unread")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) == 2
        assert data["total"] == 2

    def test_list_filter_read(self, client, repo, user):
        ids = _seed_news(repo, 3)
        repo.mark_news_read(user.id, ids[0])
        resp = client.get("/api/v1/news?filter=read")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) == 1
        assert data["total"] == 1

    def test_list_category_filter(self, client, repo):
        _seed_news(repo, 5)
        resp = client.get("/api/v1/news?category=ban")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(item["category"] == "ban" for item in data["items"])

    def test_list_pagination(self, client, repo):
        _seed_news(repo, 5)
        resp = client.get("/api/v1/news?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) == 2
        assert data["total"] == 5

    def test_invalid_filter_rejected(self, client):
        resp = client.get("/api/v1/news?filter=invalid")
        assert resp.status_code == 422


class TestMarkRead:
    def test_mark_read(self, client, repo, user):
        ids = _seed_news(repo, 1)
        resp = client.post(f"/api/v1/news/{ids[0]}/mark-read")
        assert resp.status_code == 200
        assert resp.json()["data"]["marked"] is True
        # Verify via unread count
        count_resp = client.get("/api/v1/news/unread-count")
        assert count_resp.json()["data"]["count"] == 0

    def test_mark_read_idempotent(self, client, repo, user):
        ids = _seed_news(repo, 1)
        client.post(f"/api/v1/news/{ids[0]}/mark-read")
        resp = client.post(f"/api/v1/news/{ids[0]}/mark-read")
        assert resp.status_code == 200


class TestMarkUnread:
    def test_mark_unread(self, client, repo, user):
        ids = _seed_news(repo, 1)
        repo.mark_news_read(user.id, ids[0])
        resp = client.post(f"/api/v1/news/{ids[0]}/mark-unread")
        assert resp.status_code == 200
        count_resp = client.get("/api/v1/news/unread-count")
        assert count_resp.json()["data"]["count"] == 1

    def test_mark_unread_idempotent(self, client, repo, user):
        ids = _seed_news(repo, 1)
        resp = client.post(f"/api/v1/news/{ids[0]}/mark-unread")
        assert resp.status_code == 200


class TestNewsStatus:
    def test_status_empty(self, client):
        resp = client.get("/api/v1/news/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data == {
            "total_items": 0,
            "last_fetched_at": None,
            "newest_published_at": None,
        }

    def test_status_with_items(self, client, repo):
        with Session(repo.engine) as session:
            session.add_all(
                [
                    NewsItemRow(
                        title="Item 1",
                        source_url="https://example.com/news/1",
                        source_name="Test Source",
                        category="other",
                        published_at=datetime(2026, 9, 1, 10, 0, 0),
                        fetched_at=datetime(2026, 9, 1, 10, 5, 0),
                    ),
                    NewsItemRow(
                        title="Item 2",
                        source_url="https://example.com/news/2",
                        source_name="Test Source",
                        category="other",
                        published_at=datetime(2026, 9, 21, 12, 0, 0),
                        fetched_at=datetime(2026, 9, 21, 12, 5, 0),
                    ),
                    NewsItemRow(
                        title="Item 3",
                        source_url="https://example.com/news/3",
                        source_name="Test Source",
                        category="other",
                        published_at=datetime(2026, 9, 10, 8, 0, 0),
                        fetched_at=datetime(2026, 9, 15, 9, 0, 0),
                    ),
                ]
            )
            session.commit()

        resp = client.get("/api/v1/news/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_items"] == 3
        assert data["last_fetched_at"] == datetime(2026, 9, 21, 12, 5, 0).isoformat()
        assert data["newest_published_at"] == datetime(2026, 9, 21, 12, 0, 0).isoformat()

    def test_status_all_published_at_null(self, client, repo):
        with Session(repo.engine) as session:
            session.add(
                NewsItemRow(
                    title="Item 1",
                    source_url="https://example.com/news/1",
                    source_name="Test Source",
                    category="other",
                    published_at=None,
                    fetched_at=datetime(2026, 9, 1, 10, 0, 0),
                )
            )
            session.commit()

        resp = client.get("/api/v1/news/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_items"] == 1
        assert data["newest_published_at"] is None
        assert data["last_fetched_at"] == datetime(2026, 9, 1, 10, 0, 0).isoformat()

    def test_status_single_item(self, client, repo):
        _seed_news(repo, 1)
        resp = client.get("/api/v1/news/status")
        assert resp.status_code == 200
        assert resp.json()["data"]["total_items"] == 1

    def test_status_requires_auth(self, repo):
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: repo
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get("/api/v1/news/status")
        assert resp.status_code in (401, 422, 500)

    def test_unread_count_route_still_resolves(self, client, repo):
        """Ensure /status doesn't shadow /unread-count (route order)."""
        _seed_news(repo, 2)
        resp = client.get("/api/v1/news/unread-count")
        assert resp.status_code == 200
        assert resp.json()["data"]["count"] == 2


class TestNewsRouterNoNetworkImports:
    def test_no_forbidden_imports(self):
        """AC6: news router must never do network I/O (read-only endpoints)."""
        import inspect

        import src.api.routers.news as news_module

        source = inspect.getsource(news_module)
        forbidden = ["news_fetcher", "httpx", "feedparser", "requests"]
        for name in forbidden:
            assert f"import {name}" not in source and f"from {name}" not in source, (
                f"news.py must not import {name}"
            )


class TestUnreadCount:
    def test_unread_count_all_unread(self, client, repo):
        _seed_news(repo, 3)
        resp = client.get("/api/v1/news/unread-count")
        assert resp.status_code == 200
        assert resp.json()["data"]["count"] == 3

    def test_unread_count_some_read(self, client, repo, user):
        ids = _seed_news(repo, 3)
        repo.mark_news_read(user.id, ids[0])
        repo.mark_news_read(user.id, ids[1])
        resp = client.get("/api/v1/news/unread-count")
        assert resp.status_code == 200
        assert resp.json()["data"]["count"] == 1

    def test_unread_count_empty(self, client):
        resp = client.get("/api/v1/news/unread-count")
        assert resp.status_code == 200
        assert resp.json()["data"]["count"] == 0
