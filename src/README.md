# Remote sensor logging
The goal of this project is to set up a framework for having one or more sensors log data to a remote server. My goal is to have sensors around my farm, and a centralized server that will collect data from them, for analysis, triggering other actions, etc.

## Decision log
### Raspberry Pi Zero 2 W as the server
I started this project with a Raspberry Pi 4, but switched to using a Raspberry Pi Zero 2 W after wanting to repurpose the Pi 4 for another project. We'll see if it's powerful enough!

### Raspberry Pi Pico as the microcontroller
During Christmas 2023, I gave the [Maker Advent Calendar](https://thepihut.com/products/maker-advent-calendar-includes-raspberry-pi-pico-h?srsltid=AfmBOoppkc3dBWIXFhAGYaUmgQvObJisdkjafNRuqTpctx4AZcWn5yEP) to my three kids (ages 7, 9, and 11 at the time). My kids and I had a great time, them connecting things together and doing some basic coding, and me learning about microcontrollers. A cheap, python-based microcontroller that lets you do things in the real world; what's not to like?

### MQTT as the communication protocol
I was looking for a simple, but extensible option for communication between the microcontroller and the server, specifically something that was lightweight enough for the Pico, but didn't require complex setup.

#### Considered options
- MQTT
- HTTP/REST API
- LwM2M/CoAP

#### Decision outcome
I choose MQTT; it's lightweight, simpler to implement than HTTP/REST API, and better supported than LwM2M/CoAP in MicroPython.

### Use MicroPython on the Pico
I'm comfortable with Python, but have never coded in C or C++, so that was that!
