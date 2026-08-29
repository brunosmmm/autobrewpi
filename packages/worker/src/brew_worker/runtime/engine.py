from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from brew_worker.hal.mock import MockHal
from brew_worker.runtime.block import REGISTRY, Block
from brew_worker.runtime.graph import (
    ProgramValidationError,
    parse_program,
    validate_and_order,
)


class Engine:
    def __init__(self, hal: MockHal, persist_path: Path | None = None):
        self._hal = hal
        self._persist_path = persist_path
        self._program_dict: dict[str, Any] | None = None
        self._program_id: str | None = None
        self._cycle_ms: int | None = None
        self._blocks: dict[str, Block] = {}
        self._order: list[str] = []
        self._wires: list[tuple[str, str]] = []
        self._values: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def deploy(self, program_dict: dict[str, Any]) -> None:
        was_running = False
        with self._lock:
            was_running = self._running
            if self._running:
                self._stop_unlocked()

            program = parse_program(program_dict)
            known = set(REGISTRY.keys())
            if not known:
                raise ProgramValidationError("no block types registered")
            hal_names = {c.name for c in self._hal.list_channels()}
            order = validate_and_order(program, known, hal_names)

            blocks: dict[str, Block] = {}
            for spec in program.blocks:
                cls = REGISTRY[spec.type]
                kwargs = dict(spec.params)
                if spec.type == "GpioOut":
                    blocks[spec.name] = cls(spec.name, hal=self._hal, **kwargs)
                else:
                    blocks[spec.name] = cls(spec.name, **kwargs)

            # seed param-backed inputs
            for name, block in blocks.items():
                params = program.blocks[
                    next(i for i, b in enumerate(program.blocks) if b.name == name)
                ].params
                block.apply_params(params)

            self._blocks = blocks
            self._order = order
            self._wires = [(w.from_port, w.to_port) for w in program.wires]
            self._program_dict = program_dict
            self._program_id = program.id
            self._cycle_ms = program.cycle_ms
            self._values = {}

            # ensure master ports exist for wired destinations/sources
            for src, dst in self._wires:
                for p in (src, dst):
                    if p.startswith("master.") and p not in self._values:
                        self._values[p] = None

            if self._persist_path is not None:
                self._persist_path.parent.mkdir(parents=True, exist_ok=True)
                self._persist_path.write_text(json.dumps(program_dict, indent=2))

        if was_running:
            self.start()

    def load_persisted(self) -> bool:
        if self._persist_path is None or not self._persist_path.is_file():
            return False
        data = json.loads(self._persist_path.read_text())
        self.deploy(data)
        return True

    def start(self) -> None:
        with self._lock:
            if self._program_id is None:
                raise RuntimeError("no program deployed")
            if self._running:
                return
            self._stop_event.clear()
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, name="engine-cycle", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._stop_unlocked()

    def _stop_unlocked(self) -> None:
        self._running = False
        self._stop_event.set()
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            # release lock while joining
            self._lock.release()
            try:
                thread.join(timeout=2.0)
            finally:
                self._lock.acquire()

    def set_master_port(self, name: str, value: float | bool) -> None:
        if not name.startswith("master."):
            name = f"master.{name}"
        with self._lock:
            self._values[name] = value

    def set_hal_channel(self, name: str, value: float | bool) -> None:
        self._hal.set(name, value)

    def snapshot(self) -> dict[str, float | bool | None]:
        with self._lock:
            out: dict[str, float | bool | None] = dict(self._values)
            for ch in self._hal.list_channels():
                out[ch.name] = self._hal.get(ch.name)
            for bname, block in self._blocks.items():
                for oname in block.outputs:
                    out[f"{bname}.{oname}"] = block.get_output(oname)
                for iname in block.inputs:
                    key = f"{bname}.{iname}"
                    if key not in out:
                        out[key] = block.get_input(iname)
            return out

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "program_id": self._program_id,
                "cycle_ms": self._cycle_ms,
            }

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                self._cycle_once()
            except Exception:
                # hold last outputs; keep looping
                pass
            elapsed = time.monotonic() - started
            with self._lock:
                period = (self._cycle_ms or 100) / 1000.0
            remaining = period - elapsed
            if remaining > 0:
                self._stop_event.wait(remaining)

    def _cycle_once(self) -> None:
        with self._lock:
            # HAL sources into values
            for ch in self._hal.list_channels():
                if ch.direction == "input":
                    self._values[ch.name] = self._hal.get(ch.name)

            # propagate wires then cycle blocks in order
            # First apply all wires whose sources are already known, iterating topo
            for bname in self._order:
                block = self._blocks[bname]
                # apply incoming wires to this block
                for src, dst in self._wires:
                    if not dst.startswith(f"{bname}."):
                        continue
                    if src not in self._values:
                        continue
                    port = dst.split(".", 1)[1]
                    block.set_input(port, self._values[src])

                block.cycle()

                for oname in block.outputs:
                    self._values[f"{bname}.{oname}"] = block.get_output(oname)

            # second pass: wires from blocks to other sinks (HAL already via GpioOut)
            for src, dst in self._wires:
                if src in self._values and dst.startswith("master."):
                    # do not overwrite master from graph in v1
                    continue
                if src in self._values and not dst.startswith("hal."):
                    # block inputs already applied above
                    pass
