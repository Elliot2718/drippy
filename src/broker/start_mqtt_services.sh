#!/bin/bash

# Wait for Mosquitto to initialize
sleep 2

# Change to your project directory
cd /home/elliot.wargo/drippy/src/broker || exit

# Activate virtual environment and run script in the same shell
source env/bin/activate
python3 mqtt_to_sqlite.py &
