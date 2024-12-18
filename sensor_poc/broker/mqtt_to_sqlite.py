import sqlite3
import paho.mqtt.client as mqtt
import os

# Database setup
DATABASE = "sensor_data.db"
MQTT_TOPIC = "sensors/temperature"


def load_env(file_path=".env") -> None:
    """
    Load environment variables from a .env file and save them to os.environ.

    Args:
        file_path (str): Path to the .env file (default is ".env").
    """
    try:
        with open(file_path, "r") as file:
            for line in file:
                # Strip whitespace and skip empty lines or lines starting with #
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Remove inline comments
                line = line.split("#", 1)[0].strip()
                
                # Parse key-value pairs
                if "=" in line:  # Ensure valid key-value format
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Save to system environment variables
                    os.environ[key] = value
    except FileNotFoundError:
        print(f"Warning: {file_path} not found.")


def init_db(database: str) -> tuple:
    """
    Initialize the SQLite database and create the readings table if it doesn't exist.
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        topic TEXT,
                        value TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )""")
    conn.commit()
    return conn, cursor


def on_connect(client, userdata, flags, rc):
    """
    The callback for when the client receives a CONNACK response from the server.
    """
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    """
    The callback for when a PUBLISH message is received from the server.
    """
    value = msg.payload.decode()
    print(f"Received message: {value} on topic: {msg.topic}")
    cursor.execute("INSERT INTO readings (topic, value) VALUES (?, ?)", (msg.topic, value))
    conn.commit()
    print("Message saved to database")


def main():
    """
    Main function to run the MQTT subscriber and save messages to SQLite.
    """
    # Load environment variables
    load_env()

    # Initialize the database
    conn, cursor = init_db()

    # Set up the MQTT client
    client_id = os.environ.get("CLIENT_ID")
    mqtt_broker = os.environ.get("MQTT_BROKER")

    client = mqtt.Client(client_id=client_id)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(mqtt_broker, 1883, 60)  # Connect to the MQTT broker
        print("Listening for messages...")
        client.loop_forever()  # Keep the subscriber running
    except KeyboardInterrupt:
        print("Exiting...")
        conn.close()
        client.disconnect()

if __name__ == "__main__":
    main()
