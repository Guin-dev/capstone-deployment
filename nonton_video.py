import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import numpy as np

class LaneDetectionApp:
    def __init__(self, root, video_path):
        self.root = root
        self.root.title("Lane Detection Player with View Options")
        self.video_path = video_path
        self.cap = cv2.VideoCapture(self.video_path)
        self.playing = False
        self.seeking = False

        # Data video
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0

        # === Area kontrol tampilan ===
        option_frame = ttk.Frame(root)
        option_frame.pack(pady=5)
        ttk.Label(option_frame, text="Tampilkan:").pack(side=tk.LEFT, padx=5)
        self.display_option = tk.StringVar(value="Keduanya")
        view_choices = ["Keduanya", "Mask Saja", "Deteksi Saja"]
        self.view_selector = ttk.Combobox(option_frame, textvariable=self.display_option,
                                          values=view_choices, state="readonly", width=15)
        self.view_selector.pack(side=tk.LEFT, padx=5)

        # === Area video ===
        self.video_frame = ttk.Frame(root)
        self.video_frame.pack(padx=10, pady=10)
        self.mask_label = ttk.Label(self.video_frame)
        self.mask_label.grid(row=0, column=0, padx=10)
        self.result_label = ttk.Label(self.video_frame)
        self.result_label.grid(row=0, column=1, padx=10)

        # === Tombol kontrol ===
        control_frame = ttk.Frame(root)
        control_frame.pack(pady=5)
        ttk.Button(control_frame, text="▶️ Start", command=self.start_video).grid(row=0, column=0, padx=10)
        ttk.Button(control_frame, text="⏸ Pause", command=self.pause_video).grid(row=0, column=1, padx=10)
        ttk.Button(control_frame, text="❌ Exit", command=self.close).grid(row=0, column=2, padx=10)

        # === Slider progress ===
        self.progress_var = tk.DoubleVar()
        self.progress_slider = ttk.Scale(root, from_=0, to=self.duration, orient="horizontal",
                                         length=600, variable=self.progress_var,
                                         command=self.on_seek_drag)
        self.progress_slider.pack(pady=5)
        self.progress_slider.bind("<ButtonRelease-1>", self.on_seek_release)

        # === Label waktu ===
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
        self.time_label.config(text=f"{self.format_time(current_time)} / {self.format_time(self.duration)}")

    def on_seek_release(self, event):
        self.seeking = False
        self.pause_video()
        new_time = float(self.progress_var.get())
        frame_number = int(new_time * self.fps)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.show_frame_once()

    # ========== Pemrosesan frame ==========
    def process_frame(self, frame):
        frame = cv2.resize(frame, (640, 360))
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 70, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

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

        # ROI visual (garis biru)
        cv2.polylines(hasil, [polygon], True, (255, 0, 0), 2)

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
            total_cx, count = 0, 0
            for cnt in contours_list:
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    total_cx += int(M["m10"] / M["m00"])
                    count += 1
            return total_cx // count if count > 0 else None

        pos_kiri = hitung_posisi(kiri_contours)
        pos_tengah = hitung_posisi(tengah_contours)
        pos_kanan = hitung_posisi(kanan_contours)

        # Garis tengah kamera
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

        return hasil, mask

    # ========== Tampilan frame ==========
    def display_frame(self, mask, hasil):
        mode = self.display_option.get()
        mask_rgb = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        imgtk_mask = ImageTk.PhotoImage(image=Image.fromarray(mask_rgb))
        imgtk_result = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(hasil, cv2.COLOR_BGR2RGB)))

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
        current_time = current_frame / self.fps
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


# === Jalankan aplikasi ===
root = tk.Tk()
app = LaneDetectionApp(root, "video 3 november.mp4")
root.mainloop()
