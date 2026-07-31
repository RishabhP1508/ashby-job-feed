import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import db


@pytest.fixture()
def client():
    import app.main as main_module

    main_module.cache._store.clear()
    with TestClient(main_module.app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_board_uses_cache_on_second_call(client, monkeypatch):
    async def fake_fetch(slug: str):
        return [{"company": slug, "title": "Role"}]

    monkeypatch.setattr("app.main.fetch_board", fake_fetch)

    first = client.get("/api/board/openai")
    assert first.status_code == 200
    assert first.json()["cached"] is False
    second = client.get("/api/board/openai")
    assert second.json()["cached"] is True


def test_board_maps_upstream_404(client, monkeypatch):
    async def fake_fetch(slug: str):
        raise httpx.HTTPStatusError(
            "not found",
            request=httpx.Request("GET", "https://api.ashbyhq.com/x"),
            response=httpx.Response(404),
        )

    monkeypatch.setattr("app.main.fetch_board", fake_fetch)
    assert client.get("/api/board/missing").status_code == 404


def _logged_slugs():
    """Read the discovery log through a fresh session.

    Background tasks run on another thread, so this also proves the write really
    landed in the test database rather than failing a SQLite thread check.
    """
    with db.SessionLocal() as session:
        return {r.slug: r.fetch_count for r in session.execute(select(db.BoardFetch)).scalars()}


def test_cache_miss_logs_the_fetch_and_a_hit_does_not(client, monkeypatch):
    async def fake_fetch(slug: str):
        return [{"company": slug, "title": "Role"}]

    monkeypatch.setattr("app.main.fetch_board", fake_fetch)

    assert client.get("/api/board/logme").json()["cached"] is False
    assert _logged_slugs() == {"logme": 1}, "a cache miss records the fetch"

    # Second call is served from the TTL cache, so it must not touch the database.
    assert client.get("/api/board/logme").json()["cached"] is True
    assert _logged_slugs() == {"logme": 1}, "a cache hit must not record anything"


def test_board_still_succeeds_when_logging_raises(client, monkeypatch):
    async def fake_fetch(slug: str):
        return [{"company": slug, "title": "Role"}]

    def boom(*_args, **_kwargs):
        raise RuntimeError("database is down")

    monkeypatch.setattr("app.main.fetch_board", fake_fetch)
    monkeypatch.setattr("app.main.db.record_fetch", boom)

    res = client.get("/api/board/boomco")
    assert res.status_code == 200
    assert res.json()["count"] == 1
    assert _logged_slugs() == {}, "the failed write left nothing behind"


def test_searches_crud_when_logged_in(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "password123"})

    assert client.get("/api/searches").json() == []

    bad = client.post("/api/searches", json={"name": "x", "companies": [], "filters": {}})
    assert bad.status_code == 400

    created = client.post(
        "/api/searches",
        json={"name": "OpenAI", "companies": ["openai"], "filters": {"datePreset": "7"}},
    )
    assert created.status_code == 200
    sid = created.json()["id"]

    listed = client.get("/api/searches?sort=recent").json()
    assert len(listed) == 1

    used = client.post(f"/api/searches/{sid}/use")
    assert used.status_code == 200
    assert used.json()["useCount"] == 1

    assert client.delete(f"/api/searches/{sid}").status_code == 200
    assert client.post(f"/api/searches/{sid}/use").status_code == 404
