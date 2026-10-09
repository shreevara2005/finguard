# FinGuard – Algorithmic Debt & Savings Optimizer

A full-stack app that computes an optimal monthly debt-payoff and
savings-allocation plan. Two metaheuristic optimizers -- **Particle Swarm
Optimization (PSO)** and the **Firefly Algorithm** -- both run internally on
every request; the API returns only whichever one converged to the better
plan (less interest, more progress toward the savings goal).

## How the math works

Given a user's monthly cash, a list of debts (balance + APR + minimum
payment), and a savings goal, the optimizer searches for a weight vector
`[w_debt_1, ..., w_debt_n, w_savings]` (normalized to sum to 1) describing how
"extra cash" (cash left over after every debt's minimum payment) should be
split each month. A month-by-month simulation applies those weights, accrues
interest at `APR / 12` on remaining balances, and reallocates freed-up
minimum payments once a debt is paid off. The **objective function**
minimizes total interest paid, with a penalty term if the savings goal isn't
met and a large penalty if minimum payments can't be covered at all.

Both PSO and the Firefly Algorithm search this weight space on every request;
the endpoint keeps whichever one scored lower and discards the other -- you
never have to choose an algorithm or see a side-by-side comparison, you just
get the best plan found.

See `app/optimizers/objective.py`, `pso.py`, and `firefly.py` for the full
implementation and docstrings.

## Project layout

```
finguard/
├── app/
│   ├── main.py                 # FastAPI app entrypoint, DB table creation + demo user seed
│   ├── models.py                # Pydantic request/response schemas
│   ├── auth.py                  # JWT auth, now backed by the real users table
│   ├── db.py                    # SQLAlchemy engine/session (SQLite by default, Postgres-ready)
│   ├── db_models.py              # User ORM model
│   ├── api/routes.py             # /auth/register, /auth/login, /optimize-allocation
│   └── optimizers/
│       ├── objective.py         # simulation + fitness function
│       ├── pso.py               # Particle Swarm Optimization
│       └── firefly.py           # Firefly Algorithm
├── frontend/                    # React (Vite) single-page app
│   ├── src/
│   │   ├── App.jsx              # auth state + layout
│   │   ├── AuthForm.jsx         # login / signup
│   │   ├── PlanForm.jsx         # debts + savings goal input
│   │   ├── Results.jsx          # stats, balance-over-time chart, monthly table
│   │   └── api.js               # fetch wrapper for the backend
│   └── Dockerfile               # builds static assets, serves via nginx
├── tests/                       # pytest suite (16 tests: algorithms + API + auth)
├── scripts/sandbox_check.py     # standalone script to sanity-check convergence
├── Dockerfile                   # backend multi-stage production build
├── docker-compose.yml           # runs backend + frontend together
├── requirements.txt / requirements-dev.txt
└── .github/workflows/ci.yml     # test -> build -> push to GHCR on push to main
```
## Running everything locally with Docker (easiest)

```bash
cp .env.example .env              # edit JWT_SECRET_KEY to a real random string
docker compose up --build
```

- Frontend: **http://localhost:5173**
- Backend + docs: **http://localhost:8000/docs**

The backend's SQLite database is persisted in a named Docker volume
(`finguard-db`), so your users survive container restarts. `docker-compose.yml`
refuses to start without a real `JWT_SECRET_KEY` in `.env` -- by design, so a
placeholder secret never silently ends up in a real deployment.

## Running without Docker

**Backend:**
```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env               # edit JWT_SECRET_KEY
export $(cat .env | xargs)         # Windows: set vars manually, or use python-dotenv

uvicorn app.main:app --reload --port 8000
```
This creates a local `finguard.db` SQLite file on first run (no setup needed).
Swap `DATABASE_URL` to a Postgres URL when you're ready for production.

**Frontend** (separate terminal):
```bash
cd frontend
cp .env.example .env               # points at http://localhost:8000 by default
npm install
npm run dev
```
Visit **http://localhost:5173**.

**Tests:**
```bash
pytest tests/ -v                   # 16 tests: algorithms, simulation, auth, API
python scripts/sandbox_check.py    # sanity-check optimizer convergence directly
```

## Using the API directly

**1. Register (or log in with the seeded demo account `demo` / `demopassword`):**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "jane", "password": "a-real-password"}'
```
Copy the `access_token` from the response.

**2. Request an optimized allocation plan:**
```bash
curl -X POST http://localhost:8000/api/v1/optimize-allocation \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -d '{
    "monthly_cash": 3000,
    "debts": [
      {"name": "Credit Card", "balance": 5000, "apr": 0.22, "min_payment": 150},
      {"name": "Personal Loan", "balance": 10000, "apr": 0.07, "min_payment": 200}
    ],
    "savings_goal": {"target_amount": 5000, "target_month": 24},
    "horizon_months": 36
  }'
```
The response reports which algorithm won (`algorithm_used`), the plan's
totals, allocation weights, and a full month-by-month breakdown -- both
solvers ran, but only the winner is returned.

## Is the JWT setup correct? (plain-language check)

Yes -- this is a standard, correct implementation of JWT auth for an API.
Here's exactly what's happening and why it's reasonable:

1. **You log in once** with a username/password. The server checks your
   password against a bcrypt hash stored in the database (never the plain
   password), then hands back a **JWT** -- a string with three parts
   (header, payload, signature) that encodes your username and an expiry
   time.
2. **The JWT is signed, not encrypted.** Anyone can decode and read it
   (try pasting one into jwt.io), but nobody can *edit* it and have the
   signature still check out, because the signature requires
   `JWT_SECRET_KEY`, which only the server knows. That's the entire security
   model: possession of a validly-signed token is treated as proof you
   logged in successfully and haven't expired yet.
3. **Every protected request** (like `/optimize-allocation`) sends the token
   back as `Authorization: Bearer <token>`. The server re-verifies the
   signature and checks the expiry (`ACCESS_TOKEN_EXPIRE_MINUTES`, 60 by
   default) on every request -- no database lookup needed for that part,
   which is the main appeal of JWTs over server-side sessions.
4. **No password is ever stored or sent after login.** Only the token
   travels after that point, and it self-expires.

What to double check / harden before this touches real money data:
- **Always serve over HTTPS in production.** A JWT sent over plain HTTP can
  be intercepted and reused by anyone who sees it, exactly like a stolen
  session cookie.
- **`JWT_SECRET_KEY` must be a long random string you control** -- the
  `.env.example` placeholder (`dev-secret-change-me` fallback in `auth.py`)
  is only there so the app boots for local testing; never deploy with it.
- **There's no logout/revocation mechanism** -- a token is valid until it
  expires, full stop. That's normal for short-lived tokens (60 min here) but
  worth knowing: if a token leaks, it works until it naturally expires.
- **No rate-limiting on `/auth/login`** yet -- add one (e.g. via a reverse
  proxy or `slowapi`) before exposing this publicly, to blunt password
  brute-forcing.

None of these are bugs in what's shipped -- they're the standard "next
hardening steps" between a correct JWT implementation and a production-grade
one, and the same list would apply to almost any JWT setup at this stage.

## CI/CD

`.github/workflows/ci.yml` runs on every push/PR to `main`: installs deps,
runs `pytest` (fails the build on any test failure), then on pushes to `main`
builds the backend Docker image and pushes it to GitHub Container Registry.
A commented-out `deploy` job shows where to add a Render/AWS deploy hook.

## Deploying (Render example)

1. Push this repo to GitHub (already wired for GHCR image builds).
2. In Render: **New → Web Service → Deploy an existing image from a registry**,
   pointing at `ghcr.io/<owner>/<repo>/finguard-api:latest`.
3. Set env vars in Render's dashboard: `JWT_SECRET_KEY` (a real secret) and,
   if you've moved to Postgres, `DATABASE_URL`.
4. For the frontend, either deploy `frontend/Dockerfile` as a second Render
   static/web service, or build it with `VITE_API_BASE_URL` pointed at your
   deployed backend's public URL and host the static output anywhere
   (Render Static Site, Netlify, Vercel, S3+CloudFront, etc.).

(AWS ECS/Fargate works the same way in spirit: push to ECR instead of GHCR.)

## Moving from SQLite to Postgres

The app already reads `DATABASE_URL` from the environment (see `app/db.py`),
so switching is just:
```bash
DATABASE_URL=postgresql://user:password@host:5432/finguard
```
Add `psycopg2-binary` to `requirements.txt` and rebuild -- no code changes
needed. For a real production schema, add Alembic migrations instead of
relying on the automatic `Base.metadata.create_all()` used here for
convenience.
