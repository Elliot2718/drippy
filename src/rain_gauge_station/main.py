"""
Micropython script to read sensor data and publish it to an MQTT broker.
"""

import gc
import network
import time
import ujson
from umqtt.simple import MQTTClient
from machine import Pin, ADC

from sensor.onboard_temperature import read_onboard_temperature
from sensor.temperature import read_temperature

# Global variables
unsent_messages = []
led = machine.Pin("LED", machine.Pin.OUT)
temperature_pin = 26
rainfall_timestamps = []

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


def connect_mqtt(broker_ip, port, client_id, user, password, retries=10, delay=3):
    for attempt in range(retries):
        try:
            client = MQTTClient(client_id, broker_ip, port=port, user=user, password=password)
            client.connect()
            print(f"✅ Connected to MQTT Broker at {broker_ip}:{port}")
            return client
        except Exception as e:
            print(f"❌ MQTT connect failed (attempt {attempt+1}/{retries}): {e}")
            time.sleep(delay)
    return None


def get_precise_timestamp() -> str:
    """
    Get the current timestamp with milliseconds.
    """
    unix_time = time.time()
    millis = time.ticks_ms() % 1000
    return f"{unix_time:.0f}.{millis:03d}"


def format_precise_timestamp(precise_timestamp: str) -> str:
    seconds, millis = map(int, precise_timestamp.split("."))
    local_time = time.localtime(seconds)
    return (
        f"{local_time[0]:04d}-{local_time[1]:02d}-{local_time[2]:02d} "
        f"{local_time[3]:02d}:{local_time[4]:02d}:{local_time[5]:02d}.{millis:03d}"
    )


def rainfall_handler(pin: int) -> list:
    """
    ISR for the tipping bucket sensor. Buffers a message for each tip.
    """
    try:
        rainfall_timestamps.append(get_precise_timestamp())
    except:
        pass  # Avoid crashing on memory errors or overflow


def publish_messages() -> None:
    """
    Publish all unsent messages to MQTT, continuing even if some fail.
    """
    if not unsent_messages:
        return

    global client  # so we can reset it if needed

    for index, (topic, message) in enumerate(unsent_messages[:]):
        try:
            client.publish(topic, message)
            print(f"[{index + 1}] Published to {topic}: {message}")
            unsent_messages.remove((topic, message))
        except Exception as e:
            print(f"[{index + 1}] Failed to publish {message} to {topic}: {e}")
            client = None  # force reconnect
            break


def check_and_append_change(current_value, topic, timestamp, prior_value=None, change_threshold=None):
    if prior_value is None:
        message = ujson.dumps({"timestamp": timestamp, "value": current_value})
        unsent_messages.append((topic, message))
        return current_value

    if change_threshold is not None:
        if abs(current_value - prior_value) >= change_threshold:
            message = ujson.dumps({"timestamp": timestamp, "value": current_value})
            unsent_messages.append((topic, message))
            return current_value
    elif current_value != prior_value:
        message = ujson.dumps({"timestamp": timestamp, "value": current_value})
        unsent_messages.append((topic, message))
        return current_value

    return prior_value


def publish_status(client, reason="ok"):
    message = ujson.dumps({
        "timestamp": get_precise_timestamp(),
        "status": reason,
        "uptime": time.ticks_ms() // 1000
    })
    try:
        client.publish("rain_gauge_station/status", message)
        print(f"Published status: {message}")
    except Exception as e:
        print("Failed to publish status:", e)


def publish_boot_status():
    global client
    message = ujson.dumps({
        "timestamp": get_precise_timestamp(),
        "status": "boot",
        "reason": "power_on"
    })
    try:
        client.publish("rain_gauge_station/status/boot", message)
        print("Published boot status.")
    except Exception as e:
        print("Failed to publish boot status:", e)


def publish_heartbeat(client):
    message = ujson.dumps({
        "timestamp": get_precise_timestamp(),
        "status": "ok",
        "uptime": time.ticks_ms() // 1000,
        "heap_free": gc.mem_free()
    })
    try:
        client.publish("rain_gauge_station/status/heartbeat", message)
        print("Published heartbeat.")
    except Exception as e:
        print("Failed to publish heartbeat:", e)


def blink_led():
    """
    Toggle the state of the onboard LED.
    """
    led.value(True)
    time.sleep(0.1)
    led.value(False)


def main():
    """
    Main loop to handle Wi-Fi connection, MQTT publishing, and tipping bucket data.
    """
    env_vars = load_env()
    print("ENV VARS:", env_vars)
    wifi_ssid = env_vars.get("WIFI_SSID")
    wifi_password = env_vars.get("WIFI_PASSWORD")
    mqtt_broker_ip = env_vars.get("MQTT_BROKER_IP")
    mqtt_broker_port = int(env_vars.get("MQTT_BROKER_PORT"))
    mqtt_client_id = env_vars.get("MQTT_CLIENT_ID")
    mqtt_username = env_vars.get("MQTT_USERNAME")
    mqtt_password = env_vars.get("MQTT_PASSWORD")

    if not connect_wifi(wifi_ssid=wifi_ssid, wifi_password=wifi_password):
        print("Failed to connect to Wi-Fi.")
        return

    global client, boot_sent
    client = None
    boot_sent = False

    # Set up tipping bucket interrupt
    tipping_bucket = Pin(16, Pin.IN, Pin.PULL_UP)
    tipping_bucket.irq(trigger=Pin.IRQ_FALLING, handler=rainfall_handler)

    prior_onboard_temperature_value = None
    prior_temperature_value = None

    heartbeat_interval = 300  # seconds
    last_heartbeat_time = time.time()

    try:
        while True:
            timestamp = get_precise_timestamp()

            # Send heartbeat
            if time.time() - last_heartbeat_time >= heartbeat_interval:
                if client:
                    publish_heartbeat(client)
                last_heartbeat_time = time.time()

            # Drain rainfall events
            while rainfall_timestamps:
                ts = rainfall_timestamps.pop(0)
                message = ujson.dumps({"timestamp": ts})
                unsent_messages.append(("rain_gauge_station/sensor/rain_gauge_tips", message))
                print(f"Bucket tip recorded at {format_precise_timestamp(ts)}")

            # Read temperatures
            current_onboard_temp = read_onboard_temperature()
            current_temp = read_temperature(pin=temperature_pin)

            prior_onboard_temperature_value = check_and_append_change(
                current_onboard_temp,
                "rain_gauge_station/sensor/onboard_temperature",
                timestamp,
                prior_onboard_temperature_value,
                change_threshold=1.0
            )

            prior_temperature_value = check_and_append_change(
                current_temp,
                "rain_gauge_station/sensor/temperature",
                timestamp,
                prior_temperature_value,
                change_threshold=0.25
            )

            if client is None:
                client = client = connect_mqtt(mqtt_broker_ip, mqtt_broker_port, mqtt_client_id, mqtt_username, mqtt_password)
                if client and not boot_sent:
                    publish_boot_status()
                    boot_sent = True

            publish_messages()


            blink_led()
            time.sleep(5)

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        if client:
            publish_status(client, reason="shutdown")
            client.disconnect()


# Run the main function
if __name__ == "__main__":
    main()