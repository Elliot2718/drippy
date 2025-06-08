import json, sqlite3, os
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, jsonify

DB = os.path.expanduser("~/drippy.db")  # /home/elliot.wargo/drippy.db
TIP_PER_INCH = 150

app = Flask(__name__)

def _query_one(topic):
    """Return latest payload JSON + DB insert time for a topic."""
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        "SELECT payload, timestamp FROM mqtt_log "
        "WHERE topic=? ORDER BY timestamp DESC LIMIT 1",
        (topic,),
    )
    row = cur.fetchone()
    con.close()
    if not row:
        return None
    payload = json.loads(row[0])
    db_ts = datetime.fromisoformat(row[1]).replace(tzinfo=timezone.utc)
    return payload, db_ts

def _count_tips(since_utc):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM mqtt_log "
        "WHERE topic='rain_gauge_station/sensor/rain_gauge_tips' "
        "AND timestamp>=?",
        (since_utc.isoformat(timespec='seconds'),),
    )
    count = cur.fetchone()[0]
    con.close()
    return count

@app.route("/api/latest")
def api_latest():
    now = datetime.now(timezone.utc)

    hb, hb_db_ts = _query_one("rain_gauge_station/status/heartbeat") or ({}, None)
    onboard, _ = _query_one("rain_gauge_station/sensor/onboard_temperature") or ({}, None)
    env, _ = _query_one("rain_gauge_station/sensor/temperature") or ({}, None)

    # Rainfall last 24 h
    cutoff = now - timedelta(hours=24)
    tips = _count_tips(cutoff)
    rainfall_in = tips / TIP_PER_INCH

    return jsonify(
        status={
            **hb,
            "db_timestamp": hb_db_ts.isoformat() if hb_db_ts else None,
        },
        onboard_temperature=onboard,
        environment_temperature=env,
        rainfall_24h_in=round(rainfall_in, 3),
        generated_at=now.isoformat(),
    )

@app.route("/")
def index():
    return render_template("index.html")

# --- start the server when launched directly -------------------
if __name__ == "__main__":
    # 0.0.0.0 makes it reachable from other machines;
    # remove "port=5000" if you’re happy with Flask’s default (also 5000)
    app.run(host="0.0.0.0", port=5000)
