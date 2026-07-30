# Deploying the Ashby job feed

This takes the app from a zip on your machine to a live URL, running as one service with a real database behind it. It assumes the accounts and per-user saved searches the app now has, which means it needs durable Postgres, not the local SQLite file.

The setup is one Render web service running the app's Docker image (it serves the API and the built frontend together) plus one Neon Postgres database for accounts and saved searches. Both have free tiers that are enough for a small group.

**Why an external database.** The app stores accounts, so the data has to survive restarts. A Render free web service has an ephemeral filesystem: it resets on every redeploy and every wake from sleep, which would wipe a SQLite file and every account with it. Putting the database on Neon, separate from the web service, lets the web service sleep, wake, and redeploy freely while the data persists.

**Why Neon.** We rolled our own auth, so all we need from a provider is a plain managed Postgres. Neon is serverless Postgres with a free tier that does not expire, needs no card, and hands you a standard connection string that SQLAlchemy uses unchanged. It scales the database to zero when idle and wakes in about half a second, so an idle tracker barely touches the free allowance.

## Before you start

Three free accounts: GitHub to host the code, Neon for the database, and Render for the app. None need a card for the free path.

Local prerequisites: Python 3.12 or 3.13, and Node.js 18 or newer. Use 3.12 or 3.13 specifically. Python 3.14 is new enough that some dependencies, notably psycopg2-binary on Windows, may not ship prebuilt wheels yet, which turns the install into a compile step that can fail. Check what you have with `py --list` on Windows or `python3 --version` elsewhere; if the only version is 3.14, install 3.12 or 3.13 from python.org (they coexist fine).

## Step 1: Run it locally once

Confirm the app works before deploying. Locally it uses a SQLite file and a development secret, so it needs no configuration and no Postgres.

Unzip, then create a virtual environment with a stable Python and activate it. The create and activate commands differ by OS:

```bash
cd ashby-job-feed/backend

# create the venv (pick 3.12 or 3.13)
py -3.12 -m venv .venv            # Windows
python3.12 -m venv .venv          # macOS / Linux

# activate it
.venv\Scripts\activate            # Windows (CMD)
.venv\Scripts\Activate.ps1        # Windows (PowerShell)
source .venv/bin/activate         # macOS / Linux
```

Your prompt should now start with `(.venv)`. With the environment active, install and run:

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Use `python -m pip` and `python -m uvicorn` rather than bare `pip` and `uvicorn`, so they run inside the venv instead of some other Python on your PATH. That PATH mismatch is the most common local setup failure. Locally the app runs on a throwaway SQLite file and a dev signing secret; psycopg2 and the real secret only matter in production.

In a second terminal, start the frontend:

```bash
cd ashby-job-feed/frontend
npm install
npm run dev
```

Open the Vite URL it prints (usually http://localhost:5173). Register an account, add a company or two, and save a search. If that works, the app is sound, and anything that breaks after deploying is configuration, not code.

Recommended: run the tests too, with the same venv active.

```bash
cd ashby-job-feed/backend
python -m pip install -r requirements-dev.txt
ruff check .
python -m pytest
```

## Step 2: Create the database on Neon

1. Sign in at neon.tech and create a project. Pick a region near where the web service will run; same continent keeps latency low.
2. Neon shows a connection string when the project is ready. Copy the pooled one: its host contains `-pooler`. The pooled string handles many short connections better, which suits a web app.
3. It looks like `postgresql://user:password@ep-xxxx-pooler.region.aws.neon.tech/dbname?sslmode=require`. Save it for Step 4 and treat it like the password it contains.

The app takes this string as-is. If it starts with `postgres://`, the app rewrites it for SQLAlchemy automatically; `postgresql://` is used directly.

Free-tier note: the free project gives 0.5 GB of storage and 100 compute-hours a month, far more than a few people's accounts and saved searches will use, especially with the database asleep most of the time. Those limits are hard stops rather than throttles, so blowing past them would pause the database until the next cycle. At this scale you won't.

## Step 3: Put the code on GitHub

From the project root:

```bash
cd ashby-job-feed
git init
git add .
git commit -m "Ashby job feed with accounts and saved searches"
```

Create a new empty repository on GitHub with no README, license, or .gitignore, since the project already has them. Then connect and push using the commands GitHub shows, along the lines of:

```bash
git remote add origin https://github.com/RishabhP1508/ashby-job-feed.git
git branch -M main
git push -u origin main
```

If Git asks for a password, GitHub wants a personal access token, not your account password. Create one under Settings, Developer settings, personal access tokens, and use it as the password.

One follow-up:

- Open the Actions tab and confirm the workflow runs green. It installs the dependencies and runs the backend tests against SQLite plus the frontend typecheck, unit tests, and build, so a green check means the parts that can't run offline actually pass. If it's red, open the failing job and read the first error line.

## Step 4: Deploy on Render

1. In the Render dashboard, choose New, then Web Service, and connect the GitHub repo.
2. Render detects the Dockerfile; choose the Docker runtime if prompted. Pick the Free instance type.
3. Before creating, open the Environment section and add three variables:
   - `DATABASE_URL`: the Neon pooled connection string from Step 2.
   - `JWT_SECRET`: a long random value. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and paste the output.
   - `COOKIE_SECURE`: `true`. Render serves over HTTPS, so the session cookie should be HTTPS-only.

   A split deploy (frontend and backend on separate origins) also needs `COOKIE_SAMESITE=none` and `COOKIE_SECURE=true`, otherwise the browser drops the cross-site session cookie. `COOKIE_SAMESITE` must be exactly `lax`, `strict`, or `none`; any other value falls back to `lax`.
4. Set the health check path to `/api/health` so Render knows when the service is up.
5. Create the service. The first build takes a few minutes: it builds the frontend, then the Python image. When it's live, Render gives you a URL.

On start the Docker image runs `alembic upgrade head`, which creates or updates the schema in the Neon database, then launches the server. There's nothing to run by hand for the first deploy, and the migration step is a safe no-op once the schema is current, so it runs harmlessly on every restart.

## Step 5: Verify it end to end

Open the Render URL. Register an account, save a search, then trigger a redeploy (or wait for the free service to sleep and hit it again). Log back in: the account and its saved searches are still there, because they live in Neon, not on the web service's disk. That is the whole reason for the external database.

## What "free" feels like in practice

There are two independent idle behaviors:

- The Render free web service sleeps after about 15 minutes with no traffic. The next request wakes it, which takes roughly 30 to 50 seconds, after which it stays responsive until it idles again.
- The Neon database scales to zero when idle and wakes on the first query in about half a second.

So the slow part of a cold visit is Render waking the web service, not the database. Data survives both sleeping and redeploys. If the wait bothers you, a paid Render instance stays always-on, and the database can remain on Neon's free tier regardless.

## Hardening and next steps

A few things this setup does not do yet, roughly in the order worth tackling them:

Two items are already handled:

- **Login rate limiting** is in place: the login and registration routes are limited per IP. The limiter is in-memory, so it resets on restart and counts per instance. If you ever run more than one instance, move it to a shared store like Redis.
- **Schema migrations** run through Alembic. When you change the models, create a migration with `alembic revision --autogenerate -m "describe the change"` from the `backend` directory, commit it, and it applies automatically on the next deploy (the container runs `alembic upgrade head` on start).

Still worth doing later:

- **Backups.** Neon's free tier keeps your data but has no long backup window. For anything you'd hate to lose, export occasionally with `pg_dump`, or move to a paid tier for point-in-time restore.
- **Password reset.** There is no reset flow, and JWT sessions can't be revoked without a denylist. For a few users that's livable; a real reset needs an email provider.

## Running as two services instead (optional)

To host the frontend and backend separately (for example the frontend on a static host), deploy the backend on its own with the same three env vars, build the frontend with `VITE_API_BASE` set to the backend's URL, and set `ALLOWED_ORIGINS` on the backend to the frontend's origin. One catch: split origins make the session cookie cross-site, so it must be sent as `SameSite=None; Secure` and the browser will only accept it over HTTPS. The single-service setup above avoids this because everything is one origin.

## Troubleshooting

- **Login returns 500.** Usually `JWT_SECRET` isn't set. Confirm all three env vars are present, then redeploy.
- **Database connection errors on boot.** Check the string is the pooled one and includes `?sslmode=require`. If the error mentions channel binding, remove a trailing `&channel_binding=require`.
- **Login works but you're logged out on the next click.** A cookie problem. In production confirm `COOKIE_SECURE=true` and that you're on the HTTPS URL. Locally, use the Vite dev URL rather than hitting port 8000 directly, so the browser sees one origin.
- **CI is red.** Open the failing job in the Actions tab; the first error line is the cause. Backend failures are almost always a missing dependency or a real test failure; frontend failures are usually a type error from `npm run build`.
- **Render build fails.** Read the build logs. The Docker build needs both halves to build cleanly, which local Step 1 and green CI already confirm.
- **Deploy starts then exits during migrations.** Look for the `alembic upgrade head` output in the deploy logs. A failure there usually means `DATABASE_URL` is wrong or unreachable, or a hand-edited migration is invalid. Confirm the connection string, then redeploy. To reproduce locally, run `alembic upgrade head` from the `backend` directory against a copy of the database.
- **Local install lands in the wrong place, or uvicorn or pytest can't find installed modules.** The virtual environment isn't active. Activate it (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` elsewhere) and confirm the prompt shows `(.venv)` before installing. Bare `pip`, `uvicorn`, and `pytest` can resolve to a different Python on your PATH; use `python -m pip`, `python -m uvicorn`, and `python -m pytest` to force the venv. On Windows, `source .venv/bin/activate` will not work; that is the Unix path, and the Windows script is `.venv\Scripts\activate`.
- **Local install fails while building psycopg2-binary.** Your Python is probably 3.14, which may lack prebuilt wheels. Delete `.venv`, recreate it with 3.12 or 3.13 (`py -3.12 -m venv .venv`), reactivate, and reinstall.
