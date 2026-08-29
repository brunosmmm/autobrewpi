function $(id) {
  return document.getElementById(id);
}

function renderState(state) {
  const w = state.worker || {};
  const online = !!w.online;
  const stale = !!w.stale;
  $("banner").classList.toggle("hidden", online && !stale);

  const st = w.status || {};
  $("worker-status").innerHTML = [
    ["online", online],
    ["stale", stale],
    ["program", st.program_id || "—"],
    ["running", st.running],
    ["target", w.target || "—"],
    ["error", w.last_error || "—"],
  ]
    .map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`)
    .join("");

  const t = w.last_telemetry || {};
  $("live").innerHTML = [
    ["temp_c", t["hal.adc.temp_c"]],
    ["heater", t["hal.gpio.heater_hlt"]],
    ["enabled", state.enabled],
    ["setpoint_c", state.setpoint_c],
    ["Hyst.CtlOut", t["Hyst.CtlOut"]],
  ]
    .map(([k, v]) => `<dt>${k}</dt><dd>${v === undefined || v === null ? "—" : v}</dd>`)
    .join("");
}

async function post(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

$("btn-deploy").onclick = async () => {
  renderState(await post("/api/deploy/sample", {}));
};

$("btn-temp").onclick = async () => {
  const temp_c = parseFloat($("temp").value);
  renderState(await post("/api/mock/temp", { temp_c }));
};

$("btn-manual").onclick = async () => {
  renderState(
    await post("/api/manual", {
      enabled: $("enabled").checked,
      setpoint_c: parseFloat($("setpoint").value),
    })
  );
};

const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/telemetry`);
ws.onmessage = (ev) => {
  try {
    renderState(JSON.parse(ev.data));
  } catch (_) {}
};

fetch("/api/state")
  .then((r) => r.json())
  .then(renderState)
  .catch(console.error);
