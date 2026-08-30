#!/usr/bin/env bash
# Interactive mock sim: start worker + master and leave them running for UI inspection.
# Ctrl+C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

WORKER_HOST=127.0.0.1
WORKER_PORT=50051
MASTER_HOST=127.0.0.1
MASTER_PORT=8000
SEED=1

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

  --worker-port PORT   Worker gRPC port (default: ${WORKER_PORT})
  --master-port PORT   Master HTTP port (default: ${MASTER_PORT})
  --bare               Do not auto-deploy / inject / enable (empty sim)
  -h, --help           Show this help

Starts brew-worker + brew-master, optionally seeds the HLT loop sample
(temp 50°C, setpoint 66°C, enabled), then waits until Ctrl+C.

UI: http://${MASTER_HOST}:${MASTER_PORT}
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --worker-port) WORKER_PORT="$2"; shift 2 ;;
    --master-port) MASTER_PORT="$2"; shift 2 ;;
    --bare) SEED=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

WORKER_TARGET="${WORKER_HOST}:${WORKER_PORT}"
MASTER_URL="http://${MASTER_HOST}:${MASTER_PORT}"

uv run brew-worker --host "$WORKER_HOST" --port "$WORKER_PORT" &
WPID=$!
uv run brew-master --host "$MASTER_HOST" --port "$MASTER_PORT" --worker "$WORKER_TARGET" &
MPID=$!

cleanup() {
  echo
  echo "Stopping sim (master=${MPID} worker=${WPID})..."
  kill "$MPID" "$WPID" 2>/dev/null || true
  wait "$MPID" "$WPID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Waiting for master at ${MASTER_URL} ..."
ready=0
for _ in $(seq 1 100); do
  if curl -sf "${MASTER_URL}/api/health" >/dev/null; then
    ready=1
    break
  fi
  if ! kill -0 "$WPID" 2>/dev/null || ! kill -0 "$MPID" 2>/dev/null; then
    echo "worker or master exited early" >&2
    exit 1
  fi
  sleep 0.1
done

if [[ "$ready" != "1" ]]; then
  echo "master did not become healthy in time" >&2
  exit 1
fi

if [[ "$SEED" == "1" ]]; then
  echo "Seeding sample program (cold HLT, heater enabled)..."
  curl -sf -X POST "${MASTER_URL}/api/deploy/sample" >/dev/null
  curl -sf -X POST "${MASTER_URL}/api/mock/temp" \
    -H 'content-type: application/json' \
    -d '{"temp_c":50}' >/dev/null
  curl -sf -X POST "${MASTER_URL}/api/manual" \
    -H 'content-type: application/json' \
    -d '{"enabled":true,"setpoint_c":66}' >/dev/null
fi

cat <<EOF

Sim running.
  Worker gRPC : ${WORKER_TARGET}
  Master UI   : ${MASTER_URL}
  Seeded      : $([[ "$SEED" == "1" ]] && echo yes || echo no)

Open the UI, tweak mock temp / setpoint, watch heater bit.
Ctrl+C to stop.
EOF

# Keep the script alive while children run; exit if either dies.
while kill -0 "$WPID" 2>/dev/null && kill -0 "$MPID" 2>/dev/null; do
  sleep 1
done

echo "a process exited; shutting down" >&2
exit 1
