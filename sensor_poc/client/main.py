"""
Micropython script to read temperature sensor data and publish it to an MQTT broker.
"""

import network
import time
from umqtt.simple import MQTTClient
from machine import Pin, ADC


MQTT_TOPIC = "sensors/temperature"
CLIENT_ID = "pico_client"


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


def read_pico_temperature() -> float:
    adc = ADC(Pin(26))  # Analog pin for a temperature sensor

    # Example: Read analog sensor value
    raw_value = adc.read_u16()
    # Convert to a meaningful value (e.g., temperature in Celsius)
    temperature = (raw_value / 65535) * 100  # Example scaling
    return round(temperature, 2)


def main():
    # Load the .env file
    env_vars = load_env()

    wifi_ssid = env_vars.get("WIFI_SSID")
    wifi_password = env_vars.get("WIFI_PASSWORD")
    mqtt_broker_ip = env_vars.get("MQTT_BROKER_IP")

    # Connect to WiFi
    connect_wifi(wifi_ssid=wifi_ssid, wifi_password=wifi_password)

    # Connect to MQTT broker
    client = MQTTClient(CLIENT_ID, mqtt_broker_ip, port=1883)
    client.connect()
    print("Connected to MQTT Broker")

    try:
        while True:
            # Read sensor value
            temperature = read_pico_temperature()
            print("Temperature:", temperature)

            # Publish sensor reading
            client.publish(MQTT_TOPIC, str(temperature))
            print(f"Published to {MQTT_TOPIC}: {temperature}")

            # Wait for the next reading
            time.sleep(5)
    except KeyboardInterrupt:
        print("Disconnected")
        client.disconnect()

# Run the main function
main()
