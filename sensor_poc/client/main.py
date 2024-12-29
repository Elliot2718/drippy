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
    Load environment variables from a .env file.
    The .env file should contain key-value pairs in the format:
    KEY=value
    Comments are allowed using the '#' character.
    """
    env_vars = {}
    try:
        with open(file_path, "r") as file:
            for line in file:
                # Strip whitespace and skip empty lines
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Remove inline comments
                line = line.split("#", 1)[0].strip()
                
                # Parse the key-value pair
                if "=" in line:  # Ensure valid key-value format
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    except OSError:
        print(f"Warning: {file_path} not found.")
    return env_vars


def connect_wifi(wifi_ssid: str, wifi_password: str) -> bool:
    """
    Connect to a WiFi network using the credentials provided in the .env file.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(wifi_ssid, wifi_password)
    
    max_retries = 10  # Maximum number of retries
    retry_count = 0
    
    print("Connecting to WiFi...")
    
    while not wlan.isconnected():
        time.sleep(1)
        retry_count += 1
        print(f"Retry {retry_count}/{max_retries}...")
        
        if retry_count >= max_retries:
            print("Failed to connect to WiFi. Please check your credentials or network.")
            return False  # Return False if connection fails
    
    print("Connected to WiFi:", wlan.ifconfig())
    return True  # Return True if connection succeeds


def connect_mqtt(broker_ip, port, client_id):
    """
    Creates and connects an MQTT client to the broker.

    Args:
        broker_ip (str): IP address of the MQTT broker.
        port (int): Port number for the MQTT connection.
        client_id (str): Unique client ID for the MQTT connection.

    Returns:
        MQTTClient: Connected MQTT client instance.

    Raises:
        RuntimeError: If the client fails to connect.
    """
    try:
        # Create the MQTT client
        client = MQTTClient(client_id, broker_ip, port=port)
        # Connect to the broker
        client.connect()
        print(f"Connected to MQTT Broker at {broker_ip}:{port} with Client ID '{client_id}'")
        return client
    except Exception as e:
        # Handle connection failure
        print(f"Error: Failed to connect to MQTT Broker at {broker_ip}:{port}.")
        print(f"Details: {e}")
        raise RuntimeError("Failed to connect to MQTT broker.") from e


def get_precise_timestamp():
    # Current Unix timestamp in seconds
    unix_time = time.time()
    # Current milliseconds within the second
    millis = time.ticks_ms() % 1000
    # Combine seconds and milliseconds
    return f"{unix_time}.{millis:03d}"


def format_precise_timestamp(precise_timestamp):
    """
    Converts a precise timestamp (seconds.milliseconds) into a human-readable timestamp.
    
    Args:
        precise_timestamp (str or float): Precise Unix timestamp (e.g., "1672531200.123" or 1672531200.123).
    
    Returns:
        str: Human-readable timestamp in the format YYYY-MM-DD HH:MM:SS.mmm
    """
    # Handle float input
    if isinstance(precise_timestamp, float):
        seconds = int(precise_timestamp)  # Extract the seconds part
        millis = int((precise_timestamp - seconds) * 1000)  # Extract the milliseconds part
    # Handle string input
    elif isinstance(precise_timestamp, str):
        seconds, millis = precise_timestamp.split(".")
        seconds = int(seconds)
        millis = int(millis)
    else:
        raise ValueError("Input must be a string or float representing the precise timestamp.")
    
    # Convert the seconds part to a human-readable format
    local_time = time.localtime(seconds)
    formatted_time = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}.{:03d}".format(
        local_time[0],  # Year
        local_time[1],  # Month
        local_time[2],  # Day
        local_time[3],  # Hour
        local_time[4],  # Minute
        local_time[5],  # Second
        millis          # Milliseconds
    )
    return formatted_time


def publish_with_retries(client, topic, message):
    """
    Attempts to publish a message. If it fails, stores the message in the buffer for retry.
    """
    global message_buffer
    try:
        client.publish(topic, message)
        print(f"Published to {topic}: {message}")
    except Exception as e:
        print(f"Publish failed: {e}. Adding message to buffer.")
        message_buffer.append((topic, message))


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
    unsent_messages.append(("sensor/bucket_tip", message))
    print(f"Bucket tip at {format_precise_timestamp(timestamp)}")


def publish_messages(client):
    """
    Retries publishing all messages, continuing even if some fail.
    """
    global unsent_messages
    if not unsent_messages:
        return

    total_messages = len(unsent_messages)
    print(f"Publishing {total_messages} messages...")
    for index, (topic, message) in enumerate(unsent_messages[:]):  # Iterate over a copy of the buffer
        try:
            client.publish(topic, message)
            print(f"Successfully published message {index + 1} of {total_messages}: {message} to topic {topic}.")
            unsent_messages.remove((topic, message))  # Remove successfully published message
        except Exception as e:
            print(f"Failed to publish message {index + 1}: {message} to {topic}: {e}")
            # Do not break; continue trying to send other messages
    print(f"Done attempting to publish {total_messages} messages.")


def main():
    global last_published_onboard_temperature, client
    
    env_vars = load_env()
    wifi_ssid = env_vars.get("WIFI_SSID")
    wifi_password = env_vars.get("WIFI_PASSWORD")
    mqtt_broker_ip = env_vars.get("MQTT_BROKER_IP")
    mqtt_broker_port = int(env_vars.get("MQTT_BROKER_PORT"))
    mqtt_client_id = env_vars.get("MQTT_CLIENT_ID")

    if not connect_wifi(wifi_ssid=wifi_ssid, wifi_password=wifi_password):
        print("Failed to connect to Wi-Fi. Exiting.")
        return

    client = None

    # Set up the tipping bucket interrupt
    tipping_bucket = Pin(22, Pin.IN, Pin.PULL_UP)
    tipping_bucket.irq(trigger=Pin.IRQ_FALLING, handler=rainfall_handler)

    
    try:
        while True:
            if client is None:
                try:
                    client = connect_mqtt(mqtt_broker_ip, mqtt_broker_port, mqtt_client_id)
                except Exception as e:
                    print(e)
            elif client:
                publish_messages(client)

            time.sleep(5)  # Wait before the next cycle
    except KeyboardInterrupt:
        print("Stopping sensors...")
    finally:
        client.disconnect()

# Run the main function
if __name__ == "__main__":
    main()
