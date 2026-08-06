import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import settings

PBKDF2_ITERATIONS = 600_000
PBKDF2_ALGORITHM = "pbkdf2_sha256"
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hashes a password with PBKDF2-SHA256 and a random per-user salt."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verifies a password against a stored PBKDF2 hash string."""
    try:
        algorithm, iterations_str, salt_hex, hash_hex = hashed.split("$")
        if algorithm != PBKDF2_ALGORITHM:
            return False
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError):
        return False

    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(dk, expected)


def create_access_token(
    subject: str, expires_delta: timedelta | None = None
) -> str:
    """Creates a signed JWT access token for the given subject (user id)."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decodes and validates a JWT access token."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
