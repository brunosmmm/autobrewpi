# AGENTS.md

Guidance for AI agents and humans working in this repository.

## What this project is

Brew-day control system being rebuilt around:

1. **Worker** (`packages/worker`) — runs offloaded dataflow programs against a HAL (mock today, live GPIO later); gRPC server.
2. **Master** (`packages/master`) — brew-day / manual control, observability, HTTP+WebSocket API for the UI; gRPC client to the worker.
3. **Web UI** (`web/`) — simple sim console; talks **only** to the master.

Spirit preserved from the legacy tree: typed ports, wired blocks, `cycle()`-driven logic. Implementation is new.

## Canonical docs

| Doc | Purpose |
|-----|---------|
| `docs/superpowers/specs/2026-08-29-brewday-dataflow-worker-design.md` | Architecture / product design (source of truth) |
| `docs/superpowers/plans/2026-08-29-worker-mock-grpc.md` | Plan 1 — worker + mock HAL + gRPC (implemented) |
| `docs/superpowers/plans/2026-08-29-master-web-sim.md` | Plan 2 — master + web sim (implemented) |

Read the design spec before changing architecture, protocol, or workstream boundaries.

## Workstreams (do not conflate)

| Track | Meaning |
|-------|---------|
| **(b) Worker** | Brand-new edge runtime — graphs, plugins, HAL, gRPC |
| **(a) Master** | Concept rewrite of brew-day control — not an `abpi` refactor |
| **(c) Simulation** | `HAL=mock` mode on the worker (+ UI inject), not a separate app |

Build order preference: worker+mock → gRPC → master/UI → later live HAL.

## Legacy code (`abpi/`, `autobrew`)

- Treat as **reference only** (mash/boil domain, hysteresis ideas, old wiring configs under `config/`).
- **Do not** import `abpi.*` from `brew_worker` / `brew_master`.
- **Do not** invest in the LCD/UI/HBUS stack (`abpi/ui`, fonts, HBUS clients) unless explicitly asked.
- Old poetry `pyproject.legacy.toml` is archival; active tooling is **uv** + root `pyproject.toml`.

## Dev commands

```bash
uv sync --all-packages
uv run pytest tests/ -v
./scripts/gen_proto.sh          # after editing proto/worker/v1/worker.proto
./scripts/sim_smoke.sh          # quick worker+master mock e2e (exits)
./scripts/sim_run.sh            # leave sim up for UI inspection (Ctrl+C)
# Ports: BREW_MASTER_PORT / BREW_WORKER_PORT, or --master-port / --worker-port.
# Busy defaults auto-bump to the next free port.

uv run brew-worker --port 50051
uv run brew-master --worker 127.0.0.1:50051 --port 8000
# UI: http://127.0.0.1:8000
```

Python **≥ 3.11**. Package layout: `packages/worker`, `packages/master`, `proto/`, `programs/`, `web/`, `tests/`.

## Design constraints (v1)

- Worker is gRPC **server**; master dials in.
- On disconnect, worker **keeps cycling** (hold last setpoints); master shows offline/stale.
- Brew-day orchestration lives on the **master**; worker runs low-level loops only.
- Programs = declarative JSON graphs + Python block plugins.
- Reject cyclic wire graphs at deploy.
- Default output policy: hold last.
- Sim-first: no real GPIO required for development.

## When changing code

- Prefer small, focused files; match existing package patterns.
- Add/adjust tests next to the behavior you change (`tests/worker`, `tests/master`).
- Regenerate gRPC stubs via `scripts/gen_proto.sh` (do not hand-edit `*_pb2*.py` except the import rewrite the script applies).
- Do not commit secrets, `.venv/`, or `state/`.
- Only commit when asked; do not force-push `main`/`master`.

## Out of scope unless requested

- Live GPIO / 1-Wire / I²C drivers
- Multi-worker fleets
- Offloading mash/boil FSMs to the worker
- Visual graph editor
- Auth on gRPC/UI
