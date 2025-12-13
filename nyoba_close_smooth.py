import cv2
import numpy as np

video = cv2.VideoCapture("video panjang 2.mp4")
if not video.isOpened():
    raise RuntimeError("❌ Gagal membuka video, periksa nama dan lokasi file.")

try:
    while True:
        ret, frame = video.read()
        if not ret:
            print("⚠️ Video selesai atau frame tidak terbaca.")
            break

        frame = cv2.resize(frame, (640, 360))
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 90, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        height, width = mask.shape
        roi = np.zeros_like(mask)
        polygon = np.array([[
            (0, height),
            (width, height),
            (width, int(height * 0.55)),
            (0, int(height * 0.55))
        ]], np.int32)
        cv2.fillPoly(roi, polygon, 255)
        mask = cv2.bitwise_and(mask, roi)
        mask = cv2.GaussianBlur(mask, (7, 7), 0)

        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        hasil = frame.copy()
        for contour in contours:
            if cv2.contourArea(contour) > 300:
                cv2.drawContours(hasil, [contour], -1, (0, 255, 0), -1)

        # tampilkan jendela
        cv2.imshow("Mask Putih", mask)
        cv2.imshow("Hasil Deteksi Garis", hasil)

        # ✅ cek apakah jendela ditutup manual
        mask_vis = cv2.getWindowProperty("Mask Putih", cv2.WND_PROP_VISIBLE)
        hasil_vis = cv2.getWindowProperty("Hasil Deteksi Garis", cv2.WND_PROP_VISIBLE)
        if mask_vis < 1 or hasil_vis < 1:
            print("🟡 Jendela ditutup manual.")
            break

        # tetap izinkan keyboard untuk keluar juga
        key = cv2.waitKey(10) & 0xFF
        if key in (27, ord('q')):
            print("🟢 Keluar lewat keyboard.")
            break

finally:
    video.release()
    cv2.destroyAllWindows()
    print("✅ Semua jendela ditutup dan resource dilepaskan dengan aman.")
