import cv2
import numpy as np
import time

# Buka video atau camera (0 untuk camera default)
# Ubah ke 0 jika ingin menggunakan webcam real-time
video = cv2.VideoCapture(0)  # 0 untuk webcam default
# video = cv2.VideoCapture("tes 3 mobil.mp4")  # Uncomment untuk file video

# Set video properties untuk performa lebih baik
video.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Buffer minimal untuk latency rendah

# Parameter frame
frame_width = 640
frame_height = 360

# FPS counter
fps_start = time.time()
fps_counter = 0

# Titik sumber (dari frame asli) - trapesium (area jalan)
# Area bagian bawah lebih lebar, bagian atas lebih sempit (perspektif normal)
src_points = np.float32([
    [0, frame_height],                      # kiri bawah
    [frame_width, frame_height],            # kanan bawah
    [int(frame_width * 0.2), int(frame_height * 0.3)],   # kiri atas
    [int(frame_width * 0.8), int(frame_height * 0.3)]    # kanan atas
])

# Titik tujuan (bird eye view) - persegi penuh
# Stretch area atas agar terlihat seperti dari atas
dst_points = np.float32([
    [0, frame_height],                      # kiri bawah
    [frame_width, frame_height],            # kanan bawah
    [0, 0],                                 # kiri atas
    [frame_width, 0]                        # kanan atas
])

# Hitung transformation matrix untuk bird eye view
M = cv2.getPerspectiveTransform(src_points, dst_points)

while True:
    ret, frame = video.read()
    if not ret:
        break
    
    frame = cv2.resize(frame, (frame_width, frame_height))
    
    # Terapkan Bird Eye View transformation
    frame_bird_eye = cv2.warpPerspective(frame, M, (frame_width, frame_height))
    
    # Ubah ke HSV untuk deteksi warna putih
    hsv = cv2.cvtColor(frame_bird_eye, cv2.COLOR_BGR2HSV)
    
    # Batas bawah dan atas warna putih
    lower_white = np.array([0, 0, 200])
    upper_white = np.array([180, 70, 255])
    mask = cv2.inRange(hsv, lower_white, upper_white)
    
    # ROI - gunakan seluruh frame karena sudah bird eye view
    height, width = mask.shape
    
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # Cari kontur dari area putih
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # Gambar hasil
    hasil = frame_bird_eye.copy()
    
    # Kelompokkan contour berdasarkan posisi X (kiri, tengah, kanan)
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
                M_moments = cv2.moments(cnt)
                if M_moments["m00"] != 0:
                    total_cx += int(M_moments["m10"] / M_moments["m00"])
            
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
    
    # ===== PROSES TANPA BIRD EYE VIEW UNTUK PERBANDINGAN =====
    hsv_normal = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask_normal = cv2.inRange(hsv_normal, lower_white, upper_white)
    
    kernel_normal = np.ones((5, 5), np.uint8)
    mask_normal = cv2.morphologyEx(mask_normal, cv2.MORPH_OPEN, kernel_normal)
    
    contours_normal, _ = cv2.findContours(mask_normal, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    hasil_normal = frame.copy()
    
    kiri_contours_normal = []
    tengah_contours_normal = []
    kanan_contours_normal = []
    
    for contour in contours_normal:
        area = cv2.contourArea(contour)
        if area > 300:
            M_moments = cv2.moments(contour)
            if M_moments["m00"] != 0:
                cx = int(M_moments["m10"] / M_moments["m00"])
                
                if cx < width * 0.33:
                    kiri_contours_normal.append(contour)
                elif cx < width * 0.67:
                    tengah_contours_normal.append(contour)
                else:
                    kanan_contours_normal.append(contour)
            
            cv2.drawContours(hasil_normal, [contour], -1, (0, 255, 0), -1)
    
    pos_kiri_normal = hitung_posisi(kiri_contours_normal)
    pos_tengah_normal = hitung_posisi(tengah_contours_normal)
    pos_kanan_normal = hitung_posisi(kanan_contours_normal)
    
    cv2.line(hasil_normal, (center_frame, 0), (center_frame, height), (0, 255, 255), 2)
    cv2.putText(hasil_normal, "Posisi Kamera", (center_frame - 60, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
    pos_referensi_normal = None
    if pos_tengah_normal is not None:
        pos_referensi_normal = pos_tengah_normal
    elif pos_kiri_normal is not None and pos_kanan_normal is not None:
        pos_referensi_normal = (pos_kiri_normal + pos_kanan_normal) // 2
    
    if pos_referensi_normal is not None:
        offset_normal = center_frame - pos_referensi_normal
        
        if offset_normal > 5:
            arah_normal = "KIRI"
            warna_offset_normal = (0, 165, 255)
        elif offset_normal < -5:
            arah_normal = "KANAN"
            warna_offset_normal = (0, 165, 255)
        else:
            arah_normal = "TENGAH"
            warna_offset_normal = (0, 255, 0)
        
        offset_text_normal = f"Offset: {abs(offset_normal)}px ke {arah_normal}"
        cv2.putText(hasil_normal, offset_text_normal, (10, height - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, warna_offset_normal, 2)
        
        if abs(offset_normal) > 5:
            arrow_start_normal = (center_frame, height - 60)
            arrow_end_normal = (pos_referensi_normal, height - 60)
            cv2.arrowedLine(hasil_normal, arrow_start_normal, arrow_end_normal, warna_offset_normal, 3, tipLength=0.3)
    
    # ===== TAMPILKAN HASIL PERBANDINGAN =====
    # Hitung FPS
    fps_counter += 1
    fps_elapsed = time.time() - fps_start
    if fps_elapsed >= 1.0:
        fps = fps_counter / fps_elapsed
        fps_start = time.time()
        fps_counter = 0
    else:
        fps = fps_counter / fps_elapsed if fps_elapsed > 0 else 0
    
    # Tampilkan FPS di kedua window
    cv2.putText(hasil_normal, f"FPS: {fps:.1f}", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(hasil, f"FPS: {fps:.1f}", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    cv2.imshow("Tanpa Bird Eye View", hasil_normal)
    cv2.imshow("Dengan Bird Eye View", hasil)
    
    # Gunakan waitKey dengan delay minimal untuk real-time (1ms)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video.release()
cv2.destroyAllWindows()
