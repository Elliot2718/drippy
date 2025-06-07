#!/bin/bash

sleep 2
cd /home/elliot.wargo/drippy/src/broker || exit
source env/bin/activate

# Run Python in foreground so systemd knows the service is running
python3 mqtt_to_sqlite.py >> /home/elliot.wargo/drippy/mqtt.log 2>&1
