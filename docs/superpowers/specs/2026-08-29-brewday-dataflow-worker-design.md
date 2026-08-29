# Brew-day dataflow worker — design

**Date:** 2026-08-29  
**Status:** Draft for review  
**Heritage:** New development in the spirit of `autobrewpi` (vspace drivers, port wiring, logic-controlled brew states). Legacy LCD UI, HBUS gadget stack, and in-process-only variable space are not carried forward.

## Goals

- Run **low-level dataflow programs on a remote Linux worker** that owns I/O.
- Keep **brew-day orchestration on a master** (mash/boil stages, recipes, UI).
- Worker runs **fully autonomously** after a program is loaded (survives master disconnect) while the master has **full observability and controllability** when connected.
- **Simulate first:** mock HAL so master + worker + web UI work with no hardware.
- Preserve the spirit of typed ports, connected blocks, and `cycle()`-driven state — not the old implementation.

## Non-goals (v1)

- Real GPIO / 1-Wire / I²C drivers (HAL interface only; `live` later).
- Multi-worker fleets / discovery.
- Offloading brew-day FSMs to the worker.
- Visual graph editor.
- Hard real-time / sub-millisecond cycles.
- Carrying over pygame/LCD/`abpi.ui` code.

## Architecture

```
[Web UI] --HTTP/WS--> [Master]
                         |
                       gRPC
                         |
                      [Worker]
                    /    |    \
                 HAL   Graph   Plugins
           (mock|live) (cycle) (Python blocks)
```

| Component | Responsibility |
|-----------|----------------|
| **Worker** | HAL, load/persist graph + plugins, cycle loop, gRPC server, telemetry stream |
| **Master** | Brew-day FSMs, recipes, gRPC client, HTTP/WS API for UI |
| **Web UI** | Live values, mock inject, deploy/status, mash/boil controls — talks only to master |

**Approach:** Two-process Python stack (Approach 1). Same language for plugins and brew logic; fastest path to mock-first development.

## Communication (gRPC)

- **Worker is the gRPC server**; master dials in (LAN v1). Reconnect/backoff on the master; worker does not depend on the link to keep cycling.
- On disconnect: graph keeps running with last setpoints/`master.*` port values; master marks worker `offline`; UI shows last-known + stale. On reconnect: resubscribe telemetry; optionally reconcile desired params.

### RPCs (v1)

| RPC | Kind | Purpose |
|-----|------|---------|
| `DeployProgram` | unary | Install/replace graph artifact |
| `GetProgram` | unary | Current program id + artifact |
| `Start` / `Stop` | unary | Run or pause cycle loop |
| `SetPort` / `SetParam` | unary | Write `master.*` or block params |
| `CallBlock` | unary | Invoke marked plugin methods |
| `GetStatus` | unary | Running, program id, cycle health, link meta |
| `SubscribeTelemetry` | server stream | Port values, block state, logs, alarms (~1–10 Hz) |
| `ListHalChannels` | unary | Discover HAL channels |
| `SetHalChannel` | unary | Inject mock sensor / read actuator state |
| `SetHalMode` | unary | `mock` \| `live` (v1: mock only required) |

Protobuf package lives in-repo (e.g. `proto/worker/v1/worker.proto`); codegen for master and worker.

## Program format & worker runtime

### Artifact

Declarative JSON: program `id`, `cycle_ms`, `blocks[]` (`name`, `type`, `params`), `wires[]` (`from` → `to`).

Port addressing:

- `BlockName.PortName` — block ports
- `hal.<subsystem>.<channel>` — HAL sources/sinks (e.g. `hal.adc.hlt_r`, `hal.gpio.heater_hlt`)
- `master.<name>` — virtual inputs written by the master over gRPC (setpoints, enables)

Example (illustrative):

```json
{
  "id": "hlt-loop-v1",
  "cycle_ms": 100,
  "blocks": [
    {"name": "HLTSens", "type": "Pt100", "params": {"table": "pt100"}},
    {"name": "Hyst", "type": "Hysteresis", "params": {"hyst_type": "updown", "level": 2.0}},
    {"name": "HeatOut", "type": "GpioOut", "params": {"channel": "heater_hlt"}}
  ],
  "wires": [
    {"from": "hal.adc.hlt_r", "to": "HLTSens.Resistance"},
    {"from": "HLTSens.Temperature", "to": "Hyst.CurrTemp"},
    {"from": "Hyst.CtlOut", "to": "HeatOut.Value"},
    {"from": "master.Hyst.SetPoint", "to": "Hyst.SetPoint"},
    {"from": "master.Hyst.Enabled", "to": "Hyst.Enabled"}
  ]
}
```

### Plugins

- Block **types** are Python classes registered on the worker (`Hysteresis`, `Pt100`, `GpioOut`, `LogicAnd`, …).
- Spirit of old `VSpaceDriver`: typed ports, input updates, `cycle()`, optional callable methods.
- Graphs reference type names only; implementations ship with the worker (plugin package updates later).

### Cycle

1. Read HAL → feed source ports  
2. Propagate along wires (topological order; **reject cycles at deploy**)  
3. `cycle()` on stateful blocks  
4. Write sinks to HAL  
5. Sample telemetry for subscribers  

### Deploy / persist

- Replace-in-place; brief hold of previous outputs or per-channel safe defaults.
- Persist last good program to disk; reboot reloads and can auto-`Start`.

## Master brew-day

- Mash/boil **state machines live on the master** (domain spirit of `mashctl` / `boilctl`, new code).
- Master drives the worker only through **`SetPort` / `SetParam`** on `master.*` (and deploy of the low-level graph).
- On link loss: local loops keep last setpoints; **stage/recipe progress pauses** until the master is back.
- Recipes and stage config are master-side; worker never interprets mash stages in v1.

## Simulation-first (v1 delivery focus)

**Success criteria:** run master + worker + web UI with **no hardware**, exercising real gRPC deploy, graph cycle, brew-day (or manual) writes to `master.*`, and full observability.

| Feature | Behavior |
|---------|----------|
| HAL `mock` | In-memory channels; sensors injectable; actuators observable |
| Sensor inject | Master/UI `SetHalChannel` (sliders) |
| Actuator watch | Telemetry shows graph-driven outputs |
| Plant stub (optional) | Simple thermal-mass / lag so heater-on raises mock temp |
| Disconnect drill | Kill stream; worker keeps cycling; UI stale/offline |

**Process layout:** same host is fine — Web UI → Master → gRPC → Worker (mock HAL).

**Explicitly later:** live GPIO backends, remote board packaging, multi-worker.

## Web UI (v1 — simple)

Talks only to master (HTTP + WebSocket or SSE mirroring worker telemetry).

Minimum surfaces:

1. **Worker status** — online/offline, program id, cycle rate  
2. **Live ports** — key temps, enables, actuator bits  
3. **Mock panel** — inject HAL sensors  
4. **Deploy** — load sample program / show current  
5. **Brew controls** — start/stop mash or boil (or manual setpoint/enable if FSM is thin at first)

No custom LCD stack; no graph editor in v1.

## Mapping from legacy codebase

| Keep (idea / domain) | Drop |
|----------------------|------|
| Port-wired drivers + propagation | `abpi/ui`, fonts, input client |
| Hysteresis / mash / boil behavior as requirements | HBUS / `GadgetVariableSpace` as-is |
| Config-as-graph mental model | Magic `__getattr__` port access |
| Recipe JSON shape as reference | pygame / embedded screenbuf |

Legacy tree may remain as reference; new packages should not import `abpi.ui` or HBUS clients.

## Suggested repo layout (greenfield packages)

```
proto/worker/v1/          # gRPC definitions
worker/                   # runtime, HAL, plugins, gRPC server
master/                   # brew-day, gRPC client, HTTP/WS API
web/                      # simple UI
programs/                 # sample graphs (e.g. hlt-loop-v1.json)
docs/superpowers/specs/   # this design
```

Exact packaging (monorepo poetry/uv workspaces) decided in the implementation plan.

## Error handling & safety (v1)

- Deploy validation: unknown block types, bad wires, cyclic graphs → reject with clear error.
- Plugin exceptions: log, mark block fault in telemetry; configurable per-output fail policy (hold last vs force off) — default **hold last** to match autonomy choice.
- Master never assumes worker is live for safety-critical UI: always show connection/staleness.

## Testing

- Unit: wire propagation, hysteresis block, deploy validation.
- Integration: worker + mock HAL in-process or subprocess; gRPC deploy + telemetry.
- Sim smoke: master brew or manual setpoint → mock heater bit → optional plant stub temp rise.
- Disconnect: stop master client; assert worker continues cycling.

## Open points (non-blocking for sim v1)

- Fail-safe profile beyond hold-last (e.g. heater off after N seconds offline) — decide before live hardware.
- Plugin distribution to remote boards.
- Auth on gRPC / UI (LAN trust assumed for sim).

## Approval

Agreed in design discussion:

- Approach 1 (Python master + worker)
- gRPC, worker as server
- Declarative graph + Python plugins
- Brew-day on master; low-level loops on worker
- Full worker autonomy + master observability/control
- GPIO-class HAL later; **mock-first now**
- API + simple web UI + mock I/O
