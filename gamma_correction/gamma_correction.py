import time, cv2, csv, os
import numpy as np
from picamera2 import Picamera2
import board, busio, adafruit_tsl2591

durasi = int(input("Masukkan durasi logging (dalam detik): "))
print(f"[INFO] Logging akan berjalan selama {durasi} detik\n")

# =====================================================================
# 1. SETUP SENSOR TSL2591
# =====================================================================
i2c = busio.I2C(board.SCL, board.SDA)
tsl = adafruit_tsl2591.TSL2591(i2c)
tsl.integration_time = adafruit_tsl2591.INTEGRATIONTIME_300MS
tsl.gain = adafruit_tsl2591.GAIN_MED

# =====================================================================
# 2. SETUP KAMERA PICAMERA2
# =====================================================================
cam = Picamera2()
cam_config = cam.create_video_configuration(main={"size": (640, 480)})
cam.configure(cam_config)
cam.start()
time.sleep(0.5)
print("[OK] Kamera dan sensor siap\n")

# =====================================================================
# 3. DETEKSI FORMAT WARNA SEKALI SAJA
# =====================================================================
test_frame = cam.capture_array()
if np.mean(test_frame[:,:,0]) > np.mean(test_frame[:,:,2]):
    is_rgb = True
    print("[INFO] Kamera output: RGB → akan dikonversi ke BGR")
else:
    is_rgb = False
    print("[INFO] Kamera output: BGR → tidak perlu konversi")

# =====================================================================
# 4. FOLDER OUTPUT & FILE OUTPUT
# =====================================================================
out_dir = "/home/mbasis/output_gamma_video"
os.makedirs(out_dir, exist_ok=True)

timestamp = int(time.time())
csv_file = os.path.join(out_dir, f"log_gamma_{timestamp}.csv")
video_file = os.path.join(out_dir, f"video_gamma_{timestamp}.mp4")

# =====================================================================
# 5. FUNGSI FUZZY GAMMA
# =====================================================================
def fuzzy_gamma(lux, brightness):
    L = np.clip(lux / 1500.0, 0, 1)
    B = np.clip(brightness / 100.0, 0, 1)

    dark = 1 - L
    bright = L
    too_dark = dark * (1 - B)
    too_bright = bright * B
    normal = 1 - np.abs(L - B)

    gamma = (1.6 * too_dark + 1.0 * normal + 0.4 * too_bright) / (too_dark + normal + too_bright + 1e-6)
    return np.clip(gamma, 0.4, 1.6)

# =====================================================================
# 6. FUNGSI BANTUAN
# =====================================================================
def measure_brightness(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return np.mean(gray)

def apply_gamma(frame, gamma):
    inv = 1.0 / gamma
    lut = np.array([((i / 255.0) ** inv) * 255 for i in np.arange(256)]).astype("uint8")
    return cv2.LUT(frame, lut)

# =====================================================================
# 7. SETUP VIDEO WRITER
# =====================================================================
fps = 30  # bisa kamu ubah sesuai kebutuhan
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(video_file, fourcc, fps, (640, 480))

print("[OK] VideoWriter aktif:", video_file)

# =====================================================================
# 8. LOOP UTAMA — RECORD VIDEO + LOGGING CSV
# =====================================================================
start = time.time()

with open(csv_file, "w", newline="") as f:
    writer_csv = csv.writer(f)
    writer_csv.writerow(["timestamp", "lux", "brightness", "gamma"])

    print("[START] Recording + logging dimulai...\n")

    while (time.time() - start) < durasi:
        lux = tsl.lux or 0
        frame = cam.capture_array()

        if is_rgb:
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        else:
            frame_bgr = frame

        brightness = measure_brightness(frame_bgr)
        gamma = fuzzy_gamma(lux, brightness)

        corrected = apply_gamma(frame_bgr, gamma)

        text = f"Lux:{lux:.1f}  Bright:{brightness:.1f}  Gamma:{gamma:.2f}"
        cv2.putText(corrected, text, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

        # === SAVE VIDEO FRAME ===
        writer.write(corrected)

        # === SAVE CSV DATA ===
        writer_csv.writerow([
            time.strftime("%H:%M:%S"), lux, brightness, gamma
        ])
        f.flush()

        # === SHOW LIVE PREVIEW ===
        cv2.imshow("Recording Auto Gamma", corrected)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[STOP] Dihentikan manual oleh user\n")
            break

writer.release()
cv2.destroyAllWindows()
cam.stop()

print("\n[DONE] Logging selesai.")
print("CSV  :", csv_file)
print("Video:", video_file)