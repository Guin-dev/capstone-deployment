import time, cv2, csv, os
import numpy as np
from picamera2 import Picamera2
import board, busio, adafruit_tsl2591

# =====================================================================
# 0. INPUT MANUAL DURASI LOGGING
# =====================================================================
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
frame_width = 640
frame_height = 480
cam_config = cam.create_video_configuration(main={"size": (frame_width, frame_height)})
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
out_dir = "/home/mbasis/output_gamma_lane"
os.makedirs(out_dir, exist_ok=True)

timestamp = int(time.time())
csv_file = os.path.join(out_dir, f"log_gamma_lane_{timestamp}.csv")
video_file_lane = os.path.join(out_dir, f"video_lane_detection_{timestamp}.mp4")
video_file_bev = os.path.join(out_dir, f"video_bird_eye_{timestamp}.mp4")

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
# 6. FUNGSI BANTUAN GAMMA
# =====================================================================
def measure_brightness(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return np.mean(gray)

def apply_gamma(frame, gamma):
    inv = 1.0 / gamma
    lut = np.array([((i / 255.0) ** inv) * 255 for i in np.arange(256)]).astype("uint8")
    return cv2.LUT(frame, lut)

# =====================================================================
# 7. SETUP BIRD'S EYE VIEW TRANSFORMATION
# =====================================================================
# Titik sumber (trapesium area jalan)
src_points = np.float32([
    [0, frame_height],                                      # kiri bawah
    [frame_width, frame_height],                            # kanan bawah
    [int(frame_width * 0.2), int(frame_height * 0.3)],     # kiri atas
    [int(frame_width * 0.8), int(frame_height * 0.3)]      # kanan atas
])

# Titik tujuan (bird eye view - persegi penuh)
dst_points = np.float32([
    [0, frame_height],          # kiri bawah
    [frame_width, frame_height], # kanan bawah
    [0, 0],                     # kiri atas
    [frame_width, 0]            # kanan atas
])

# Hitung transformation matrix
M = cv2.getPerspectiveTransform(src_points, dst_points)

# =====================================================================
# 8. FUNGSI LANE DETECTION
# =====================================================================
def hitung_posisi(contours_list, width):
    """Hitung posisi rata-rata dari list contours"""
    if len(contours_list) > 0:
        total_cx = 0
        for cnt in contours_list:
            M_moments = cv2.moments(cnt)
            if M_moments["m00"] != 0:
                total_cx += int(M_moments["m10"] / M_moments["m00"])
        
        avg_cx = total_cx // len(contours_list)
        return avg_cx
    return None

def detect_lane(frame_input, with_bev=True):
    """
    Deteksi jalur dengan atau tanpa Bird's Eye View
    Returns: (hasil_frame, offset, arah)
    """
    if with_bev:
        # Terapkan Bird Eye View transformation
        frame_processed = cv2.warpPerspective(frame_input, M, (frame_width, frame_height))
    else:
        frame_processed = frame_input.copy()
    
    # Ubah ke HSV untuk deteksi warna putih
    hsv = cv2.cvtColor(frame_processed, cv2.COLOR_BGR2HSV)
    
    # Batas warna putih
    lower_white = np.array([0, 0, 200])
    upper_white = np.array([180, 70, 255])
    mask = cv2.inRange(hsv, lower_white, upper_white)
    
    # Morphological operations
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # Cari kontur
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # Gambar hasil
    hasil = frame_processed.copy()
    height, width = mask.shape
    
    # Kelompokkan contour berdasarkan posisi X
    kiri_contours = []
    tengah_contours = []
    kanan_contours = []
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 300:
            M_moments = cv2.moments(contour)
            if M_moments["m00"] != 0:
                cx = int(M_moments["m10"] / M_moments["m00"])
                
                # Kategorisasi berdasarkan posisi X
                if cx < width * 0.33:
                    kiri_contours.append(contour)
                elif cx < width * 0.67:
                    tengah_contours.append(contour)
                else:
                    kanan_contours.append(contour)
            
            cv2.drawContours(hasil, [contour], -1, (0, 255, 0), -1)
    
    # Hitung posisi untuk setiap kelompok
    pos_kiri = hitung_posisi(kiri_contours, width)
    pos_tengah = hitung_posisi(tengah_contours, width)
    pos_kanan = hitung_posisi(kanan_contours, width)
    
    # Gambar garis referensi posisi kamera
    center_frame = width // 2
    cv2.line(hasil, (center_frame, 0), (center_frame, height), (0, 255, 255), 2)
    cv2.putText(hasil, "Posisi Kamera", (center_frame - 60, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
    # Hitung offset
    pos_referensi = None
    if pos_tengah is not None:
        pos_referensi = pos_tengah
    elif pos_kiri is not None and pos_kanan is not None:
        pos_referensi = (pos_kiri + pos_kanan) // 2
    
    offset = 0
    arah = "N/A"
    
    if pos_referensi is not None:
        offset = center_frame - pos_referensi
        
        # Tentukan arah
        if offset > 5:
            arah = "KIRI"
            warna_offset = (0, 165, 255)
        elif offset < -5:
            arah = "KANAN"
            warna_offset = (0, 165, 255)
        else:
            arah = "TENGAH"
            warna_offset = (0, 255, 0)
        
        # Tampilkan info offset
        offset_text = f"Offset: {abs(offset)}px ke {arah}"
        cv2.putText(hasil, offset_text, (10, height - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, warna_offset, 2)
        
        # Gambar panah indikator
        if abs(offset) > 5:
            arrow_start = (center_frame, height - 60)
            arrow_end = (pos_referensi, height - 60)
            cv2.arrowedLine(hasil, arrow_start, arrow_end, warna_offset, 3, tipLength=0.3)
    
    return hasil, offset, arah

# =====================================================================
# 9. SETUP VIDEO WRITER
# =====================================================================
fps = 30
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer_lane = cv2.VideoWriter(video_file_lane, fourcc, fps, (frame_width, frame_height))
writer_bev = cv2.VideoWriter(video_file_bev, fourcc, fps, (frame_width, frame_height))

print("[OK] VideoWriter aktif")
print("     Lane Detection:", video_file_lane)
print("     Bird's Eye View:", video_file_bev)

# =====================================================================
# 10. LOOP UTAMA — GAMMA + LANE DETECTION + LOGGING
# =====================================================================
start = time.time()
fps_counter = 0
fps_start = time.time()
fps_value = 0

with open(csv_file, "w", newline="") as f:
    writer_csv = csv.writer(f)
    writer_csv.writerow(["timestamp", "lux", "brightness", "gamma", "offset_normal", "arah_normal", "offset_bev", "arah_bev"])

    print("[START] Recording + logging dimulai...\n")

    while (time.time() - start) < durasi:
        # === BACA SENSOR LUX ===
        lux = tsl.lux or 0
        
        # === CAPTURE FRAME ===
        frame = cam.capture_array()

        if is_rgb:
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        else:
            frame_bgr = frame

        # === APPLY GAMMA CORRECTION ===
        brightness = measure_brightness(frame_bgr)
        gamma = fuzzy_gamma(lux, brightness)
        corrected = apply_gamma(frame_bgr, gamma)

        # === LANE DETECTION - TANPA BEV ===
        hasil_normal, offset_normal, arah_normal = detect_lane(corrected, with_bev=False)
        
        # === LANE DETECTION - DENGAN BEV ===
        hasil_bev, offset_bev, arah_bev = detect_lane(corrected, with_bev=True)

        # === TAMBAHKAN INFO GAMMA DI KEDUA FRAME ===
        gamma_text = f"Lux:{lux:.1f} Bright:{brightness:.1f} Gamma:{gamma:.2f}"
        
        # Hitung FPS
  