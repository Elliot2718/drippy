# api_server.py
from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)
DB_PATH = "drippy.db"

@app.route("/latest")
def latest_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT topic, payload, timestamp FROM mqtt_log ORDER BY timestamp DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([
            {"topic": r[0], "payload": r[1], "timestamp": r[2]} for r in rows
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🌐 Starting API server on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000)
