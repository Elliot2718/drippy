"""
Functions for using the ds18b20 waterproof digital temperature sensor
"""

import time
import machine
import onewire, ds18x20

def read_temperature(pin=26):
    """
    Returns the temperature in fahrenheit from a single ds18b20 temperature sensor
    """
    pin = machine.Pin(26)
    sensor = ds18x20.DS18X20(onewire.OneWire(pin))

    # Look for DS18B20 sensors (each contains a unique rom code)
    roms = sensor.scan()

    for rom in roms: # For each sensor found (just 1 in our case)
        sensor.convert_temp() # Convert the sensor units to centigrade
        time.sleep(1)
    
        temperature_celcius = sensor.read_temp(rom)
        temperature_fahrenheit = temperature_celcius * 9/5 + 32
        return temperature_fahrenheit

