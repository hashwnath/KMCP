"""JWT-based authentication for the KnowledgeMCP admin dashboard API."""

import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.common.config import get_config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(
    data: dict, expires_delta: timedelta = timedelta(hours=24)
) -> str:
    """Create a signed JWT access token with the given payload and expiry."""
    config = get_config()
    if not config.jwt_secret_key:
        raise ValueError(
            "JWT_SECRET_KEY environment variable is not set. "
            "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
        )
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(to_encode, config.jwt_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token. Returns claims or None if invalid."""
    config = get_config()
    try:
        return jwt.decode(token, config.jwt_secret_key, algorithms=["HS256"])
    except JWTError:
        return None


def generate_api_key() -> str:
    """Generate a secure API key with the 'kmcp_sk_' prefix."""
    return f"kmcp_sk_{secrets.token_urlsafe(32)}"
