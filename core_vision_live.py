import cv2
import numpy as np
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from picamera2 import Picamera2
import board, busio, adafruit_tsl2591


class LaneDetectionLiveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lane Detection LIVE (TSL + Gamma + BEV)")
        self.playing = False

        # ======== PARAMETER FRAME ========
        self.frame_width = 640
        self.frame_height = 360

        # ======== SETUP SENSOR TSL2591 ========
        i2c = busio.I2C(board.SCL, board.SDA)
        self.tsl = adafruit_tsl2591.TSL2591(i2c)
        self.tsl.integration_time = adafruit_tsl2591.INTEGRATIONTIME_300MS
        self.tsl.gain = adafruit_tsl2591.GAIN_MED

        # ======== SETUP KAMERA PICAMERA2 ========
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(
            main={"size": (self.frame_width, self.frame_height)}
        )
        self.picam2.configure(config)
        self.picam2.start()
        time.sleep(0.3)

        # ======== BEV TRANSFORM (SAMA DENGAN KODE KAMU) ========
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

        self.lower_white = np.array([0, 0, 200], dtype=np.uint8)
        self.upper_white = np.array([180, 70, 255], dtype=np.uint8)
        self.kernel = np.ones((5, 5), np.uint8)

        # ================== UI KONTROL ==================
        option_frame = ttk.Frame(root)
        option_frame.pack(pady=5)

        ttk.Label(option_frame, text="Tampilkan:").pack(side=tk.LEFT, padx=5)
        self.display_option = tk.StringVar(value="Keduanya")
        view_choices = ["Keduanya", "Mask Saja", "Deteksi Saja"]
        self.view_selector = ttk.Combobox(
            option_frame,
            textvariable=self.display_option,
            values=view_choices,
            state="readonly",
            width=15
        )
        self.view_selector.pack(side=tk.LEFT, padx=5)

        ttk.Label(option_frame, text="Mode View:").pack(side=tk.LEFT, padx=5)
        self.view_mode = tk.StringVar(value="Bird Eye")
        mode_choices = ["Bird Eye", "Normal"]
        self.mode_selector = ttk.Combobox(
            option_frame,
            textvariable=self.view_mode,
            values=mode_choices,
            state="readonly",
            width=10
        )
        self.mode_selector.pack(side=tk.LEFT, padx=5)

        # Area video (2 label: mask & hasil)
        self.video_frame = ttk.Frame(root)
        self.video_frame.pack(padx=10, pady=10)

        self.mask_label = ttk.Label(self.video_frame)
        self.mask_label.grid(row=0, column=0, padx=10)

        self.result_label = ttk.Label(self.video_frame)
        self.result_label.grid(row=0, column=1, padx=10)

        # Tombol kontrol
        control_frame = ttk.Frame(root)
        control_frame.pack(pady=5)

        ttk.Button(control_frame, text="▶️ Start",
                   command=self.start_live).grid(row=0, column=0, padx=10)
        ttk.Button(control_frame, text="⏸ Pause",
                   command=self.pause_live).grid(row=0, column=1, padx=10)
        ttk.Button(control_frame, text="❌ Exit",
                   command=self.close).grid(row=0, column=2, padx=10)

        # Info status di bawah
        self.status_label = ttk.Label(root, text="Ready - Tekan Start untuk mulai")
        self.status_label.pack(pady=5)

        # supaya WM close juga panggil close()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    # ===================== FUZZY GAMMA & UTIL =====================

    def fuzzy_gamma(self, lux, brightness):
        """
        Versi sama seperti kode dasarmu:
        - too_dark pakai pangkat 1.7
        - gamma boost kalau lux kecil
        """
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
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))

    def apply_gamma(self, frame_bgr, gamma):
        inv = 1.0 / gamma
        lut = np.array(
            [((i / 255.0) ** inv) * 255 for i in np.arange(256)],
            dtype="uint8"
        )
        return cv2.LUT(frame_bgr, lut)

    def hitung_posisi(self, contours_list):
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

    # ===================== DETEKSI LANE =====================

    def detect_lane(self, frame_input, with_bev=True):
        """
        Mengadopsi logika dari kode CLI:
        - Jika with_bev: pakai warpPerspective -> ROI penuh
        - Jika Normal : langsung di frame corrected, ROI trapesium
        Return: hasil(BGR), mask(gray), offset(int), arah(str)
        """
        if with_bev:
            frame_processed = cv2.warpPerspective(
                frame_input, self.M_bev,
                (self.frame_width, self.frame_height)
            )
            height, width = self.frame_height, self.frame_width

            hsv = cv2.cvtColor(frame_processed, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, self.lower_white, self.upper_white)

            polygon = np.array([[
                (0, height),
                (width, height),
                (width, 0),
                (0, 0)
            ]], np.int32)

        else:
            frame_processed = frame_input.copy()
            frame_processed = cv2.resize(
                frame_processed, (self.frame_width, self.frame_height)
            )
            height, width, _ = frame_processed.shape

            hsv = cv2.cvtColor(frame_processed, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, self.lower_white, self.upper_white)

            polygon = np.array([[
                (0, height),
                (width, height),
                (int(width * 0.8), int(height * 0.3)),
                (int(width * 0.2), int(height * 0.3))
            ]], np.int32)

        # ROI masking
        roi = np.zeros_like(mask)
        cv2.fillPoly(roi, [polygon], 255)
        mask = cv2.bitwise_and(mask, roi)

        # Morphology
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)

        # Kontur
        contours, _ = cv2.findContours(
            mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        hasil = frame_processed.copy()
        cv2.polylines(hasil, [polygon], True, (255, 0, 0), 2)

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

        pos_kiri = self.hitung_posisi(kiri_contours)
        pos_tengah = self.hitung_posisi(tengah_contours)
        pos_kanan = self.hitung_posisi(kanan_contours)

        center_frame = width // 2
        cv2.line(
            hasil, (center_frame, 0),
            (center_frame, height), (0, 255, 255), 2
        )
        cv2.putText(
            hasil, "Posisi Kamera", (center_frame - 60, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2
        )

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
                warna_offset = (0, 165, 255)
            elif offset < -5:
                arah = "KANAN"
                warna_offset = (0, 165, 255)
            else:
                arah = "TENGAH"
                warna_offset = (0, 255, 0)

            offset_text = f"Offset: {abs(offset)}px ke {arah}"
            cv2.putText(
                hasil, offset_text, (10, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, warna_offset, 2
            )

            if abs(offset) > 5:
                arrow_start = (center_frame, height - 60)
                arrow_end = (pos_referensi, height - 60)
                cv2.arrowedLine(
                    hasil, arrow_start, arrow_end,
                    warna_offset, 3, tipLength=0.3
                )
        else:
            cv2.putText(
                hasil, "Offset: N/A", (10, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
            )

        return hasil, mask, offset, arah

    # ===================== PIPELINE PER FRAME =====================

    def process_frame(self, frame_bgr):
        # baca lux dari sensor
        lux = self.tsl.lux or 0.0

        # hitung brightness dan gamma
        brightness = self.measure_brightness(frame_bgr)
        gamma = self.fuzzy_gamma(lux, brightness)
        corrected = self.apply_gamma(frame_bgr, gamma)

        # mode view (BEV / Normal)
        with_bev = (self.view_mode.get() == "Bird Eye")

        hasil, mask, offset, arah = self.detect_lane(corrected, with_bev=with_bev)

        mode_txt = "BEV" if with_bev else "Normal"
        info_text = (
            f"Mode:{mode_txt} Lux:{lux:.1f} Bright:{brightness:.1f} "
            f"Gamma:{gamma:.2f} Off:{offset}px {arah}"
        )

        cv2.putText(
            hasil, info_text, (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2
        )

        return hasil, mask

    # ===================== DISPLAY KE TKINTER =====================

    def display_frame(self, mask, hasil):
        mode = self.display_option.get()

        # convert untuk Tkinter
        mask_rgb = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        imgtk_mask = ImageTk.PhotoImage(image=Image.fromarray(mask_rgb))
        imgtk_result = ImageTk.PhotoImage(
            image=Image.fromarray(cv2.cvtColor(hasil, cv2.COLOR_BGR2RGB))
        )

        if mode == "Keduanya":
            self.mask_label.configure(image=imgtk_mask)
            self.mask_label.imgtk = imgtk_mask
            self.result_label.configure(image=imgtk_result)
            self.result_label.imgtk = imgtk_result
            self.mask_label.grid(row=0, column=0)
            self.result_label.grid(row=0, column=1)

        elif mode == "Mask Saja":
            self.mask_label.configure(image=imgtk_mask)
            self.mask_label.imgtk = imgtk_mask
            self.mask_label.grid(row=0, column=0)
            self.result_label.grid_forget()

        elif mode == "Deteksi Saja":
            self.result_label.configure(image=imgtk_result)
            self.result_label.imgtk = imgtk_result
            self.result_label.grid(row=0, column=0)
            self.mask_label.grid_forget()

    # ===================== LOOP LIVE =====================

    def start_live(self):
        if not self.playing:
            self.playing = True
            self.status_label.config(text="Running...")
            self.update_frame()

    def pause_live(self):
        self.playing = False
        self.status_label.config(text="Paused")

    def update_frame(self):
        if not self.playing:
            return

        # ambil frame dari kamera
        frame_rgb = self.picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

        hasil, mask = self.process_frame(frame_bgr)
        self.display_frame(mask, hasil)

        # jadwalkan frame berikutnya
        self.root.after(10, self.update_frame)

    def close(self):
        self.playing = False
        try:
            self.picam2.stop()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = LaneDetectionLiveApp(root)
    root.mainloop()
