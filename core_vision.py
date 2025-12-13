import cv2
import numpy as np
import time

from picamera2 import Picamera2
import board, busio, adafruit_tsl2591

# ===================== 1. SETUP SENSOR TSL2591 =====================
i2c = busio.I2C(board.SCL, board.SDA)
tsl = adafruit_tsl2591.TSL2591(i2c)
# boleh disesuaikan kalau perlu
tsl.integration_time = adafruit_tsl2591.INTEGRATIONTIME_300MS
tsl.gain = adafruit_tsl2591.GAIN_MED

# ===================== 2. SETUP KAMERA =====================
picam2 = Picamera2()
frame_width = 640
frame_height = 360

config = picam2.create_preview_configuration(main={"size": (frame_width, frame_height)})
picam2.configure(config)
picam2.start()
time.sleep(0.3)

# ===================== 3. FUZZY GAMMA FUNCTIONS =====================
def fuzzy_gamma(lux, brightness):
    # versi dari kode #3/#5
    L = np.clip(lux / 1500.0, 0, 1)
    B = np.clip(brightness / 100.0, 0, 1)

    dark = 1 - L
    bright = L
    too_dark = dark * (1 - B)
    too_bright = bright * B
    normal = 1 - np.abs(L - B)

    gamma = (1.6 * too_dark + 1.0 * normal + 0.4 * too_bright) / (too_dark + normal + too_bright + 1e-6)
    return float(np.clip(gamma, 0.4, 1.6))

def measure_brightness(frame_bgr):
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))

def apply_gamma(frame_bgr, gamma):
    inv = 1.0 / gamma
    lut = np.array([((i / 255.0) ** inv) * 255 for i in np.arange(256)]).astype("uint8")
    return cv2.LUT(frame_bgr, lut)

# ===================== 4. BEV TRANSFORM (SAMA SEPERTI KODE BERHASIL) =====================
src_points = np.float32([
    [0, frame_height],
    [frame_width, frame_height],
    [int(frame_width * 0.2), int(frame_height * 0.3)],
    [int(frame_width * 0.8), int(frame_height * 0.3)]
])

dst_points = np.float32([
    [0, frame_height],
    [frame_width, frame_height],
    [0, 0],
    [frame_width, 0]
])

# pakai nama lain supaya tidak bentrok
M_bev = cv2.getPerspectiveTransform(src_points, dst_points)

lower_white = np.array([0, 0, 200])
upper_white = np.array([180, 70, 255])
kernel = np.ones((5, 5), np.uint8)

print("Kamera siap dengan Gamma+TSL! Tekan 'q' untuk keluar")

# ===================== 5. MAIN LOOP =====================
while True:
    # ---- Ambil frame dari kamera ----
    frame_rgb = picam2.capture_array()
    frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

    # ---- Baca lux & hitung gamma ----
    lux = tsl.lux or 0.0
    brightness = measure_brightness(frame)
    gamma = fuzzy_gamma(lux, brightness)

    # ---- Apply gamma correction ----
    corrected = apply_gamma(frame, gamma)

    # ================== BEV PATH ==================
    frame_bird_eye = cv2.warpPerspective(corrected, M_bev, (frame_width, frame_height))

    hsv = cv2.cvtColor(frame_bird_eye, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_white, upper_white)

    height, width = mask.shape

    polygon = np.array([[
        (0, height),
        (width, height),
        (width, 0),
        (0, 0)
    ]], np.int32)

    roi = np.zeros_like(mask)
    cv2.fillPoly(roi, [polygon], 255)
    mask = cv2.bitwise_and(mask, roi)

    # ================== NORMAL PATH (TANPA BEV) ==================
    hsv_normal = cv2.cvtColor(corrected, cv2.COLOR_BGR2HSV)
    mask_normal = cv2.inRange(hsv_normal, lower_white, upper_white)

    roi_normal = np.zeros_like(mask_normal)
    polygon_normal = np.array([[
        (0, height),
        (width, height),
        (int(width * 0.8), int(height * 0.3)),
        (int(width * 0.2), int(height * 0.3))
    ]], np.int32)
    cv2.fillPoly(roi_normal, [polygon_normal], 255)
    mask_normal = cv2.bitwise_and(mask_normal, roi_normal)
    hasil_normal = corrected.copy()

    # ================== DETEKSI KONTOUR (BEV) ==================
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    hasil = frame_bird_eye.copy()
    cv2.polylines(hasil, [polygon], True, (255, 0, 0), 3)

    kiri_contours = []
    tengah_contours = []
    kanan_contours = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 300:
            mom = cv2.moments(contour)
            if mom["m00"] != 0:
                cx = int(mom["m10"] / mom["m00"])

                if cx < width * 0.33:
                    kiri_contours.append(contour)
                elif cx < width * 0.67:
                    tengah_contours.append(contour)
                else:
                    kanan_contours.append(contour)

            cv2.drawContours(hasil, [contour], -1, (0, 255, 0), -1)

    def hitung_posisi(contours_list):
        if len(contours_list) > 0:
            total_cx = 0
            for cnt in contours_list:
                mom = cv2.moments(cnt)
                if mom["m00"] != 0:
                    total_cx += int(mom["m10"] / mom["m00"])
            avg_cx = total_cx // len(contours_list)
            return avg_cx
        return None

    pos_kiri = hitung_posisi(kiri_contours)
    pos_tengah = hitung_posisi(tengah_contours)
    pos_kanan = hitung_posisi(kanan_contours)

    # ================== HITUNG OFFSET & ARAH ==================
    center_frame = width // 2
    cv2.line(hasil, (center_frame, 0), (center_frame, height), (0, 255, 255), 2)
    cv2.putText(hasil, "Posisi Kamera", (center_frame - 60, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

    pos_referensi = None
    if pos_tengah is not None:
        pos_referensi = pos_tengah
    elif pos_kiri is not None and pos_kanan is not None:
        pos_referensi = (pos_kiri + pos_kanan) // 2

    if pos_referensi is not None:
        offset = center_frame - pos_referensi

        if offset > 5:
            arah = "KIRI"
            warna_offset = (0, 165, 255)  # Orange
        elif offset < -5:
            arah = "KANAN"
            warna_offset = (0, 165, 255)  # Orange
        else:
            arah = "TENGAH"
            warna_offset = (0, 255, 0)    # Hijau

        offset_text = f"Offset: {abs(offset)}px ke {arah}"
        cv2.putText(hasil, offset_text, (10, height - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, warna_offset, 2)

        if abs(offset) > 5:
            arrow_start = (center_frame, height - 60)
            arrow_end = (pos_referensi, height - 60)
            cv2.arrowedLine(hasil, arrow_start, arrow_end, warna_offset, 3, tipLength=0.3)
    else:
        cv2.putText(hasil, "Offset: N/A", (10, height - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # ================== OVERLAY INFO LUX + GAMMA ==================
    info_text = f"Lux:{lux:.1f} Bright:{brightness:.1f} Gamma:{gamma:.2f}"
    cv2.putText(hasil, info_text, (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.putText(hasil_normal, info_text, (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # ================== TAMPILKAN ==================
    cv2.imshow("Mask Putih (BEV)", mask)
    cv2.imshow("Hasil Deteksi Garis (BEV + Gamma)", hasil)
    cv2.imshow("Tanpa Bird Eye View (Gamma Corrected)", hasil_normal)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

picam2.stop()
cv2.destroyAllWindows()
