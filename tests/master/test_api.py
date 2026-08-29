from fastapi.testclient import TestClient

from brew_master.api import create_app


class FakeController:
    def state(self):
        return {
            "mode": "manual",
            "enabled": False,
            "setpoint_c": 66.0,
            "worker": {"online": False, "stale": True, "status": None, "last_telemetry": {}},
        }

    def ensure_sample_deployed(self):
        return None

    def set_manual(self, *, enabled, setpoint_c):
        self.enabled = enabled
        self.setpoint_c = setpoint_c

    def inject_temp(self, temp_c):
        self.temp_c = temp_c


def test_health():
    app = create_app(controller=FakeController(), start_supervisor=False)
    client = TestClient(app)
    assert client.get("/api/health").json()["ok"] is True


def test_manual_and_mock_endpoints():
    ctl = FakeController()
    app = create_app(controller=ctl, start_supervisor=False)
    client = TestClient(app)
    r = client.post("/api/manual", json={"enabled": True, "setpoint_c": 70.0})
    assert r.status_code == 200
    assert ctl.enabled is True
    assert ctl.setpoint_c == 70.0
    r = client.post("/api/mock/temp", json={"temp_c": 55.5})
    assert r.status_code == 200
    assert ctl.temp_c == 55.5
