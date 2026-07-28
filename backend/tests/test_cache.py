import app.cache as cache_module
from app.cache import TTLCache


def test_get_returns_stored_value():
    c = TTLCache(ttl_seconds=300)
    c.set("k", [1, 2, 3])
    assert c.get("k") == [1, 2, 3]


def test_missing_key_returns_none():
    c = TTLCache(ttl_seconds=300)
    assert c.get("absent") is None


def test_value_expires_after_ttl(monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(cache_module.time, "time", lambda: clock["now"])
    c = TTLCache(ttl_seconds=60)
    c.set("k", "v")
    assert c.get("k") == "v"
    clock["now"] = 1000.0 + 61
    assert c.get("k") is None
