"""Tests for auth domain models."""

from __future__ import annotations

from src.domain.models import AuthProvider, User


class TestAuthProvider:
    def test_values(self):
        assert AuthProvider.EMAIL == "email"
        assert AuthProvider.GOOGLE == "google"
        assert AuthProvider.MICROSOFT == "microsoft"
        assert AuthProvider.APPLE == "apple"

    def test_is_str_enum(self):
        assert isinstance(AuthProvider.EMAIL, str)


class TestUser:
    def test_defaults(self):
        user = User(id=1, email="test@example.com")
        assert user.display_name is None
        assert user.avatar_url is None
        assert user.auth_provider == "email"
        assert user.is_active is True

    def test_all_fields(self):
        user = User(
            id=42,
            email="full@test.com",
            display_name="Test User",
            avatar_url="https://example.com/avatar.png",
            auth_provider="google",
            is_active=False,
        )
        assert user.id == 42
        assert user.email == "full@test.com"
        assert user.display_name == "Test User"
        assert user.auth_provider == "google"
        assert user.is_active is False
