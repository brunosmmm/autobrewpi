#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

uv run brew-worker --host 127.0.0.1 --port 50055 &
WPID=$!
uv run brew-master --host 127.0.0.1 --port 8010 --worker 127.0.0.1:50055 &
MPID=$!

cleanup() {
  kill "$MPID" "$WPID" 2>/dev/null || true
  wait "$MPID" "$WPID" 2>/dev/null || true
}
trap cleanup EXIT

# wait for health
for i in $(seq 1 50); do
  if curl -sf http://127.0.0.1:8010/api/health >/dev/null; then
    break
  fi
  sleep 0.1
done

curl -sf -X POST http://127.0.0.1:8010/api/deploy/sample >/dev/null
curl -sf -X POST http://127.0.0.1:8010/api/mock/temp -H 'content-type: application/json' -d '{"temp_c":50}' >/dev/null
curl -sf -X POST http://127.0.0.1:8010/api/manual -H 'content-type: application/json' -d '{"enabled":true,"setpoint_c":66}' >/dev/null

ok=0
for i in $(seq 1 40); do
  state=$(curl -sf http://127.0.0.1:8010/api/state)
  heater=$(python3 -c 'import json,sys; s=json.load(sys.stdin); print(s.get("worker",{}).get("last_telemetry",{}).get("hal.gpio.heater_hlt"))' <<<"$state")
  if [[ "$heater" == "True" ]]; then
    ok=1
    break
  fi
  sleep 0.15
done

if [[ "$ok" != "1" ]]; then
  echo "FAIL: heater did not turn on" >&2
  echo "$state" >&2
  exit 1
fi

echo "sim smoke OK"
