"""
Micropython script to read sensor data and publish it to an MQTT broker.
"""

import gc
import network
import time
import ujson
from umqtt.simple import MQTTClient
from machine import Pin, ADC

# Global variables
unsent_messages = []
led = machine.Pin("LED", machine.Pin.OUT)
chg_pin = Pin(15, Pin.IN, Pin.PULL_UP)
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


def format_precise_timestamp(precise_timestamp: str) -> str:
    seconds, millis = map(int, precise_timestamp.split("."))
    local_time = time.localtime(seconds)
    return (
        f"{local_time[0]:04d}-{local_time[1]:02d}-{local_time[2]:02d} "
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


def read_chg_pin():
    return chg_pin.value()
    

def rainfall_handler(pin: int) -> list:
    """
    ISR for the tipping bucket sensor. Buffers a message for each tip.
    """
    try:
        rainfall_timestamps.append(get_precise_timestamp())
    except:
        pass  # Avoid crashing on memory errors or overflow



def publish_messages(client: MQTTClient) -> None:
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


def check_and_append_change(function, topic, timestamp, prior_value=None, change_threshold=None):
    """
    Check if the value of the pin has changed. If it has, append the change to unsent_messages.
    """
    current_value = function()

    if prior_value is None or current_value != prior_value:
        message = ujson.dumps({"timestamp": timestamp, "value": current_value})
        unsent_messages.append((topic, message))
        return current_value

    if change_threshold is not None:
        try:
            if abs(current_value - prior_value) >= change_threshold:
                message = ujson.dumps({"timestamp": timestamp, "value": current_value})
                unsent_messages.append((topic, message))
                return current_value
        except TypeError:
            pass
    elif current_value != prior_value:
        # Fall back to basic equality
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
        client.publish("rain_gauge_1/status", message)
        print(f"Published status: {message}")
    except Exception as e:
        print("Failed to publish status:", e)


def publish_boot_status(client):
    message = ujson.dumps({
        "timestamp": get_precise_timestamp(),
        "status": "boot",
        "reason": "power_on"
    })
    try:
        client.publish("rain_gauge_1/status/boot", message)
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
        client.publish("rain_gauge_1/status/heartbeat", message)
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

    pgood_pin = Pin(16, Pin.IN, Pin.PULL_UP)

    prior_temperature_value = None
    prior_charge_value = None
    
    heartbeat_interval = 300  # seconds
    last_heartbeat_time = time.time()

    try:
        while True:
            timestamp = get_precise_timestamp()

            if time.time() - last_heartbeat_time >= heartbeat_interval:
                publish_heartbeat(client)
                last_heartbeat_time = time.time()

            while rainfall_timestamps:
                ts = rainfall_timestamps.pop(0)  # Remove the oldest timestamp
                message = ujson.dumps({"timestamp": ts})
                unsent_messages.append(("rain_gauge_1/sensors/rain_gauge_tips", message))
                print(f"Bucket tip recorded at {format_precise_timestamp(ts)}")

            prior_temperature_value = check_and_append_change(read_onboard_temperature, "rain_gauge_1/sensors/temperature", timestamp, prior_temperature_value, 1.0)

            prior_charge_value = check_and_append_change(read_chg_pin, "rain_gauge_1/sensors/charge_value", timestamp, prior_charge_value)
            
            if client is None:
                client = connect_mqtt(mqtt_broker_ip, mqtt_broker_port, mqtt_client_id)
                if client:
                    publish_boot_status(client)

            if not client:
                print("MQTT not connected — skipping publish cycle")
                time.sleep(5)
                continue

            publish_messages(client)
    
            blink_led()
            time.sleep(5)  # Wait before the next cycle
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        if client:
            publish_status(client, reason="shutdown")
            client.disconnect()

# Run the main function
if __name__ == "__main__":
    main()
