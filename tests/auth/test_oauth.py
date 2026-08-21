"""Tests for OAuth configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from src.auth.oauth import get_oauth_config


class TestGetOAuthConfig:
    def test_google_config(self):
        config = get_oauth_config("google")
        assert "authorize_url" in config
        assert "token_url" in config
        assert "accounts.google.com" in config["authorize_url"]
        assert isinstance(config["scopes"], list)

    def test_microsoft_config(self):
        config = get_oauth_config("microsoft")
        assert "login.microsoftonline.com" in config["authorize_url"]

    def test_apple_config(self):
        config = get_oauth_config("apple")
        assert "appleid.apple.com" in config["authorize_url"]
        assert config["userinfo_url"] is None

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown OAuth provider"):
            get_oauth_config("github")

    def test_reads_env_vars(self):
        with patch.dict(
            os.environ,
            {
                "TCG_OAUTH_GOOGLE_CLIENT_ID": "my-id",
                "TCG_OAUTH_GOOGLE_CLIENT_SECRET": "my-secret",
            },
        ):
            config = get_oauth_config("google")
            assert config["client_id"] == "my-id"
            assert config["client_secret"] == "my-secret"

    def test_case_insensitive_provider(self):
        config = get_oauth_config("Google")
        assert "authorize_url" in config

    def test_empty_env_defaults(self):
        config = get_oauth_config("google")
        assert config["client_id"] == ""
        assert config["client_secret"] == ""
