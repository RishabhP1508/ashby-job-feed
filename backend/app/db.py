"""Database layer: SQLAlchemy models, engine, session, and per-user CRUD.

Uses DATABASE_URL. It defaults to a local SQLite file for development and takes
a PostgreSQL URL in production, so the same code runs against both.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
    # Managed Postgres providers often hand out postgres:// URLs;
    # SQLAlchemy expects the postgresql+psycopg2:// form.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://") :]
    return url


DATABASE_URL = _database_url()
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

if DATABASE_URL.startswith("sqlite:///") and ":memory:" not in DATABASE_URL:
    _file = DATABASE_URL[len("sqlite:///") :]
    Path(_file).resolve().parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # When the user last marked the feed as seen; used to badge newer roles.
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    searches: Mapped[list["SavedSearch"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class SavedSearch(Base):
    __tablename__ = "saved_searches"
    __table_args__ = (UniqueConstraint("user_id", "signature", name="uq_user_signature"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    signature: Mapped[str] = mapped_column(String(64))
    companies: Mapped[str] = mapped_column(Text)
    filters: Mapped[str] = mapped_column(Text)
    use_count: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user: Mapped["User"] = relationship(back_populates="searches")


class Application(Base):
    """A user's tracked status for one job, keyed by the job's apply URL."""

    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "job_key", name="uq_user_job"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_key: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user: Mapped["User"] = relationship(back_populates="applications")


VALID_STATUSES = {"applied", "interviewing", "rejected", "offer"}


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    """Serialize a stored datetime as UTC ISO 8601.

    SQLite does not preserve tzinfo, so a value read back can be naive. We always
    store UTC, so treat a naive value as UTC. This keeps the output identical
    across SQLite and Postgres and between a just-written value and a re-read one.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


# ---- users ----
def create_user(session: Session, email: str, password_hash: str) -> User:
    user = User(email=email, password_hash=password_hash, created_at=_now())
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.execute(select(User).where(User.email == email)).scalar_one_or_none()


# ---- saved searches (all scoped to a user) ----
def _signature(companies: list[str], filters: dict[str, Any]) -> str:
    canon_companies = ",".join(sorted({c.strip().lower() for c in companies if c.strip()}))
    canon_filters = json.dumps(filters, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{canon_companies}|{canon_filters}".encode()).hexdigest()


def _to_dict(s: SavedSearch) -> dict[str, Any]:
    return {
        "id": s.id,
        "name": s.name,
        "companies": json.loads(s.companies),
        "filters": json.loads(s.filters),
        "useCount": s.use_count,
        "createdAt": _iso(s.created_at),
        "lastUsedAt": _iso(s.last_used_at),
    }


def save_search(
    session: Session, user_id: int, name: str, companies: list[str], filters: dict[str, Any]
) -> dict[str, Any]:
    sig = _signature(companies, filters)
    now = _now()
    existing = session.execute(
        select(SavedSearch).where(
            SavedSearch.user_id == user_id, SavedSearch.signature == sig
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.use_count += 1
        existing.last_used_at = now
        if name.strip():
            existing.name = name.strip()
        session.commit()
        session.refresh(existing)
        return _to_dict(existing)

    row = SavedSearch(
        user_id=user_id,
        name=name.strip() or "Untitled search",
        signature=sig,
        companies=json.dumps(companies),
        filters=json.dumps(filters),
        use_count=1,
        created_at=now,
        last_used_at=now,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_dict(row)


def list_searches(
    session: Session, user_id: int, sort: str = "recent", limit: int = 12
) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 50))
    stmt = select(SavedSearch).where(SavedSearch.user_id == user_id)
    if sort == "popular":
        stmt = stmt.order_by(SavedSearch.use_count.desc(), SavedSearch.last_used_at.desc())
    else:
        stmt = stmt.order_by(SavedSearch.last_used_at.desc())
    rows = session.execute(stmt.limit(limit)).scalars().all()
    return [_to_dict(s) for s in rows]


def touch_search(session: Session, user_id: int, search_id: int) -> dict[str, Any] | None:
    row = session.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id, SavedSearch.user_id == user_id
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    row.use_count += 1
    row.last_used_at = _now()
    session.commit()
    session.refresh(row)
    return _to_dict(row)


def delete_search(session: Session, user_id: int, search_id: int) -> bool:
    row = session.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id, SavedSearch.user_id == user_id
        )
    ).scalar_one_or_none()
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True


# ---- last-seen watermark ----
def get_last_seen(session: Session, user_id: int) -> str | None:
    user = session.get(User, user_id)
    if user is None or user.last_seen_at is None:
        return None
    return _iso(user.last_seen_at)


def update_last_seen(session: Session, user_id: int) -> str:
    user = session.get(User, user_id)
    user.last_seen_at = _now()
    session.commit()
    return _iso(user.last_seen_at)


# ---- application tracking ----
def list_applications(session: Session, user_id: int) -> list[dict[str, Any]]:
    rows = session.execute(
        select(Application).where(Application.user_id == user_id)
    ).scalars().all()
    return [
        {"jobKey": r.job_key, "status": r.status, "updatedAt": _iso(r.updated_at)}
        for r in rows
    ]


def set_application(
    session: Session, user_id: int, job_key: str, status: str
) -> dict[str, Any] | None:
    """Upsert a job's status. An empty status clears (deletes) the row."""
    existing = session.execute(
        select(Application).where(
            Application.user_id == user_id, Application.job_key == job_key
        )
    ).scalar_one_or_none()

    if not status:
        if existing is not None:
            session.delete(existing)
            session.commit()
        return None

    now = _now()
    if existing is not None:
        existing.status = status
        existing.updated_at = now
        session.commit()
        return {"jobKey": existing.job_key, "status": existing.status, "updatedAt": _iso(now)}

    row = Application(
        user_id=user_id, job_key=job_key, status=status, created_at=now, updated_at=now
    )
    session.add(row)
    session.commit()
    return {"jobKey": row.job_key, "status": row.status, "updatedAt": _iso(now)}
