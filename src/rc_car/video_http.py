#!/usr/bin/env python3
"""
Very-light MJPEG server: GET /stream.mjpg
Latency ~120 ms over Wi-Fi.
"""

from flask import Flask, Response
from picamera2 import Picamera2
import io, time

app = Flask(__name__)
picam = Picamera2()
picam.configure(picam.create_video_configuration(main={"format": "RGB888", "size": (640, 480)}))
picam.start()

def gen():
    while True:
        frame = io.BytesIO()
        picam.capture_file(frame, format="jpeg", quality=85)
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" +
               frame.getvalue() + b"\r\n")
        time.sleep(0.03)             # ~33 fps

@app.route("/stream.mjpg")
def mjpeg():
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
