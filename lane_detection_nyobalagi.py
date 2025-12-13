import cv2
import numpy as np
import os

# === CEK VIDEO ADA ATAU TIDAK ===
video_path = "video 3 november.mp4"

if not os.path.exists(video_path):
    raise FileNotFoundError(f"❌ File video tidak ditemukan: {os.path.abspath(video_path)}")

video = cv2.VideoCapture(video_path)
if not video.isOpened():
    raise RuntimeError("❌ Gagal membuka video. Pastikan format dan path benar.")

print("✅ Video berhasil dibuka, tekan 'Q' untuk keluar.\n")

try:
    while True:
        ret, frame = video.read()
        if not ret:
            print("⚠️ Frame habis atau tidak bisa dibaca.")
            break
        
        frame = cv2.resize(frame, (640, 360))
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Batas bawah dan atas warna putih
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 70, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        # ROI trapesium
        height, width = mask.shape
        polygon = np.array([[
            (0, height),
            (width, height),
            (int(width * 1.0), int(height * 0.4)),
            (int(width * 0.0), int(height * 0.4))
        ]], np.int32)

        roi = np.zeros_like(mask)
        cv2.fillPoly(roi, [polygon], 255)
        mask = cv2.bitwise_and(mask, roi)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        hasil = frame.copy()
        cv2.polylines(hasil, [polygon], True, (255, 0, 0), 3)

        kiri_contours, tengah_contours, kanan_contours = [], [], []

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

        def hitung_posisi(contours_list):
            total_cx = 0
            count = 0
            for cnt in contours_list:
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    total_cx += int(M["m10"] / M["m00"])
                    count += 1
            return total_cx // count if count > 0 else None

        pos_kiri = hitung_posisi(kiri_contours)
        pos_tengah = hitung_posisi(tengah_contours)
        pos_kanan = hitung_posisi(kanan_contours)

        center_frame = width // 2
        cv2.line(hasil, (center_frame, 0), (center_frame, height), (0, 255, 255), 2)
        cv2.putText(hasil, "Posisi Kamera", (center_frame - 60, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        pos_referensi = pos_tengah or ((pos_kiri + pos_kanan) // 2 if pos_kiri and pos_kanan else None)

        if pos_referensi is not None:
            offset = center_frame - pos_referensi
            if offset > 5:
                arah, warna = "KIRI", (0, 165, 255)
            elif offset < -5:
                arah, warna = "KANAN", (0, 165, 255)
            else:
                arah, warna = "TENGAH", (0, 255, 0)

            cv2.putText(hasil, f"Offset: {abs(offset)}px ke {arah}",
                        (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, warna, 2)

            if abs(offset) > 5:
                cv2.arrowedLine(hasil, (center_frame, height - 60),
                                (pos_referensi, height - 60), warna, 3, tipLength=0.3)

        # === TAMPILKAN HASIL ===
        cv2.imshow("Mask Putih", mask)
        cv2.imshow("Hasil Deteksi Garis", hasil)

        # Kalau GUI tidak muncul, beri tahu
        if cv2.getWindowProperty("Hasil Deteksi Garis", cv2.WND_PROP_VISIBLE) < 1:
            print("⚠️ Jendela OpenCV tertutup, keluar...")
            break

        key = cv2.waitKey(10) & 0xFF
        if key in [ord('q'), 27]:  # Q atau ESC
            print("⏹ Dihentikan oleh pengguna.")
            break

except Exception as e:
    print(f"❗ Terjadi error: {e}")

finally:
    video.release()
    cv2.destroyAllWindows()
    print("✅ Semua jendela ditutup dan resource dilepaskan dengan aman.")
