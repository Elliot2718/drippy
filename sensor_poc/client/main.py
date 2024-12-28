"""
Micropython script to read sensor data and publish it to an MQTT broker.
"""

import network
import time
from umqtt.simple import MQTTClient
from machine import Pin, ADC


tip_count = 0
last_published_tip_count = 0


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
    client = MQTTClient(client_id, broker_ip, port=1883)
    client.connect()
    print("Connected to MQTT Broker")
    return client


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
    global tip_count
    tip_count += 1
    print(f"Number of tips: {tip_count}")


def main():
    global tip_count, last_published_tip_count
    
    env_vars = load_env()
    wifi_ssid = env_vars.get("WIFI_SSID")
    wifi_password = env_vars.get("WIFI_PASSWORD")
    mqtt_broker_ip = env_vars.get("MQTT_BROKER_IP")
    mqtt_broker_port = env_vars.get("MQTT_BROKER_PORT")
    mqtt_client_id = env_vars.get("MQTT_CLIENT_ID")

    connect_wifi(wifi_ssid=wifi_ssid, wifi_password=wifi_password)
    client = connect_mqtt(broker_ip=mqtt_broker_ip, port=mqtt_broker_port, client_id=mqtt_client_id)

    # Set up the tipping bucket interrupt
    tipping_bucket = Pin(22, Pin.IN, Pin.PULL_UP)
    tipping_bucket.irq(trigger=Pin.IRQ_FALLING, handler=rainfall_handler)

    try:
        while True:
            # Read temperature
            temperature = read_onboard_temperature()
            print(f"Temperature: {temperature}°C")

            # Publish temperature
            client.publish("sensors/onboard_temperature", str(temperature))
            print(f"Published onboard temperature: {temperature}°F.")

            # Publish rainfall count
            if tip_count != last_published_tip_count:
                client.publish("sensors/rainfall", str(tip_count))
                print(f"Published rainfall count: {tip_count}.")
                last_published_tip_count = tip_count


            # Wait before next loop
            time.sleep(5)
    except KeyboardInterrupt:
        print("Stopping sensors...")
    finally:
        client.disconnect()

# Run the main function
if __name__ == "__main__":
    main()
