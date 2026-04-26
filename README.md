# DeepFake Detector

A production-grade SaaS platform for detecting AI-generated content across
**images, videos, audio, text, and URLs**. Built with a strong security
posture: every uploaded file is virus-scanned with **ClamAV** before any AI
model is allowed to touch it.

```
┌──────────┐   ┌────────────┐   ┌──────────┐   ┌────────┐   ┌──────────┐
│ Next.js  │──▶│  FastAPI   │──▶│  ClamAV  │──▶│ MinIO  │──▶│ Celery   │
│ (React)  │   │  (uvicorn) │   │ (clamd)  │   │ (S3)   │   │ workers  │
└──────────┘   └─────┬──────┘   └──────────┘   └────────┘   └────┬─────┘
                     │                                             │
                     ▼                                             ▼
              ┌────────────┐                               ┌──────────────┐
              │ PostgreSQL │                               │ HuggingFace  │
              │  + Redis   │                               │  AI models   │
              └────────────┘                               └──────────────┘
```

---

## Features

### Detection modules (modular, swappable)
| Module | Default Model | Approach |
|--------|---------------|----------|
| Image  | `prithivMLmods/Deep-Fake-Detector-v2-Model` | ViT classifier |
| Video  | (uses image model) | Sample N frames → mean + max aggregation |
| Audio  | `MelodyMachine/Deepfake-audio-detection-V2`  | wav2vec2 + spectrogram fallback |
| Text   | `roberta-base-openai-detector`               | Classifier + lexical burstiness |
| URL    | (text + heuristics)                          | SSRF-safe fetch + content + metadata score |

Every module returns a uniform JSON shape:
```json
{ "score": 0.92, "label": "AI Generated", "explanation": "...", "confidence": "high" }
```

### Security pipeline (every upload)
1. **File validation** — extension allow-list, MIME sniff (libmagic), per-plan size cap
2. **SHA-256 hashing** — duplicate detection + blacklist lookup
3. **ClamAV virus scan** — over TCP `clamd`, **fail-closed** if scanner is unreachable
4. **Isolated storage** — files saved as UUID keys in a private MinIO bucket
5. **Async processing** — Celery workers with per-modality queues
6. **Audit logging** — every upload, rejection, virus hit, login, payment

### User & billing
- JWT auth (access + refresh + reset tokens), bcrypt password hashing
- Forgot/reset password by email (SMTP)
- Three plans: **Free / Pro / Enterprise** with daily-quota and file-size caps
- **Razorpay** integration with server-side signature verification
- Per-user + per-IP rate limiting (`slowapi`, Redis-backed)
- Admin endpoints for audit log + malicious-hash blacklist

### Frontend
- Next.js 14 (App Router) + TypeScript
- TailwindCSS + Framer Motion + Lucide icons
- Drag-and-drop upload (`react-dropzone`)
- Real-time scan polling, animated score bars
- Downloadable PDF reports (server-side ReportLab)

---

## Project layout

```
deepfake-detector/
├── frontend/                  Next.js app
├── backend/
│   └── app/
│       ├── api/               Auth, detection, history, subscription, admin
│       ├── core/              Config, logging, security primitives
│       ├── db/                SQLAlchemy session
│       ├── models/            ORM models (User, Subscription, Scan, …)
│       ├── schemas/           Pydantic request/response schemas
│       ├── security/          virus_scanner, file_validator, hashing,
│       │                      rate_limit, audit
│       ├── services/          MinIO, Redis cache, email, payments, plans, PDF
│       └── workers/           Celery app + tasks
├── ai-services/               Modular detectors (image/video/audio/text/url)
├── infra/
│   └── docker-compose.yml     Postgres, Redis, MinIO, ClamAV, backend,
│                              worker, flower, frontend
├── start.sh / start.ps1       One-command bootstrap
├── .env.example               All configuration
└── README.md
```

---

## Quickstart

### Prerequisites
- Docker Desktop (with Compose v2)
- ~6 GB free RAM (HuggingFace models + ClamAV signatures)
- ~3 GB free disk

### Run everything
```bash
# Linux / macOS
./start.sh

# Windows PowerShell
.\start.ps1
powershell -ExecutionPolicy Bypass -File .\start.ps1```

The script:
1. Creates `.env` from `.env.example` if missing
2. Builds all containers
3. Starts the full stack

> **Heads up:** the first time `clamav` starts, it downloads ~500 MB of
> virus signatures (typically 5–10 minutes). Until that finishes, uploads
> will be rejected with HTTP 503 — this is the **fail-closed** design.
>
> Watch progress with: `docker compose -f infra/docker-compose.yml logs -f clamav`

### Endpoints
| URL | Description |
|------|------------|
| http://localhost:3000        | Frontend (Next.js) |
| http://localhost:8000/docs   | Backend OpenAPI / Swagger UI |
| http://localhost:9001        | MinIO console (`minioadmin` / `minioadmin`) |
| http://localhost:5555        | Flower (Celery dashboard) |

---

## API reference (selected)

### Auth
```
POST /auth/register          Register
POST /auth/login             Login → JWT pair
POST /auth/refresh           Refresh access token
POST /auth/forgot-password   Request reset email
POST /auth/reset-password    Reset using token
GET  /auth/me                Current user
```

### Detection (require Bearer token)
```
POST /detect/image           multipart file
POST /detect/video           multipart file
POST /detect/audio           multipart file
POST /detect/text            { "text": "..." }
POST /detect/url             { "url": "https://..." }
GET  /detect/{scan_id}       Poll status / fetch result
```

All four file endpoints respond `202 Accepted` with a `scan_id`. Poll
`GET /detect/{scan_id}` until `status == "completed"`.

### History & reports
```
GET  /history                       Paginated past scans
GET  /report/{scan_id}              Download PDF report
```

### Subscription
```
GET  /subscription                  Current plan + usage
GET  /subscription/plans            Available plans
POST /subscription/order            Create Razorpay order
POST /subscription/verify           Verify payment signature
POST /subscription/cancel           Cancel & revert to Free
```

### Admin (role=admin)
```
GET  /admin/audit                   Full audit log
GET  /admin/blacklist               Malicious-hash blacklist
POST /admin/blacklist               Add a SHA-256 to blacklist
```

---

## Configuration

All configuration is in a single `.env` file at the repo root. Minimum
required for production:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing key — **must** be a long random string |
| `DATABASE_URL` | Postgres URI |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis URIs |
| `MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY/BUCKET` | Object storage |
| `CLAMAV_HOST/PORT` | ClamAV daemon |
| `SMTP_*` | Outgoing email for password reset |
| `RAZORPAY_KEY_ID/SECRET/WEBHOOK_SECRET` | Payments |
| `PLAN_FREE_DAILY`, `PLAN_PRO_DAILY`, `PLAN_ENTERPRISE_DAILY` | Quota |
| `PLAN_*_MAX_FILE_MB` | File-size caps |
| `RATE_LIMIT_PER_MINUTE` | Per-user + per-IP rate limit |

---

## Production deployment

This compose file is suitable for a single-host install. For real
production:

1. **Use Postgres / Redis / MinIO managed services** (RDS, ElastiCache, S3).
2. **Run Alembic migrations** instead of `Base.metadata.create_all`
   (auto-create runs only when `APP_ENV != production`).
3. **Front the API with a reverse proxy** (nginx, Caddy, Traefik) and
   terminate TLS there.
4. **Scale workers horizontally** — each detection module has its own
   queue (`-Q image,video,audio,text,url`); spawn one Celery worker per
   queue and tune `--concurrency` per CPU/GPU available.
5. **Mount a GPU into the worker container** for HuggingFace models — set
   `device=0` in the AI services' pipeline calls.
6. **Run ClamAV in a separate, dedicated container/host**. Keep the daemon
   close to the API to minimize round-trip on `instream` calls.
7. **Rotate `SECRET_KEY`** and store secrets in a vault (Doppler, AWS
   Secrets Manager, GCP Secret Manager).

---

## Development workflow

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Workers (in another shell)
cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=info \
  -Q image,video,audio,text,url --concurrency=2
```

Set `DATABASE_URL=postgresql+psycopg2://...@localhost:5432/...` and
`REDIS_URL=redis://localhost:6379/0` in your local `.env` (the docker
services bind to those ports).

---

## Swapping AI models

Each detector reads a `*_MODEL` environment variable:
```
DEEPFAKE_IMAGE_MODEL=your-org/your-image-model
DEEPFAKE_AUDIO_MODEL=your-org/your-audio-model
DEEPFAKE_TEXT_MODEL=your-org/your-text-model
```
On the next worker restart the new model is downloaded and used. To plug
in a custom architecture, edit `ai-services/<modality>/detector.py` —
each module exposes a single `detect_<modality>(...)` function returning
the standard result dict.

---

## Security checklist

- [x] ClamAV scan **before** AI processing (fail-closed)
- [x] MIME sniff via libmagic — declared MIME ignored
- [x] Plan-based size cap per upload
- [x] SHA-256 hashing + malicious-hash blacklist
- [x] Files stored as UUIDs, never executed
- [x] Rate limiting per user + per IP
- [x] Audit log for every security-relevant event
- [x] SSRF protection on URL fetcher (private IP block)
- [x] JWT with short-lived access + refresh tokens
- [x] bcrypt password hashing
- [x] Server-side Razorpay signature verification
- [x] CORS pinned to `FRONTEND_URL`

---

## License

MIT — built as a reference architecture for production-grade ML SaaS.
