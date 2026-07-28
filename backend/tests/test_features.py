import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    import app.main as main_module

    with TestClient(main_module.app) as c:
        yield c


def _register(client, email="a@b.com"):
    return client.post("/api/auth/register", json={"email": email, "password": "password123"})


def test_login_is_rate_limited(client):
    _register(client)
    client.post("/api/auth/logout")
    codes = [
        client.post("/api/auth/login", json={"email": "a@b.com", "password": "wrongpass1"}).status_code
        for _ in range(11)
    ]
    assert codes.count(401) == 10
    assert codes[-1] == 429


def test_watermark_defaults_null_then_updates(client):
    _register(client)
    assert client.get("/api/seen").json()["lastSeenAt"] is None
    marked = client.post("/api/seen").json()["lastSeenAt"]
    assert marked is not None
    assert client.get("/api/seen").json()["lastSeenAt"] == marked


def test_watermark_requires_login(client):
    assert client.get("/api/seen").status_code == 401
    assert client.post("/api/seen").status_code == 401


def test_application_tracking_crud(client):
    _register(client)
    assert client.get("/api/applications").json() == []

    bad = client.put("/api/applications", json={"jobKey": "https://x/apply", "status": "banana"})
    assert bad.status_code == 400

    set_applied = client.put("/api/applications", json={"jobKey": "https://x/apply", "status": "applied"})
    assert set_applied.status_code == 200
    assert set_applied.json()["status"] == "applied"

    listed = client.get("/api/applications").json()
    assert len(listed) == 1
    assert listed[0]["jobKey"] == "https://x/apply"
    assert listed[0]["status"] == "applied"

    client.put("/api/applications", json={"jobKey": "https://x/apply", "status": "interviewing"})
    assert client.get("/api/applications").json()[0]["status"] == "interviewing"

    cleared = client.put("/api/applications", json={"jobKey": "https://x/apply", "status": ""})
    assert cleared.json()["cleared"] is True
    assert client.get("/api/applications").json() == []


def test_applications_require_login_and_are_isolated(client):
    assert client.get("/api/applications").status_code == 401

    _register(client, "a@b.com")
    client.put("/api/applications", json={"jobKey": "k1", "status": "applied"})
    client.post("/api/auth/logout")

    _register(client, "b@b.com")
    assert client.get("/api/applications").json() == []
