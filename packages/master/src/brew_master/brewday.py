from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from brew_master.mash_session import MashSession
from brew_master.supervisor import WorkerSupervisor

ROOT = Path(__file__).resolve().parents[4]
SAMPLE_PROGRAM = ROOT / "programs" / "hlt-loop-v1.json"
STAGES_FILE = ROOT / "config" / "brewday" / "mash_stages_v1.json"


class BrewDayController:
    def __init__(
        self,
        supervisor: WorkerSupervisor,
        *,
        stages_path: Path | None = None,
        tick_s: float = 0.25,
    ):
        self._sup = supervisor
        self._enabled = False
        self._setpoint_c = 66.0
        self._session = MashSession.from_json_file(stages_path or STAGES_FILE)
        self._tick_s = tick_s
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._tick_loop, name="mash-session-tick", daemon=True
        )
        self._thread.start()

    def shutdown(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)

    def ensure_sample_deployed(self) -> None:
        client = self._sup.client()
        if not client.connected:
            client.connect()
        program = json.loads(SAMPLE_PROGRAM.read_text())
        client.deploy_json(program)
        client.start()

    def ensure_graph(self) -> None:
        """Operator-facing ensure: deploy standard HLT loop if needed."""
        self.ensure_sample_deployed()

    def set_manual(self, *, enabled: bool, setpoint_c: float) -> None:
        # Sim-only path — refuse to fight an active mash session.
        if self._session.phase in ("active", "paused"):
            raise RuntimeError("mash session active; stop it before manual control")
        client = self._sup.client()
        if not client.connected:
            client.connect()
        self._enabled = enabled
        self._setpoint_c = float(setpoint_c)
        client.set_port("master.Hyst.SetPoint", self._setpoint_c)
        client.set_port("master.Hyst.Enabled", self._enabled)
        st = client.get_status()
        if not st.get("running"):
            client.start()

    def inject_temp(self, temp_c: float) -> None:
        client = self._sup.client()
        if not client.connected:
            client.connect()
        client.set_hal_channel("hal.adc.temp_c", float(temp_c))

    def graph_ready(self) -> bool:
        snap = self._sup.snapshot()
        st = snap.get("status") or {}
        return bool(snap.get("online") and st.get("running") and st.get("program_id"))

    def operator_state(self) -> dict[str, Any]:
        worker = self._sup.snapshot()
        telem = worker.get("last_telemetry") or {}
        temp = telem.get(self._session.temp_port)
        return {
            "operator": {
                **self._session.state(),
                "graph_ready": self.graph_ready(),
                "current_temp": temp,
            },
            "worker": worker,
            "sim": {
                "mode": "manual",
                "enabled": self._enabled,
                "setpoint_c": self._setpoint_c,
            },
        }

    def state(self) -> dict[str, Any]:
        """Backward-compatible shape used by /sim + WS."""
        full = self.operator_state()
        return {
            "mode": "manual",
            "enabled": self._enabled,
            "setpoint_c": self._setpoint_c,
            "worker": full["worker"],
            "operator": full["operator"],
        }

    def session_start(self) -> None:
        self._session.start()
        self._flush_session_outputs()

    def session_stop(self) -> None:
        self._session.stop()
        self._flush_session_outputs()

    def session_pause(self) -> None:
        self._session.pause()
        self._flush_session_outputs()

    def session_resume(self) -> None:
        self._session.resume()
        self._flush_session_outputs()

    def session_advance(self) -> None:
        self._session.advance()
        self._flush_session_outputs()

    def _flush_session_outputs(self) -> None:
        snap = self._sup.snapshot()
        if not snap.get("online"):
            return
        client = self._sup.client()
        if not client.connected:
            try:
                client.connect()
            except Exception:
                return
        try:
            self._session.apply_outputs(client)
        except Exception:
            pass

    def _tick_loop(self) -> None:
        while not self._stop.wait(self._tick_s):
            snap = self._sup.snapshot()
            online = bool(snap.get("online"))
            telem = snap.get("last_telemetry") or {}
            temp = telem.get(self._session.temp_port)
            try:
                temp_f = float(temp) if temp is not None else None
            except (TypeError, ValueError):
                temp_f = None
            before = (
                self._session.phase,
                self._session.stage_index,
                self._session.stage_status,
                self._session._desired_enable,
            )
            self._session.tick(worker_online=online, current_temp=temp_f)
            after = (
                self._session.phase,
                self._session.stage_index,
                self._session.stage_status,
                self._session._desired_enable,
            )
            if before != after:
                self._flush_session_outputs()
            elif self._session.phase == "active" and online:
                # keep outputs asserted while running
                self._flush_session_outputs()
