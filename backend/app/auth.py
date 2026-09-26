"""Local password and session primitives for the self-hosted foundation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import secrets


PBKDF2_ITERATIONS = 310_000
SESSION_TTL = timedelta(hours=8)
MAX_LOGIN_FAILURES = 5
LOCKOUT = timedelta(minutes=15)


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("password must be at least 12 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode(), base64.urlsafe_b64encode(digest).decode())


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                     base64.urlsafe_b64decode(salt), int(iterations))
        return hmac.compare_digest(base64.urlsafe_b64encode(digest).decode(), expected)
    except (ValueError, TypeError):
        return False


def new_session() -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    return secrets.token_urlsafe(32), secrets.token_urlsafe(24), now + SESSION_TTL


def new_api_key() -> tuple[str, str, str]:
    secret = "dp_" + secrets.token_urlsafe(32)
    return secret, secret[:11], hashlib.sha256(secret.encode()).hexdigest()
