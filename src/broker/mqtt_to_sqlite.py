# mqtt_to_sqlite.py
import sqlite3
import paho.mqtt.client as mqtt
import os
from typing import Tuple

def load_env(file_path: str = ".env") -> None:
    try:
        with open(file_path, "r") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                line = line.split("#", 1)[0].strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"⚠️ Warning: {file_path} not found.")

def init_db(database: str) -> None:
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mqtt_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            payload TEXT NOT NULL,
            qos INTEGER,
            retain INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

def on_connect(client, userdata, flags, rc):
    print(f"✅ Connected to MQTT broker with result code {rc}")
    if rc == 0:
        print("🔔 Subscribing to all topics: #")
        client.subscribe("#")

def on_message(client, userdata, msg):
    print("📥 on_message() triggered")
    try:
        topic = msg.topic
        payload = msg.payload.decode(errors='ignore')
        qos = msg.qos
        retain = int(msg.retain)

        print(f"📩 Received: {topic} {payload} (QoS={qos}, Retain={retain})")

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mqtt_log (topic, payload, qos, retain)
            VALUES (?, ?, ?, ?)
        """, (topic, payload, qos, retain))
        conn.commit()
        conn.close()
        print("✅ Inserted into database.")
    except Exception as e:
        print(f"❌ on_message() error: {e}")

def main() -> None:
    load_env()
    print("  MQTT_BROKER_IP:", os.environ.get("MQTT_BROKER_IP"))
    print("  MQTT_CLIENT_ID:", os.environ.get("MQTT_CLIENT_ID"))
    print("  MQTT_USERNAME:", os.environ.get("MQTT_USERNAME"))
    print("  MQTT_PASSWORD:", os.environ.get("MQTT_PASSWORD"))
    client_id = os.environ.get("MQTT_CLIENT_ID", "drippy_client")
    mqtt_broker = os.environ.get("MQTT_BROKER_IP", "localhost")
    port = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
    username = os.environ.get("MQTT_USERNAME")
    password = os.environ.get("MQTT_PASSWORD")
    DATABASE = os.path.expanduser(os.environ.get("DATABASE_PATH"))
    init_db(DATABASE)
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

    client.enable_logger()

    if username and password:
        client.username_pw_set(username, password)

    client.on_connect = on_connect
    client.on_message = on_message

    print("🚀 Starting MQTT logger...")
    client.connect(mqtt_broker, port, 60)
    print("🌀 Entering MQTT loop...")
    client.loop_forever()

if __name__ == "__main__":
    main()
