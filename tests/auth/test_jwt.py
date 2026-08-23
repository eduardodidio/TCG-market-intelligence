"""Tests for JWT token creation and validation."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from jose import JWTError

from src.auth.jwt import create_access_token, create_refresh_token, decode_token


class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token(user_id=1, email="test@example.com")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_contains_expected_claims(self):
        token = create_access_token(user_id=42, email="user@test.com")
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["email"] == "user@test.com"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload


class TestCreateRefreshToken:
    def test_returns_string(self):
        token = create_refresh_token(user_id=1)
        assert isinstance(token, str)

    def test_token_contains_refresh_type(self):
        token = create_refresh_token(user_id=7)
        payload = decode_token(token)
        assert payload["sub"] == "7"
        assert payload["type"] == "refresh"


class TestDecodeToken:
    def test_valid_access_token(self):
        token = create_access_token(user_id=5, email="a@b.com")
        payload = decode_token(token)
        assert payload["sub"] == "5"
        assert payload["email"] == "a@b.com"

    def test_invalid_token_raises(self):
        with pytest.raises(JWTError):
            decode_token("not.a.valid.token")

    def test_tampered_token_raises(self):
        token = create_access_token(user_id=1, email="x@y.com")
        # Tamper with the token
        tampered = token[:-4] + "XXXX"
        with pytest.raises(JWTError):
            decode_token(tampered)

    def test_custom_secret_via_env(self):
        with patch.dict(os.environ, {"TCG_JWT_SECRET": "my-test-secret-123"}):
            token = create_access_token(user_id=10, email="env@test.com")
            payload = decode_token(token)
            assert payload["sub"] == "10"

    def test_missing_secret_raises_runtime_error(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove TCG_JWT_SECRET entirely
            os.environ.pop("TCG_JWT_SECRET", None)
            with pytest.raises(RuntimeError, match="TCG_JWT_SECRET"):
                create_access_token(user_id=1, email="x@y.com")
