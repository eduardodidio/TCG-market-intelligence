"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    id: int
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    auth_provider: str
    preferred_currency: str = "BRL"
    preferred_language: str = "en"
    is_active: bool


class PreferencesUpdate(BaseModel):
    preferred_currency: str | None = Field(None, pattern="^(BRL|USD|PILA)$")
    preferred_language: str | None = Field(None, pattern="^(en|pt-BR)$")
