from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Protocol


class PortWriter(Protocol):
    def set_port(self, name: str, value: float | bool) -> None: ...


@dataclass(frozen=True)
class Stage:
    type: str
    label: str
    target_temp: float | None = None
    time_min: float | None = None
    use_pump: bool = False


WritePorts = Callable[[float | None, bool], None]


class MashSession:
    """Minimal mash stage machine owned by the master (AUTOBREW-0001)."""

    def __init__(
        self,
        stages: list[Stage],
        *,
        temp_tolerance_c: float = 0.5,
        setpoint_port: str = "master.Hyst.SetPoint",
        enable_port: str = "master.Hyst.Enabled",
        temp_port: str = "hal.adc.temp_c",
    ):
        if not stages:
            raise ValueError("stages must be non-empty")
        self._stages = stages
        self._tol = float(temp_tolerance_c)
        self._setpoint_port = setpoint_port
        self._enable_port = enable_port
        self.temp_port = temp_port

        self.phase = "idle"  # idle | active | paused | finished
        self.stage_index = 0
        self.stage_status = "idle"  # running | waiting_ack | done
        self._timer_end: datetime | None = None
        self._saved: dict[str, Any] | None = None
        self._desired_setpoint: float | None = None
        self._desired_enable = False

    @classmethod
    def from_json_file(cls, path: Path) -> MashSession:
        data = json.loads(path.read_text())
        stages = [
            Stage(
                type=s["type"],
                label=s.get("label") or s["type"],
                target_temp=s.get("target_temp"),
                time_min=s.get("time_min"),
                use_pump=bool(s.get("use_pump", False)),
            )
            for s in data["stages"]
        ]
        return cls(
            stages,
            temp_tolerance_c=float(data.get("temp_tolerance_c", 0.5)),
            setpoint_port=str(data.get("setpoint_port", "master.Hyst.SetPoint")),
            enable_port=str(data.get("enable_port", "master.Hyst.Enabled")),
            temp_port=str(data.get("temp_port", "hal.adc.temp_c")),
        )

    @property
    def stages(self) -> list[Stage]:
        return list(self._stages)

    @property
    def current_stage(self) -> Stage | None:
        if 0 <= self.stage_index < len(self._stages):
            return self._stages[self.stage_index]
        return None

    def start(self) -> None:
        self.phase = "active"
        self.stage_index = 0
        self._enter_stage(self._stages[0])

    def stop(self) -> None:
        self.phase = "idle"
        self.stage_index = 0
        self.stage_status = "idle"
        self._timer_end = None
        self._saved = None
        self._desired_setpoint = None
        self._desired_enable = False

    def pause(self) -> None:
        if self.phase != "active":
            return
        self._saved = {
            "setpoint": self._desired_setpoint,
            "enable": self._desired_enable,
            "stage_index": self.stage_index,
            "stage_status": self.stage_status,
            "timer_end": self._timer_end,
        }
        self.phase = "paused"
        self._desired_enable = False

    def resume(self) -> None:
        if self.phase != "paused" or self._saved is None:
            return
        self.phase = "active"
        self.stage_index = self._saved["stage_index"]
        self.stage_status = self._saved["stage_status"]
        self._timer_end = self._saved["timer_end"]
        self._desired_setpoint = self._saved["setpoint"]
        self._desired_enable = bool(self._saved["enable"])
        self._saved = None

    def advance(self) -> None:
        if self.phase != "active":
            raise RuntimeError("session not active")
        if self.stage_status != "waiting_ack":
            raise RuntimeError("current stage is not waiting for advance")
        self._next_stage()

    def tick(self, *, worker_online: bool, current_temp: float | None) -> None:
        """Advance timers / preheat detection. No-op when offline or paused."""
        if self.phase != "active" or not worker_online:
            return
        stage = self.current_stage
        if stage is None:
            return

        if stage.type == "preheat" and self.stage_status == "running":
            if current_temp is not None and stage.target_temp is not None:
                if abs(float(current_temp) - float(stage.target_temp)) <= self._tol:
                    self.stage_status = "waiting_ack"
                    self._desired_enable = False
            return

        if stage.type == "timed" and self.stage_status == "running":
            if self._timer_end is not None and datetime.now() >= self._timer_end:
                self._next_stage()

    def apply_outputs(self, writer: PortWriter) -> None:
        if self._desired_setpoint is not None:
            writer.set_port(self._setpoint_port, float(self._desired_setpoint))
        writer.set_port(self._enable_port, bool(self._desired_enable))

    def state(self) -> dict[str, Any]:
        stage = self.current_stage
        return {
            "phase": self.phase,
            "stage_index": self.stage_index,
            "stage_status": self.stage_status,
            "stage_label": stage.label if stage else None,
            "stage_type": stage.type if stage else None,
            "timer_end": self._timer_end.isoformat(timespec="seconds")
            if self._timer_end
            else None,
            "desired_setpoint": self._desired_setpoint,
            "desired_enable": self._desired_enable,
            "stages": [
                {
                    "type": s.type,
                    "label": s.label,
                    "target_temp": s.target_temp,
                    "time_min": s.time_min,
                    "use_pump": s.use_pump,
                }
                for s in self._stages
            ],
        }

    def _enter_stage(self, stage: Stage) -> None:
        self._timer_end = None
        if stage.type == "idle":
            self.phase = "finished"
            self.stage_status = "done"
            self._desired_enable = False
            self._desired_setpoint = None
            return

        if stage.type == "preheat":
            self.stage_status = "running"
            self._desired_setpoint = float(stage.target_temp or 0.0)
            self._desired_enable = True
            return

        if stage.type == "ack":
            self.stage_status = "waiting_ack"
            self._desired_enable = False
            return

        if stage.type == "timed":
            self.stage_status = "running"
            self._desired_setpoint = float(stage.target_temp or 0.0)
            self._desired_enable = True
            minutes = float(stage.time_min or 0.0)
            self._timer_end = datetime.now() + timedelta(minutes=minutes)
            return

        raise ValueError(f"unknown stage type: {stage.type}")

    def _next_stage(self) -> None:
        if self.stage_index >= len(self._stages) - 1:
            self.phase = "finished"
            self.stage_status = "done"
            self._desired_enable = False
            return
        self.stage_index += 1
        self._enter_stage(self._stages[self.stage_index])
