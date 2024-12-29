
# Setting Up an MQTT Broker on the Raspberry Pi 4

## 1. Install Mosquitto
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install mosquitto mosquitto-clients -y
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```S

## 2. Allow External Connections
```bash
sudo nano /etc/mosquitto/mosquitto.conf
```
Add the following lines:
```conf
listener 1883
allow_anonymous true
```
Restart Mosquitto:
```bash
sudo systemctl restart mosquitto
```

## 3. Verify the Broker is Running
```bash
sudo systemctl status mosquitto
sudo lsof -i :1883
```

## 4. Test the Broker
Subscribe to a test topic:
```bash
mosquitto_sub -h localhost -t test/topic
```
Publish a message to the topic:
```bash
mosquitto_pub -h localhost -t test/topic -m "Hello from MQTT!"
```

## 5. Test External Connections
Find the Raspberry Pi's IP address:
```bash
hostname -I
```
From another device, subscribe to the broker:
```bash
mosquitto_sub -h <raspberry_pi_ip> -t test/topic
```
Publish a message from the Raspberry Pi:
```bash
mosquitto_pub -h localhost -t test/topic -m "Hello from Pi!"
```

## 6. Optional: Enable Security
Set up a username/password:
```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd your_username
```
Update the configuration:
```conf
allow_anonymous false
password_file /etc/mosquitto/passwd
```
Restart Mosquitto:
```bash
sudo systemctl restart mosquitto
```

## 7. Ensure Mosquitto Broker Runs on Boot
1. Enable the Mosquitto service to start on boot:
   ```bash
   sudo systemctl enable mosquitto
   ```

2. Verify the service is enabled:
   ```bash
   sudo systemctl is-enabled mosquitto
   ```

   You should see:
   ```
   enabled
   ```

3. Test the service:
   - Reboot the Raspberry Pi:
     ```bash
     sudo reboot
     ```
   - After rebooting, check the Mosquitto service status:
     ```bash
     sudo systemctl status mosquitto
     ```

   If Mosquitto is running, you'll see:
   ```
   Active: active (running)


# Enable the mqtt_to_sqlite service to run on boot
To ensure the `mqtt_to_sqlite.py` script runs on boot, set it up as a **systemd service**.

### Create the Service File
1. Create a new systemd service file:
   ```bash
   sudo nano /etc/systemd/system/mqtt_to_sqlite.service
   ```

2. Add the following configuration:
   ```ini
   [Unit]
   Description=MQTT to SQLite Subscriber Service
   After=network.target

   [Service]
   ExecStart=/usr/bin/python3 /path/to/mqtt_to_sqlite.py
   WorkingDirectory=/path/to
   Restart=always
   User=<username>
   Environment=PYTHONUNBUFFERED=1

   [Install]
   WantedBy=multi-user.target
   ```

   Replace `/path/to` with the actual path where your script is located (e.g., `/home/pi/Documents`) and username with your username.

3. Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

### Enable and Test the Service
1. Reload systemd to register the new service:
   ```bash
   sudo systemctl daemon-reload
   ```

2. Enable the service to run on boot:
   ```bash
   sudo systemctl enable mqtt_to_sqlite.service
   ```

3. Start the service immediately:
   ```bash
   sudo systemctl start mqtt_to_sqlite.service
   ```

4. Check the service status:
   ```bash
   sudo systemctl status mqtt_to_sqlite.service
   ```

   You should see:
   ```
   Active: active (running)
   ```

5. Test the service after reboot:
   - Reboot the Raspberry Pi:
     ```bash
     sudo reboot
     ```
   - After rebooting, check the service status:
     ```bash
     sudo systemctl status mqtt_to_sqlite.service
     ```
