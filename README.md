# Ashby job feed

![CI](https://github.com/RishabhP1508/ashby-job-feed/actions/workflows/ci.yml/badge.svg)

A small full-stack app that reads any company's public [Ashby](https://www.ashbyhq.com/) job board, merges several companies into one list, and filters roles by when they were posted, their location, team, and type. You apply straight from the list, and you can save a set of companies and filters to reopen later.

Backend: FastAPI (Python). Frontend: React and TypeScript, built with Vite. Storage: SQLite.

## What it does

- Track several companies at once. Each board loads on its own, with a live status per company (loading, role count, or failed with a retry button).
- Filter by a posted-within preset (24 hours, 7, 30, or 90 days) or by an exact year and month, by job type, by a text search, and by an exclude-words list.
- Narrow by location or team using facets that show live counts. Team can be grouped by department or by team.
- Sort by posted date, role, or company. Roles posted in the last week are marked.
- Save the current companies and filters, then reopen them from a recent or popular list. Export the current view to CSV.
- Every filter is also encoded in the URL, so a view can be shared as a link.

## Why there is a backend

Ashby's public posting API allows cross-origin browser requests, so a static page could call it directly. The server here does three things a static page cannot do on its own.

It caches each board for a short interval, so repeated views and multiple visitors do not refetch the same board or add load to Ashby. It normalizes each board into a small, uniform shape: the large HTML and plain-text description fields are dropped, country-name variants (US, U.S.A., United States) are folded into one value, a single `isRemote` flag is derived, and only the fields the table renders are kept, so the browser downloads a fraction of the raw feed. And it stores saved searches in a database, which is state a static page has no way to keep.

## Accounts and saved searches

Browsing and filtering are open to anyone, so the app is usable and demoable without an account. Saving a search requires logging in, and saved searches are private to each account: you only see and can change your own.

An account is an email and a password. Passwords are hashed with bcrypt, and the session is a JWT stored in an httpOnly cookie, so JavaScript cannot read it and the browser sends it automatically. Set `JWT_SECRET` to a long random value in production, and set `COOKIE_SECURE=true` so the cookie is only sent over HTTPS.

Saving a search records the selected companies and the full filter state under a name. Reopening one restores them in a click, and the list can be ordered by most recent or by how often each search has been reopened.

## Tracking and new roles

Two per-user features build on accounts. Each job row has a status you can set (applied, interviewing, rejected, or offer), stored privately per account and keyed by the job's apply URL. Separately, a "mark all as seen" button records when you last checked, so roles posted since then are badged as new in the list. Both appear only when logged in.

The login and registration routes are rate limited per IP to blunt password guessing. The limiter is in-memory, so it resets on restart and counts per instance; back it with a shared store like Redis if you run more than one instance.

## API

| Method | Path                   | Purpose                                       |
| ------ | ---------------------- | --------------------------------------------- |
| GET    | /api/health            | Liveness check.                               |
| GET    | /api/board/{slug}      | Normalized, cached feed for one Ashby board.  |
| POST   | /api/auth/register     | Create an account and start a session.        |
| POST   | /api/auth/login        | Log in and start a session.                   |
| POST   | /api/auth/logout       | End the session.                              |
| GET    | /api/auth/me           | The current account, or 401.                  |
| GET    | /api/searches          | List saved searches (sort=recent or popular). |
| POST   | /api/searches          | Save the current companies and filters.       |
| POST   | /api/searches/{id}/use | Record that a saved search was reopened.      |
| DELETE | /api/searches/{id}     | Delete a saved search.                        |
| GET    | /api/seen              | When the feed was last marked seen.           |
| POST   | /api/seen              | Mark the feed as seen now.                    |
| GET    | /api/applications      | List tracked application statuses.            |
| PUT    | /api/applications      | Set or clear a job's status.                  |

The `/api/searches`, `/api/seen`, and `/api/applications` routes require login. The board and health routes are public. Login and registration are rate limited per IP.

`slug` is the handle in `jobs.ashbyhq.com/NAME`.

## Run locally

Two terminals.

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
uvicorn app.main:app --reload                        # http://localhost:8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev                                          # http://localhost:5173
```

The Vite dev server proxies `/api` to the backend on port 8000, so nothing else needs configuring. Locally the backend uses a SQLite file (`backend/data/app.db`) and a development signing secret, so it runs without setting any environment variables; the proxy also keeps the session cookie working in dev, since the browser sees one origin.

## Run with Docker

Builds the frontend, then serves it and the API from one container:

```bash
docker build -t ashby-job-feed .
docker run -p 8000:8000 ashby-job-feed              # http://localhost:8000
```

## Tests

The backend tests live under `backend/tests`:

- `test_ashby.py`: country normalization, location dedup, the normalized job shape, and `fetch_board` against a mocked HTTP transport (no network).
- `test_cache.py`: cache hits, misses, and TTL expiry.
- `test_db.py`: saving, dedup, recent and popular ordering, reopen counts, deletion, and per-user isolation.
- `test_auth.py`: password hashing, the register/login/logout/session flow, bad-input and duplicate handling, and that saved searches require login and stay scoped to their owner.
- `test_api.py`: the endpoints through FastAPI's TestClient, including cache reuse, upstream-error mapping, and the saved-search routes when logged in.
- `test_features.py`: login rate limiting, the last-seen watermark, and application tracking, including that both require login and stay per-user.

The tests run against SQLite (via a temporary `DATABASE_URL`), so they need no Postgres.

Run them:

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
ruff check .
pytest
```

GitHub Actions runs the same lint and tests, plus the frontend typecheck, unit tests, and build, on every push and pull request (`.github/workflows/ci.yml`).

## Deploy

The code lives on GitHub; a live demo needs a host that can run Python. The simplest path is a single service built from the included Dockerfile on Render, Railway, or Fly.io: point the host at the repo, choose the Docker build, and it serves the API and the built frontend together.

Because there are accounts now, production needs durable storage and a signing secret. Set `DATABASE_URL` to a PostgreSQL connection string (Render, Neon, and Supabase all offer managed Postgres), `JWT_SECRET` to a long random value, and `COOKIE_SECURE=true` so the session cookie is only sent over HTTPS. The default SQLite file is for local development only: on a host with an ephemeral filesystem it resets on redeploy, which would wipe every account, so it is not enough once people can log in.

The schema is managed with Alembic. On a Docker deploy the container runs `alembic upgrade head` on start, so tables are created and kept current with no manual step. When you change a model, add a migration with `alembic revision --autogenerate -m "describe it"` from the `backend` directory, commit it, and it applies on the next deploy. Local development skips this: against the throwaway SQLite file the app just creates the tables on startup. See [DEPLOYMENT.md](DEPLOYMENT.md) for the full walkthrough on Render with Neon Postgres.

To run the frontend and backend as separate services instead, deploy the backend on its own, build the frontend with `VITE_API_BASE` set to the backend URL, and set `ALLOWED_ORIGINS` on the backend to the frontend's origin. A split deploy makes the cookie cross-site, so set `COOKIE_SAMESITE=none` and `COOKIE_SECURE=true` on the backend; a single service keeps everything same-origin and avoids that.

## Configuration

| Variable        | Default                 | Purpose                                                     |
| --------------- | ----------------------- | ----------------------------------------------------------- |
| DATABASE_URL    | backend/data/app.db     | Database connection. Use a PostgreSQL URL in production.     |
| JWT_SECRET      | (dev fallback)          | Secret for signing session tokens. Set a long random value. Required: the app refuses to start on a production-like deploy without it. |
| COOKIE_SECURE   | false                   | Set true in production so the session cookie is HTTPS-only.  |
| COOKIE_SAMESITE | lax                     | Session cookie SameSite. Use none for a split deploy, which also forces Secure. |
| TOKEN_TTL_HOURS | 168                     | Session lifetime in hours (default 7 days).                 |
| CACHE_TTL       | 300                     | Seconds to cache each board.                                |
| ALLOWED_ORIGINS | *                       | Comma-separated CORS origins for the API.                   |
| VITE_API_BASE   | (empty)                 | Frontend build-time API base; empty is same origin.         |

## Project layout

```
backend/
  app/
    main.py     FastAPI app, routes, static serving
    ashby.py    fetch and normalize one board
    cache.py    in-memory TTL cache
    db.py       SQLAlchemy models and per-user storage (SQLite or Postgres)
    auth.py     password hashing, JWT sessions, current-user dependency
    ratelimit.py in-memory per-IP rate limiter for the auth routes
    models.py   Pydantic response models
  alembic/        database migrations (applied on deploy)
  tests/          pytest suite
  pyproject.toml  ruff and pytest config
frontend/
  src/
    App.tsx           state, data fetching, URL sync, layout
    api.ts            backend client
    lib/              pure helpers (format, filters, url)
    components/       CompanyBar, SavedSearches, AuthPanel, Filters, Facet, JobTable
Dockerfile            multi-stage build (node then python)
.github/workflows/    CI pipeline (lint, tests, build)
```

The filtering, faceting, and CSV logic in `frontend/src/lib` is written as pure functions, which keeps `App.tsx` thin and makes that logic easy to test. The app reads public job-board data; the only personal data it stores is each account's email and a bcrypt hash of its password.
