/* helper: convert seconds → “Xd Yh Zm” */
function fmtUptime(sec) {
  const d = Math.floor(sec / 86400);
  const h = Math.floor((sec % 86400) / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return `${d}d ${h}h ${m}m`;
}

/* helper: UNIX-string → locale date-time */
function fmtTs(str) {
  if (!str) return 'n/a';
  return new Date(parseFloat(str) * 1000).toLocaleString();
}

async function refresh() {
  try {
    const res = await fetch('/api/latest');
    const data = await res.json();

    /* ---------- status block ---------- */
    const hb = data.status || {};
    const onboard = data.onboard_temperature?.value;
    const statusUl = document.getElementById('status');
    const lastSeen = hb.db_timestamp
      ? new Date(hb.db_timestamp).toLocaleString()
      : 'n/a';

    statusUl.innerHTML = `
      <li class="list-group-item"><strong>Status:</strong> ${hb.status ?? '—'}</li>
      <li class="list-group-item"><strong>Uptime:</strong> ${hb.uptime ? fmtUptime(hb.uptime) : '—'}</li>
      <li class="list-group-item"><strong>Onboard Temp:</strong> ${
        onboard !== undefined ? `${onboard.toFixed(1)} °F` : '—'
      }</li>
      <li class="list-group-item"><strong>Last Heartbeat:</strong> ${lastSeen}</li>
    `;

    /* ---------- environment temp ---------- */
    const envVal = data.environment_temperature?.value;
    document.getElementById('env').textContent =
      envVal !== undefined ? `${envVal.toFixed(1)} °F` : '—';

    /* ---------- rainfall ---------- */
    document.getElementById('rain').textContent =
      `${data.rainfall_24h_in}" in last 24 h`;
  } catch (err) {
    console.error(err);
  }
}

refresh();
setInterval(refresh, 60_000);
