import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import numpy as np

class LaneDetectionApp:
    def __init__(self, root, video_path):
        self.root = root
        self.root.title("Lane Detection Player (BEV + Offset)")
        self.video_path = video_path
        self.cap = cv2.VideoCapture(self.video_path)
        self.playing = False
        self.seeking = False

        # ===== Data video =====
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.fps = self.fps if self.fps and self.fps > 0 else 30
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0

        # Resolusi kerja (sinkron dengan transform BEV)
        self.frame_width = 640
        self.frame_height = 360

        # ===== Setup Bird Eye View (ala kode #3) =====
        self.src_points = np.float32([
            [0, self.frame_height],                              # kiri bawah
            [self.frame_width, self.frame_height],               # kanan bawah
            [int(self.frame_width * 0.2), int(self.frame_height * 0.3)],  # kiri atas
            [int(self.frame_width * 0.8), int(self.frame_height * 0.3)]   # kanan atas
        ])

        self.dst_points = np.float32([
            [0, self.frame_height],                              # kiri bawah
            [self.frame_width, self.frame_height],               # kanan bawah
            [0, 0],                                              # kiri atas
            [self.frame_width, 0]                                # kanan atas
        ])

        self.M = cv2.getPerspectiveTransform(self.src_points, self.dst_points)

        # ===== Area kontrol tampilan =====
        option_frame = ttk.Frame(root)
        option_frame.pack(pady=5)

        # Pilihan tampilan mask / deteksi
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

        # Pilihan mode BEV atau Normal
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

        # ===== Area video =====
        self.video_frame = ttk.Frame(root)
        self.video_frame.pack(padx=10, pady=10)
        self.mask_label = ttk.Label(self.video_frame)
        self.mask_label.grid(row=0, column=0, padx=10)
        self.result_label = ttk.Label(self.video_frame)
        self.result_label.grid(row=0, column=1, padx=10)

        # ===== Tombol kontrol =====
        control_frame = ttk.Frame(root)
        control_frame.pack(pady=5)
        ttk.Button(control_frame, text="▶️ Start", command=self.start_video).grid(row=0, column=0, padx=10)
        ttk.Button(control_frame, text="⏸ Pause", command=self.pause_video).grid(row=0, column=1, padx=10)
        ttk.Button(control_frame, text="❌ Exit", command=self.close).grid(row=0, column=2, padx=10)

        # ===== Slider progress =====
        self.progress_var = tk.DoubleVar()
        self.progress_slider = ttk.Scale(
            root, from_=0, to=self.duration, orient="horizontal",
            length=600, variable=self.progress_var,
            command=self.on_seek_drag
        )
        self.progress_slider.pack(pady=5)
        self.progress_slider.bind("<ButtonRelease-1>", self.on_seek_release)

        # ===== Label waktu =====
        self.time_label = ttk.Label(root, text="00:00 / 00:00")
        self.time_label.pack()

    # ========== Utilitas dasar ==========

    def format_time(self, seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m:02}:{s:02}"

    def start_video(self):
        if not self.playing:
            self.playing = True
            self.update_frame()

    def pause_video(self):
        self.playing = False

    def on_seek_drag(self, value):
        self.seeking = True
        current_time = float(value)
        self.time_label.config(
            text=f"{self.format_time(current_time)} / {self.format_time(self.duration)}"
        )

    def on_seek_release(self, event):
        self.seeking = False
        self.pause_video()
        new_time = float(self.progress_var.get())
        frame_number = int(new_time * self.fps)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.show_frame_once()

    # ========== Fungsi dari “kode #3” yang diadaptasi ==========

    def fuzzy_gamma(self, lux, brightness):
        L = np.clip(lux / 1500.0, 0, 1)
        B = np.clip(brightness / 100.0, 0, 1)

        dark = 1 - L
        bright = L
        too_dark = dark * (1 - B)
        too_bright = bright * B
        normal = 1 - np.abs(L - B)

        gamma = (1.6 * too_dark + 1.0 * normal + 0.4 * too_bright) / (too_dark + normal + too_bright + 1e-6)
        return float(np.clip(gamma, 0.4, 1.6))

    def measure_brightness(self, frame_bgr):
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))

    def apply_gamma(self, frame_bgr, gamma):
        inv = 1.0 / gamma
        lut = np.array([((i / 255.0) ** inv) * 255 for i in np.arange(256)]).astype("uint8")
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

    def detect_lane(self, frame_input, with_bev=True):
        """
        Adaptasi dari fungsi detect_lane di kode #3.
        Mengembalikan: frame_hasil (BGR), mask (gray), offset (px), arah (str)
        """
        if with_bev:
            frame_processed = cv2.warpPerspective(
                frame_input, self.M, (self.frame_width, self.frame_height)
            )
        else:
            frame_processed = frame_input.copy()

        hsv = cv2.cvtColor(frame_processed, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 200], dtype=np.uint8)
        upper_white = np.array([180, 70, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_white, upper_white)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        hasil = frame_processed.copy()
        height, width = mask.shape

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
        cv2.line(hasil, (center_frame, 0), (center_frame, height), (0, 255, 255), 2)
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
                    hasil, arrow_start, arrow_end, warna_offset, 3, tipLength=0.3
                )

        return hasil, mask, offset, arah

    # ========== Pemrosesan frame utama ==========

    def process_frame(self, frame):
        # Resize ke resolusi kerja
        frame = cv2.resize(frame, (self.frame_width, self.frame_height))

        # Brightness dan gamma (adaptasi kode #3, lux disimulasikan)
        brightness = self.measure_brightness(frame)
        lux_sim = brightness * 10.0  # dummy lux hanya untuk simulasi
        gamma = self.fuzzy_gamma(lux_sim, brightness)
        corrected = self.apply_gamma(frame, gamma)

        # Pilih mode view: Bird Eye atau Normal
        with_bev = (self.view_mode.get() == "Bird Eye")

        # Deteksi jalur
        hasil, mask, offset, arah = self.detect_lane(corrected, with_bev=with_bev)

        # Overlay informasi brightness, gamma, offset di hasil
        mode_txt = "BEV" if with_bev else "Normal"
        info_text = f"Mode:{mode_txt}  Bright:{brightness:.1f}  Gamma:{gamma:.2f}  Offset:{offset}px {arah}"
        cv2.putText(
            hasil, info_text, (10, 55),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2
        )

        return hasil, mask

    # ========== Tampilan frame ke UI ==========

    def display_frame(self, mask, hasil):
        mode = self.display_option.get()

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

    # ========== Pemutaran video ==========

    def update_frame(self):
        if not self.playing or self.seeking:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.playing = False
            return

        hasil, mask = self.process_frame(frame)
        self.display_frame(mask, hasil)

        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        current_time = current_frame / self.fps if self.fps > 0 else 0
        self.progress_var.set(current_time)
        self.time_label.config(
            text=f"{self.format_time(current_time)} / {self.format_time(self.duration)}"
        )

        self.root.after(int(1000 / self.fps), self.update_frame)

    def show_frame_once(self):
        ret, frame = self.cap.read()
        if ret:
            hasil, mask = self.process_frame(frame)
            self.display_frame(mask, hasil)

    def close(self):
        self.playing = False
        if self.cap:
            self.cap.release()
        self.root.destroy()


# ===== Jalankan aplikasi =====
if __name__ == "__main__":
    root = tk.Tk()
    app = LaneDetectionApp(root, "video 3 november.mp4")  # ganti dengan path videomu
    root.mainloop()
