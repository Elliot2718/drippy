#!/bin/bash

# start mosquitto broker
mosquitto -c /etc/mosquitto/mosquitto.conf &

sleep 2

cd /home/elliot.wargo/drippy
python3 src/broker/mqtt_to_sqlite.py &
