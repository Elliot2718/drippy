#!/usr/bin/env python3
"""
MQTT → PWM bridge.
Topics:
  car/steer    {"value": -1 .. +1}
  car/throttle {"value": -1 .. +1}
Requires pigpio daemon (`sudo systemctl enable --now pigpiod`)
"""

import json, time, paho.mqtt.client as mqtt, pigpio

MQTT_HOST = "127.0.0.1"
STEER_GPIO = 13          # or PCA9685 later
THROTTLE_GPIO = 18
NEUTRAL_US, SPAN_US = 1500, 500     # 1000–2000 µs

pi = pigpio.pi()
pi.set_servo_pulsewidth(THROTTLE_GPIO, NEUTRAL_US)
pi.set_servo_pulsewidth(STEER_GPIO,    NEUTRAL_US)

last_msg = time.time()

def pwm(pin, val):
    pi.set_servo_pulsewidth(pin, int(NEUTRAL_US + val * SPAN_US))

def on_msg(_, __, m):
    global last_msg
    last_msg = time.time()
    val = json.loads(m.payload).get("value", 0)
    if m.topic.endswith("steer"):
        pwm(STEER_GPIO, val)
    elif m.topic.endswith("throttle"):
        pwm(THROTTLE_GPIO, val)

cli = mqtt.Client()
cli.on_message = on_msg
cli.connect(MQTT_HOST)
cli.subscribe([("car/steer", 0), ("car/throttle", 0)])
cli.loop_start()

try:
    while True:
        if time.time() - last_msg > 0.3:          # failsafe 300 ms
            pwm(THROTTLE_GPIO, 0); pwm(STEER_GPIO, 0)
        time.sleep(0.05)
except KeyboardInterrupt:
    pass
finally:
    pi.set_servo_pulsewidth(THROTTLE_GPIO, 0)
    pi.set_servo_pulsewidth(STEER_GPIO,    0)
    pi.stop()
