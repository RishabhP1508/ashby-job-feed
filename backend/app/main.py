"""FastAPI service for the Ashby job-feed dashboard.

Public endpoints:
  GET    /api/health              liveness check
  GET    /api/board/{slug}        normalized, cached job feed for one Ashby board

Auth endpoints:
  POST   /api/auth/register       create an account, set the session cookie
  POST   /api/auth/login          verify credentials, set the session cookie
  POST   /api/auth/logout         clear the session cookie
  GET    /api/auth/me             the current account, or 401

Saved searches (require login, scoped to the current user):
  GET    /api/searches            list (sort=recent|popular)
  POST   /api/searches            save the current companies and filters
  POST   /api/searches/{id}/use   record that a saved search was reopened
  DELETE /api/searches/{id}       delete a saved search

If a built frontend exists at frontend/dist, it is served too, so the whole
project can run as one deployable app.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import db
from .ashby import fetch_board
from .auth import (
    check_signing_secret,
    clear_auth_cookie,
    current_user,
    hash_password,
    make_token,
    set_auth_cookie,
    verify_password,
)
from .cache import TTLCache
from .db import User, get_session
from .models import BoardResponse, Job
from .ratelimit import RateLimiter


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    check_signing_secret()
    # Local SQLite is a throwaway dev database, so create tables on the fly.
    # Postgres (production) is migrated with Alembic (`alembic upgrade head`).
    if db.DATABASE_URL.startswith("sqlite"):
        db.init_db()
    yield


app = FastAPI(title="Ashby Job Feed API", version="2.0.0", lifespan=lifespan)

_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

cache = TTLCache(ttl_seconds=int(os.getenv("CACHE_TTL", "300")))
auth_limiter = RateLimiter(max_attempts=10, window_seconds=300)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _log_fetch(slug: str, job_count: int) -> None:
    """Record that a board was fetched, as a discovery signal.

    Runs as a background task, so it is off the event loop and the response has
    already been sent. It opens its own session on purpose: the request-scoped
    one from get_session is closed by the time this runs.
    """
    try:
        with db.SessionLocal() as session:
            db.record_fetch(session, slug, job_count)
    except Exception:  # noqa: BLE001 - a discovery write must never matter
        logging.exception("could not record board fetch for %s", slug)


# ---- job feed (public) ----
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/board/{slug}", response_model=BoardResponse)
async def board(slug: str, background: BackgroundTasks) -> BoardResponse:
    slug = slug.strip().lower()
    if not slug or "/" in slug:
        raise HTTPException(status_code=400, detail="Invalid company handle.")

    cached_jobs = cache.get(slug)
    if cached_jobs is not None:
        jobs, was_cached = cached_jobs, True
    else:
        try:
            jobs = await fetch_board(slug)
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code == 404:
                raise HTTPException(status_code=404, detail=f"No Ashby board found for '{slug}'.")
            raise HTTPException(status_code=502, detail=f"Ashby returned {code} for '{slug}'.")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Could not reach Ashby: {exc}")
        cache.set(slug, jobs)
        was_cached = False
        # Misses only. This endpoint is public and otherwise touches no database,
        # so logging every view would wake a scale-to-zero Postgres on each
        # anonymous browse. Repeat views inside the cache TTL are free, and
        # undercounting is fine for a discovery signal.
        background.add_task(_log_fetch, slug, len(jobs))

    return BoardResponse(
        slug=slug,
        fetchedAt=datetime.now(timezone.utc).isoformat(),
        cached=was_cached,
        count=len(jobs),
        jobs=[Job(**j) for j in jobs],
    )


# ---- auth ----
class AuthIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str


def _validate_credentials(email: str, password: str) -> str:
    email = email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password is too long.")
    return email


@app.post("/api/auth/register", response_model=UserOut)
def register(
    payload: AuthIn,
    response: Response,
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    auth_limiter.check(f"register:{_client_ip(request)}")
    email = _validate_credentials(payload.email, payload.password)
    if db.get_user_by_email(session, email) is not None:
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    user = db.create_user(session, email, hash_password(payload.password))
    set_auth_cookie(response, make_token(user.id))
    return {"id": user.id, "email": user.email}


@app.post("/api/auth/login", response_model=UserOut)
def login(
    payload: AuthIn,
    response: Response,
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    auth_limiter.check(f"login:{_client_ip(request)}")
    email = payload.email.strip().lower()
    user = db.get_user_by_email(session, email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    set_auth_cookie(response, make_token(user.id))
    return {"id": user.id, "email": user.email}


@app.post("/api/auth/logout")
def logout(response: Response) -> dict[str, bool]:
    clear_auth_cookie(response)
    return {"ok": True}


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> dict[str, Any]:
    return {"id": user.id, "email": user.email}


# ---- saved searches (require login) ----
class SaveSearchIn(BaseModel):
    name: str = ""
    companies: list[str] = []
    filters: dict[str, Any] = {}


class SavedSearch(BaseModel):
    id: int
    name: str
    companies: list[str]
    filters: dict[str, Any]
    useCount: int
    createdAt: str
    lastUsedAt: str


@app.get("/api/searches", response_model=list[SavedSearch])
def get_searches(
    sort: str = Query("recent", pattern="^(recent|popular)$"),
    limit: int = Query(12, ge=1, le=50),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return db.list_searches(session, user.id, sort=sort, limit=limit)


@app.post("/api/searches", response_model=SavedSearch)
def create_search(
    payload: SaveSearchIn,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    companies = [c.strip() for c in payload.companies if c.strip()]
    if not companies:
        raise HTTPException(status_code=400, detail="A saved search needs at least one company.")
    return db.save_search(session, user.id, payload.name, companies, payload.filters)


@app.post("/api/searches/{search_id}/use", response_model=SavedSearch)
def use_search(
    search_id: int,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    row = db.touch_search(session, user.id, search_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Saved search not found.")
    return row


@app.delete("/api/searches/{search_id}")
def remove_search(
    search_id: int,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> dict[str, bool]:
    if not db.delete_search(session, user.id, search_id):
        raise HTTPException(status_code=404, detail="Saved search not found.")
    return {"deleted": True}


# ---- last-seen watermark (require login) ----
class SeenOut(BaseModel):
    lastSeenAt: str | None


@app.get("/api/seen", response_model=SeenOut)
def get_seen(
    user: User = Depends(current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    return {"lastSeenAt": db.get_last_seen(session, user.id)}


@app.post("/api/seen", response_model=SeenOut)
def mark_seen(
    user: User = Depends(current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    return {"lastSeenAt": db.update_last_seen(session, user.id)}


# ---- application tracking (require login) ----
class ApplicationOut(BaseModel):
    jobKey: str
    status: str
    updatedAt: str


class ApplicationIn(BaseModel):
    jobKey: str
    status: str  # one of applied|interviewing|rejected|offer, or "" to clear


@app.get("/api/applications", response_model=list[ApplicationOut])
def get_applications(
    user: User = Depends(current_user), session: Session = Depends(get_session)
) -> list[dict[str, Any]]:
    return db.list_applications(session, user.id)


@app.put("/api/applications")
def put_application(
    payload: ApplicationIn,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    key = payload.jobKey.strip()
    if not key:
        raise HTTPException(status_code=400, detail="Missing job identifier.")
    status = payload.status.strip().lower()
    if status and status not in db.VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Unknown status.")
    result = db.set_application(session, user.id, key, status)
    return {"jobKey": key, "status": status, "cleared": result is None}


# ---- serve the built frontend, if present (single-service deploy) ----
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.is_dir():
    _ASSETS = _DIST / "assets"
    if _ASSETS.is_dir():
        app.mount("/assets", StaticFiles(directory=_ASSETS), name="assets")

    # HEAD too, so link unfurlers get a preview instead of a 405.
    @app.api_route("/", methods=["GET", "HEAD"])
    def _index() -> FileResponse:
        return FileResponse(_DIST / "index.html")

    @app.get("/{full_path:path}")
    def _spa(full_path: str) -> FileResponse:
        # An unmatched /api path must not fall through to the SPA shell, or the
        # caller gets 200 and HTML where it expects JSON. Real API routes are
        # registered above and never reach this.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Unknown API route.")
        candidate = _DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
