"""Authentication router — register, login, OAuth, refresh, logout, profile."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response

from src.api.deps import get_current_user, get_db
from src.api.schemas.auth import (
    AuthTokens,
    ChangePasswordRequest,
    LoginRequest,
    PreferencesUpdate,
    RefreshRequest,
    RegisterRequest,
    UserProfile,
)
from src.api.schemas.envelope import ApiResponse, success_response
from src.auth.jwt import create_access_token, create_refresh_token, decode_token
from src.auth.passwords import hash_password, verify_password
from src.database.repository import Repository
from src.domain.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=ApiResponse[AuthTokens])
def register(
    body: RegisterRequest,
    repo: Repository = Depends(get_db),
):
    """Register a new user with email and password."""
    existing = repo.get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    pw_hash = hash_password(body.password)
    user = repo.create_user(
        email=body.email,
        display_name=body.display_name,
        auth_provider="email",
        password_hash=pw_hash,
    )

    tokens = AuthTokens(
        access_token=create_access_token(user.id, user.email),
        refresh_token=create_refresh_token(user.id),
    )
    return success_response(data=tokens)


@router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    repo: Repository = Depends(get_db),
):
    """Authenticate with email and password."""
    user = repo.get_user_by_email(body.email)
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")

    # Check password expiration (admin-created users with temporary passwords)
    password_expires_at = getattr(user, "password_expires_at", None)
    if (
        password_expires_at is not None
        and isinstance(password_expires_at, datetime)
        and password_expires_at <= datetime.now()
    ):
        temp_token = create_access_token(user.id, user.email, expires_minutes=5)
        return success_response(
            data={
                "access_token": temp_token,
                "refresh_token": None,
                "password_expired": True,
            }
        )

    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id)

    # Set cookie for browser clients
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=1440 * 60,  # 24 hours
    )

    tokens = AuthTokens(
        access_token=access_token,
        refresh_token=refresh_token,
    )
    return success_response(data=tokens)


@router.get("/me", response_model=ApiResponse[UserProfile])
def get_me(user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    pw_exp = getattr(user, "password_expires_at", None)
    must_change = pw_exp is not None and isinstance(pw_exp, datetime) and pw_exp <= datetime.now()
    profile = UserProfile(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        auth_provider=user.auth_provider,
        preferred_currency=user.preferred_currency,
        preferred_language=user.preferred_language,
        is_active=user.is_active,
        is_admin=user.is_admin,
        must_change_password=must_change,
    )
    return success_response(data=profile)


@router.patch("/me/preferences", response_model=ApiResponse[UserProfile])
def update_preferences(
    body: PreferencesUpdate,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Update the current user's preferences (e.g. preferred currency, language)."""
    updates: dict = {}
    if body.preferred_currency is not None:
        updates["preferred_currency"] = body.preferred_currency
    if body.preferred_language is not None:
        updates["preferred_language"] = body.preferred_language

    if not updates:
        raise HTTPException(status_code=422, detail="No preferences provided")

    updated = repo.update_user(user.id, **updates)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    profile = UserProfile(
        id=updated.id,
        email=updated.email,
        display_name=updated.display_name,
        avatar_url=updated.avatar_url,
        auth_provider=updated.auth_provider,
        preferred_currency=updated.preferred_currency,
        preferred_language=updated.preferred_language,
        is_active=bool(updated.is_active),
        is_admin=bool(updated.is_admin),
    )
    return success_response(data=profile)


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Change the current user's password. Clears password expiration."""
    db_user = repo.get_user_by_id(user.id)
    if not db_user or not db_user.password_hash:
        raise HTTPException(status_code=400, detail="Password change not available")

    if not verify_password(body.current_password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    new_hash = hash_password(body.new_password)
    repo.update_user(user.id, password_hash=new_hash, password_expires_at=None)

    tokens = AuthTokens(
        access_token=create_access_token(user.id, user.email),
        refresh_token=create_refresh_token(user.id),
    )
    return success_response(data=tokens)


@router.get("/{provider}")
def oauth_redirect(provider: str):
    """Redirect to OAuth provider's authorization page."""
    from src.auth.oauth import get_oauth_config

    try:
        config = get_oauth_config(provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown OAuth provider: {provider}")

    if not config["client_id"]:
        raise HTTPException(
            status_code=501,
            detail=f"OAuth provider {provider} is not configured",
        )

    # Build authorization URL
    params = {
        "client_id": config["client_id"],
        "redirect_uri": f"/api/v1/auth/{provider}/callback",
        "response_type": "code",
        "scope": " ".join(config["scopes"]),
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    auth_url = f"{config['authorize_url']}?{query}"

    return {"redirect_url": auth_url}


@router.get("/{provider}/callback", response_model=ApiResponse[AuthTokens])
def oauth_callback(
    provider: str,
    code: str | None = None,
    repo: Repository = Depends(get_db),
):
    """Handle OAuth callback (placeholder — full flow requires authlib setup)."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # In a full implementation, exchange code for tokens via authlib
    # For now, return a 501 indicating the flow is not yet implemented
    raise HTTPException(
        status_code=501,
        detail="OAuth callback flow not yet implemented. Use email/password login.",
    )


@router.post("/refresh", response_model=ApiResponse[AuthTokens])
def refresh_token(
    body: RefreshRequest,
    repo: Repository = Depends(get_db),
):
    """Exchange a refresh token for new access + refresh tokens."""
    from jose import JWTError

    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = int(payload["sub"])
    user = repo.get_user_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    tokens = AuthTokens(
        access_token=create_access_token(user.id, user.email),
        refresh_token=create_refresh_token(user.id),
    )
    return success_response(data=tokens)


@router.post("/logout")
def logout(response: Response):
    """Clear auth cookies."""
    response.delete_cookie("access_token")
    return success_response(data={"message": "Logged out"})
