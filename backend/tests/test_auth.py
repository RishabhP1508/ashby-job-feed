import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password, verify_password


@pytest.fixture()
def client():
    import app.main as main_module

    main_module.cache._store.clear()
    with TestClient(main_module.app) as c:
        yield c


def test_password_hash_roundtrip():
    h = hash_password("password123")
    assert h != "password123"
    assert verify_password("password123", h) is True
    assert verify_password("wrongpass", h) is False


def test_register_login_me_logout_flow(client):
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "a@b.com"

    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401

    again = client.post("/api/auth/login", json={"email": "a@b.com", "password": "password123"})
    assert again.status_code == 200


def test_register_rejects_bad_input(client):
    assert client.post("/api/auth/register", json={"email": "nope", "password": "password123"}).status_code == 400
    assert client.post("/api/auth/register", json={"email": "a@b.com", "password": "short"}).status_code == 400


def test_duplicate_email_rejected(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "password123"})
    dup = client.post("/api/auth/register", json={"email": "a@b.com", "password": "password123"})
    assert dup.status_code == 409


def test_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "password123"})
    client.post("/api/auth/logout")
    bad = client.post("/api/auth/login", json={"email": "a@b.com", "password": "wrongpass1"})
    assert bad.status_code == 401


def test_saved_searches_require_login(client):
    assert client.get("/api/searches").status_code == 401
    assert client.post("/api/searches", json={"name": "x", "companies": ["openai"], "filters": {}}).status_code == 401


def test_saved_searches_scoped_to_user(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "password123"})
    client.post("/api/searches", json={"name": "A search", "companies": ["openai"], "filters": {}})
    assert len(client.get("/api/searches").json()) == 1

    client.post("/api/auth/logout")
    client.post("/api/auth/register", json={"email": "b@b.com", "password": "password123"})
    assert client.get("/api/searches").json() == []
    client.post("/api/searches", json={"name": "B search", "companies": ["ramp"], "filters": {}})
    only = client.get("/api/searches").json()
    assert len(only) == 1
    assert only[0]["name"] == "B search"
