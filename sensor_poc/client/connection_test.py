import socket

BROKER = "192.168.230.33"  # Replace with your Mac's IP address
PORT = 1883

try:
    s = socket.socket()
    s.connect((BROKER, PORT))
    print("Connection to MQTT broker successful!")
    s.close()
except Exception as e:
    print("Failed to connect:", e)
