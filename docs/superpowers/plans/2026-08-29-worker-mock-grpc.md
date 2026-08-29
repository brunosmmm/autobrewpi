# Worker + Mock HAL + gRPC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a standalone Python worker that loads declarative dataflow programs, cycles them against a mock HAL, and exposes the full v1 gRPC control/telemetry API — no hardware, no master UI yet.

**Architecture:** In-process graph runtime (blocks + wires + `master.*` ports) bound to a mock HAL. A background cycle thread keeps running after deploy even if gRPC clients disconnect. gRPC server is the only remote surface in this plan.

**Tech Stack:** Python 3.11+, `uv` workspace, `grpcio` + `grpcio-tools` + protobuf, `pytest`, stdlib `threading`/`json`.

**Spec:** `docs/superpowers/specs/2026-08-29-brewday-dataflow-worker-design.md`  
**Follow-on plan:** `docs/superpowers/plans/2026-08-29-master-web-sim.md` (master + web UI)

## Global Constraints

- Do **not** import or depend on legacy `abpi.*` packages.
- HAL mode for this plan is **`mock` only** (interface must allow a future `live` backend).
- Worker is the **gRPC server**; default listen `127.0.0.1:50051`.
- On client disconnect, the cycle loop **keeps running** (hold last `master.*` / outputs).
- Reject cyclic wire graphs at deploy time.
- Default output fail policy: **hold last**.
- Package layout under repo root: `proto/`, `packages/worker/`, `programs/`, `tests/worker/`.

---

## File map

| Path | Responsibility |
|------|----------------|
| `proto/worker/v1/worker.proto` | gRPC service + messages |
| `packages/worker/pyproject.toml` | Worker package metadata / deps |
| `packages/worker/src/brew_worker/__init__.py` | Package version |
| `packages/worker/src/brew_worker/hal/base.py` | `Hal` protocol / ABC |
| `packages/worker/src/brew_worker/hal/mock.py` | In-memory HAL |
| `packages/worker/src/brew_worker/runtime/ports.py` | Port types / values |
| `packages/worker/src/brew_worker/runtime/block.py` | Block plugin base + registry |
| `packages/worker/src/brew_worker/runtime/graph.py` | Program model, wire validate, topo order |
| `packages/worker/src/brew_worker/runtime/engine.py` | Load/deploy, cycle loop, master ports |
| `packages/worker/src/brew_worker/plugins/hysteresis.py` | Hysteresis block |
| `packages/worker/src/brew_worker/plugins/passthrough.py` | Simple numeric/bool passthrough helpers if needed |
| `packages/worker/src/brew_worker/plugins/gpio_out.py` | Writes bool/float to HAL channel |
| `packages/worker/src/brew_worker/plugins/__init__.py` | Register built-in plugins |
| `packages/worker/src/brew_worker/grpc_server.py` | Servicer + server bootstrap |
| `packages/worker/src/brew_worker/__main__.py` | `python -m brew_worker` entry |
| `programs/hlt-loop-v1.json` | Sample program for sim |
| `tests/worker/test_*.py` | Unit / integration tests |
| `pyproject.toml` (root) | `uv` workspace root (new; leave legacy poetry file unused or replace carefully) |

---

### Task 1: Workspace scaffolding

**Files:**
- Create: `pyproject.toml` (workspace root — if legacy poetry `pyproject.toml` conflicts, rename legacy to `pyproject.legacy.toml` first and note it in the commit message)
- Create: `packages/worker/pyproject.toml`
- Create: `packages/worker/src/brew_worker/__init__.py`
- Create: `tests/worker/test_scaffold.py`
- Create: `.gitignore` entries for `__pycache__/`, `.venv/`, `*_pb2*.py` if generated into tree (prefer generate into `packages/worker/src/brew_worker/gen/`)

**Interfaces:**
- Produces: installable package `brew-worker` importable as `brew_worker`

- [ ] **Step 1: Write the failing test**

```python
# tests/worker/test_scaffold.py
def test_brew_worker_importable():
    import brew_worker
    assert brew_worker.__version__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bruno/work/autobrewpi && uv run pytest tests/worker/test_scaffold.py -v`  
Expected: FAIL (package missing or uv project not configured)

- [ ] **Step 3: Write minimal scaffolding**

Root `pyproject.toml`:

```toml
[project]
name = "autobrewpi-workspace"
version = "0.0.0"
requires-python = ">=3.11"

[tool.uv.workspace]
members = ["packages/worker"]

[dependency-groups]
dev = ["pytest>=8.0", "grpcio-tools>=1.62"]
```

`packages/worker/pyproject.toml`:

```toml
[project]
name = "brew-worker"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "grpcio>=1.62",
  "protobuf>=5.0",
]

[project.scripts]
brew-worker = "brew_worker.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/brew_worker"]
```

`packages/worker/src/brew_worker/__init__.py`:

```python
__version__ = "0.1.0"
```

If existing root `pyproject.toml` is the old poetry file, move it to `pyproject.legacy.toml` before writing the workspace file.

- [ ] **Step 4: Sync and run test**

Run:

```bash
cd /home/bruno/work/autobrewpi
uv sync --all-packages
uv run pytest tests/worker/test_scaffold.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml pyproject.legacy.toml packages/worker tests/worker/test_scaffold.py
git commit -m "chore: add uv workspace and brew-worker package scaffold"
```

---

### Task 2: Mock HAL

**Files:**
- Create: `packages/worker/src/brew_worker/hal/base.py`
- Create: `packages/worker/src/brew_worker/hal/mock.py`
- Create: `packages/worker/src/brew_worker/hal/__init__.py`
- Test: `tests/worker/test_mock_hal.py`

**Interfaces:**
- Produces:
  - `class Hal(Protocol)` with `list_channels() -> list[HalChannel]`, `get(name: str) -> float | bool | None`, `set(name: str, value: float | bool) -> None`, `mode: Literal["mock","live"]`
  - `dataclass HalChannel(name: str, direction: Literal["input","output"], dtype: Literal["float","bool"])`
  - `class MockHal(Hal)` constructed with `channels: list[HalChannel]`, default values via `set`

- [ ] **Step 1: Write the failing test**

```python
# tests/worker/test_mock_hal.py
from brew_worker.hal.mock import MockHal
from brew_worker.hal.base import HalChannel

def test_mock_hal_set_get_and_list():
    hal = MockHal([
        HalChannel("hal.adc.hlt_r", "input", "float"),
        HalChannel("hal.gpio.heater_hlt", "output", "bool"),
    ])
    hal.set("hal.adc.hlt_r", 110.0)
    assert hal.get("hal.adc.hlt_r") == 110.0
    hal.set("hal.gpio.heater_hlt", True)
    assert hal.get("hal.gpio.heater_hlt") is True
    names = {c.name for c in hal.list_channels()}
    assert names == {"hal.adc.hlt_r", "hal.gpio.heater_hlt"}

def test_mock_hal_unknown_channel_raises():
    hal = MockHal([])
    try:
        hal.get("nope")
        assert False, "expected KeyError"
    except KeyError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/worker/test_mock_hal.py -v`  
Expected: FAIL (import error)

- [ ] **Step 3: Implement HAL**

```python
# packages/worker/src/brew_worker/hal/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Protocol

HalMode = Literal["mock", "live"]
Direction = Literal["input", "output"]
DType = Literal["float", "bool"]

@dataclass(frozen=True)
class HalChannel:
    name: str
    direction: Direction
    dtype: DType

class Hal(Protocol):
    mode: HalMode
    def list_channels(self) -> list[HalChannel]: ...
    def get(self, name: str) -> float | bool | None: ...
    def set(self, name: str, value: float | bool) -> None: ...
```

```python
# packages/worker/src/brew_worker/hal/mock.py
from __future__ import annotations
from brew_worker.hal.base import HalChannel, HalMode

class MockHal:
    mode: HalMode = "mock"

    def __init__(self, channels: list[HalChannel]):
        self._channels = {c.name: c for c in channels}
        self._values: dict[str, float | bool | None] = {c.name: None for c in channels}

    def list_channels(self) -> list[HalChannel]:
        return list(self._channels.values())

    def get(self, name: str) -> float | bool | None:
        if name not in self._channels:
            raise KeyError(name)
        return self._values[name]

    def set(self, name: str, value: float | bool) -> None:
        if name not in self._channels:
            raise KeyError(name)
        ch = self._channels[name]
        if ch.dtype == "bool" and not isinstance(value, bool):
            raise TypeError(f"{name} expects bool")
        if ch.dtype == "float" and not isinstance(value, (int, float)):
            raise TypeError(f"{name} expects float")
        self._values[name] = float(value) if ch.dtype == "float" else value
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/worker/test_mock_hal.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/worker/src/brew_worker/hal tests/worker/test_mock_hal.py
git commit -m "feat(worker): add mock HAL"
```

---

### Task 3: Graph model, validation, topo order

**Files:**
- Create: `packages/worker/src/brew_worker/runtime/graph.py`
- Create: `packages/worker/src/brew_worker/runtime/__init__.py`
- Test: `tests/worker/test_graph.py`

**Interfaces:**
- Produces:
  - `dataclass BlockSpec(name: str, type: str, params: dict)`
  - `dataclass WireSpec(from_port: str, to_port: str)` — JSON fields `from`/`to` map to these
  - `dataclass Program(id: str, cycle_ms: int, blocks: list[BlockSpec], wires: list[WireSpec])`
  - `parse_program(data: dict) -> Program`
  - `validate_and_order(program: Program, known_block_types: set[str], hal_names: set[str]) -> list[str]`  
    Returns block names in evaluation order. Raises `ProgramValidationError` on unknown types, bad endpoints, duplicate block names, or cycles.

Port name rules:
- HAL: must start with `hal.` and exist in `hal_names`
- Master: must start with `master.`
- Block: `BlockName.PortName` where `BlockName` is in the program

- [ ] **Step 1: Write the failing test**

```python
# tests/worker/test_graph.py
import pytest
from brew_worker.runtime.graph import parse_program, validate_and_order, ProgramValidationError

SAMPLE = {
    "id": "t1",
    "cycle_ms": 100,
    "blocks": [
        {"name": "A", "type": "Hysteresis", "params": {}},
        {"name": "B", "type": "GpioOut", "params": {"channel": "hal.gpio.heater_hlt"}},
    ],
    "wires": [
        {"from": "hal.adc.hlt_r", "to": "A.CurrTemp"},
        {"from": "master.SetPoint", "to": "A.SetPoint"},
        {"from": "A.CtlOut", "to": "B.Value"},
    ],
}

def test_parse_and_topo_ok():
    prog = parse_program(SAMPLE)
    order = validate_and_order(
        prog,
        known_block_types={"Hysteresis", "GpioOut"},
        hal_names={"hal.adc.hlt_r", "hal.gpio.heater_hlt"},
    )
    assert order.index("A") < order.index("B")

def test_rejects_cycle():
    data = {
        "id": "cyc",
        "cycle_ms": 50,
        "blocks": [
            {"name": "A", "type": "Hysteresis", "params": {}},
            {"name": "B", "type": "Hysteresis", "params": {}},
        ],
        "wires": [
            {"from": "A.CtlOut", "to": "B.CurrTemp"},
            {"from": "B.CtlOut", "to": "A.CurrTemp"},
        ],
    }
    prog = parse_program(data)
    with pytest.raises(ProgramValidationError):
        validate_and_order(prog, {"Hysteresis"}, set())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/worker/test_graph.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement graph.py**

Implement `parse_program`, `ProgramValidationError`, and Kahn topo-sort over **block→block** edges derived from wires (HAL/`master` sources have no block predecessor; HAL sinks are not nodes). Unknown block type / unknown HAL name / malformed port → `ProgramValidationError`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/worker/test_graph.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/worker/src/brew_worker/runtime/graph.py packages/worker/src/brew_worker/runtime/__init__.py tests/worker/test_graph.py
git commit -m "feat(worker): program parse, validate, and topo order"
```

---

### Task 4: Block base, registry, Hysteresis + GpioOut

**Files:**
- Create: `packages/worker/src/brew_worker/runtime/block.py`
- Create: `packages/worker/src/brew_worker/plugins/hysteresis.py`
- Create: `packages/worker/src/brew_worker/plugins/gpio_out.py`
- Create: `packages/worker/src/brew_worker/plugins/__init__.py`
- Test: `tests/worker/test_hysteresis.py`

**Interfaces:**
- Produces:
  - `class Block(ABC)` with class attrs `type_name: str`, `inputs: dict[str, str]`, `outputs: dict[str, str]` (dtype strings `"float"|"bool"|"generic"`), methods `set_input(name, value)`, `get_output(name)`, `cycle()`, `apply_params(params: dict)`
  - `REGISTRY: dict[str, type[Block]]` and `register_builtins()`
  - `Hysteresis` — ports: inputs `SetPoint:float`, `HystLevel:float`, `HystType:generic`, `CurrTemp:float`, `Enabled:bool`; output `CtlOut:bool`. Behavior matches old spirit: when enabled, heat when below setpoint band per `updown`/`up`/`down`.
  - `GpioOut` — input `Value:bool`; param `channel:str`; on cycle calls `hal.set(channel, value)` (hal injected in constructor)

- [ ] **Step 1: Write the failing test**

```python
# tests/worker/test_hysteresis.py
from brew_worker.plugins.hysteresis import Hysteresis

def test_hysteresis_updown_turns_on_below_setpoint():
    h = Hysteresis(name="Hyst")
    h.apply_params({"hyst_type": "updown", "level": 2.0})
    h.set_input("Enabled", True)
    h.set_input("SetPoint", 66.0)
    h.set_input("HystLevel", 2.0)
    h.set_input("HystType", "updown")
    h.set_input("CurrTemp", 60.0)
    h.cycle()
    assert h.get_output("CtlOut") is True
    h.set_input("CurrTemp", 69.0)
    h.cycle()
    assert h.get_output("CtlOut") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/worker/test_hysteresis.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement block base + plugins**

Port dtypes as string tags. `Hysteresis.cycle()` implements updown deadband (on below `SetPoint - level` after off above `SetPoint + level` — mirror `abpi/vspace/hystctl.py` updown logic). `GpioOut` stores `hal` reference from `__init__(self, name, hal=None, **params)`.

`plugins/__init__.py`:

```python
from brew_worker.runtime.block import REGISTRY
from brew_worker.plugins.hysteresis import Hysteresis
from brew_worker.plugins.gpio_out import GpioOut

def register_builtins() -> None:
    REGISTRY[Hysteresis.type_name] = Hysteresis
    REGISTRY[GpioOut.type_name] = GpioOut
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/worker/test_hysteresis.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/worker/src/brew_worker/runtime/block.py packages/worker/src/brew_worker/plugins tests/worker/test_hysteresis.py
git commit -m "feat(worker): block registry, hysteresis, gpio_out plugins"
```

---

### Task 5: Engine — deploy, master ports, cycle loop

**Files:**
- Create: `packages/worker/src/brew_worker/runtime/engine.py`
- Test: `tests/worker/test_engine.py`

**Interfaces:**
- Consumes: `MockHal`, `parse_program`, `validate_and_order`, `register_builtins`, plugins
- Produces: `class Engine`:
  - `__init__(self, hal: MockHal, persist_path: Path | None = None)`
  - `deploy(self, program_dict: dict) -> None`
  - `start(self) / stop(self) -> None`
  - `set_master_port(self, name: str, value: float | bool) -> None`  # name without or with `master.` prefix — normalize to full `master.*`
  - `set_hal_channel(self, name: str, value: float | bool) -> None`
  - `snapshot(self) -> dict[str, float | bool | None]`  # all interesting port/hal values for telemetry
  - `status(self) -> dict` with keys `running: bool`, `program_id: str | None`, `cycle_ms: int | None`
  - Background thread: while running, every `cycle_ms`: read HAL into wired sources → push wire values in topo order → `block.cycle()` → write GpioOut/HAL sinks → update snapshot

Wire propagation: maintain a `values: dict[str, Any]` keyed by full port path (`A.CtlOut`, `hal.adc.hlt_r`, `master.SetPoint`).

- [ ] **Step 1: Write the failing test**

```python
# tests/worker/test_engine.py
import time
from brew_worker.hal.base import HalChannel
from brew_worker.hal.mock import MockHal
from brew_worker.runtime.engine import Engine
from brew_worker.plugins import register_builtins

PROGRAM = {
    "id": "hlt-loop-v1",
    "cycle_ms": 50,
    "blocks": [
        {"name": "Hyst", "type": "Hysteresis", "params": {"hyst_type": "updown", "level": 2.0}},
        {"name": "HeatOut", "type": "GpioOut", "params": {"channel": "hal.gpio.heater_hlt"}},
    ],
    "wires": [
        {"from": "hal.adc.temp_c", "to": "Hyst.CurrTemp"},
        {"from": "master.Hyst.SetPoint", "to": "Hyst.SetPoint"},
        {"from": "master.Hyst.Enabled", "to": "Hyst.Enabled"},
        {"from": "Hyst.CtlOut", "to": "HeatOut.Value"},
    ],
}

def test_engine_heats_when_cold():
    register_builtins()
    hal = MockHal([
        HalChannel("hal.adc.temp_c", "input", "float"),
        HalChannel("hal.gpio.heater_hlt", "output", "bool"),
    ])
    eng = Engine(hal)
    eng.deploy(PROGRAM)
    eng.set_hal_channel("hal.adc.temp_c", 50.0)
    eng.set_master_port("master.Hyst.SetPoint", 66.0)
    eng.set_master_port("master.Hyst.Enabled", True)
    eng.start()
    time.sleep(0.2)
    eng.stop()
    assert hal.get("hal.gpio.heater_hlt") is True
```

Note: For sim simplicity in this test, wire `CurrTemp` from a **float HAL channel already in °C** (skip Pt100). Sample program in Task 7 can document that.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/worker/test_engine.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement Engine**

Thread must be daemon=False or explicitly joinable on `stop()`. `deploy` stops briefly, builds blocks, validates, optionally writes JSON to `persist_path`, then leaves stopped until `start()`. Persist reload is Task 5b optional — include `load_persisted()` called from `__main__` if file exists.

Also set default `HystLevel`/`HystType` from block params during deploy if those inputs are not wired.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/worker/test_engine.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/worker/src/brew_worker/runtime/engine.py tests/worker/test_engine.py
git commit -m "feat(worker): engine deploy, master ports, and cycle loop"
```

---

### Task 6: Sample program artifact

**Files:**
- Create: `programs/hlt-loop-v1.json`
- Test: `tests/worker/test_sample_program.py`

**Interfaces:**
- Produces: checked-in JSON matching Task 5 program shape (temp_c HAL, not Pt100)

- [ ] **Step 1: Write failing test that loads file and deploys**

```python
# tests/worker/test_sample_program.py
import json
from pathlib import Path
from brew_worker.hal.base import HalChannel
from brew_worker.hal.mock import MockHal
from brew_worker.runtime.engine import Engine
from brew_worker.plugins import register_builtins

ROOT = Path(__file__).resolve().parents[2]

def test_sample_program_deploys():
    register_builtins()
    data = json.loads((ROOT / "programs/hlt-loop-v1.json").read_text())
    hal = MockHal([
        HalChannel("hal.adc.temp_c", "input", "float"),
        HalChannel("hal.gpio.heater_hlt", "output", "bool"),
    ])
    eng = Engine(hal)
    eng.deploy(data)
    assert eng.status()["program_id"] == "hlt-loop-v1"
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/worker/test_sample_program.py -v`  
Expected: FAIL (missing file)

- [ ] **Step 3: Write `programs/hlt-loop-v1.json`**

Same structure as `PROGRAM` in Task 5.

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit**

```bash
git add programs/hlt-loop-v1.json tests/worker/test_sample_program.py
git commit -m "feat(worker): add hlt-loop-v1 sample program"
```

---

### Task 7: Protobuf + codegen

**Files:**
- Create: `proto/worker/v1/worker.proto`
- Create: `scripts/gen_proto.sh`
- Create: `packages/worker/src/brew_worker/gen/` (generated `worker_pb2.py`, `worker_pb2_grpc.py`)
- Modify: `packages/worker/pyproject.toml` if needed so `brew_worker.gen` imports

**Interfaces:**
- Produces proto service `Worker` with RPCs from the spec: `DeployProgram`, `GetProgram`, `Start`, `Stop`, `SetPort`, `SetParam`, `GetStatus`, `SubscribeTelemetry`, `ListHalChannels`, `SetHalChannel` (skip `CallBlock`/`SetHalMode` until needed — add empty reserved comments or stub RPCs returning UNIMPLEMENTED)

Message sketch:

```protobuf
syntax = "proto3";
package worker.v1;

service Worker {
  rpc DeployProgram(DeployProgramRequest) returns (DeployProgramResponse);
  rpc GetProgram(GetProgramRequest) returns (GetProgramResponse);
  rpc Start(StartRequest) returns (StartResponse);
  rpc Stop(StopRequest) returns (StopResponse);
  rpc SetPort(SetPortRequest) returns (SetPortResponse);
  rpc SetParam(SetParamRequest) returns (SetParamResponse);
  rpc GetStatus(GetStatusRequest) returns (Status);
  rpc SubscribeTelemetry(SubscribeTelemetryRequest) returns (stream TelemetryFrame);
  rpc ListHalChannels(ListHalChannelsRequest) returns (ListHalChannelsResponse);
  rpc SetHalChannel(SetHalChannelRequest) returns (SetHalChannelResponse);
}

message DeployProgramRequest { string json_program = 1; }
message DeployProgramResponse { string program_id = 1; }
message GetProgramRequest {}
message GetProgramResponse { string program_id = 1; string json_program = 2; }
message StartRequest {}
message StartResponse {}
message StopRequest {}
message StopResponse {}
message SetPortRequest { string name = 1; string json_value = 2; }
message SetPortResponse {}
message SetParamRequest { string block = 1; string param = 2; string json_value = 3; }
message SetParamResponse {}
message GetStatusRequest {}
message Status {
  bool running = 1;
  string program_id = 2;
  int32 cycle_ms = 3;
  bool stale = 4;
}
message SubscribeTelemetryRequest { int32 hz = 1; }
message TelemetryFrame {
  int64 unix_ms = 1;
  map<string, string> values_json = 2; // port -> JSON-encoded value
}
message HalChannelInfo { string name = 1; string direction = 2; string dtype = 3; }
message ListHalChannelsRequest {}
message ListHalChannelsResponse { repeated HalChannelInfo channels = 1; }
message SetHalChannelRequest { string name = 1; string json_value = 2; }
message SetHalChannelResponse {}
```

- [ ] **Step 1: Write proto + gen script**

`scripts/gen_proto.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/packages/worker/src/brew_worker/gen"
mkdir -p "$OUT"
uv run python -m grpc_tools.protoc \
  -I "$ROOT/proto" \
  --python_out="$OUT" \
  --grpc_python_out="$OUT" \
  "$ROOT/proto/worker/v1/worker.proto"
# Fix imports if grpc generates `import worker_pb2` — adjust to relative package imports
touch "$OUT/__init__.py"
```

- [ ] **Step 2: Run codegen**

Run: `chmod +x scripts/gen_proto.sh && ./scripts/gen_proto.sh`  
Expected: generated files exist

- [ ] **Step 3: Add smoke import test**

```python
# tests/worker/test_proto_import.py
def test_proto_importable():
    from brew_worker.gen import worker_pb2, worker_pb2_grpc
    assert worker_pb2.DESCRIPTOR
```

Fix package imports until PASS.

- [ ] **Step 4: Commit**

```bash
git add proto scripts/gen_proto.sh packages/worker/src/brew_worker/gen tests/worker/test_proto_import.py
git commit -m "feat(worker): add worker.v1 protobuf and generated stubs"
```

---

### Task 8: gRPC servicer + process entrypoint

**Files:**
- Create: `packages/worker/src/brew_worker/grpc_server.py`
- Create: `packages/worker/src/brew_worker/__main__.py`
- Test: `tests/worker/test_grpc_integration.py`

**Interfaces:**
- Consumes: `Engine`, generated stubs
- Produces: `serve(engine: Engine, host: str = "127.0.0.1", port: int = 50051) -> grpc.Server`  
  `main()` builds default `MockHal` with `hal.adc.temp_c` + `hal.gpio.heater_hlt`, `Engine`, starts cycle optionally stopped, serves forever.

`SubscribeTelemetry`: loop at `hz` (default 5), send `engine.snapshot()` as JSON strings until cancelled.

- [ ] **Step 1: Write integration test**

```python
# tests/worker/test_grpc_integration.py
import json
import threading
import time
import grpc
from brew_worker.hal.base import HalChannel
from brew_worker.hal.mock import MockHal
from brew_worker.runtime.engine import Engine
from brew_worker.plugins import register_builtins
from brew_worker.grpc_server import serve
from brew_worker.gen import worker_pb2, worker_pb2_grpc
from pathlib import Path

PROGRAM = json.loads(Path("programs/hlt-loop-v1.json").read_text())

def test_deploy_setport_telemetry():
    register_builtins()
    hal = MockHal([
        HalChannel("hal.adc.temp_c", "input", "float"),
        HalChannel("hal.gpio.heater_hlt", "output", "bool"),
    ])
    eng = Engine(hal)
    server = serve(eng, host="127.0.0.1", port=50052)
    channel = grpc.insecure_channel("127.0.0.1:50052")
    stub = worker_pb2_grpc.WorkerStub(channel)
    stub.DeployProgram(worker_pb2.DeployProgramRequest(json_program=json.dumps(PROGRAM)))
    stub.SetHalChannel(worker_pb2.SetHalChannelRequest(name="hal.adc.temp_c", json_value="50.0"))
    stub.SetPort(worker_pb2.SetPortRequest(name="master.Hyst.SetPoint", json_value="66.0"))
    stub.SetPort(worker_pb2.SetPortRequest(name="master.Hyst.Enabled", json_value="true"))
    stub.Start(worker_pb2.StartRequest())
    time.sleep(0.25)
    status = stub.GetStatus(worker_pb2.GetStatusRequest())
    assert status.running is True
    assert status.program_id == "hlt-loop-v1"
    assert hal.get("hal.gpio.heater_hlt") is True
    server.stop(grace=0)
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/worker/test_grpc_integration.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement servicer + `serve` + `__main__`**

Map JSON values with `json.loads`. `DeployProgram` calls `engine.deploy`. Errors → `grpc.StatusCode.INVALID_ARGUMENT` with message.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/worker/ -v`  
Expected: all PASS

- [ ] **Step 5: Manual smoke**

```bash
uv run brew-worker --host 127.0.0.1 --port 50051
# in another terminal, optional grpcurl or a 10-line python client deploy+start
```

- [ ] **Step 6: Commit**

```bash
git add packages/worker/src/brew_worker/grpc_server.py packages/worker/src/brew_worker/__main__.py tests/worker/test_grpc_integration.py
git commit -m "feat(worker): gRPC server and CLI entrypoint"
```

---

### Task 9: Disconnect autonomy check

**Files:**
- Test: `tests/worker/test_autonomy.py`

**Interfaces:**
- Produces: proof that stopping the gRPC server/client does not stop the engine thread

- [ ] **Step 1: Write test**

```python
# tests/worker/test_autonomy.py
import json, time
from pathlib import Path
from brew_worker.hal.base import HalChannel
from brew_worker.hal.mock import MockHal
from brew_worker.runtime.engine import Engine
from brew_worker.plugins import register_builtins

def test_engine_keeps_running_without_grpc():
    register_builtins()
    hal = MockHal([
        HalChannel("hal.adc.temp_c", "input", "float"),
        HalChannel("hal.gpio.heater_hlt", "output", "bool"),
    ])
    eng = Engine(hal)
    eng.deploy(json.loads(Path("programs/hlt-loop-v1.json").read_text()))
    eng.set_hal_channel("hal.adc.temp_c", 50.0)
    eng.set_master_port("master.Hyst.Enabled", True)
    eng.set_master_port("master.Hyst.SetPoint", 66.0)
    eng.start()
    time.sleep(0.15)
    assert eng.status()["running"] is True
    assert hal.get("hal.gpio.heater_hlt") is True
    # no grpc involved — autonomy of cycle loop
    eng.stop()
```

- [ ] **Step 2: Run — PASS**

- [ ] **Step 3: Commit**

```bash
git add tests/worker/test_autonomy.py
git commit -m "test(worker): cycle loop autonomy without gRPC client"
```

---

## Plan 1 done when

- `uv run pytest tests/worker/ -v` all green
- `uv run brew-worker` serves gRPC on `:50051` with mock HAL
- Sample `programs/hlt-loop-v1.json` deployable over gRPC
- Ready for Plan 2 (master + web UI)

## Spec coverage (Plan 1)

| Spec item | Task |
|-----------|------|
| Mock HAL | 2 |
| Declarative program + plugins | 3–6 |
| Cycle + autonomy | 5, 9 |
| gRPC worker-as-server | 7–8 |
| Sample hlt-loop | 6 |
| Master / web UI | Plan 2 |
| Live GPIO | out of scope |
| Pt100 / brew FSMs | deferred (temp_c HAL for sim) |
