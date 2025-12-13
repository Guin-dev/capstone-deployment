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
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 90, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        height, width = mask.shape
        roi = np.zeros_like(mask)
        polygon = np.array([[
            (0, height), (width, height),
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
            self.result_label.grid_forget()  # sembunyikan deteksi

        elif mode == "Deteksi Saja":
            self.result_label.configure(image=imgtk_result)
            self.result_label.imgtk = imgtk_result
            self.result_label.grid(row=0, column=0)
            self.mask_label.grid_forget()  # sembunyikan mask

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

#aktivasi venv
#.venv\Scripts\activate