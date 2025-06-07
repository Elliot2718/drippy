# Raspberry Pi Zero 2 W MQTT Broker and Service Setup

This guide walks you through setting up a secure MQTT broker using Mosquitto on a Raspberry Pi Zero 2 W, connecting a Pico device that publishes sensor data to the broker, and creating a systemd service to automatically start the broker and a logging script at boot.

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

## 🧩 8. Create a Service for Mosquitto and Logging Script

This step creates a systemd service to automatically start the Mosquitto MQTT broker and your Python logging script at boot.

### 1. Enable Mosquitto as a systemd service
```bash
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### 2. Create Startup Script

Make the file `start_mqtt_services.sh` executable:

```bash
chmod +x /home/username/drippy/src/broker/start_mqtt_services.sh
```

### 3. Create systemd Service File

Create the service unit file:

```bash
sudo nano /etc/systemd/system/mqtt_stack.service
```

Paste the following:

```ini
[Unit]
Description=Start Mosquitto and MQTT logging script
After=network.target

[Service]
Type=simple
ExecStart=/home/username/your_project_directory/start_mqtt_services.sh
Restart=on-failure
User=username
WorkingDirectory=/home/username/your_project_directory

[Install]
WantedBy=multi-user.target
```

### 4. Enable and Start the Service

Reload systemd and enable the service:

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable mqtt_stack.service
sudo systemctl start mqtt_stack.service
```

### 5. Check Service Status

To check if it's working:

```bash
sudo systemctl status mqtt_stack.service
```

Or to view logs:

```bash
journalctl -u mqtt_stack.service
```

---

## ✅ Done!

You now have a secure MQTT broker running on your Pi Zero 2 W, a MicroPython-based Pico device publishing to it, and an automatic service that starts everything at boot.

You can now subscribe to topics like:

```bash
mosquitto_sub -h 192.168.0.16 -u rain_gauge_station -P password -t "rain_gauge_station/#" -v
```

Enjoy building your sensor network!

---

## Notes

- Make sure your script and its dependencies (e.g., Python packages) are installed and accessible to the `username` user.
- You can add logging to the bash script if desired using redirection:

  ```bash
  python3 mqtt_to_sqlite.py >> log.txt 2>&1 &
  ```
