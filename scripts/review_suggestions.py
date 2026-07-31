#!/usr/bin/env python3
"""Turn the board-fetch log into seed entries.

Unlike validate_boards.py, which is stdlib-only, this imports backend/app/db.py
for the engine and models, so it RUNS FROM THE BACKEND VENV:

    cd backend
    DATABASE_URL="postgresql://...-pooler...?sslmode=require" \
        .venv/Scripts/python ../scripts/review_suggestions.py

DATABASE_URL has to point at production. The log lives in the Neon database, not
in the local SQLite file, so pointing this at SQLite finds nothing.

The posting API returns no company name, so promotion cannot be automatic. This
shows job titles for each unknown slug, you supply a name and industries, and it
writes them into companies.seed.json. Rerun validate_boards.py afterwards.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SEED_PATH = SCRIPT_DIR / "companies.seed.json"
OVERRIDES_PATH = SCRIPT_DIR / "manual-overrides.json"
IGNORE_PATH = SCRIPT_DIR / ".review-ignore.json"
DIRECTORY_PATH = REPO_ROOT / "frontend" / "src" / "data" / "companies.json"

API_BASE = "https://api.ashbyhq.com/posting-api/job-board/"
BOARD_URL = "https://jobs.ashbyhq.com/"
USER_AGENT = "ashby-job-feed-review/1.0 (+https://github.com/RishabhP1508/ashby-job-feed)"
TIMEOUT = 30
SAMPLE_TITLES = 3

# Same idiom as backend/alembic/env.py: make the app package importable so the
# engine, session, and models come from one place.
sys.path.insert(0, str(REPO_ROOT / "backend"))


def norm(text: str) -> str:
    """Lowercase, strip separators. 'Scale AI' and 'scale-ai' both give 'scaleai'."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, payload) -> None:
    """Atomic write, 2-space indent, so a partial file never lands."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def fetch_board(slug: str) -> tuple[int, list[dict]]:
    """Return (status, jobs). Status 0 means the request never completed."""
    req = urllib.request.Request(
        API_BASE + urllib.parse.quote(slug), headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read())
        jobs = data.get("jobs")
        return 200, jobs if isinstance(jobs, list) else []
    except urllib.error.HTTPError as exc:
        return exc.code, []
    except Exception:
        return 0, []


def ask(prompt: str, default: str = "") -> str | None:
    """Return the answer, or None to quit."""
    try:
        answer = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if answer.lower() in {"q", "quit"}:
        return None
    return answer or default


def _guard_database_url(database_url: str) -> None:
    print("DATABASE_URL must point at the production database.")
    print()
    print("The fetch log lives in Neon, not in the local SQLite file, so this")
    print("script would otherwise report an empty log and look like a no-op.")
    print()
    print("  cd backend")
    print('  DATABASE_URL="postgresql://...-pooler...?sslmode=require" \\')
    print("      .venv/Scripts/python ../scripts/review_suggestions.py")
    print()
    print(f"currently: DATABASE_URL={database_url or '(unset)'}")


def main() -> int:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url or database_url.startswith("sqlite"):
        _guard_database_url(database_url)
        return 1

    from sqlalchemy import select

    from app import db

    with db.SessionLocal() as session:
        rows = (
            session.execute(select(db.BoardFetch).order_by(db.BoardFetch.fetch_count.desc()))
            .scalars()
            .all()
        )
        logged = [
            {
                "slug": r.slug,
                "first_seen": db._iso(r.first_seen),
                "fetch_count": r.fetch_count,
            }
            for r in rows
        ]

    if not logged:
        print("No board fetches logged yet, so there is nothing to review.")
        print("Fetch a board in the app, then run this again.")
        return 0

    seed = load_json(SEED_PATH, None)
    directory = load_json(DIRECTORY_PATH, None)
    if seed is None or directory is None:
        print(f"Could not read {SEED_PATH.name} or {DIRECTORY_PATH.name}.")
        return 1
    overrides = load_json(OVERRIDES_PATH, {})
    ignored = [str(s) for s in load_json(IGNORE_PATH, [])]
    valid_industries = list(directory.get("industries") or [])

    # Slugs are compared case-insensitively. Ashby slugs are not all lowercase
    # (ConductorOne is "C1") and the API lowercases on the way in, so a logged
    # "c1" has to match a stored "C1". Nothing is lowercased when stored.
    known = {c["slug"].lower() for c in directory["companies"] if c.get("slug")}
    known |= {c["slug"].lower() for c in seed["companies"] if c.get("slug")}
    known |= {s.lower() for s in ignored}
    # ponytail: rejected companies are candidate-tier with slug=null, so the seed
    # holds no slug to exclude. Normalizing the name covers the current three
    # (Runway, Cedar, Levels). A reject whose real slug is a derived variant
    # needs a .review-ignore.json entry.
    known |= {norm(n) for n in (overrides.get("reject") or [])}

    # slug -> [(candidate index, entry)]. The big win: 5,192 candidate slugs
    # against 23 confirmed ones, so a slug we already guessed and 404'd on is
    # recognized instead of offered as a brand-new company.
    by_candidate: dict[str, list[tuple[int, dict]]] = {}
    for entry in seed["companies"]:
        for i, cand in enumerate(entry.get("slugCandidates") or []):
            by_candidate.setdefault(cand.lower(), []).append((i, entry))
    by_name = {norm(e["name"]): e for e in seed["companies"]}

    todo = [row for row in logged if row["slug"].lower() not in known]
    if not todo:
        print(f"{len(logged)} slugs in the fetch log, all already known. Nothing to review.")
        return 0

    print(f"{len(logged)} slugs in the fetch log, {len(todo)} unknown.")
    print("Enter accepts the suggestion. 's' skips for good, 'q' quits and keeps accepted work.")

    accepted: list[tuple[dict | None, str, str, list[str]]] = []
    claimed = {c["slug"].lower() for c in seed["companies"] if c.get("slug")}
    newly_ignored: list[str] = []

    for row in todo:
        slug = row["slug"]
        status, jobs = fetch_board(slug)
        if status == 404:
            # A board can come back, so this is deliberately not remembered.
            print(f"\n{slug}: board is gone (404), skipping.")
            continue
        if status != 200:
            print(f"\n{slug}: could not fetch (status {status}), skipping for now.")
            continue

        owners = sorted(by_candidate.get(slug.lower(), []), key=lambda m: m[0])
        entry = owners[0][1] if owners else None

        print()
        print(f"  slug        {slug}")
        print(f"  board       {BOARD_URL}{slug}")
        print(f"  jobs now    {len(jobs)}")
        print(f"  first seen  {row['first_seen']}")
        print(f"  fetches     {row['fetch_count']}")
        for job in jobs[:SAMPLE_TITLES]:
            dept = (job.get("department") or "").strip()
            title = (job.get("title") or "").strip() or "(untitled)"
            print(f"  role        {title}{f' ({dept})' if dept else ''}")
        if entry is not None:
            if len(owners) > 1:
                names = ", ".join(f"{e['name']} (candidate {i})" for i, e in owners)
                print(f"  ambiguous   {slug} is a candidate for: {names}")
            print(f"  known       {slug} is a slug candidate for {entry['name']}, already in the")
            print("              seed as unresolved. Accepting resolves it instead of adding one.")

        guess = entry["name"] if entry else slug.replace("-", " ").replace("_", " ").title()
        name = ask(f"  name [{guess}]: ", guess)
        if name is None:
            print("  quitting, keeping what was accepted.")
            break
        if name.lower() in {"s", "skip"}:
            newly_ignored.append(slug)
            print("  skipped, will not be offered again.")
            continue

        # A typed name can point at a different entry than the slug index picked.
        target = by_name.get(norm(name), entry)
        default_inds = ", ".join(target["industries"]) if target else ""

        picked: list[str] = []
        while True:
            raw = ask(f"  industries [{default_inds}]: ", default_inds)
            if raw is None:
                break
            picked = [p.strip() for p in raw.split(",") if p.strip()]
            unknown = [p for p in picked if p not in valid_industries]
            if not picked:
                print(f"  at least one is required. Valid: {', '.join(valid_industries)}")
                continue
            if unknown:
                print(f"  not valid industries: {', '.join(unknown)}")
                print(f"  choose from: {', '.join(valid_industries)}")
                continue
            break
        if not picked:
            print("  quitting, keeping what was accepted.")
            break

        # Refuse a slug another confirmed entry already owns, here where it is
        # visible, rather than as a uniqueness assertion inside validate_boards.
        if slug.lower() in claimed:
            holder = next(
                (
                    c["name"]
                    for c in seed["companies"]
                    if (c.get("slug") or "").lower() == slug.lower()
                ),
                "another entry",
            )
            print(f"  refused: {holder} already holds slug {slug}. Skipping this one.")
            continue

        claimed.add(slug.lower())
        accepted.append((target, name, slug, picked))
        print(f"  accepted: {name} -> {slug} {picked}")

    if newly_ignored:
        write_json(IGNORE_PATH, sorted({*ignored, *newly_ignored}))
        print(f"\nAdded {len(newly_ignored)} slugs to {IGNORE_PATH.name}.")

    if not accepted:
        print("\nNothing accepted, seed file unchanged.")
        return 0

    updated = appended = 0
    for target, name, slug, industries in accepted:
        if target is not None:
            was = target.get("tier")
            target["name"] = name
            target["slug"] = slug
            target["tier"] = "confirmed"
            target["industries"] = industries
            target.pop("slugCandidates", None)
            if was and was in seed.get("tierCounts", {}):
                seed["tierCounts"][was] -= 1
            seed["tierCounts"]["confirmed"] = seed["tierCounts"].get("confirmed", 0) + 1
            updated += 1
        else:
            seed["companies"].append(
                {"name": name, "industries": industries, "tier": "confirmed", "slug": slug}
            )
            seed["companyCount"] = seed.get("companyCount", 0) + 1
            seed["tierCounts"]["confirmed"] = seed["tierCounts"].get("confirmed", 0) + 1
            appended += 1

    write_json(SEED_PATH, seed)
    print(f"\n{SEED_PATH.name}: {updated} resolved in place, {appended} appended.")
    print("Next: rerun scripts/validate_boards.py to probe the new slugs, apply the")
    print("industry threshold rules, and regenerate companies.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
