#!/usr/bin/env bash
# Stand up worker + master for operator UI testing.
# Master binds 0.0.0.0 by default so you can hit it from another machine.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

WORKER_HOST=0.0.0.0
WORKER_PORT="${BREW_WORKER_PORT:-50051}"
MASTER_HOST=0.0.0.0
MASTER_PORT="${BREW_MASTER_PORT:-8000}"
WORKER_PORT_SET=0
MASTER_PORT_SET=0
SEED=1

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

  --worker-port PORT   Worker gRPC port (env BREW_WORKER_PORT, default 50051)
  --master-port PORT   Master HTTP port (env BREW_MASTER_PORT, default 8000)
  --bare               Do not ensure-graph / seed mock temp
  -h, --help           Show this help

Binds worker and master on 0.0.0.0. Operator UI: http://<this-host>:\${MASTER_PORT}/
Sim harness: http://<this-host>:\${MASTER_PORT}/sim
Ctrl+C stops both.
EOF
}

port_in_use() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "sport = :${port}" 2>/dev/null | grep -q ":${port}"
    return $?
  fi
  uv run python - "$port" <<'PY'
import socket, sys
port = int(sys.argv[1])
s = socket.socket()
try:
    s.bind(("0.0.0.0", port))
except OSError:
    sys.exit(0)
else:
    sys.exit(1)
finally:
    s.close()
PY
}

find_free_port() {
  local start="$1"
  local p
  for p in $(seq "$start" $((start + 50))); do
    if ! port_in_use "$p"; then
      echo "$p"
      return 0
    fi
  done
  echo "no free port near ${start}" >&2
  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --worker-port) WORKER_PORT="$2"; WORKER_PORT_SET=1; shift 2 ;;
    --master-port) MASTER_PORT="$2"; MASTER_PORT_SET=1; shift 2 ;;
    --bare) SEED=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if port_in_use "$WORKER_PORT"; then
  if [[ "$WORKER_PORT_SET" == "1" ]]; then
    echo "worker port ${WORKER_PORT} is already in use" >&2
    exit 1
  fi
  old="$WORKER_PORT"
  WORKER_PORT="$(find_free_port "$WORKER_PORT")"
  echo "worker port ${old} busy → using ${WORKER_PORT}"
fi

if port_in_use "$MASTER_PORT"; then
  if [[ "$MASTER_PORT_SET" == "1" ]]; then
    echo "master port ${MASTER_PORT} is already in use" >&2
    exit 1
  fi
  old="$MASTER_PORT"
  MASTER_PORT="$(find_free_port "$MASTER_PORT")"
  echo "master port ${old} busy → using ${MASTER_PORT}"
fi

# Master dials worker on loopback (same host).
WORKER_DIAL="127.0.0.1:${WORKER_PORT}"
MASTER_URL="http://127.0.0.1:${MASTER_PORT}"

uv run brew-worker --host "$WORKER_HOST" --port "$WORKER_PORT" &
WPID=$!
uv run brew-master --host "$MASTER_HOST" --port "$MASTER_PORT" --worker "$WORKER_DIAL" &
MPID=$!

cleanup() {
  echo
  echo "Stopping (master=${MPID} worker=${WPID})..."
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
  echo "Ensuring graph + seeding mock temp 50°C ..."
  curl -sf -X POST "${MASTER_URL}/api/operator/ensure-graph" >/dev/null
  curl -sf -X POST "${MASTER_URL}/api/mock/temp" \
    -H 'content-type: application/json' \
    -d '{"temp_c":50}' >/dev/null
fi

cat <<EOF

Operator stack running (0.0.0.0).
  Worker gRPC : ${WORKER_HOST}:${WORKER_PORT}  (master dials ${WORKER_DIAL})
  Operator UI : http://<this-host>:${MASTER_PORT}/
  Sim UI      : http://<this-host>:${MASTER_PORT}/sim
  Local       : ${MASTER_URL}/

Ctrl+C to stop.
EOF

while kill -0 "$WPID" 2>/dev/null && kill -0 "$MPID" 2>/dev/null; do
  sleep 1
done

echo "a process exited; shutting down" >&2
exit 1
