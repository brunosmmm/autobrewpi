from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from brew_master.brewday import BrewDayController
from brew_master.supervisor import WorkerSupervisor

WEB_ROOT = Path(__file__).resolve().parents[4] / "web"


class ManualBody(BaseModel):
    enabled: bool
    setpoint_c: float


class MockTempBody(BaseModel):
    temp_c: float


def create_app(
    controller: BrewDayController | None = None,
    worker_target: str = "127.0.0.1:50051",
    start_supervisor: bool = True,
) -> FastAPI:
    if controller is None:
        supervisor = WorkerSupervisor(worker_target)
        if start_supervisor:
            supervisor.start()
        controller = BrewDayController(supervisor)

    app = FastAPI(title="brew-master")
    app.state.controller = controller

    @app.get("/api/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/state")
    def state() -> dict[str, Any]:
        return controller.state()

    @app.get("/api/operator/state")
    def operator_state() -> dict[str, Any]:
        return controller.operator_state()

    @app.post("/api/operator/ensure-graph")
    def ensure_graph() -> dict[str, Any]:
        try:
            controller.ensure_graph()
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
        return controller.operator_state()

    @app.post("/api/operator/session/start")
    def session_start() -> dict[str, Any]:
        try:
            controller.session_start()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return controller.operator_state()

    @app.post("/api/operator/session/stop")
    def session_stop() -> dict[str, Any]:
        controller.session_stop()
        return controller.operator_state()

    @app.post("/api/operator/session/pause")
    def session_pause() -> dict[str, Any]:
        controller.session_pause()
        return controller.operator_state()

    @app.post("/api/operator/session/resume")
    def session_resume() -> dict[str, Any]:
        controller.session_resume()
        return controller.operator_state()

    @app.post("/api/operator/session/advance")
    def session_advance() -> dict[str, Any]:
        try:
            controller.session_advance()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return controller.operator_state()

    @app.post("/api/deploy/sample")
    def deploy_sample() -> dict[str, Any]:
        controller.ensure_sample_deployed()
        return controller.state()

    @app.post("/api/manual")
    def manual(body: ManualBody) -> dict[str, Any]:
        try:
            controller.set_manual(enabled=body.enabled, setpoint_c=body.setpoint_c)
        except RuntimeError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        return controller.state()

    @app.post("/api/mock/temp")
    def mock_temp(body: MockTempBody) -> dict[str, Any]:
        controller.inject_temp(body.temp_c)
        return controller.state()

    @app.websocket("/ws/telemetry")
    async def ws_telemetry(ws: WebSocket) -> None:
        await ws.accept()
        try:
            while True:
                await ws.send_text(json.dumps(controller.state()))
                await asyncio.sleep(0.2)
        except WebSocketDisconnect:
            return

    if WEB_ROOT.is_dir():
        operator = WEB_ROOT / "operator.html"
        sim = WEB_ROOT / "sim.html"

        @app.get("/")
        def index_page() -> FileResponse:
            return FileResponse(operator if operator.is_file() else WEB_ROOT / "index.html")

        @app.get("/sim")
        def sim_page() -> FileResponse:
            return FileResponse(sim if sim.is_file() else WEB_ROOT / "index.html")

        app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")

    return app
