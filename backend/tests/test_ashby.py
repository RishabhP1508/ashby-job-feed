import asyncio

import httpx
import pytest

from app.ashby import _countries, fetch_board, norm_country, normalize


def test_norm_country_aliases():
    assert norm_country("USA") == "United States"
    assert norm_country("united states") == "United States"
    assert norm_country("U.K.") == "United Kingdom"
    assert norm_country("France") == "France"
    assert norm_country("") == ""
    assert norm_country(None) == ""


def test_countries_dedupes_primary_and_secondary():
    job = {
        "address": {"postalAddress": {"addressCountry": "USA"}},
        "secondaryLocations": [
            {"address": {"postalAddress": {"addressCountry": "United States"}}},
            {"address": {"postalAddress": {"addressCountry": "Canada"}}},
        ],
    }
    assert _countries(job) == ["United States", "Canada"]


def test_countries_handles_missing_fields():
    assert _countries({}) == []
    assert _countries({"address": None, "secondaryLocations": None}) == []


def test_normalize_trims_and_derives():
    job = {
        "title": "Backend Engineer",
        "team": " Applied AI ",
        "department": "Engineering",
        "location": "San Francisco",
        "employmentType": "FullTime",
        "workplaceType": "Hybrid - Remote",
        "isRemote": False,
        "secondaryLocations": [{"address": {"postalAddress": {"addressCountry": "USA"}}}],
        "address": {"postalAddress": {"addressCountry": "USA"}},
        "jobUrl": "https://jobs.ashbyhq.com/openai/123",
        "descriptionHtml": "<p>huge</p>",
        "descriptionPlain": "huge",
    }
    out = normalize(job, "openai")
    assert out["company"] == "openai"
    assert out["team"] == "Applied AI"
    assert out["isRemote"] is True  # workplaceType contains "remote"
    assert out["secondaryCount"] == 1
    assert out["countries"] == ["United States"]
    assert out["applyUrl"] == "https://jobs.ashbyhq.com/openai/123"  # falls back to jobUrl
    assert "descriptionHtml" not in out
    assert "descriptionPlain" not in out


def test_normalize_defaults_for_sparse_job():
    out = normalize({}, "acme")
    assert out["title"] == "Untitled role"
    assert out["isRemote"] is False
    assert out["countries"] == []
    assert out["applyUrl"] == ""


def test_fetch_board_filters_unlisted_and_normalizes():
    payload = {
        "jobs": [
            {"title": "Kept", "isListed": True, "workplaceType": "Remote"},
            {"title": "Dropped", "isListed": False},
            {"title": "AlsoKept"},  # isListed absent -> kept
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/openai")
        return httpx.Response(200, json=payload)

    jobs = asyncio.run(fetch_board("openai", transport=httpx.MockTransport(handler)))
    assert [j["title"] for j in jobs] == ["Kept", "AlsoKept"]
    assert jobs[0]["isRemote"] is True


def test_fetch_board_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(fetch_board("nope", transport=httpx.MockTransport(handler)))
