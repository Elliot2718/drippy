
# Raspberry Pi Zero 2 W MQTT Broker Setup

This guide walks you through setting up a secure MQTT broker using Mosquitto on a Raspberry Pi Zero 2 W, and connecting a Pico device that publishes sensor data to the broker.

---

## 🛠 Requirements

- Raspberry Pi Zero 2 W running Raspberry Pi OS
- Raspberry Pi Pico (or Pico W) running MicroPython
- MQTT client libraries installed (e.g., `umqtt.simple` for Pico)
- Network connection (same Wi-Fi for Pico and Pi Zero)

---

## 🔧 1. Install Mosquitto on the Pi Zero 2 W

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install mosquitto mosquitto-clients -y
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

---

## 🔒 2. Secure the MQTT Broker

### Disable anonymous access:

Edit the config file:

```bash
sudo nano /etc/mosquitto/mosquitto.conf
```

Add or update these lines:

```
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
```

Restart Mosquitto:

```bash
sudo systemctl restart mosquitto
```

---

## 👤 3. Create a User

```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd rain_gauge_station
```

Enter a strong password (e.g., `password` if testing — not recommended for production).

---

## 🚀 4. Test the Broker

From the Pi or another device on the same network:

```bash
mosquitto_sub -h 192.168.0.16 -u rain_gauge_station -P password -t "#" -v
```

You should now be subscribed to all topics and able to receive data from the Pico.

---

## 📄 5. Pico `.env` File

Create a file called `.env` on your Pico with the following:

```
WIFI_SSID=YourNetwork
WIFI_PASSWORD=YourPassword
MQTT_BROKER_IP=192.168.0.16
MQTT_BROKER_PORT=1883
MQTT_CLIENT_ID=rain_gauge_station_pico
MQTT_USERNAME=rain_gauge_station
MQTT_PASSWORD=YourMQTTPassword
```

Make sure the Pico script reads and uses these values correctly.

---

## 🧠 6. Pico Python Setup

Make sure you pass the loaded `MQTT_USERNAME` and `MQTT_PASSWORD` into the MQTTClient:

```python
client = MQTTClient(
    client_id=mqtt_client_id,
    server=mqtt_broker_ip,
    port=mqtt_broker_port,
    user=mqtt_username,
    password=mqtt_password
)
```

---

## 📡 7. Verify the Connection

Monitor the Mosquitto logs to confirm connections:

```bash
sudo journalctl -u mosquitto -f
```

You should see messages like:

```
New connection from 192.168.0.15 on port 1883.
Client rain_gauge_station_pico connected with username 'rain_gauge_station'.
```

---

## ✅ Done!

You now have a secure MQTT broker running on your Pi Zero 2 W and a MicroPython-based Pico device publishing to it.

You can now subscribe to topics like:

```bash
mosquitto_sub -h 192.168.0.16 -u rain_gauge_station -P password -t "rain_gauge_station/#" -v
```

Enjoy building your sensor network!
