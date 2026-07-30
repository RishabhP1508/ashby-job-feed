"""Authentication: password hashing, JWT issuing, and the current-user dependency.

The token is stored in an httpOnly cookie, so the browser sends it automatically
and JavaScript cannot read it.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .db import DATABASE_URL, User, get_session

DEV_SECRET = "dev-insecure-secret-change-me"
# `or` rather than a getenv default, so JWT_SECRET="" counts as unset too.
JWT_SECRET = os.getenv("JWT_SECRET") or DEV_SECRET
JWT_ALG = "HS256"
TOKEN_TTL_HOURS = int(os.getenv("TOKEN_TTL_HOURS", "168"))  # 7 days
COOKIE_NAME = "session"

# A split deploy makes the session cookie cross-site, which needs SameSite=None.
# Unrecognized values fall back to "lax": a typo should not quietly emit a
# cookie the browser refuses.
_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()
COOKIE_SAMESITE = _SAMESITE if _SAMESITE in {"lax", "strict", "none"} else "lax"
# Browsers reject SameSite=None unless the cookie is also Secure.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true" or COOKIE_SAMESITE == "none"


def check_signing_secret() -> None:
    """Refuse to start a production-like deploy that still uses the dev secret."""
    if JWT_SECRET != DEV_SECRET:
        return
    if not DATABASE_URL.startswith("sqlite") or COOKIE_SECURE:
        raise RuntimeError(
            "JWT_SECRET is unset or still the dev default, but this looks like a "
            "production deploy. Set JWT_SECRET to a long random value: "
            'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def make_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(hours=TOKEN_TTL_HOURS)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=TOKEN_TTL_HOURS * 3600,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    # The deletion cookie has to carry the same attributes as the one it
    # replaces, or a cross-site browser ignores it and the session survives.
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )


def _user_id_from_token(token: str | None) -> int | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def current_user(request: Request, session: Session = Depends(get_session)) -> User:
    user_id = _user_id_from_token(request.cookies.get(COOKIE_NAME))
    user = session.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user
