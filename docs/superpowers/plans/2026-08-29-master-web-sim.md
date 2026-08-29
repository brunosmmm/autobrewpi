# Master + Web UI (Sim) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Python master that controls the worker over gRPC and a simple web UI for live telemetry, mock sensor inject, deploy/start, and manual/mash-lite setpoint control — all against mock HAL.

**Architecture:** Master owns brew-day (thin v1: manual enable/setpoint + optional mash timer FSM), reconnecting gRPC client, and HTTP+WebSocket API. Web UI is static+small JS (or minimal FastAPI Jinja) talking only to the master. Worker from Plan 1 is unchanged except as a dependency.

**Tech Stack:** Python 3.11+, `uv` workspace member `packages/master`, FastAPI + uvicorn, `grpcio`, pytest, plain HTML/JS in `web/`.

**Depends on:** Plan 1 complete (`docs/superpowers/plans/2026-08-29-worker-mock-grpc.md`)  
**Spec:** `docs/superpowers/specs/2026-08-29-brewday-dataflow-worker-design.md`

## Global Constraints

- Do **not** import legacy `abpi.*`.
- UI talks **only** to master (never dials worker gRPC from the browser).
- Master marks worker `offline` + telemetry `stale` when the gRPC channel drops; does not stop the worker.
- Sim-first: default worker address `127.0.0.1:50051`.
- Thin brew-day in v1: **manual controls required**; full mash stage machine can be minimal (start/stop + setpoint ramp later).

---

## File map

| Path | Responsibility |
|------|----------------|
| `packages/master/pyproject.toml` | Master package |
| `packages/master/src/brew_master/grpc_client.py` | Worker gRPC client + reconnect |
| `packages/master/src/brew_master/brewday.py` | Thin brew / manual control facade |
| `packages/master/src/brew_master/api.py` | FastAPI routes + WebSocket |
| `packages/master/src/brew_master/__main__.py` | Entry: `brew-master` |
| `web/index.html` | Simple sim console |
| `web/app.js` | Fetch + WS client |
| `web/style.css` | Minimal layout |
| `tests/master/test_*.py` | Master tests |
| Root `pyproject.toml` | Add `packages/master` to workspace members |

Shared proto: import generated stubs from `brew_worker.gen` (master depends on `brew-worker` package) **or** duplicate gen path — prefer depending on `brew-worker` for stubs only.

---

### Task 1: Master package scaffold + gRPC client

**Files:**
- Modify: root `pyproject.toml` workspace members
- Create: `packages/master/pyproject.toml`
- Create: `packages/master/src/brew_master/__init__.py`
- Create: `packages/master/src/brew_master/grpc_client.py`
- Test: `tests/master/test_grpc_client.py`

**Interfaces:**
- Consumes: `brew_worker.gen.worker_pb2`, `worker_pb2_grpc`, running worker from Plan 1
- Produces: `class WorkerClient`:
  - `__init__(self, target: str = "127.0.0.1:50051")`
  - `connect(self) -> None` / `close(self) -> None`
  - `connected: bool`
  - `deploy_json(self, program: dict) -> str`  # returns program_id
  - `start(self) / stop(self) -> None`
  - `set_port(self, name: str, value: float | bool) -> None`
  - `set_hal_channel(self, name: str, value: float | bool) -> None`
  - `get_status(self) -> dict`
  - `telemetry_stream(self, hz: int = 5)` → iterator of `dict[str, Any]`

- [ ] **Step 1: Write failing test (uses live worker subprocess or skips if no server)**

Prefer starting worker engine in-process via Plan 1 `serve()` on port `50053`:

```python
# tests/master/test_grpc_client.py
import json, time
from pathlib import Path
import grpc
from brew_worker.hal.base import HalChannel
from brew_worker.hal.mock import MockHal
from brew_worker.runtime.engine import Engine
from brew_worker.plugins import register_builtins
from brew_worker.grpc_server import serve
from brew_master.grpc_client import WorkerClient

def test_client_deploy_and_status():
    register_builtins()
    hal = MockHal([
        HalChannel("hal.adc.temp_c", "input", "float"),
        HalChannel("hal.gpio.heater_hlt", "output", "bool"),
    ])
    eng = Engine(hal)
    server = serve(eng, "127.0.0.1", 50053)
    client = WorkerClient("127.0.0.1:50053")
    client.connect()
    pid = client.deploy_json(json.loads(Path("programs/hlt-loop-v1.json").read_text()))
    assert pid == "hlt-loop-v1"
    client.set_hal_channel("hal.adc.temp_c", 50.0)
    client.set_port("master.Hyst.SetPoint", 66.0)
    client.set_port("master.Hyst.Enabled", True)
    client.start()
    time.sleep(0.2)
    st = client.get_status()
    assert st["running"] is True
    client.close()
    server.stop(0)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/master/test_grpc_client.py -v`

- [ ] **Step 3: Implement package + `WorkerClient`**

`packages/master/pyproject.toml` dependencies: `fastapi`, `uvicorn`, `grpcio`, `brew-worker` (workspace).

- [ ] **Step 4: Run — PASS**

- [ ] **Step 5: Commit**

```bash
git add packages/master tests/master/test_grpc_client.py pyproject.toml
git commit -m "feat(master): package scaffold and worker gRPC client"
```

---

### Task 2: Reconnect + stale status

**Files:**
- Modify: `packages/master/src/brew_master/grpc_client.py`
- Create: `packages/master/src/brew_master/supervisor.py`
- Test: `tests/master/test_supervisor.py`

**Interfaces:**
- Produces: `class WorkerSupervisor`:
  - wraps `WorkerClient`
  - background thread attempts reconnect every `2.0` seconds when down
  - `snapshot() -> dict` with `online: bool`, `stale: bool`, `status: dict | None`, `last_telemetry: dict`, `last_error: str | None`
  - `start_telemetry(hz=5)` merges frames into `last_telemetry`; on stream error set `online=False`, `stale=True`

- [ ] **Step 1: Write failing test** — kill server mid-telemetry; assert `online is False` and `stale is True` while local assertions don't require worker stopped.

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement supervisor**

- [ ] **Step 4: Run — PASS**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(master): worker supervisor with reconnect and stale flags"
```

---

### Task 3: Thin brew-day / manual control facade

**Files:**
- Create: `packages/master/src/brew_master/brewday.py`
- Test: `tests/master/test_brewday.py`

**Interfaces:**
- Produces: `class BrewDayController`:
  - `__init__(self, supervisor: WorkerSupervisor)`
  - `ensure_sample_deployed(self) -> None` — deploys `programs/hlt-loop-v1.json` if needed
  - `set_manual(self, *, enabled: bool, setpoint_c: float) -> None` — writes `master.Hyst.Enabled` / `master.Hyst.SetPoint`, starts worker if needed
  - `inject_temp(self, temp_c: float) -> None` — `set_hal_channel("hal.adc.temp_c", ...)`
  - `state(self) -> dict` — `{mode: "manual", enabled, setpoint_c, worker: supervisor.snapshot()}`

No full mash stage machine in this task (YAGNI for sim console). Leave a `TODO` comment only if you also add a stub `class MashSession` with `idle` state and `start(setpoint, minutes)` that sets ports and tracks a timer in-process — optional; if included, cover with one test.

- [ ] **Step 1: Failing test for `set_manual` + `inject_temp` against in-process worker**

- [ ] **Step 2: FAIL → implement → PASS**

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(master): manual brew-day control facade"
```

---

### Task 4: FastAPI HTTP + WebSocket

**Files:**
- Create: `packages/master/src/brew_master/api.py`
- Create: `packages/master/src/brew_master/__main__.py`
- Test: `tests/master/test_api.py` (httpx `AsyncClient` + TestClient)

**Interfaces:**
- Produces routes:
  - `GET /api/health` → `{ok: true}`
  - `GET /api/state` → `BrewDayController.state()`
  - `POST /api/deploy/sample` → ensure sample deployed + start
  - `POST /api/manual` body `{"enabled": bool, "setpoint_c": float}`
  - `POST /api/mock/temp` body `{"temp_c": float}`
  - `WS /ws/telemetry` → push JSON state ~5 Hz

Static files mounted from repo `web/` at `/`.

- [ ] **Step 1: Write API tests with mocked supervisor OR in-process worker on 50054**

```python
from fastapi.testclient import TestClient
from brew_master.api import create_app

def test_health(monkeypatch):
    app = create_app(worker_target="127.0.0.1:50054")  # or inject fake controller
    client = TestClient(app)
    assert client.get("/api/health").json()["ok"] is True
```

Prefer dependency-injectable `BrewDayController` for unit tests; one integration test with real worker optional.

- [ ] **Step 2: FAIL → implement `create_app(controller: BrewDayController | None = None, worker_target: str = ...)` → PASS**

- [ ] **Step 3: `__main__.py`** runs uvicorn on `127.0.0.1:8000`

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(master): FastAPI state/manual/mock endpoints and WS"
```

---

### Task 5: Simple web UI

**Files:**
- Create: `web/index.html`
- Create: `web/app.js`
- Create: `web/style.css`

**Interfaces:**
- Produces UI sections matching spec: worker status, live ports (temp, heater, enabled, setpoint), mock temp slider/input, deploy sample button, manual enable + setpoint controls.
- `app.js` uses `fetch` for POSTs and `WebSocket` to `/ws/telemetry` to refresh readouts.
- Show **stale/offline** banner when `worker.online` is false.

- [ ] **Step 1: Implement static files** (no screenshot automation required)

- [ ] **Step 2: Manual smoke**

```bash
# terminal 1
uv run brew-worker --port 50051
# terminal 2
uv run brew-master --worker 127.0.0.1:50051 --port 8000
# browser: http://127.0.0.1:8000
# Deploy sample → set temp 50 → enable / setpoint 66 → observe heater true
# Stop worker process → UI shows offline/stale
```

- [ ] **Step 3: Commit**

```bash
git add web
git commit -m "feat(web): simple sim console for mock brew loop"
```

---

### Task 6: End-to-end sim smoke script

**Files:**
- Create: `scripts/sim_smoke.sh`
- Test: documented in script; optional `tests/master/test_e2e_sim.py` that orchestrates worker+master briefly

**Interfaces:**
- Produces: one-command smoke that exits 0 if heater turns on under mock conditions (API-only, no browser)

```bash
#!/usr/bin/env bash
set -euo pipefail
# start worker background, start master background, curl deploy + manual + mock temp, poll /api/state until heater true or timeout
```

- [ ] **Step 1: Write script + run it — expect success**

- [ ] **Step 2: Commit**

```bash
git commit -m "test: add sim smoke script for worker+master mock loop"
```

---

## Plan 2 done when

- Browser sim console can deploy, inject temp, enable hysteresis, see heater bit
- Offline worker shows stale/offline in UI
- `scripts/sim_smoke.sh` passes
- Ready later for live HAL and richer mash FSM (not in this plan)

## Spec coverage (Plan 2)

| Spec item | Task |
|-----------|------|
| Master gRPC client + observability | 1–2 |
| Brew-day on master (thin/manual) | 3 |
| API + simple web UI | 4–5 |
| Mock inject via UI | 5 |
| Disconnect / stale UX | 2, 5 |
| Full mash stage machine | deferred |
| Auth | out of scope |
