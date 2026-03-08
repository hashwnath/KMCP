"""Tests for auth module."""

from src.admin.auth import (
    hash_password, verify_password, create_access_token,
    decode_access_token, generate_api_key,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        h = hash_password("secret")
        assert verify_password("secret", h)

    def test_wrong_password(self):
        h = hash_password("secret")
        assert not verify_password("wrong", h)


class TestJwt:
    def test_roundtrip(self):
        token = create_access_token({"tenant_id": "t1", "email": "a@b.c"})
        claims = decode_access_token(token)
        assert claims["tenant_id"] == "t1"

    def test_invalid_token(self):
        assert decode_access_token("garbage") is None


class TestApiKey:
    def test_prefix(self):
        key = generate_api_key()
        assert key.startswith("kmcp_sk_")

    def test_unique(self):
        assert generate_api_key() != generate_api_key()
