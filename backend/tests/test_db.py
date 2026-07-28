import pytest

from app import db
from app.db import SessionLocal


@pytest.fixture()
def session():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def user(session):
    return db.create_user(session, "u@example.com", "hash")


def test_save_and_get(session, user):
    row = db.save_search(session, user.id, "OpenAI", ["openai"], {"datePreset": "7"})
    assert row["useCount"] == 1
    assert row["companies"] == ["openai"]
    listed = db.list_searches(session, user.id, "recent")
    assert len(listed) == 1
    assert listed[0]["name"] == "OpenAI"


def test_identical_search_dedupes_and_bumps(session, user):
    db.save_search(session, user.id, "A", ["openai", "ramp"], {"x": 1})
    row = db.save_search(session, user.id, "B", ["ramp", "openai"], {"x": 1})
    assert row["useCount"] == 2
    assert row["name"] == "B"
    assert len(db.list_searches(session, user.id, "recent")) == 1


def test_recent_and_popular_ordering(session, user):
    a = db.save_search(session, user.id, "A", ["openai"], {})
    b = db.save_search(session, user.id, "B", ["ramp"], {})
    assert [r["id"] for r in db.list_searches(session, user.id, "recent")] == [b["id"], a["id"]]
    db.touch_search(session, user.id, a["id"])
    db.touch_search(session, user.id, a["id"])
    assert db.list_searches(session, user.id, "popular")[0]["id"] == a["id"]


def test_delete_and_missing(session, user):
    row = db.save_search(session, user.id, "A", ["openai"], {})
    assert db.delete_search(session, user.id, row["id"]) is True
    assert db.delete_search(session, user.id, row["id"]) is False
    assert db.touch_search(session, user.id, 999) is None


def test_searches_are_isolated_per_user(session):
    a = db.create_user(session, "a@example.com", "h")
    b = db.create_user(session, "b@example.com", "h")
    db.save_search(session, a.id, "A search", ["openai"], {})
    assert len(db.list_searches(session, a.id, "recent")) == 1
    assert db.list_searches(session, b.id, "recent") == []
    # a search B cannot touch or delete one of A's rows
    a_row = db.list_searches(session, a.id, "recent")[0]
    assert db.touch_search(session, b.id, a_row["id"]) is None
    assert db.delete_search(session, b.id, a_row["id"]) is False
