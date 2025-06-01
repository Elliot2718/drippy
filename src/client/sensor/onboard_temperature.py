"""
Functions for measuring the onboard temperature of the pico
"""

from machine import ADC

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

