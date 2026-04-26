# Observability — viewing logs through a UI

This stack adds **Grafana + Loki + Promtail** so you can read, filter and
graph logs from every container in your project from a single web UI.
A second optional service, **Dozzle**, gives you a 1-container "live tail"
view if you don't want the full stack.

| Tool | Image size | What you get | When to use it |
|------|-----------|--------------|----------------|
| **Loki + Promtail + Grafana** | ~250 MB | Searchable history, dashboards, alerts | Default. Real debugging, pre-prod, prod |
| **Dozzle** | ~25 MB | Live tail with substring filter, no history | "I just want to glance at logs in a browser" |

The Grafana + Loki + Promtail stack is **on by default** in `start.ps1` and
`start.sh`. Pass `-NoObservability` (PowerShell) or `--no-observability`
(bash) to skip it on a low-RAM machine, in CI, etc.

If you start the stack with raw `docker compose up`, observability is opt-in
because that command doesn't read flags — see the explicit file list below.

---

## Quick start (Grafana + Loki)

```powershell
# Windows — observability is included automatically
.\start.ps1                       # neon DB + Grafana
.\start.ps1 local                 # local DB + Grafana
.\start.ps1 -NoObservability      # neon DB, no Grafana
```

```bash
# macOS / Linux — observability is included automatically
./start.sh                         # neon DB + Grafana
./start.sh local                   # local DB + Grafana
./start.sh --no-observability      # neon DB, no Grafana
```

Or use Docker Compose directly:

```bash
docker compose \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.neon.yml \
  -f infra/docker-compose.observability.yml \
  --env-file .env up -d
```

Wait ~30 seconds, then open:

- **Grafana**: <http://localhost:3001>
  - Login: `admin` / `$GRAFANA_PASSWORD` (default `admin` — set in `.env`)
  - Dashboard: **Dashboards → Browse → "DeepFake Detector — Logs Overview"**
- **Loki API** (advanced): <http://localhost:3100/ready> (bound to localhost only)

That's it. The dashboard live-tails the backend, worker, and Celery logs and
shows error rate, email-pipeline events, and auth events out of the box.

---

## How it works

```
                              ┌──────────────┐
   Docker container stdout ─▶ │   Promtail   │  (reads /var/run/docker.sock,
                              │              │   service-discovers your
                              │              │   project's containers)
                              └──────┬───────┘
                                     │ JSON push
                                     ▼
                              ┌──────────────┐
                              │     Loki     │  (stores logs by label, indexes
                              │              │   labels only — bodies are
                              │              │   compressed & cheap to keep)
                              └──────┬───────┘
                                     │ LogQL
                                     ▼
                              ┌──────────────┐
                              │   Grafana    │  ◀── your browser
                              └──────────────┘
```

- **Promtail** watches `/var/run/docker.sock` and only scrapes containers in
  the `deepfake-detector` Compose project (filter in
  `infra/observability/promtail/promtail-config.yaml`).
- It parses each line as JSON (your `structlog` output), promotes `level` to
  a Loki label, and uses the `timestamp` field as the event time.
- Loki keeps logs for **7 days** by default (`retention_period: 168h` in
  `loki-config.yaml`). For prod, raise that to `720h` or longer.

---

## Useful LogQL queries

Open Grafana → **Explore** (compass icon, left sidebar) → datasource **Loki**.

```logql
# Live tail every container in the project
{project="deepfake-detector"}

# Backend only
{service="backend"}

# Backend errors only
{service="backend", level="error"}

# Anything mentioning email
{project="deepfake-detector"} |= "email"

# SMTP failures with hint extracted
{service="backend"} |~ "email\\.send_failed" | json

# Auth failures grouped per minute
sum by (service) (rate(
  {project="deepfake-detector"} |~ "login_failure" [1m]
))

# Group log volume by container
sum by (container) (count_over_time(
  {project="deepfake-detector"}[5m]
))
```

The panel filter syntax is the same:

| Filter | Meaning |
|--------|---------|
| `{label="value"}` | Label match (uses Loki's index — fast) |
| `\|= "literal"` | Line contains literal substring |
| `\|~ "regex"` | Line matches regex |
| `\| json` | Parse line as JSON, exposes fields for `\|=` filtering |
| `\| line_format "{{.event}}"` | Reformat output |

Click any log line in a panel → **right-click → "View context"** to see the
20 lines on either side.

---

## Setting up alerts (optional)

In Grafana → **Alerting → Alert rules → New rule** → datasource Loki:

```logql
sum(rate({project="deepfake-detector", level="error"}[5m])) > 0.5
```

Then add a contact point (Slack, Discord, email, webhook) under
**Alerting → Contact points**. The OSS Grafana image already supports all of
those — no extra plugin needed.

A starter rule you'll probably want:

```logql
# Page me if email_send_failed.auth happens (SMTP creds wrong)
sum(rate(
  {service="backend"} |~ "email\\.send_failed\\.auth" [5m]
)) > 0
```

---

## Dozzle (the tiny alternative)

If the full stack feels like overkill, run Dozzle on its own:

```bash
docker compose \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.observability.yml \
  --profile dozzle up -d dozzle
```

Open <http://localhost:9999>. You'll see every container in your project
with a real-time scrolling log view, a substring search box, and severity
colouring. **No history is kept** — when a container restarts, its logs are
gone. Stop it with:

```bash
docker compose -f infra/docker-compose.observability.yml \
  --profile dozzle stop dozzle
```

Set `DOZZLE_USERNAME` / `DOZZLE_PASSWORD` in `.env` if you ever expose it
beyond `localhost`.

---

## Production notes

The compose file binds Loki and Dozzle to `127.0.0.1` so they can never be
hit from outside the host. Grafana is bound to `:3001` because you generally
do want to access it. Before exposing Grafana to the internet:

1. Set a strong `GRAFANA_PASSWORD` in `.env`.
2. Put it behind your reverse proxy (Caddy / Traefik / nginx) on a subdomain
   with HTTPS, e.g. `logs.example.com`.
3. Optionally enable single sign-on:
   - `GF_AUTH_GOOGLE_ENABLED=true`, `GF_AUTH_GOOGLE_CLIENT_ID=…`
   - or use Cloudflare Access / Tailscale for IP-based gating.
4. For multi-day retention, change `retention_period` in `loki-config.yaml`
   and either raise the volume size or move chunks to S3/GCS:
   ```yaml
   storage_config:
     aws:
       s3: s3://us-east-1/deepfake-loki-chunks
   ```
5. Watch Loki's disk use: `docker exec -it deepfake-detector-loki-1 du -sh /loki`.

---

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Grafana asks for login forever | First login is `admin`/`admin`; it forces a password change. Set `GRAFANA_PASSWORD` in `.env` and recreate the container to pre-set it: `docker compose -f infra/docker-compose.yml -f infra/docker-compose.observability.yml up -d --force-recreate grafana`. |
| Dashboard shows "No data" | Open **Explore → Loki** and run `{project="deepfake-detector"}`. If empty, check `docker logs deepfake-detector-promtail-1` — it should print `discovered N containers`. |
| Promtail keeps restarting | The Docker socket isn't mounted (Windows: enable WSL2 file sharing for `/var/run/docker.sock`; macOS: works out of the box). |
| Logs visible but `level` is empty | Some lines aren't JSON (e.g. uvicorn access logs). The `json` pipeline stage in `promtail-config.yaml` skips those silently — they still show up, just without parsed fields. |
| Loki disk full | Lower `retention_period` in `loki-config.yaml`, or move to S3 (see Production notes). |

---

## File layout

```
infra/
├── docker-compose.observability.yml      ← the opt-in stack
└── observability/
    ├── loki/loki-config.yaml             ← single-binary Loki config
    ├── promtail/promtail-config.yaml     ← Docker SD + JSON parsing
    └── grafana/
        ├── provisioning/
        │   ├── datasources/loki.yaml     ← auto-add Loki on first boot
        │   └── dashboards/default.yaml   ← pick up dashboards/*.json
        └── dashboards/
            └── deepfake-overview.json    ← starter dashboard
```

Edit any of these and restart the relevant container — provisioning files
re-load on startup, dashboards reload every 30s.
