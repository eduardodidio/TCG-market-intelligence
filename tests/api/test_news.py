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
