from __future__ import annotations

import threading
import time
from typing import Any

import grpc

from brew_master.grpc_client import WorkerClient


class WorkerSupervisor:
    def __init__(self, target: str = "127.0.0.1:50051", reconnect_s: float = 2.0):
        self._target = target
        self._reconnect_s = reconnect_s
        self._client = WorkerClient(target)
        self._lock = threading.RLock()
        self._online = False
        self._stale = True
        self._status: dict[str, Any] | None = None
        self._last_telemetry: dict[str, Any] = {}
        self._last_error: str | None = None
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        self._stop.clear()
        t1 = threading.Thread(target=self._reconnect_loop, name="ws-reconnect", daemon=True)
        t2 = threading.Thread(target=self._telemetry_loop, name="ws-telemetry", daemon=True)
        self._threads = [t1, t2]
        t1.start()
        t2.start()

    def stop(self) -> None:
        self._stop.set()
        try:
            self._client.close()
        except Exception:
            pass
        for t in self._threads:
            t.join(timeout=2.0)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "online": self._online,
                "stale": self._stale,
                "status": dict(self._status) if self._status else None,
                "last_telemetry": dict(self._last_telemetry),
                "last_error": self._last_error,
                "target": self._target,
            }

    def client(self) -> WorkerClient:
        return self._client

    def _mark_offline(self, err: str) -> None:
        with self._lock:
            self._online = False
            self._stale = True
            self._last_error = err

    def _reconnect_loop(self) -> None:
        while not self._stop.is_set():
            try:
                if not self._client.connected:
                    self._client.connect()
                st = self._client.get_status()
                with self._lock:
                    self._online = True
                    self._status = st
                    self._last_error = None
            except grpc.RpcError as e:
                self._mark_offline(str(e))
                try:
                    self._client.close()
                except Exception:
                    pass
            except Exception as e:
                self._mark_offline(str(e))
                try:
                    self._client.close()
                except Exception:
                    pass
            self._stop.wait(self._reconnect_s)

    def _telemetry_loop(self) -> None:
        while not self._stop.is_set():
            if not self._client.connected:
                self._stop.wait(0.5)
                continue
            try:
                for frame in self._client.telemetry_stream(hz=5):
                    if self._stop.is_set():
                        break
                    with self._lock:
                        self._online = True
                        self._stale = False
                        self._last_telemetry = frame.get("values", {})
            except grpc.RpcError as e:
                self._mark_offline(str(e))
                try:
                    self._client.close()
                except Exception:
                    pass
                self._stop.wait(0.5)
            except Exception as e:
                self._mark_offline(str(e))
                self._stop.wait(0.5)
