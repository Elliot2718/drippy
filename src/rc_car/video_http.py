#!/usr/bin/env python3
"""
Tiny MJPEG server – /stream.mjpg
Uses Picamera2 + OpenCV for JPEG encoding.
"""

from flask import Flask, Response
from picamera2 import Picamera2
import cv2, time

app = Flask(__name__)
picam = Picamera2()

# 640×480 RGB888 video stream, 30 fps
video_cfg = picam.create_video_configuration(main={"size": (640, 480),
                                                   "format": "RGB888"})
picam.configure(video_cfg)
picam.start()

def gen():
    while True:
        frame = picam.capture_array()
        # JPEG-encode (cv2 returns tuple: success flag, buf)
        _, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        jpg_bytes = jpg.tobytes()

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n"
               b"Content-Length: " + str(len(jpg_bytes)).encode() + b"\r\n\r\n" +
               jpg_bytes + b"\r\n")

        time.sleep(0.033)          # ~30 fps

@app.route("/stream.mjpg")
def mjpeg():
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)

