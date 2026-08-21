"""OAuth provider configuration."""

from __future__ import annotations

import os

# Well-known OAuth endpoints for each provider
_PROVIDER_ENDPOINTS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scopes": ["openid", "email", "profile"],
    },
    "microsoft": {
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/v1.0/me",
        "scopes": ["openid", "email", "profile"],
    },
    "apple": {
        "authorize_url": "https://appleid.apple.com/auth/authorize",
        "token_url": "https://appleid.apple.com/auth/token",
        "userinfo_url": None,  # Apple returns user info in the ID token
        "scopes": ["name", "email"],
    },
}


def get_oauth_config(provider: str) -> dict:
    """Return OAuth configuration for the given provider.

    Reads client_id and client_secret from environment variables:
      TCG_OAUTH_{PROVIDER}_CLIENT_ID
      TCG_OAUTH_{PROVIDER}_CLIENT_SECRET

    Returns dict with: client_id, client_secret, authorize_url, token_url,
    userinfo_url, scopes.
    """
    provider_lower = provider.lower()
    if provider_lower not in _PROVIDER_ENDPOINTS:
        raise ValueError(f"Unknown OAuth provider: {provider}")

    prefix = f"TCG_OAUTH_{provider.upper()}"
    endpoints = _PROVIDER_ENDPOINTS[provider_lower]

    return {
        "client_id": os.environ.get(f"{prefix}_CLIENT_ID", ""),
        "client_secret": os.environ.get(f"{prefix}_CLIENT_SECRET", ""),
        **endpoints,
    }
