"""
Flask MJPEG Streaming Server untuk Raspberry Pi
================================================

File ini akan berjalan di Raspberry Pi untuk:
1. Baca video dari kamera
2. Proses lane detection
3. Stream hasil via HTTP (MJPEG format)
4. Expose metadata via REST API

Cara pakai:
1. Copy file ini ke Raspberry Pi (folder /home/pi/capstone/)
2. Install dependencies: pip install flask opencv-python
3. Jalankan: python stream_server.py
4. Akses dari browser: http://<IP_PI>:5000/video_feed
"""

from flask import Flask, Response, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import time
from picamera2 import Picamera2
import board
import busio
import adafruit_tsl2591

app = Flask(__name__)
CORS(app)  # Enable CORS untuk akses dari Next.js

# ============ GLOBAL VARIABLES ============
# Untuk store latest detection results
latest_data = {
    "offset": 0,
    "arah": "N/A",
    "gamma": 1.0,
    "lux": 0.0,
    "brightness": 0.0,
    "fps": 0.0,
    "timestamp": time.time()
}

# ============ LANE DETECTION CLASS ============
class LaneDetector:
    """
    Extract dari core_vision_live.py
    Simplified untuk streaming
    """
    def __init__(self):
        self.frame_width = 640
        self.frame_height = 360
        
        # Setup TSL2591 sensor
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.tsl = adafruit_tsl2591.TSL2591(i2c)
            self.tsl.integration_time = adafruit_tsl2591.INTEGRATIONTIME_300MS
            self.tsl.gain = adafruit_tsl2591.GAIN_MED
            self.has_tsl = True
        except:
            print("TSL2591 sensor not found, using default lux")
            self.has_tsl = False
        
        # Setup PiCamera2
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(
            main={"size": (self.frame_width, self.frame_height)}
        )
        self.picam2.configure(config)
        self.picam2.start()
        time.sleep(0.3)
        
        # BEV Transform
        self.src_points = np.float32([
            [0, self.frame_height],
            [self.frame_width, self.frame_height],
            [int(self.frame_width * 0.2), int(self.frame_height * 0.3)],
            [int(self.frame_width * 0.8), int(self.frame_height * 0.3)]
        ])
        
        self.dst_points = np.float32([
            [0, self.frame_height],
            [self.frame_width, self.frame_height],
            [0, 0],
            [self.frame_width, 0]
        ])
        
        self.M_bev = cv2.getPerspectiveTransform(self.src_points, self.dst_points)
        
        # Detection parameters
        self.lower_white = np.array([0, 0, 200], dtype=np.uint8)
        self.upper_white = np.array([180, 70, 255], dtype=np.uint8)
        self.kernel = np.ones((5, 5), np.uint8)
    
    def fuzzy_gamma(self, lux, brightness):
        """Calculate optimal gamma correction"""
        L = np.clip(lux / 1500.0, 0, 1)
        B = np.clip(brightness / 100.0, 0, 1)
        
        dark = 1 - L
        bright = L
        too_dark = (dark ** 1.7) * (1 - B)
        too_bright = bright * B
        normal = 1 - np.abs(L - B)
        
        gamma = (2.2 * too_dark + 1.0 * normal + 0.4 * too_bright) / (
            too_dark + normal + too_bright + 1e-6
        )
        
        if L < 0.15:
            gamma *= 1.3
        
        return float(np.clip(gamma, 0.4, 2.5))
    
    def measure_brightness(self, frame_bgr):
        """Measure average brightness"""
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))
    
    def apply_gamma(self, frame_bgr, gamma):
        """Apply gamma correction"""
        inv = 1.0 / gamma
        lut = np.array(
            [((i / 255.0) ** inv) * 255 for i in np.arange(256)],
            dtype="uint8"
        )
        return cv2.LUT(frame_bgr, lut)
    
    def detect_lane(self, frame_bgr):
        """
        Main detection function
        Returns: annotated frame (BGR), offset (int), direction (str)
        """
        # Get lux from sensor
        if self.has_tsl:
            lux = self.tsl.lux or 0.0
        else:
            lux = 500.0  # default
        
        # Brightness and gamma correction
        brightness = self.measure_brightness(frame_bgr)
        gamma = self.fuzzy_gamma(lux, brightness)
        corrected = self.apply_gamma(frame_bgr, gamma)
        
        # Bird Eye View transform
        frame_bev = cv2.warpPerspective(
            corrected, self.M_bev,
            (self.frame_width, self.frame_height)
        )
        
        # White lane detection
        hsv = cv2.cvtColor(frame_bev, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_white, self.upper_white)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
        
        # Find contours
        contours, _ = cv2.findContours(
            mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Annotate frame
        hasil = frame_bev.copy()
        height, width = self.frame_height, self.frame_width
        center_frame = width // 2
        
        # Draw center line
        cv2.line(hasil, (center_frame, 0), (center_frame, height), (0, 255, 255), 2)
        
        # Process contours
        kiri_contours = []
        tengah_contours = []
        kanan_contours = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 300:
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    if cx < width * 0.33:
                        kiri_contours.append(contour)
                    elif cx < width * 0.67:
                        tengah_contours.append(contour)
                    else:
                        kanan_contours.append(contour)
                cv2.drawContours(hasil, [contour], -1, (0, 255, 0), -1)
        
        # Calculate offset
        pos_tengah = self._hitung_posisi(tengah_contours)
        pos_kiri = self._hitung_posisi(kiri_contours)
        pos_kanan = self._hitung_posisi(kanan_contours)
        
        pos_referensi = None
        if pos_tengah is not None:
            pos_referensi = pos_tengah
        elif pos_kiri is not None and pos_kanan is not None:
            pos_referensi = (pos_kiri + pos_kanan) // 2
        
        offset = 0
        arah = "N/A"
        
        if pos_referensi is not None:
            offset = center_frame - pos_referensi
            
            if offset > 5:
                arah = "KIRI"
                warna = (0, 165, 255)
            elif offset < -5:
                arah = "KANAN"
                warna = (0, 165, 255)
            else:
                arah = "TENGAH"
                warna = (0, 255, 0)
            
            # Draw arrow
            if abs(offset) > 5:
                arrow_start = (center_frame, height - 60)
                arrow_end = (pos_referensi, height - 60)
                cv2.arrowedLine(hasil, arrow_start, arrow_end, warna, 3, tipLength=0.3)
            
            # Draw offset text
            offset_text = f"Offset: {abs(offset)}px {arah}"
            cv2.putText(hasil, offset_text, (10, height - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, warna, 2)
        
        # Draw info overlay
        info_text = f"Lux:{lux:.1f} Gamma:{gamma:.2f} Bright:{brightness:.1f}"
        cv2.putText(hasil, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Update global data
        global latest_data
        latest_data.update({
            "offset": int(offset),
            "arah": arah,
            "gamma": round(gamma, 2),
            "lux": round(lux, 1),
            "brightness": round(brightness, 1),
            "timestamp": time.time()
        })
        
        return hasil, offset, arah
    
    def _hitung_posisi(self, contours_list):
        """Calculate average x position of contours"""
        if len(contours_list) == 0:
            return None
        total_cx = 0
        count = 0
        for cnt in contours_list:
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                total_cx += int(M["m10"] / M["m00"])
                count += 1
        if count == 0:
            return None
        return total_cx // count
    
    def get_frame(self):
        """Capture and process one frame"""
        frame_rgb = self.picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        hasil, offset, arah = self.detect_lane(frame_bgr)
        return hasil

# ============ INITIALIZE DETECTOR ============
print("Initializing Lane Detector...")
detector = LaneDetector()
print("Lane Detector ready!")

# ============ FLASK ROUTES ============

def generate_frames():
    """
    Generator function untuk MJPEG streaming
    Kayak async generator di JavaScript
    """
    fps_start = time.time()
    frame_count = 0
    
    while True:
        try:
            # Get processed frame
            frame = detector.get_frame()
            
            # Calculate FPS
            frame_count += 1
            if frame_count >= 30:
                fps = frame_count / (time.time() - fps_start)
                latest_data["fps"] = round(fps, 1)
                frame_count = 0
                fps_start = time.time()
            
            # Encode ke JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            
            # Yield sebagai MJPEG format
            # Format: --frame\r\nContent-Type: image/jpeg\r\n\r\n[JPEG_DATA]\r\n
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
        except Exception as e:
            print(f"Error in generate_frames: {e}")
            time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    """
    Video streaming route
    Endpoint ini akan di-consume oleh <img> tag di Next.js
    """
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/status')
def api_status():
    """
    REST API untuk metadata
    Returns JSON dengan info deteksi terbaru
    """
    return jsonify(latest_data)

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Lane Detection Server is running"})

@app.route('/')
def index():
    """Simple HTML page untuk test"""
    return """
    <html>
    <head><title>Lane Detection Stream</title></head>
    <body style="background: #000; color: #fff; font-family: monospace;">
        <h1>🚗 Lane Detection Live Stream</h1>
        <img src="/video_feed" width="640" height="360" style="border: 2px solid #0f0;">
        <div id="status" style="margin-top: 20px; font-size: 18px;"></div>
        
        <script>
            // Fetch metadata every 500ms
            setInterval(async () => {
                const res = await fetch('/api/status');
                const data = await res.json();
                document.getElementById('status').innerHTML = `
                    <strong>Offset:</strong> ${data.offset}px ${data.arah} | 
                    <strong>Gamma:</strong> ${data.gamma} | 
                    <strong>Lux:</strong> ${data.lux} | 
                    <strong>FPS:</strong> ${data.fps}
                `;
            }, 500);
        </script>
    </body>
    </html>
    """

# ============ RUN SERVER ============
if __name__ == '__main__':
    print("=" * 50)
    print("Lane Detection MJPEG Streaming Server")
    print("=" * 50)
    print("Access video stream at: http://<PI_IP>:5000/video_feed")
    print("Access metadata API at: http://<PI_IP>:5000/api/status")
    print("Access test page at: http://<PI_IP>:5000/")
    print("=" * 50)
    
    # Run Flask server
    # host='0.0.0.0' → accessible dari network
    # threaded=True → handle multiple connections
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
