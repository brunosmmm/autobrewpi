from datetime import datetime, timedelta

from brew_master.mash_session import MashSession, Stage


class RecWriter:
    def __init__(self):
        self.ports = {}

    def set_port(self, name, value):
        self.ports[name] = value


def test_idle_to_preheat_to_ack_waiting():
    sess = MashSession(
        [
            Stage("preheat", "Preheat", target_temp=72.0),
            Stage("ack", "Confirm"),
            Stage("idle", "Done"),
        ],
        temp_tolerance_c=0.5,
    )
    w = RecWriter()
    sess.start()
    sess.apply_outputs(w)
    assert sess.phase == "active"
    assert sess.stage_status == "running"
    assert w.ports["master.Hyst.Enabled"] is True
    assert w.ports["master.Hyst.SetPoint"] == 72.0

    sess.tick(worker_online=True, current_temp=72.0)
    sess.apply_outputs(w)
    assert sess.stage_status == "waiting_ack"
    assert w.ports["master.Hyst.Enabled"] is False

    sess.advance()
    assert sess.current_stage.type == "ack"
    assert sess.stage_status == "waiting_ack"


def test_timed_completes_to_next():
    sess = MashSession(
        [
            Stage("timed", "Short", target_temp=66.0, time_min=0.0),
            Stage("idle", "Done"),
        ]
    )
    sess.start()
    # force timer already expired
    sess._timer_end = datetime.now() - timedelta(seconds=1)
    sess.tick(worker_online=True, current_temp=66.0)
    assert sess.phase == "finished"
    assert sess.current_stage.type == "idle"


def test_pause_clears_enable():
    sess = MashSession([Stage("preheat", "P", target_temp=70.0), Stage("idle", "Done")])
    w = RecWriter()
    sess.start()
    sess.pause()
    sess.apply_outputs(w)
    assert sess.phase == "paused"
    assert w.ports["master.Hyst.Enabled"] is False
    sess.resume()
    sess.apply_outputs(w)
    assert sess.phase == "active"
    assert w.ports["master.Hyst.Enabled"] is True


def test_tick_frozen_when_offline():
    sess = MashSession(
        [Stage("preheat", "P", target_temp=70.0), Stage("idle", "Done")],
        temp_tolerance_c=0.5,
    )
    sess.start()
    sess.tick(worker_online=False, current_temp=70.0)
    assert sess.stage_status == "running"
