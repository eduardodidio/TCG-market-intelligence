"""Tests for password hashing and verification."""

from __future__ import annotations

from src.auth.passwords import hash_password, verify_password


class TestHashPassword:
    def test_returns_bcrypt_hash(self):
        hashed = hash_password("mysecret")
        assert hashed.startswith("$2")
        assert len(hashed) > 50

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("test")
        h2 = hash_password("test")
        assert h1 != h2  # salt differs


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        hashed = hash_password("correct-horse")
        assert verify_password("correct-horse", hashed) is True

    def test_wrong_password_returns_false(self):
        hashed = hash_password("correct-horse")
        assert verify_password("wrong-horse", hashed) is False

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False
