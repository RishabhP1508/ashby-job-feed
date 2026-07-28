"""Fetch a public Ashby job board and normalize it into a small, clean shape.

Normalization is the reason a server exists here: we drop the huge description
fields, collapse country-name variants, derive a single remote flag, and keep
only what the dashboard renders.
"""
from __future__ import annotations

import httpx

ASHBY_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"

COUNTRY_ALIASES = {
    "usa": "United States", "us": "United States", "u.s.": "United States",
    "u.s.a.": "United States", "united states of america": "United States",
    "united states": "United States", "america": "United States",
    "uk": "United Kingdom", "u.k.": "United Kingdom", "united kingdom": "United Kingdom",
    "great britain": "United Kingdom", "england": "United Kingdom",
    "uae": "United Arab Emirates", "u.a.e.": "United Arab Emirates",
}


def norm_country(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    return COUNTRY_ALIASES.get(text.lower(), text)


def _country_of(address: dict | None) -> str:
    if not isinstance(address, dict):
        return ""
    postal = address.get("postalAddress")
    if not isinstance(postal, dict):
        return ""
    return norm_country(postal.get("addressCountry"))


def _countries(job: dict) -> list[str]:
    found: list[str] = []
    primary = _country_of(job.get("address"))
    if primary:
        found.append(primary)
    for sec in job.get("secondaryLocations") or []:
        addr = sec.get("address") if isinstance(sec, dict) else None
        c = _country_of(addr)
        if c and c not in found:
            found.append(c)
    return found


def normalize(job: dict, slug: str) -> dict:
    workplace = job.get("workplaceType") or ""
    remote = bool(job.get("isRemote")) or ("remote" in workplace.lower())
    secondary = job.get("secondaryLocations") or []
    return {
        "company": slug,
        "title": job.get("title") or "Untitled role",
        "team": (job.get("team") or "").strip(),
        "department": (job.get("department") or "").strip(),
        "location": job.get("location") or "",
        "secondaryCount": len(secondary),
        "workplaceType": workplace or ("Remote" if job.get("isRemote") else ""),
        "employmentType": job.get("employmentType") or "",
        "isRemote": remote,
        "countries": _countries(job),
        "applyUrl": job.get("applyUrl") or job.get("jobUrl") or "",
        "publishedAt": job.get("publishedAt"),
    }


async def fetch_board(slug: str, transport: httpx.AsyncBaseTransport | None = None) -> list[dict]:
    url = ASHBY_URL.format(slug=slug)
    async with httpx.AsyncClient(timeout=20.0, transport=transport) as client:
        resp = await client.get(url, headers={"Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()
    jobs = data.get("jobs") or []
    return [
        normalize(j, slug)
        for j in jobs
        if isinstance(j, dict) and j.get("isListed") is not False
    ]
