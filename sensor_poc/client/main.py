"""
Micropython script to read sensor data and publish it to an MQTT broker.
"""

import network
import time
import ujson
from umqtt.simple import MQTTClient
from machine import Pin, ADC

# Global variables
unsent_messages = []


def load_env(file_path: str =".env") -> dict:
    """
    Load environment variables from a .env file in the format KEY=value.
    Supports comments using the '#' character.
    """
    env_vars = {}
    try:
        with open(file_path, "r") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, value = map(str.strip, line.split("=", 1))
                env_vars[key] = value
    except OSError:
        print(f"Warning: {file_path} not found.")
    return env_vars


def connect_wifi(wifi_ssid: str, wifi_password: str) -> bool:
    """
    Connect to a WiFi network.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(wifi_ssid, wifi_password)

    print("Connecting to WiFi...")
    for retry in range(10):
        if wlan.isconnected():
            print("Connected to WiFi:", wlan.ifconfig())
            return True
        print(f"Retry {retry + 1}/10...")
        time.sleep(1)

    print("Failed to connect to Wi-Fi.")
    return False


def connect_mqtt(broker_ip: str, port: int, client_id: str) -> MQTTClient:
    """
    Create and connect an MQTT client to the broker.
    """
    try:
        client = MQTTClient(client_id, broker_ip, port=port)
        client.connect()
        print(f"Connected to MQTT Broker at {broker_ip}:{port}")
        return client
    except Exception as e:
        print(f"Error: Could not connect to MQTT Broker at {broker_ip}:{port}. {e}")
        return None


def get_precise_timestamp() -> str:
    """
    Get the current timestamp with milliseconds.
    """
    unix_time = time.time()
    millis = time.ticks_ms() % 1000
    return f"{unix_time:.0f}.{millis:03d}"


def format_precise_timestamp(precise_timestamp) -> str:
    """
    Convert a precise timestamp (seconds.milliseconds) into a human-readable timestamp.
    """
    if isinstance(precise_timestamp, float):
        seconds = int(precise_timestamp)
        millis = int((precise_timestamp - seconds) * 1000)
    elif isinstance(precise_timestamp, str):
        seconds, millis = map(int, precise_timestamp.split("."))
    else:
        raise ValueError("Timestamp must be a string or float.")

    local_time = time.localtime(seconds)
    return (
        f"{local_time[0]:04d}-{local_time[1]:02d}-{local_time[2]:02d}"
        f"{local_time[3]:02d}:{local_time[4]:02d}:{local_time[5]:02d}.{millis:03d}"
    )


def read_onboard_temperature() -> float:
    """
    Reads the onboard temperature sensor and converts it to Fahrenheit.
    """
    adc = ADC(4)  # ADC Channel 4 for onboard temperature sensor
    raw_value = adc.read_u16()
    voltage = (raw_value / 65535) * 3.3  # Scale to 3.3V reference

    temperature_celsius = 27 - (voltage - 0.706) / 0.001721
    temperature_fahrenheit = (temperature_celsius * 9/5) + 32

    return round(temperature_fahrenheit, 2)


def rainfall_handler(pin):
    """
    ISR for the tipping bucket sensor. Buffers a message for each tip.
    """
    global unsent_messages
    timestamp = get_precise_timestamp()  # Record the current timestamp
    message = ujson.dumps({"timestamp": timestamp})
    unsent_messages.append(("sensor/rainfall", message))
    print(f"Bucket tip recorded at {format_precise_timestamp(timestamp)}")


def publish_messages(client: MQTTClient):
    """
    Publish all unsent messages to MQTT, continuing even if some fail.
    """
    if not unsent_messages:
        return

    for index, (topic, message) in enumerate(unsent_messages[:]):
        try:
            client.publish(topic, message)
            print(f"[{index + 1}] Published to {topic}: {message}")
            unsent_messages.remove((topic, message))
        except Exception as e:
            print(f"[{index + 1}] Failed to publish {message} to {topic}: {e}")


def main():
    """
    Main loop to handle Wi-Fi connection, MQTT publishing, and tipping bucket data.
    """
    env_vars = load_env()
    wifi_ssid = env_vars.get("WIFI_SSID")
    wifi_password = env_vars.get("WIFI_PASSWORD")
    mqtt_broker_ip = env_vars.get("MQTT_BROKER_IP")
    mqtt_broker_port = int(env_vars.get("MQTT_BROKER_PORT"))
    mqtt_client_id = env_vars.get("MQTT_CLIENT_ID")

    if not connect_wifi(wifi_ssid=wifi_ssid, wifi_password=wifi_password):
        print("Failed to connect to Wi-Fi.")
        return

    client = None
    tipping_bucket = Pin(22, Pin.IN, Pin.PULL_UP)
    tipping_bucket.irq(trigger=Pin.IRQ_FALLING, handler=rainfall_handler)
    
    try:
        while True:
            if client is None:
                client = connect_mqtt(mqtt_broker_ip, mqtt_broker_port, mqtt_client_id)

            if client:
                publish_messages(client)

            time.sleep(5)  # Wait before the next cycle
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        client.disconnect()

# Run the main function
if __name__ == "__main__":
    main()
