#!/usr/bin/env python3
"""Resolve which seed companies have a live Ashby job board.

Standard library only, no venv needed.

    python scripts/validate_boards.py                 full run
    python scripts/validate_boards.py --sample 40     deterministic spread across tiers
    python scripts/validate_boards.py --skip-careers  stop after the slug phase

Reads scripts/companies.seed.json, writes frontend/src/data/companies.json and
scripts/validation-report.md. Probe results are cached in
scripts/.validation-cache.json so reruns skip completed work.

Two passes, deliberately not interleaved: every slug is probed first and the
results reported, then careers pages are fetched for whatever is left. That
makes the slow phase a decision point instead of a mystery.
"""
from __future__ import annotations

import argparse
import html
import json
import random
import re
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SEED_PATH = SCRIPT_DIR / "companies.seed.json"
CACHE_PATH = SCRIPT_DIR / ".validation-cache.json"
OVERRIDES_PATH = SCRIPT_DIR / "manual-overrides.json"
REPORT_PATH = SCRIPT_DIR / "validation-report.md"
OUT_PATH = REPO_ROOT / "frontend" / "src" / "data" / "companies.json"

API_BASE = "https://api.ashbyhq.com/posting-api/job-board/"
USER_AGENT = (
    "ashby-job-feed-validator/1.0 "
    "(+https://github.com/RishabhP1508/ashby-job-feed; one-off board validation, low volume)"
)
API_TIMEOUT = 20
WEB_TIMEOUT = 15
MAX_WORKERS = 5
API_MIN_INTERVAL = 0.125  # ~8 requests/second against the single Ashby host
MAX_RETRIES = 3
CAREERS_PATHS = ("/careers", "/jobs", "")
SLUG_BLOCKLIST = {"embed", "api", "static", "assets", "_next"}
# Cap careers-page HTML only. API responses are read in full: a job board can
# exceed 2 MB (Ramp is 2.0 MB with 125 roles) and a truncated body fails to
# parse, which would look like an error rather than a valid board.
MAX_HTML_BODY = 400_000
SAMPLE_TITLES = 3
BREAKER_MIN = 20
BREAKER_FRACTION = 0.05

# Generic words another company could plausibly own. A slug matching one of
# these is flagged for human review even when it matches the company name
# exactly, because Ashby slugs are first-come and the API exposes no company
# name to check against. Length is deliberately NOT a trigger for exact
# matches: 404 of 816 first guesses are 7 characters or fewer and nearly all
# are distinctive names (openai, whoop, redis), so a length rule would flood
# the review section with noise instead of signal.
COMMON_WORDS = frozenset("""
ada alloy alma arcade arcadia artisan astro belong bridge cameo campsite
catalyst cava cedar census circle clay coder color column craft default
depot discord docker dust eleven eve faire fal fathom fellow fern figure
form front ghost goat grail guild guru heap height hex hippo imbue imply
increase island kin kit knock lambda landing lattice levels lighthouse
loom loops magic make maven mem mercury missive mosaic motion motive
nothing obsidian oklo omni opal origin oven owner oyster photon pika play
plenty pocus porter preset prisma public pulley quera rabbit radiant
railway rainbow range readme reclaim reflect regard remote render resend
rho rime ripple rive ro roam runway scribe sent sierra sift slice socket
sonder speak spline split sweep tana tango teller tempus throne tines tive
toast tock tonal town twelve unify unit vast vise voodoo warp wonder
writer zed
""".split())

P_EMBED = re.compile(r"ashbyhq\.com/embed\?token=([a-zA-Z0-9_-]+)", re.I)
P_BOARD = re.compile(r"jobs\.ashbyhq\.com/([a-zA-Z0-9_-]+)", re.I)
P_API = re.compile(r"posting-api/job-board/([a-zA-Z0-9_-]+)", re.I)
ASHBY_JID = re.compile(r"ashby_jid", re.I)
ASHBY_EMBED = re.compile(r"""id=["']ashby_embed["']""", re.I)


# ----------------------------------------------------------------- primitives


class Blocked(Exception):
    """HTTP 403. Never a miss: it says nothing about whether the board exists."""


class Transient(Exception):
    """Retried and still failed. Never a miss, never cached."""


class Aborted(Exception):
    """Circuit breaker tripped."""


class Pacer:
    """Minimum interval between request starts to one host."""

    def __init__(self, interval: float) -> None:
        self.interval = interval
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next - now)
            self._next = max(now, self._next) + self.interval
        if delay:
            time.sleep(delay)


class Breaker:
    """Abort when Ashby 403s dominate, because that looks like a valid result.

    Only API 403s count. Careers-page 403s are ordinary bot protection on
    marketing sites and cost one company, not the run.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.api_calls = 0
        self.api_403 = 0

    def record(self, was_403: bool) -> bool:
        with self._lock:
            self.api_calls += 1
            if was_403:
                self.api_403 += 1
            return self.api_403 >= BREAKER_MIN and self.api_403 > BREAKER_FRACTION * self.api_calls


class Cache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._dirty = 0
        try:
            self._data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._data = {}

    def get(self, key: str):
        with self._lock:
            return self._data.get(key)

    def put(self, key: str, value) -> None:
        with self._lock:
            self._data[key] = value
            self._dirty += 1
            flush = self._dirty >= 50
        if flush:
            self.save()

    def save(self) -> None:
        with self._lock:
            self._dirty = 0
            payload = json.dumps(self._data, indent=1, sort_keys=True)
        tmp = self.path.with_suffix(".tmp")
        try:
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(self.path)
        except OSError as exc:
            print(f"  warning: could not write cache: {exc}")


class Progress:
    def __init__(self, label: str, total: int) -> None:
        self.label = label
        self.total = total
        self.done = 0
        self.start = time.monotonic()
        self._lock = threading.Lock()

    def step(self, message: str) -> None:
        with self._lock:
            self.done += 1
            elapsed = time.monotonic() - self.start
            print(f"[{self.label} {self.done}/{self.total} {elapsed:6.0f}s] {message}", flush=True)

    def elapsed(self) -> float:
        return time.monotonic() - self.start


def http_fetch(url: str, timeout: int, pacer: Pacer | None = None, max_body: int | None = None):
    """Return (status, final_url, body) for 200 and 404 only.

    max_body=None reads the whole response, which JSON requires.

    Everything else raises: 403 -> Blocked, 429/5xx/transport -> Transient after
    retries. Only 200 and 404 are conclusive, so only they return normally. A
    403 falling through to "wrong slug" would report the whole seed as absent
    from Ashby and look like a valid answer, which is the worst failure here.
    """
    delay = 1.0
    last = "unknown"
    for attempt in range(MAX_RETRIES + 1):
        if pacer:
            pacer.wait()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read() if max_body is None else resp.read(max_body)
                return resp.status, resp.geturl(), body
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return 404, url, b""
            if exc.code == 403:
                raise Blocked("HTTP 403") from None
            if exc.code == 429 or 500 <= exc.code < 600:
                last = f"HTTP {exc.code}"
                retry_after = (exc.headers.get("Retry-After") or "") if exc.headers else ""
                if retry_after.strip().isdigit():
                    delay = min(30.0, float(retry_after.strip()))
            else:
                raise Transient(f"HTTP {exc.code}") from None
        except (urllib.error.URLError, ssl.SSLError, TimeoutError, OSError) as exc:
            last = type(exc).__name__
        if attempt < MAX_RETRIES:
            time.sleep(delay + random.uniform(0, 0.3))
            delay *= 2
    raise Transient(last)


# ------------------------------------------------------------------- matching


def norm(text: str) -> str:
    """Lowercase and drop every separator, so 'David AI' == 'david-ai'."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def extract_slug(text: str) -> str | None:
    """Three patterns in priority order, blocklist applied.

    Pattern order matters: an embedded board yields jobs.ashbyhq.com/embed,
    where the real slug is the token, not the path segment.
    """
    for pattern in (P_EMBED, P_BOARD, P_API):
        for match in pattern.finditer(text or ""):
            slug = match.group(1)
            if slug.lower() not in SLUG_BLOCKLIST:
                return slug
    return None


def is_exact(name: str, slug: str) -> bool:
    return norm(slug) == norm(name)


def is_risky(rec: dict) -> bool:
    """Does this acceptance need a human glance?"""
    slug = (rec.get("slug") or "").lower()
    how = rec.get("how")
    if how in ("scraped", "derived-corroborated"):
        return True
    if how == "derived":
        return True
    if how == "exact":
        return slug in COMMON_WORDS or norm(slug) in COMMON_WORDS
    return False


# --------------------------------------------------------------------- probing


def probe_slug(slug: str, cache: Cache, pacer: Pacer, breaker: Breaker) -> dict:
    key = f"slug:{slug}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    try:
        status, _, body = http_fetch(API_BASE + urllib.parse.quote(slug), API_TIMEOUT, pacer)
    except Blocked:
        if breaker.record(True):
            raise Aborted(
                f"{breaker.api_403} of {breaker.api_calls} Ashby probes returned 403. "
                "That is a block, not a result. Stopping."
            ) from None
        return {"status": "error", "reason": "HTTP 403"}
    except Transient as exc:
        breaker.record(False)
        return {"status": "error", "reason": str(exc)}
    breaker.record(False)

    if status == 404:
        result = {"status": 404}
        cache.put(key, result)
        return result

    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"status": "error", "reason": "unparseable JSON"}
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return {"status": "error", "reason": "no jobs array"}

    titles = []
    for job in jobs[:SAMPLE_TITLES]:
        title = (job.get("title") or "").strip() or "(untitled)"
        dept = (job.get("department") or "").strip()
        titles.append(f"{title} ({dept})" if dept else title)
    result = {"status": 200, "jobCount": len(jobs), "titles": titles}
    cache.put(key, result)
    return result


def scrape_domain(domain: str, cache: Cache) -> dict:
    """Look for an Ashby slug on a company's own site.

    Checks the final URL after redirects before the body, because plenty of
    companies point /careers straight at jobs.ashbyhq.com/<slug>, and that URL
    is the strongest signal available.
    """
    key = f"careers:{domain}"
    hit = cache.get(key)
    if hit is not None:
        return hit

    got_http = False
    found = None
    detected = False
    errors: list[str] = []
    for path in CAREERS_PATHS:
        url = f"https://{domain}{path}"
        try:
            status, final_url, body = http_fetch(url, WEB_TIMEOUT, max_body=MAX_HTML_BODY)
        except Blocked:
            errors.append(f"{path or '/'}: 403")
            continue
        except Transient as exc:
            errors.append(f"{path or '/'}: {exc}")
            continue
        got_http = True
        if status == 404:
            continue
        text = html.unescape(body.decode("utf-8", "replace"))
        found = extract_slug(final_url) or extract_slug(text)
        if found:
            break
        if ASHBY_JID.search(text) or ASHBY_EMBED.search(text):
            detected = True
    result = {"slug": found, "ashbyDetected": bool(found or detected), "errors": errors}
    if got_http:
        cache.put(key, result)
    return result


# ------------------------------------------------------------------- the run


def pick_sample(total: int, count: int) -> list[int]:
    """Deterministic spread including both endpoints.

    Seed indices 0-51 are the confirmed and named tiers, so a first-N slice
    would never reach the candidate tier, the acceptance gate, or the careers
    fallback. Including the last index also guarantees the David AI canary
    (final entry) lands in the sample.
    """
    if count >= total:
        return list(range(total))
    if count <= 1:
        return [0]
    return sorted({round(i * (total - 1) / (count - 1)) for i in range(count)})


def prepare(seed: dict) -> tuple[list[dict], list[str], list[str]]:
    """Pre-claim known slugs, then de-conflict contested candidates.

    Always runs over the full seed, never a sample: a smaller claimed set would
    leave collision handling untested in the very run meant to test it.
    """
    companies = seed["companies"]
    notes_known: list[str] = []
    notes_contested: list[str] = []

    owner_of = {c["slug"]: c["name"] for c in companies if c.get("slug")}
    for company in companies:
        kept = []
        for slug in company.get("slugCandidates") or []:
            if slug in owner_of and company.get("slug") != slug:
                notes_known.append(
                    f"{company['name']}: dropped `{slug}`, owned by {owner_of[slug]}"
                )
            else:
                kept.append(slug)
        company["_cands"] = kept

    # Contested among candidates: lowest candidate index wins, then seed order.
    best: dict[str, tuple[int, int, str]] = {}
    for order, company in enumerate(companies):
        for idx, slug in enumerate(company["_cands"]):
            prior = best.get(slug)
            if prior is None or (idx, order) < (prior[0], prior[1]):
                best[slug] = (idx, order, company["name"])
    for company in companies:
        kept = []
        for slug in company["_cands"]:
            winner = best[slug][2]
            if winner != company["name"]:
                notes_contested.append(
                    f"{company['name']}: dropped `{slug}`, assigned to {winner}"
                )
            else:
                kept.append(slug)
        company["_cands"] = kept

    return companies, notes_known, notes_contested


def new_record(company: dict) -> dict:
    domains = list(company.get("domainCandidates") or [])
    if not domains and company.get("domain"):
        domains = [company["domain"]]
    return {
        "name": company["name"],
        "tier": company["tier"],
        "industries": list(company["industries"]),
        "domains": domains,
        "slug": None,
        "jobCount": 0,
        "titles": [],
        "how": None,
        "state": None,
        "reason": "",
    }


def slug_phase(company: dict, cache: Cache, pacer: Pacer, breaker: Breaker, claimed, lock) -> dict:
    """Resolve one company by slug alone."""
    rec = new_record(company)

    if company.get("slug"):
        result = probe_slug(company["slug"], cache, pacer, breaker)
        if result["status"] == 200:
            rec.update(slug=company["slug"], jobCount=result["jobCount"],
                       titles=result.get("titles", []), how="confirmed", state="shipped")
        elif result["status"] == 404:
            rec.update(state="confirmed-dead", reason="known slug now 404s")
        else:
            rec.update(state="error", reason=result.get("reason", "error"))
        return rec

    for slug in company["_cands"]:
        with lock:
            if slug in claimed:
                continue
        result = probe_slug(slug, cache, pacer, breaker)
        if result["status"] == "error":
            # A throttled or blocked probe proves nothing about this slug, so do
            # not keep walking the list and treat the remaining misses as real.
            rec.update(state="error", reason=f"{slug}: {result.get('reason')}")
            return rec
        if result["status"] == 200:
            with lock:
                if slug in claimed:
                    continue
                claimed.add(slug)
            rec.update(slug=slug, jobCount=result["jobCount"], titles=result.get("titles", []))
            if is_exact(company["name"], slug):
                rec.update(how="exact", state="shipped")
            elif company["tier"] == "named":
                # Named companies genuinely use Ashby, so withholding one is the
                # wrong error. Flag it for review instead of gating it.
                rec.update(how="derived", state="shipped", reason="named tier, derived slug")
            else:
                rec.update(how="derived", state="needs-corroboration")
            return rec

    # No candidates left is an absence of guesses, not evidence of absence.
    rec.update(state="missing" if company["_cands"] else "no-candidates")
    return rec


def careers_phase(rec: dict, cache: Cache, pacer: Pacer, breaker: Breaker, claimed, lock) -> None:
    """Corroborate a derived slug, or find a slug we could not guess."""
    target = rec.get("slug")
    for domain in rec["domains"]:
        scraped = scrape_domain(domain, cache)
        found = scraped.get("slug")

        if target:
            if found and norm(found) == norm(target):
                rec.update(how="derived-corroborated", state="shipped",
                           reason=f"{domain} references {found}")
                return
            if found and norm(found) != norm(target):
                # The page names a different board. That is better evidence than
                # our guess, so prefer it after validating.
                check = probe_slug(found, cache, pacer, breaker)
                if check.get("status") == 200:
                    with lock:
                        if found not in claimed:
                            claimed.add(found)
                            rec.update(slug=found, jobCount=check["jobCount"],
                                       titles=check.get("titles", []), how="scraped",
                                       state="shipped",
                                       reason=f"{domain} pointed at {found}, not {target}")
                            return
            continue

        if found:
            check = probe_slug(found, cache, pacer, breaker)
            if check.get("status") == 200:
                with lock:
                    if found in claimed:
                        continue
                    claimed.add(found)
                rec.update(slug=found, jobCount=check["jobCount"], titles=check.get("titles", []),
                           how="scraped", state="shipped", reason=f"found on {domain}")
                return
        if scraped.get("ashbyDetected"):
            rec.update(state="ashby-unresolved",
                       reason=f"{domain} shows Ashby, no slug extractable")

    if target:
        rec.update(state="withheld",
                   reason="careers page did not corroborate the derived slug")
    elif rec["state"] != "ashby-unresolved":
        rec.update(state="missing")


# ----------------------------------------------------------------- industries


def apply_industry_rules(records: list[dict], seed: dict) -> tuple[list[str], list[str]]:
    """Merge thin industries, then drop what is still thin, then repeat.

    Order matters: evaluating one industry at a time is nondeterministic. If
    Design has 3 and Productivity 4, merging first yields 7 and both survive,
    while evaluating Productivity first drops it and Design loses its target.
    Terminates because no merge target is also a merge source.
    """
    threshold = seed["minCompaniesPerIndustry"]
    merges = seed["suggestedMerges"]
    shipped = [r for r in records if r["state"] == "shipped"]
    notes: list[str] = []

    for _ in range(10):
        counts = Counter(i for r in shipped for i in r["industries"])
        thin = {name for name, n in counts.items() if n < threshold}
        if not thin:
            break

        merged = {n: merges[n] for n in thin if n in merges}
        if merged:
            for rec in shipped:
                rec["industries"] = sorted({merged.get(i, i) for i in rec["industries"]})
            for src, dst in sorted(merged.items()):
                notes.append(f"merged {src} into {dst}: had {counts[src]}, under {threshold}")

        counts = Counter(i for r in shipped for i in r["industries"])
        still_thin = {n for n, c in counts.items() if c < threshold}
        if still_thin:
            for rec in shipped:
                rec["industries"] = [i for i in rec["industries"] if i not in still_thin]
            for name in sorted(still_thin):
                notes.append(
                    f"dropped {name}: {counts[name]} companies, under {threshold}, no merge target"
                )
        if not merged and not still_thin:
            break

    return sorted({i for r in shipped for i in r["industries"]}), notes


# --------------------------------------------------------------------- output


def write_outputs(records: list[dict], industries: list[str], generated: str) -> list[dict]:
    shipped = sorted((r for r in records if r["state"] == "shipped"),
                     key=lambda r: r["name"].lower())
    payload = {
        "generatedAt": generated,
        "industries": industries,
        "companies": [
            {"name": r["name"], "slug": r["slug"], "industries": r["industries"],
             "jobCount": r["jobCount"]}
            for r in shipped
        ],
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return shipped


def assert_output_sane(shipped: list[dict], industries: list[str]) -> None:
    """Overrides inject slugs directly, bypassing the collision pre-pass, so
    uniqueness has to be asserted on the final set."""
    seen: dict[str, str] = {}
    for rec in shipped:
        slug = rec["slug"]
        if slug in seen:
            raise SystemExit(
                f"ABORT: duplicate slug `{slug}` shipped for both {seen[slug]} and "
                f"{rec['name']}. Fix the override or the pre-pass before shipping."
            )
        seen[slug] = rec["name"]
    union = sorted({i for r in shipped for i in r["industries"]})
    if union != industries:
        raise SystemExit(
            "ABORT: industries list does not match the per-company labels.\n"
            f"  top level: {industries}\n  union:     {union}"
        )


def bullet(rec: dict) -> str:
    titles = "; ".join(rec.get("titles") or []) or "no open roles"
    extra = f" [{rec['reason']}]" if rec.get("reason") else ""
    return f"- **{rec['name']}** -> `{rec['slug']}` ({rec['jobCount']} roles){extra}\n  - {titles}"


def write_report(records, industries, merge_notes, known_notes, contested_notes,
                 override_notes, generated, clean, timings) -> None:
    def by_state(state):
        return [r for r in records if r["state"] == state]

    shipped = by_state("shipped")
    how = Counter(r["how"] for r in shipped)
    risky = sorted((r for r in shipped if is_risky(r)),
                   key=lambda r: (r["jobCount"], r["name"].lower()))
    zero = [r for r in shipped if r["jobCount"] == 0]
    found_total = len(shipped) + len(by_state("withheld")) + len(by_state("ashby-unresolved"))
    confirmed_total = len([r for r in records if r["tier"] == "confirmed"])

    lines = [
        "# Ashby board validation report",
        "",
        f"Generated {generated}. Run was {'clean' if clean else 'INCOMPLETE, see errors below'}.",
        "",
        "## Headline",
        "",
        f"- **shipped**: {len(shipped)} companies in `frontend/src/data/companies.json`",
        f"- **found**: {found_total} (shipped plus withheld plus Ashby-seen-but-unresolved)",
        "",
        "`found` is the measure of pipeline health. The acceptance gate withholds real",
        "boards on purpose, so a gap between found and shipped means corroboration is",
        "failing, not that the pipeline is broken. Those need opposite fixes.",
        "",
        "## Counts",
        "",
        f"- probed companies: {len(records)}",
        f"- confirmed boards still live: {how['confirmed']} of {confirmed_total}",
        f"- found by exact-name slug: {how['exact']}",
        f"- found by derived slug, named tier (ungated): {how['derived']}",
        f"- found by derived slug, cross-confirmed: {how['derived-corroborated']}",
        f"- found by careers-page scrape: {how['scraped']}",
        f"- shipped by manual override: {how['override']}",
        f"- withheld, derived slug unconfirmed: {len(by_state('withheld'))}",
        f"- Ashby confirmed, slug unresolved: {len(by_state('ashby-unresolved'))}",
        f"- not found: {len(by_state('missing')) + len(by_state('no-candidates'))}",
        f"- confirmed slug now dead: {len(by_state('confirmed-dead'))}",
        f"- error, unresolved: {len(by_state('error'))}",
        f"- shipped with 0 open roles: {len(zero)}",
        f"- rejected by override: {len(by_state('rejected'))}",
        "",
        f"Timing: {timings}",
        "",
        "## Verify by eye",
        "",
        "Every acceptance carrying residual risk, sorted by ascending job count so the",
        "emptiest and most suspicious boards come first. A 200 proves a board exists, not",
        "that it belongs to this company: Ashby slugs are first-come and the API exposes no",
        "company name, so job titles are the cheapest available signal. A gaming company",
        "with nursing roles means the wrong board was grabbed.",
        "",
    ]
    lines += [bullet(r) for r in risky] or ["_none_"]

    for state, title, blurb in [
        ("withheld", "Derived slug, unconfirmed (withheld, manual review queue)",
         "A live board was found but the slug is a derived variant and the careers page did "
         "not corroborate it. Add an approved entry to scripts/manual-overrides.json to ship it."),
        ("ashby-unresolved", "Ashby confirmed, slug unresolved",
         "The site shows an Ashby embed or ashby_jid but no slug could be extracted, usually "
         "because JavaScript injects it. Resolve these by hand."),
        ("error", "Error, unresolved",
         "Throttling, blocks, or transport failures. Not cached, so a rerun retries them."),
        ("confirmed-dead", "Previously confirmed, now 404",
         "These known-good slugs stopped resolving."),
        ("rejected", "Rejected by manual override", "Excluded on purpose."),
    ]:
        rows = by_state(state)
        lines += ["", f"## {title}", "", blurb, ""]
        lines += [
            f"- **{r['name']}**"
            + (f" -> `{r['slug']}`" if r.get("slug") else "")
            + (f" ({r['reason']})" if r.get("reason") else "")
            for r in sorted(rows, key=lambda r: r["name"].lower())
        ] or ["_none_"]

    scraped = [r for r in shipped if r["how"] == "scraped"]
    lines += ["", "## Resolved only by scraping", "",
              "Slug guessing alone would have missed these, which is why the careers-page "
              "fallback earns its place.", ""]
    lines += [bullet(r) for r in sorted(scraped, key=lambda r: r["name"].lower())] or ["_none_"]

    counts = Counter(i for r in shipped for i in r["industries"])
    lines += ["", "## Industries", "", "Final list after merges and drops.", ""]
    lines += [f"- {name}: {counts[name]}" for name in industries] or ["_none_"]
    lines += ["", "### Merges and drops applied", ""]
    lines += [f"- {n}" for n in (merge_notes or [])] or ["_none needed_"]
    no_industry = [r for r in shipped if not r["industries"]]
    if no_industry:
        lines += ["", f"{len(no_industry)} shipped companies ended with no industry label and "
                      "will not appear under any chip:", ""]
        lines += [f"- {r['name']}" for r in sorted(no_industry, key=lambda r: r["name"].lower())]

    lines += ["", "## Slug collisions resolved before probing", "",
              "A slug owned by a confirmed company is stripped from every other candidate list, "
              "and contested candidates go to whichever company ranked them highest. Without "
              "this, an aerospace company could ship pointing at Vast.ai's board.", ""]
    lines += [f"- {n}" for n in (known_notes + contested_notes)] or ["_none_"]

    lines += ["", "## Manual overrides applied", ""]
    lines += [f"- {n}" for n in (override_notes or [])] or ["_none_"]
    lines += [""]

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate which seed companies have live Ashby boards."
    )
    ap.add_argument("--limit", type=int, help="first N companies (quick pipeline check)")
    ap.add_argument("--sample", type=int, help="deterministic spread of N across all tiers")
    ap.add_argument("--skip-careers", action="store_true", help="stop after the slug phase")
    args = ap.parse_args()

    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    companies, known_notes, contested_notes = prepare(seed)
    total = len(companies)
    print(f"Seed: {total} companies, tiers {dict(Counter(c['tier'] for c in companies))}")
    print(f"Pre-pass: stripped {len(known_notes)} slugs owned by confirmed companies, "
          f"{len(contested_notes)} contested candidates")
    for note in known_notes:
        print(f"  {note}")

    if args.sample:
        picked = [companies[i] for i in pick_sample(total, args.sample)]
        label = f"--sample {args.sample}"
    elif args.limit:
        picked = companies[: args.limit]
        label = f"--limit {args.limit}"
    else:
        picked = companies
        label = "full run"
    print(f"{label}: {len(picked)} companies, tiers {dict(Counter(c['tier'] for c in picked))}")

    cache = Cache(CACHE_PATH)
    pacer = Pacer(API_MIN_INTERVAL)
    breaker = Breaker()
    claimed = {c["slug"] for c in companies if c.get("slug")}
    lock = threading.Lock()

    # ---- pass 1: slugs
    print(f"\n=== pass 1: slug probing ({len(picked)} companies) ===")
    prog = Progress("slug", len(picked))
    records: list[dict] = []
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = [pool.submit(slug_phase, c, cache, pacer, breaker, claimed, lock)
                       for c in picked]
            for fut in futures:
                rec = fut.result()
                records.append(rec)
                prog.step(f"{rec['name']}: {rec['state']}"
                          + (f" -> {rec['slug']} ({rec['jobCount']})" if rec.get("slug") else ""))
    except Aborted as exc:
        cache.save()
        print(f"\nABORTED: {exc}")
        return 2
    cache.save()
    slug_secs = prog.elapsed()

    print(f"\n--- pass 1 checkpoint ({slug_secs:.0f}s) ---")
    for state, n in sorted(Counter(r["state"] for r in records).items()):
        print(f"  {state}: {n}")
    print(f"  api calls: {breaker.api_calls}, 403s: {breaker.api_403}")

    pending = [r for r in records
               if r["state"] in ("needs-corroboration", "missing", "no-candidates")]
    domains = sum(len(r["domains"]) for r in pending)
    projected = domains * 6.0 / MAX_WORKERS
    print(f"  pass 2 would fetch up to {domains} domains for {len(pending)} companies, "
          f"projected ~{projected / 60:.0f} min")
    if not args.skip_careers and (slug_secs + projected) / 60 > 45:
        print("  NOTE: projected total exceeds 45 minutes.")

    # ---- pass 2: careers pages
    if args.skip_careers:
        print("\n--skip-careers: stopping after pass 1")
        for rec in pending:
            if rec["state"] == "needs-corroboration":
                rec.update(state="withheld", reason="careers pass skipped")
            elif rec["state"] == "no-candidates":
                rec.update(state="missing", reason="no candidates, careers pass skipped")
    elif pending:
        print(f"\n=== pass 2: careers pages ({len(pending)} companies) ===")
        prog2 = Progress("web", len(pending))
        try:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                futures = {pool.submit(careers_phase, r, cache, pacer, breaker, claimed, lock): r
                           for r in pending}
                for fut, rec in futures.items():
                    fut.result()
                    prog2.step(f"{rec['name']}: {rec['state']}"
                               + (f" -> {rec['slug']}" if rec.get("slug") else ""))
        except Aborted as exc:
            cache.save()
            print(f"\nABORTED: {exc}")
            return 2
        cache.save()
        print(f"--- pass 2 done ({prog2.elapsed():.0f}s) ---")

    # ---- manual overrides
    override_notes: list[str] = []
    try:
        overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        overrides = {"ship": {}, "reject": []}
    by_name = {r["name"]: r for r in records}
    for name, slug in (overrides.get("ship") or {}).items():
        rec = by_name.get(name)
        if rec is None:
            override_notes.append(f"ERROR: ship `{name}` matches no company in this run")
            continue
        result = probe_slug(slug, cache, pacer, breaker)
        if result.get("status") != 200:
            override_notes.append(
                f"ERROR: ship {name} -> `{slug}` did not validate "
                f"({result.get('reason', result.get('status'))})"
            )
            continue
        rec.update(slug=slug, jobCount=result["jobCount"], titles=result.get("titles", []),
                   how="override", state="shipped", reason="manual override")
        override_notes.append(f"shipped {name} -> `{slug}` ({result['jobCount']} roles)")
    for name in overrides.get("reject") or []:
        rec = by_name.get(name)
        if rec is None:
            override_notes.append(f"ERROR: reject `{name}` matches no company in this run")
            continue
        rec.update(state="rejected", reason="manual override")
        override_notes.append(f"rejected {name}")
    cache.save()

    # ---- industries, assertions, outputs
    industries, merge_notes = apply_industry_rules(records, seed)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    shipped = write_outputs(records, industries, generated)
    assert_output_sane(shipped, industries)

    errors = [r for r in records if r["state"] == "error"]
    clean = not errors
    timings = (f"pass 1 {slug_secs:.0f}s"
               + ("" if args.skip_careers else f", pass 2 {prog2.elapsed():.0f}s" if pending else ""))
    write_report(records, industries, merge_notes, known_notes, contested_notes,
                 override_notes, generated, clean, timings)

    # ---- summary
    withheld = [r for r in records if r["state"] == "withheld"]
    unresolved = [r for r in records if r["state"] == "ashby-unresolved"]
    how = Counter(r["how"] for r in shipped)
    found = len(shipped) + len(withheld) + len(unresolved)
    print("\n" + "=" * 64)
    print(f"shipped {len(shipped)}    found {found}    "
          f"(found = shipped + withheld + Ashby-seen-unresolved)")
    print("=" * 64)
    print(f"  probed:                       {len(records)}")
    print(f"  confirmed still live:         {how['confirmed']}")
    print(f"  found via exact slug:         {how['exact']}")
    print(f"  found via derived slug:       {how['derived']} (named tier, ungated)")
    print(f"  found via cross-confirmation: {how['derived-corroborated']}")
    print(f"  found via careers scrape:     {how['scraped']}")
    print(f"  manual overrides:             {how['override']}")
    print(f"  withheld (unconfirmed):       {len(withheld)}")
    print(f"  Ashby seen, slug unresolved:  {len(unresolved)}")
    print(f"  not found:                    "
          f"{len([r for r in records if r['state'] in ('missing', 'no-candidates')])}")
    print(f"  confirmed now dead:           "
          f"{len([r for r in records if r['state'] == 'confirmed-dead'])}")
    print(f"  error, unresolved:            {len(errors)}")
    print(f"  shipped with 0 roles:         {len([r for r in shipped if r['jobCount'] == 0])}")
    gate_seen = how["derived-corroborated"] + len(withheld)
    if gate_seen:
        print(f"  gate: {how['derived-corroborated']} corroborated, {len(withheld)} withheld "
              f"({len(withheld) / gate_seen:.0%} rejected)")
    print(f"\n  run was {'CLEAN' if clean else 'INCOMPLETE (errors listed in the report)'}")
    print(f"  wrote {OUT_PATH.relative_to(REPO_ROOT)} and {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
