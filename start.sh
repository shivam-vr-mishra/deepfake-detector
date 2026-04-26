#!/usr/bin/env bash
# =============================================================
# DeepFake Detector — one-command bootstrap
#
# Reads DB_TARGET from .env to decide which database to use:
#   DB_TARGET=neon  (default) -> skip local postgres, connect to Neon
#   DB_TARGET=local           -> launch the postgres container locally
#
# The Grafana + Loki + Promtail observability stack is started by default
# (Grafana on http://localhost:3001). Pass --no-observability to skip it.
#
# Override at runtime:
#   ./start.sh                       # .env DB_TARGET, observability ON
#   ./start.sh local                 # force local Postgres
#   ./start.sh neon                  # force Neon
#   ./start.sh prod                  # production override
#   ./start.sh --no-observability    # skip Grafana / Loki / Promtail
# =============================================================
set -euo pipefail

cd "$(dirname "$0")"

# ---------- Helpers ----------
green()  { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
red()    { printf "\033[31m%s\033[0m\n" "$*"; }
bold()   { printf "\033[1m%s\033[0m\n" "$*"; }

# ---------- 1. .env ----------
echo "[1/5] Checking environment file..."
if [ ! -f .env ]; then
  cp .env.example .env
  yellow "    .env created from .env.example — open it and fill in real secrets."
  yellow "    At minimum set DATABASE_URL_NEON, SMTP_USER, SMTP_PASSWORD, RAZORPAY_*."
  exit 1
fi

# Read DB_TARGET from .env, plus parse a positional target and an optional
# `--no-observability` / `--observability` flag (in any order).
DB_TARGET_FROM_ENV="$(grep -E '^DB_TARGET=' .env | tail -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs || true)"
DB_TARGET=""
OBSERVABILITY=1   # default: ON
for arg in "$@"; do
  case "$arg" in
    --no-observability) OBSERVABILITY=0 ;;
    --observability|-o) OBSERVABILITY=1 ;;   # accepted but redundant (default)
    neon|local|prod)    DB_TARGET="$arg" ;;
    *)
      red "Unknown argument: $arg"
      echo "Usage: ./start.sh [neon|local|prod] [--no-observability]"
      exit 2
      ;;
  esac
done
DB_TARGET="${DB_TARGET:-${DB_TARGET_FROM_ENV:-neon}}"

# ---------- 2. Pick compose files ----------
COMPOSE_FILES=(-f infra/docker-compose.yml)
case "$DB_TARGET" in
  neon)  COMPOSE_FILES+=(-f infra/docker-compose.neon.yml) ;;
  local) ;;  # base compose is enough — it includes the postgres container
  prod)  COMPOSE_FILES+=(-f infra/docker-compose.prod.yml) ;;
esac
if [ "$OBSERVABILITY" -eq 1 ]; then
  COMPOSE_FILES+=(-f infra/docker-compose.observability.yml)
fi

bold ""
bold "================================================================"
bold "  DeepFake Detector — booting with DB_TARGET=$DB_TARGET"
bold "================================================================"
case "$DB_TARGET" in
  neon)  green  "  Database: Neon (managed Postgres) — local postgres container disabled" ;;
  local) green  "  Database: local Docker Postgres" ;;
  prod)  yellow "  Database: external (Neon/RDS) — production hardening enabled" ;;
esac
bold "================================================================"

# Sanity-check that the URL the backend will actually use is set.
if [ "$DB_TARGET" = "neon" ]; then
  if ! grep -qE '^DATABASE_URL_NEON=postgres' .env; then
    red "ERROR: DB_TARGET=neon but DATABASE_URL_NEON is not set in .env."
    echo "Open .env and paste your Neon connection string from the Neon dashboard."
    exit 3
  fi
fi

# ---------- 3. Build ----------
echo ""
echo "[2/5] Building images..."
docker compose "${COMPOSE_FILES[@]}" --env-file .env build

# ---------- 4. Up ----------
echo ""
echo "[3/5] Starting services..."
docker compose "${COMPOSE_FILES[@]}" --env-file .env up -d

# ---------- 5. Wait for backend, then bootstrap schema ----------
echo ""
echo "[4/5] Waiting for backend to become healthy at http://localhost:8000/health ..."
ATTEMPTS=0
MAX_ATTEMPTS=60   # 60 * 5s = 5 minutes
until curl -fsS --max-time 3 "http://localhost:8000/health" >/dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS + 1))
  if [ $ATTEMPTS -ge $MAX_ATTEMPTS ]; then
    red "Backend did not become healthy in 5 minutes."
    yellow "Inspect logs: docker compose ${COMPOSE_FILES[*]} logs -f backend"
    exit 4
  fi
  printf "."
  sleep 5
done
echo ""
green "    Backend is up."

# Show DB profile the backend resolved to.
if command -v curl >/dev/null 2>&1; then
  HEALTH_JSON="$(curl -fsS --max-time 5 http://localhost:8000/health || true)"
  if [ -n "$HEALTH_JSON" ]; then
    echo "    /health: $HEALTH_JSON"
  fi
fi

echo ""
echo "[5/5] Ensuring database schema exists..."
if docker compose "${COMPOSE_FILES[@]}" --env-file .env exec -T backend \
     python -c "from app.db import bootstrap_schema; bootstrap_schema(); print('schema-ok')" 2>&1 \
   | tee /tmp/_bootstrap.log \
   | grep -q "schema-ok"; then
  green "    Schema is up to date."
else
  yellow "    Schema bootstrap returned a non-zero exit code; details above."
fi

# ---------- Summary ----------
cat <<EOF

$(green "DeepFake Detector is up.")

  DB target:       $DB_TARGET
  Frontend:        http://localhost:3000
  Backend (API):   http://localhost:8000/docs
  Health check:    http://localhost:8000/health
  MinIO console:   http://localhost:9001
  Flower:          http://localhost:5555$( [ "$OBSERVABILITY" -eq 1 ] && printf "\n  Grafana logs:    http://localhost:3001  (admin / \$GRAFANA_PASSWORD)" )

Useful commands:
  Logs:            docker compose ${COMPOSE_FILES[*]} logs -f
  Stop:            docker compose ${COMPOSE_FILES[*]} down
  psql to active:  docker run --rm -it --env-file .env postgres:16-alpine \
                       psql "\$DATABASE_URL_NEON"   # or DATABASE_URL_LOCAL
  Switch to local: ./start.sh local
  Switch to Neon:  ./start.sh neon
  Production:      ./start.sh prod
  Skip Grafana:    ./start.sh --no-observability

EOF
