function $(id) {
  return document.getElementById(id);
}

function render(state) {
  const op = state.operator || {};
  const w = state.worker || {};
  const online = !!w.online;
  const stale = !!w.stale;
  $("banner").classList.toggle("hidden", online && !stale);

  $("session").innerHTML = [
    ["phase", op.phase],
    ["stage", `${op.stage_index ?? "—"} ${op.stage_label || ""}`.trim()],
    ["stage_status", op.stage_status],
    ["timer_end", op.timer_end || "—"],
    ["setpoint", op.desired_setpoint],
    ["heat_enable", op.desired_enable],
    ["graph_ready", op.graph_ready],
    ["worker_online", online],
    ["stale", stale],
  ]
    .map(([k, v]) => `<dt>${k}</dt><dd>${v === undefined || v === null ? "—" : v}</dd>`)
    .join("");

  const stages = op.stages || [];
  $("stages").innerHTML = stages
    .map((s, i) => {
      const cur = i === op.stage_index ? " class=\"current\"" : "";
      return `<li${cur}>${s.label} <span class="muted">(${s.type}${
        s.target_temp != null ? `, ${s.target_temp}°C` : ""
      }${s.time_min != null ? `, ${s.time_min} min` : ""})</span></li>`;
    })
    .join("");

  const t = w.last_telemetry || {};
  $("live").innerHTML = [
    ["temp_c", op.current_temp ?? t["hal.adc.temp_c"]],
    ["heater", t["hal.gpio.heater_hlt"]],
    ["Hyst.CtlOut", t["Hyst.CtlOut"]],
    ["program", (w.status && w.status.program_id) || "—"],
  ]
    .map(([k, v]) => `<dt>${k}</dt><dd>${v === undefined || v === null ? "—" : v}</dd>`)
    .join("");
}

async function post(path) {
  const res = await fetch(path, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

$("btn-ensure").onclick = async () => render(await post("/api/operator/ensure-graph"));
$("btn-start").onclick = async () => render(await post("/api/operator/session/start"));
$("btn-pause").onclick = async () => render(await post("/api/operator/session/pause"));
$("btn-resume").onclick = async () => render(await post("/api/operator/session/resume"));
$("btn-advance").onclick = async () => render(await post("/api/operator/session/advance"));
$("btn-stop").onclick = async () => render(await post("/api/operator/session/stop"));

const ws = new WebSocket(
  `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/telemetry`
);
ws.onmessage = (ev) => {
  try {
    render(JSON.parse(ev.data));
  } catch (_) {}
};

fetch("/api/operator/state")
  .then((r) => r.json())
  .then(render)
  .catch(console.error);
