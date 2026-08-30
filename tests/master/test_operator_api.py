from pathlib import Path

from fastapi.testclient import TestClient

from brew_master.api import create_app
from brew_master.mash_session import MashSession, Stage


class FakeSupervisor:
    def __init__(self):
        self._online = True
        self._telem = {"hal.adc.temp_c": 50.0}
        self.client_obj = FakeClient(self)

    def start(self):
        pass

    def snapshot(self):
        return {
            "online": self._online,
            "stale": not self._online,
            "status": {"running": True, "program_id": "hlt-loop-v1", "cycle_ms": 100},
            "last_telemetry": dict(self._telem),
            "target": "fake",
            "last_error": None,
        }

    def client(self):
        return self.client_obj


class FakeClient:
    def __init__(self, sup: FakeSupervisor):
        self.sup = sup
        self.connected = True
        self.ports = {}
        self.hal = {}
        self.deployed = False

    def connect(self):
        self.connected = True

    def deploy_json(self, program):
        self.deployed = True
        return program.get("id", "x")

    def start(self):
        pass

    def get_status(self):
        return {"running": True, "program_id": "hlt-loop-v1", "cycle_ms": 100}

    def set_port(self, name, value):
        self.ports[name] = value

    def set_hal_channel(self, name, value):
        self.hal[name] = value
        self.sup._telem[name] = value


def _controller():
    from brew_master.brewday import BrewDayController

    stages = Path(__file__).resolve().parents[2] / "config/brewday/mash_stages_v1.json"
    sup = FakeSupervisor()
    ctl = BrewDayController(sup, stages_path=stages, tick_s=60.0)
    return ctl, sup


def test_operator_and_sim_pages():
    ctl, _ = _controller()
    app = create_app(controller=ctl, start_supervisor=False)
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert b"AutoBrew Operator" in r.content
    r = client.get("/sim")
    assert r.status_code == 200
    assert b"AutoBrew Sim" in r.content
    ctl.shutdown()


def test_operator_session_api():
    ctl, sup = _controller()
    app = create_app(controller=ctl, start_supervisor=False)
    client = TestClient(app)

    r = client.get("/api/operator/state")
    assert r.status_code == 200
    assert r.json()["operator"]["phase"] == "idle"

    r = client.post("/api/operator/ensure-graph")
    assert r.status_code == 200
    assert ctl._sup.client().deployed is True

    r = client.post("/api/operator/session/start")
    assert r.status_code == 200
    body = r.json()["operator"]
    assert body["phase"] == "active"
    assert body["stage_type"] == "preheat"
    assert sup.client_obj.ports.get("master.Hyst.Enabled") is True

    r = client.post("/api/operator/session/pause")
    assert r.json()["operator"]["phase"] == "paused"
    assert sup.client_obj.ports.get("master.Hyst.Enabled") is False

    r = client.post("/api/operator/session/resume")
    assert r.json()["operator"]["phase"] == "active"

    r = client.post("/api/operator/session/stop")
    assert r.json()["operator"]["phase"] == "idle"
    ctl.shutdown()


def test_health_still_ok():
    ctl, _ = _controller()
    app = create_app(controller=ctl, start_supervisor=False)
    assert TestClient(app).get("/api/health").json()["ok"] is True
    ctl.shutdown()
