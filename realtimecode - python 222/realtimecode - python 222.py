import cv2
import numpy as np
from picamera2 import Picamera2

# Setup Raspberry Pi Camera
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 360)})
picam2.configure(config)
picam2.start()

# Parameter frame
frame_width = 640
frame_height = 360

# Setup Bird Eye View Transformation
# Titik sumber (dari frame asli) - trapesium
src_points = np.float32([
    [0, frame_height],                      # kiri bawah
    [frame_width, frame_height],            # kanan bawah
    [int(frame_width * 0.2), int(frame_height * 0.3)],   # kiri atas
    [int(frame_width * 0.8), int(frame_height * 0.3)]    # kanan atas
])

# Titik tujuan (bird eye view) - persegi penuh
dst_points = np.float32([
    [0, frame_height],                      # kiri bawah
    [frame_width, frame_height],            # kanan bawah
    [0, 0],                                 # kiri atas
    [frame_width, 0]                        # kanan atas
])

# Hitung transformation matrix
M = cv2.getPerspectiveTransform(src_points, dst_points)

print("Kamera siap! Tekan 'q' untuk keluar")

while True:
    # Capture frame dari Raspi Camera
    frame = picam2.capture_array()
    
    # Konversi dari RGB ke BGR (OpenCV pakai BGR)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    
    # Terapkan Bird Eye View transformation
    frame_bird_eye = cv2.warpPerspective(frame, M, (frame_width, frame_height))
    
    # ubah ke HSV biar lebih mudah deteksi warna putih
    hsv = cv2.cvtColor(frame_bird_eye, cv2.COLOR_BGR2HSV)
    
    # batas bawah dan atas warna putih
    lower_white = np.array([0, 0, 200])
    upper_white = np.array([180, 70, 255])
    mask = cv2.inRange(hsv, lower_white, upper_white)
    
    # masking area jalan (ROI)
    height, width = mask.shape
    
    # ROI persegi penuh (karena sudah bird eye view)
    polygon = np.array([[
        (0, height),                    # kiri bawah
        (width, height),                # kanan bawah
        (width, 0),                     # kanan atas
        (0, 0)                          # kiri atas
    ]], np.int32)
    
    roi = np.zeros_like(mask)
    cv2.fillPoly(roi, [polygon], 255)
    mask = cv2.bitwise_and(mask, roi)
    
    # ===== PROSES NORMAL (TANPA BIRD EYE VIEW) UNTUK PERBANDINGAN =====
    hsv_normal = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
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
    hasil_normal = frame.copy()
    
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # Cari kontur dari area putih
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # Gambar hasil bird eye view
    hasil = frame_bird_eye.copy()
    cv2.polylines(hasil, [polygon], True, (255, 0, 0), 3)
    
    # Kelompokkan contour berdasarkan posisi X (kiri, tengah, kanan)
    kiri_contours = []
    tengah_contours = []
    kanan_contours = []
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 300:
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                
                # Kategorisasi berdasarkan posisi X
                if cx < width * 0.33:  # kiri
                    kiri_contours.append(contour)
                elif cx < width * 0.67:  # tengah
                    tengah_contours.append(contour)
                else:  # kanan
                    kanan_contours.append(contour)
            
            cv2.drawContours(hasil, [contour], -1, (0, 255, 0), -1)
    
    # Hitung posisi rata-rata untuk setiap kelompok
    def hitung_posisi(contours_list):
        if len(contours_list) > 0:
            total_cx = 0
            for cnt in contours_list:
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    total_cx += int(M["m10"] / M["m00"])
            
            avg_cx = total_cx // len(contours_list)
            return avg_cx
        return None
    
    pos_kiri = hitung_posisi(kiri_contours)
    pos_tengah = hitung_posisi(tengah_contours)
    pos_kanan = hitung_posisi(kanan_contours)
    
    # Gambar garis referensi posisi kamera (tengah frame)
    center_frame = width // 2
    cv2.line(hasil, (center_frame, 0), (center_frame, height), (0, 255, 255), 2)
    cv2.putText(hasil, "Posisi Kamera", (center_frame - 60, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
    # Hitung offset - prioritas: garis tengah > tengah antara kiri-kanan
    pos_referensi = None
    if pos_tengah is not None:
        pos_referensi = pos_tengah
    elif pos_kiri is not None and pos_kanan is not None:
        pos_referensi = (pos_kiri + pos_kanan) // 2
    
    if pos_referensi is not None:
        offset = center_frame - pos_referensi
        
        # Tentukan arah
        if offset > 5:
            arah = "KIRI"
            warna_offset = (0, 165, 255)  # Orange
        elif offset < -5:
            arah = "KANAN"
            warna_offset = (0, 165, 255)  # Orange
        else:
            arah = "TENGAH"
            warna_offset = (0, 255, 0)  # Hijau
        
        # Tampilkan info offset
        offset_text = f"Offset: {abs(offset)}px ke {arah}"
        cv2.putText(hasil, offset_text, (10, height - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, warna_offset, 2)
        
        # Gambar panah indikator
        if abs(offset) > 5:
            arrow_start = (center_frame, height - 60)
            arrow_end = (pos_referensi, height - 60)
            cv2.arrowedLine(hasil, arrow_start, arrow_end, warna_offset, 3, tipLength=0.3)
    
    cv2.imshow("Mask Putih", mask)
    cv2.imshow("Hasil Deteksi Garis", hasil)
    cv2.imshow("Tanpa Bird Eye View", hasil_normal)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

picam2.stop()
cv2.destroyAllWindows()