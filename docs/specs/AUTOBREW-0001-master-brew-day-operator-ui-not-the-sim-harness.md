---
id: AUTOBREW-0001
title: Master brew-day operator UI (not the sim harness)
status: done
owner: bmorais
created: 2026-08-30
updated: 2026-08-30
tags:
- brew
- ui
- master
source_outbound_id: AUTOBREW-0001
source_content_hash: 0fb7787f806ee00d
---

## Context

Promoted from `IDEA-295`. Research root: `/home/bruno/work/autobrewpi`.

What exists today under `web/` and `brew_master` is a **sim harness** titled "AutoBrew Sim": mock temperature inject, deploy sample program, manual hysteresis enable/setpoint. `BrewDayController.state()` only exposes `mode: "manual"` — no mash/boil session, stages, timers, or recipes. The operator correctly rejected treating that UI as the core brew-day console.

Architecture (already accepted in `docs/superpowers/specs/2026-08-29-brewday-dataflow-worker-design.md`): brew-day FSMs live on the **master**; the worker runs low-level dataflow graphs and exposes telemetry / `master.*` ports over gRPC. Legacy `abpi/brewday/mashctl.py` / `boilctl.py` are domain references only (states and human-wait steps) — do not port `abpi.ui`.

Sim/mock HAL tooling remains a separate concern (`IDEA-296`).

## Goals / Non-goals

**Goals**
- Ship a **brew-day operator console** as the default web UI for the master.
- Drive a **master-side mash session FSM** (v1 slice) that writes setpoints/enables to the worker and exposes phase, stage list, and timers to the UI.
- Keep **live process values** and **worker online/stale** visible on the operator surface.
- Relocate the existing sim harness under `/sim` so it is not the home page.

**Non-goals**
- Full legacy mash stage set (fly sparge, multi-vessel choreography) in this spec’s v1 slice.
- Recipe editor / CRUD UI.
- Live GPIO HAL (`IDEA-297`).
- Worker-local UI.
- Porting pygame/LCD code.

## Decision

Build **one** FastAPI-served web app with two routes: **`/` = operator console** (default), **`/sim` = mock harness** (existing behavior, re-titled). Add a master-side **`MashSession`** (name flexible) that loads **fixed JSON stages** (no editor), runs a **minimal but real** stage machine inspired by legacy mashctl, and is the sole writer of brew setpoints/enables during a session. Operator API + UI surface session state, timers, and commands (`start` / `stop` / `pause` / `resume` / `advance`). If the worker has no program running, the operator UI offers **Ensure graph loaded** (non-sim deploy of the standard HLT loop) as an explicit action. **Pause** clears heat/pump enables via existing `SetPort` paths (no new panic port in v1).

## Design

### Routing / UX

| Path | Purpose |
|------|---------|
| `/` | Operator console — session header (phase, timer, worker badge), stage list, live temps/outputs, primary actions |
| `/sim` | Existing mock inject + manual hysteresis + deploy sample (IDEA-296 surface) |

Shared chrome: worker online/stale banner on both.

### Master session module

New module under `packages/master/src/brew_master/` (e.g. `mash_session.py`), owned by an evolved `BrewDayController` or sibling service used by the API:

- Load stages from a checked-in JSON file (e.g. `config/brewday/mash_stages_v1.json`) with fields at least: `type`, `target_temp` (optional), `time_min` (optional), `use_pump` (bool), `label`.
- **v1 stage types:** `preheat` (auto → `preheat_done` when temp within tolerance), `ack` (human advance — covers water_in / add_items style waits), `timed` (mash/mashout hold with timer + pump flag), `idle` terminal.
- On each tick / command: write `master.Hyst.SetPoint`, `master.Hyst.Enabled`, and pump-related ports if the deployed graph exposes them (document required `master.*` ports in the stage file or program notes).
- On master↔worker disconnect: **freeze stage advancement** (existing design); keep showing last telemetry as stale.
- `pause`: set enables/pump false; `resume`: restore prior session outputs if still valid.

Boil can remain out of v1 UI or a stub “coming soon” — this spec’s AC targets **mash session + operator shell**.

### HTTP / WS API (additive)

Keep existing `/api/mock/*` and `/api/manual` for `/sim` only.

Add approximately:

- `GET /api/operator/state` — session phase, stage index, stage list, timer end, live snapshot, worker supervisor snapshot, `graph_ready` bool
- `POST /api/operator/ensure-graph` — deploy standard program + start if needed
- `POST /api/operator/session/start|stop|pause|resume|advance`
- Existing `WS /ws/telemetry` may carry operator state or a dedicated `/ws/operator` — prefer **one WS** that includes both `operator` and `worker` keys to avoid duplicate sockets.

### UI

- Replace default `web/index.html` (or add `web/operator.html` mounted at `/`) with operator layout; move current sim page to `web/sim.html` at `/sim`.
- No LCD/abpi widgets; keep the simple static HTML/JS approach unless a later spec chooses a framework.

### Relationship to prior design doc

Supplements (does not supersede) `docs/superpowers/specs/2026-08-29-brewday-dataflow-worker-design.md`. That doc’s “simple web UI” bullet is clarified: **operator console is required product UI**; sim harness is tooling.

## Alternatives considered

- **Polish Sim into “the” UI** — rejected by operator; conflates HAL inject with brew-day control.
- **Two separate apps/ports** — more process overhead for little gain while both talk to one master.
- **Full legacy mashctl state set in v1** — too large; ship a subset with room to extend stage types.
- **New dedicated panic gRPC port** — defer; pause via SetPort is enough for v1.

## Acceptance criteria

- [x] Operator can open the master’s default URL (`/`) and run a mash session (start / pause / resume / advance / stop) with visible phase, stage list, timer, and worker online/stale — without using the Sim page.
- [x] Visiting `/` shows an **operator** console (not branded primarily as Sim) with phase/stage/timer/worker status.
- [x] `/sim` still provides mock temp inject and manual hysteresis controls.
- [x] A fixed JSON mash stage list can be started, paused, resumed, advanced (for `ack` stages), and stopped from the operator UI; master writes worker setpoints/enables accordingly when the worker is online.
- [x] `GET /api/operator/state` (or equivalent) exposes enough for the UI without scraping sim-only fields.
- [x] Ensure-graph action can load the standard sample program when none is running.
- [x] On worker disconnect, UI shows offline/stale and session does not advance stages.
- [x] Automated tests cover session transitions (at least idle→preheat→ack or timed→idle) without requiring a browser.
- [x] Existing worker/master tests (`uv run pytest tests/`) still pass.

## Test plan

- **Automated tests:**
  - `tests/master/test_mash_session.py` — stage machine transitions, pause clears enables (mock supervisor/client), timer completion.
  - `tests/master/test_operator_api.py` — FastAPI routes for operator start/advance/state; `/` serves operator page; `/sim` serves sim page.
- **Manual verification:**
  1. `./scripts/sim_run.sh` (or worker+master).
  2. Open `/` — confirm operator chrome; start session; observe setpoint/enable via live panel or `/sim` telemetry.
  3. Disconnect worker — confirm stale + no stage advance; reconnect.
  4. Open `/sim` — mock inject still works.
- **Regression guard:** `uv run pytest tests/ -v` green after changes.

## Clock Log

CLOCK-IN: [2026-08-30 Sun 12:04]
CLOCK-OUT: [2026-08-30 Sun 12:10]
CLOCK-IN: [2026-08-30 12:07]
CLOCK-OUT: [2026-08-30 12:20]

## Definition of done

- [x] Acceptance criteria all met.
- [x] Test plan executed; automated tests pass (`uv run pytest`); manual smoke via `operator_run.sh`.
- [x] No regressions.
- [x] Spec body updated to match what shipped.
- [ ] Portable status set to `done` in target repo; `wt spec pull-status AUTOBREW-0001` when closing the loop (wt-side).

## Open questions

None blocking acceptance — decisions recorded above. Future specs may expand stage vocabulary and add boil UI.
