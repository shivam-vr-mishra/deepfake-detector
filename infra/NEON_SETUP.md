# Using Neon as your database

[Neon](https://neon.tech) is serverless Postgres. It's a great fit because:

- It's **plain PostgreSQL** — no app changes needed (`UUID`, `JSONB`, advisory locks, all supported).
- The free tier gives you 0.5 GB storage, automatic daily backups, point-in-time-recovery up to 7 days, and a built-in web SQL editor.
- Compute scales to zero when idle — you don't pay for an always-on database.
- Branching: throwaway copies of production for testing, in seconds.

This guide walks you from **0 to a working Neon-backed deploy** using the project's `start.sh` / `start.ps1` automation.

---

## How database switching works in this project

`.env` defines **two** Postgres URLs that live side-by-side, plus a switch that picks which one is active:

```env
DB_TARGET=neon                      # "neon" (default) or "local"

DATABASE_URL_LOCAL=postgresql+psycopg2://deepfake:deepfake_pw@postgres:5432/deepfake_db
DATABASE_URL_NEON=postgresql://USER:PASS@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
```

| `DB_TARGET` | Postgres source | Local `postgres` container | Used by |
|---|---|---|---|
| `neon` (default) | Neon — `DATABASE_URL_NEON` | **disabled** (skipped by `docker-compose.neon.yml`) | day-to-day work |
| `local` | Docker container — `DATABASE_URL_LOCAL` | starts normally | offline / no-internet dev |
| `prod` | Whichever URL `DB_TARGET` resolves to | disabled | production VM (adds hardening from `docker-compose.prod.yml`) |

The application reads `DB_TARGET` and picks the right URL (see `backend/app/core/config.py`). The startup scripts read `DB_TARGET` and pick the right compose files. Everything stays in sync from one variable.

---

## 1. Get the connection string from Neon

In the Neon dashboard, open your project → **Connection Details**. You'll see something like:

```
postgresql://neondb_owner:npg_xxxxxxxxxxxx@ep-orange-meadow-an1vtqgr.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require
```

Two important details:

- **Use the "direct" host** (the one *without* `-pooler` in the name). The pooler is for serverless / edge / Lambda. SQLAlchemy already pools connections itself, so the direct host is correct for our long-running FastAPI backend.
- Always keep `?sslmode=require` at the end. Neon refuses unencrypted connections.

> **Heads up:** if you ever pasted this credential into a chat, screenshot, or git commit, **rotate the password** in Neon (Project → **Roles** → select role → **Reset password**). Treat this string like a server password.

---

## 2. Wire it into the application

Open `.env` and paste your Neon URL into `DATABASE_URL_NEON`:

```env
DB_TARGET=neon

DATABASE_URL_LOCAL=postgresql+psycopg2://deepfake:deepfake_pw@postgres:5432/deepfake_db
DATABASE_URL_NEON=postgresql://neondb_owner:<NEW_PASSWORD>@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
```

Lock down the file so other Linux users on the VM can't read it:

```bash
chmod 600 .env
```

(On Windows, right-click → **Properties** → **Security** if you care; for a personal dev machine the default ACL is fine.)

---

## 3. Bring everything up — one command

### Linux / macOS

```bash
chmod +x start.sh        # only the first time
./start.sh               # uses DB_TARGET from .env (neon by default)
```

### Windows (PowerShell)

```powershell
.\start.ps1
```

If PowerShell complains about execution policy:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
# or, one-time:
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

`start.sh` / `start.ps1` will:

1. Create `.env` from `.env.example` if it doesn't exist (and stop so you can fill it in).
2. Read `DB_TARGET` from `.env`.
3. Pick the right compose files automatically:
   - `DB_TARGET=neon` → `docker-compose.yml` + `docker-compose.neon.yml`
   - `DB_TARGET=local` → `docker-compose.yml` only
   - `DB_TARGET=prod` → `docker-compose.yml` + `docker-compose.prod.yml`
4. Build images and start all services.
5. Wait for the backend to become healthy (polls `/health`).
6. Run schema bootstrap automatically (idempotent — safe to re-run).
7. Print connection info + useful follow-up commands.

You'll see something like:

```
================================================================
  DeepFake Detector — booting with DB_TARGET=neon
================================================================
  Database: Neon (managed Postgres) — local postgres container disabled
================================================================
[2/5] Building images...
[3/5] Starting services...
[4/5] Waiting for backend to become healthy...
    Backend is up.
[5/5] Ensuring database schema is created...
DB: {'profile': 'remote', 'driver': 'postgresql+psycopg2', 'host': 'ep-orange-meadow-an1vtqgr.c-6.us-east-1.aws.neon.tech', 'port': 5432, 'database': 'neondb', 'ssl': True}
db.schema.bootstrapped profile=remote
```

---

## 4. Switching between Neon and local Postgres

Two ways:

**A. Edit `.env`** (persists for next runs):

```env
DB_TARGET=local      # or neon
```

then `./start.sh`.

**B. One-shot via CLI** (doesn't change `.env`):

```bash
./start.sh local       # boot with local Postgres just for this run
./start.sh neon        # boot with Neon
./start.sh prod        # boot with full production hardening
```

Same on Windows: `.\start.ps1 local`, `.\start.ps1 neon`, `.\start.ps1 prod`.

---

## 5. Verify everything works

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "db": {
    "ok": true,
    "profile": "remote",
    "host": "ep-orange-meadow-an1vtqgr.c-6.us-east-1.aws.neon.tech"
  },
  "clamav": true
}
```

`profile=remote` confirms the engine is using Neon-tuned pool settings. `profile=local` would mean it's pointing at the docker container.

Check tables in Neon's SQL Editor (top-right of the Neon dashboard):

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema='public' ORDER BY 1;
```

You should see:

```
audit_logs
credit_wallets
malicious_hashes
scans
subscriptions
usage_records
users
```

---

## 6. How to inspect / query the database

### Option A — Neon's SQL Editor (zero setup, easiest)

In the Neon dashboard → **SQL Editor**:

```sql
SELECT id, email, role, is_verified, created_at
FROM users
ORDER BY created_at DESC
LIMIT 20;

SELECT plan, COUNT(*) AS users
FROM subscriptions
GROUP BY plan;

SELECT user_id, balance
FROM credit_wallets
WHERE balance > 0
ORDER BY balance DESC;
```

There's also a "Tables" tab for visual browsing.

### Option B — Desktop GUI (DBeaver / TablePlus / pgAdmin)

Connect with:

| Field | Value |
|---|---|
| Host | `ep-xxx.region.aws.neon.tech` (your Neon host) |
| Port | `5432` |
| Database | `neondb` |
| User | `neondb_owner` |
| Password | (from your `.env`) |
| SSL Mode | `require` |

DBeaver: **New Connection → PostgreSQL → URL: `jdbc:postgresql://...?sslmode=require`**.

TablePlus: **Create new connection → PostgreSQL** → tick **Use SSL**.

### Option C — `psql` from a throwaway container

```bash
# Linux / macOS
docker run --rm -it --env-file .env postgres:16-alpine \
  sh -c 'psql "$DATABASE_URL_NEON"'
```

```powershell
# Windows
docker run --rm -it --env-file .env postgres:16-alpine `
  sh -c 'psql "$DATABASE_URL_NEON"'
```

Inside the prompt:

```
\dt              -- list tables
\d+ users        -- describe users table with details
\timing on       -- show query timings
SELECT count(*) FROM scans;
\q
```

(For the local DB, swap `$DATABASE_URL_NEON` for `$DATABASE_URL_LOCAL`.)

---

## 7. Backups & disaster recovery

Neon handles this for you on the free tier:

- **Continuous WAL archive** with **7 days of point-in-time recovery** (longer on paid plans).
- **Restore by branching**: dashboard → **Branches** → **Create branch from history** → pick a timestamp → you get a brand-new endpoint you can read from or promote to primary.

For belt-and-braces, take a weekly logical dump to off-Neon storage (Backblaze B2 / S3 / Wasabi):

```bash
docker run --rm --env-file .env postgres:16-alpine \
  sh -c 'pg_dump -Fc "$DATABASE_URL_NEON"' \
  | rclone rcat remote:deepfake-backups/neondb-$(date -u +%Y%m%d).dump
```

Cron entry:

```cron
30 3 * * 0 cd /opt/deepfake && bash scripts/weekly-neon-backup.sh
```

Restore:

```bash
cat neondb-20260426.dump \
  | docker run --rm -i --env-file .env postgres:16-alpine \
      sh -c 'pg_restore --clean --if-exists -d "$DATABASE_URL_NEON"'
```

---

## 8. Neon-specific gotchas

| Gotcha | What's happening | Mitigation |
|---|---|---|
| **First request takes ~500 ms after idle** | Neon suspends compute after ~5 min idle on free tier. | `pool_pre_ping=True` + `pool_recycle=300` already configured in `app/db/dbconfig.py`. First request slow, subsequent fast. |
| **Connection limit** | Free tier ≈ 100 direct connections. | Engine pool is `pool_size=10, max_overflow=10` for remote DBs (auto-detected). 1 backend + 4 workers stays well under the cap. |
| **Long-running transactions** | Neon closes idle-in-transaction sessions after ~5 min. | Don't hold a session open across slow external calls. |
| **`pg_stat_statements`** | Enabled by default. | `SELECT * FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 20;` to find slow queries. |
| **Write costs storage** | Free tier counts WAL written to disk. | Audit log is fine; don't run tight insert loops on free tier. |

---

## 9. Production deployment checklist

When promoting from dev → real production VM:

- [ ] **Use the prod overlay**: `./start.sh prod` (or `.\start.ps1 prod`) — adds resource limits, log rotation, password-protected Redis, and hides Flower / MinIO console behind localhost-only ports.
- [ ] Set `APP_ENV=production` in production `.env`.
- [ ] Generate strong values for `SECRET_KEY`, `REDIS_PASSWORD`, `MINIO_*_KEY`, `FLOWER_PASSWORD`:
      ```bash
      openssl rand -base64 32
      ```
- [ ] Live Razorpay keys: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`.
- [ ] `chmod 600 .env`.
- [ ] Put Caddy or Nginx in front for HTTPS (see `infra/SELF_HOSTING.md` §6).
- [ ] Rotate the Neon password (and update `DATABASE_URL_NEON`) if the password ever appeared in chat / logs / screenshots.

---

## TL;DR

1. Paste your Neon URL into `DATABASE_URL_NEON` in `.env`.
2. `./start.sh` (or `.\start.ps1` on Windows). Done.
3. Switch databases anytime with `./start.sh local` / `./start.sh neon`.
4. Browse tables in Neon's SQL Editor or any PG GUI client.
