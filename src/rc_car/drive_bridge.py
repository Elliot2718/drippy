#!/usr/bin/env python3
"""
MQTT  ➜  PWM bridge for an RC-car

Topics published by the browser UI
----------------------------------
  car/steer    {"value": -1.0 … +1.0}   # left / right   (servo)
  car/throttle {"value": -1.0 … +1.0}   # forward / rev  (ESC)

Pulse mapping
-------------
  • Steering  : 1000–2000 µs  (1500 µs centre, ±500 span)
  • Throttle  : 1400–1600 µs  (1500 µs idle, ±100 span)

Dependencies
------------
  sudo apt install pigpio        # daemon: sudo systemctl enable --now pigpiod
  pip install paho-mqtt
"""

import json, time, logging
import paho.mqtt.client as mqtt
import pigpio

# ───────────────────────── configuration ──────────────────────────
MQTT_HOST       = "127.0.0.1"    # broker running on the Pi
STEER_GPIO      = 13             # BCM pin numbers
THROTTLE_GPIO   = 18

STEER_NEUTRAL   = 1500           # µs
STEER_SPAN      =  500           # ±500 → 1000–2000 µs

ESC_NEUTRAL     = 1500           # µs  (idle / brake)

ESC_SPAN        =  100           # µs  (±100 → 1400–1600 µs)

ESC_ARM_TIME    = 2.0            # s   hold neutral on boot so ESC arms
FAILSAFE_MS     = 300            # ms  no message → neutral

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)s: %(message)s")

# ───────────────────────── pigpio setup ───────────────────────────
pi = pigpio.pi()
if not pi.connected:
    raise SystemExit("pigpiod not running — start with: sudo systemctl enable --now pigpiod")

def set_us(pin: int, pulse: float):
    """Write a pulse-width (µs) to a GPIO pin."""
    pi.set_servo_pulsewidth(pin, int(pulse))

# steering neutral
set_us(STEER_GPIO, STEER_NEUTRAL)

# ESC arming sequence
logging.info("Arming ESC at neutral (%d µs) for %.1f s", ESC_NEUTRAL, ESC_ARM_TIME)
set_us(THROTTLE_GPIO, ESC_NEUTRAL)
time.sleep(ESC_ARM_TIME)
logging.info("ESC armed")

# ───────────────────────── helper mapping ─────────────────────────
def esc_throttle(percent: float):
    """
    Map ±1.0 from UI to 1400–1600 µs around neutral 1500 µs.
        +1.0 → forward  (1400 µs, below neutral)
        -1.0 → reverse  (1600 µs, above neutral)
    """
    percent = max(-1.0, min(1.0, percent))       # clamp
    pulse   = ESC_NEUTRAL - percent * ESC_SPAN   # NOTE: minus sign
    set_us(THROTTLE_GPIO, pulse)

# ───────────────────────── MQTT callbacks ─────────────────────────
last_msg = time.time()

def on_message(_, __, m):
    global last_msg
    last_msg = time.time()

    try:
        val = float(json.loads(m.payload)["value"])
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        logging.warning("Bad payload on %s: %s", m.topic, e)
        return

    if m.topic.endswith("steer"):
        pulse = STEER_NEUTRAL - val * STEER_SPAN
        set_us(STEER_GPIO, pulse)
    elif m.topic.endswith("throttle"):
        esc_throttle(val)

# ───────────────────────── MQTT plumbing ──────────────────────────
cli = mqtt.Client()
cli.on_message = on_message
cli.connect(MQTT_HOST)
cli.subscribe([("car/steer", 0), ("car/throttle", 0)])
cli.loop_start()

# ───────────────────────── watchdog loop ──────────────────────────
try:
    while True:
        if (time.time() - last_msg) * 1000 > FAILSAFE_MS:
            esc_throttle(0.0)
            set_us(STEER_GPIO, STEER_NEUTRAL)
        time.sleep(0.05)
except KeyboardInterrupt:
    pass
finally:
    # stop pulses so ESC/servo shut down cleanly
    set_us(THROTTLE_GPIO, 0)
    set_us(STEER_GPIO,    0)
    pi.stop()
    logging.info("Exiting ‒ GPIO released")
