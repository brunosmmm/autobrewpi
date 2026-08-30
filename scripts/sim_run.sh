#!/usr/bin/env bash
# Interactive mock sim: start worker + master and leave them running for UI inspection.
# Ctrl+C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

WORKER_HOST=127.0.0.1
MASTER_HOST=127.0.0.1
# Defaults; override with env or flags.
WORKER_PORT="${BREW_WORKER_PORT:-50051}"
MASTER_PORT="${BREW_MASTER_PORT:-8000}"
WORKER_PORT_SET=0
MASTER_PORT_SET=0
SEED=1

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

  --worker-port PORT   Worker gRPC port
                       (env BREW_WORKER_PORT, default ${BREW_WORKER_PORT:-50051})
  --master-port PORT   Master HTTP / UI port
                       (env BREW_MASTER_PORT, default ${BREW_MASTER_PORT:-8000})
  --bare               Do not auto-deploy / inject / enable (empty sim)
  -h, --help           Show this help

If a default/env port is already in use, the next free port is chosen
automatically. An explicit --worker-port / --master-port that is busy fails.

UI: http://${MASTER_HOST}:<master-port>
EOF
}

port_in_use() {
  local port="$1"
  # Prefer ss; fall back to python bind probe.
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "sport = :${port}" 2>/dev/null | grep -q ":${port}"
    return $?
  fi
  uv run python - "$port" <<'PY'
import socket, sys
port = int(sys.argv[1])
s = socket.socket()
try:
    s.bind(("127.0.0.1", port))
except OSError:
    sys.exit(0)  # in use
else:
    sys.exit(1)  # free
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
    --worker-port)
      WORKER_PORT="$2"
      WORKER_PORT_SET=1
      shift 2
      ;;
    --master-port)
      MASTER_PORT="$2"
      MASTER_PORT_SET=1
      shift 2
      ;;
    --bare) SEED=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

# Resolve ports if busy (auto for non-explicit; fail for explicit).
if port_in_use "$WORKER_PORT"; then
  if [[ "$WORKER_PORT_SET" == "1" ]]; then
    echo "worker port ${WORKER_PORT} is already in use (pass a free --worker-port)" >&2
    exit 1
  fi
  old="$WORKER_PORT"
  WORKER_PORT="$(find_free_port "$WORKER_PORT")"
  echo "worker port ${old} busy → using ${WORKER_PORT}"
fi

if port_in_use "$MASTER_PORT"; then
  if [[ "$MASTER_PORT_SET" == "1" ]]; then
    echo "master port ${MASTER_PORT} is already in use (pass a free --master-port)" >&2
    exit 1
  fi
  old="$MASTER_PORT"
  MASTER_PORT="$(find_free_port "$MASTER_PORT")"
  echo "master port ${old} busy → using ${MASTER_PORT}"
fi

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

Tip: fixed ports →  BREW_MASTER_PORT=8010 ./scripts/sim_run.sh
                 or  ./scripts/sim_run.sh --master-port 8010
EOF

while kill -0 "$WPID" 2>/dev/null && kill -0 "$MPID" 2>/dev/null; do
  sleep 1
done

echo "a process exited; shutting down" >&2
exit 1
