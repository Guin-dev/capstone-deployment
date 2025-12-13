import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import numpy as np

class LaneDetectionApp:
    def __init__(self, root, video_path):
        self.root = root
        self.root.title("Lane Detection HMI")
        self.video_path = video_path
        self.cap = cv2.VideoCapture(self.video_path)
        self.playing = False

        # Layout
        frame_container = ttk.Frame(root)
        frame_container.pack(padx=10, pady=10)

        self.mask_label = ttk.Label(frame_container, text="Mask Putih")
        self.mask_label.grid(row=0, column=0, padx=10)
        self.result_label = ttk.Label(frame_container, text="Hasil Deteksi Garis")
        self.result_label.grid(row=0, column=1, padx=10)

        control_frame = ttk.Frame(root)
        control_frame.pack(pady=10)
        ttk.Button(control_frame, text="▶️ Start", command=self.start_video).grid(row=0, column=0, padx=10)
        ttk.Button(control_frame, text="⏸ Pause", command=self.pause_video).grid(row=0, column=1, padx=10)
        ttk.Button(control_frame, text="❌ Exit", command=self.close).grid(row=0, column=2, padx=10)

    def start_video(self):
        if not self.playing:
            self.playing = True
            self.update_frame()

    def pause_video(self):
        self.playing = False

    def update_frame(self):
        if not self.playing:
            return
        ret, frame = self.cap.read()
        if not ret:
            self.playing = False
            return

        frame = cv2.resize(frame, (640, 360))

        # === Deteksi lane ===
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

        # === Konversi ke format Tkinter ===
        mask_rgb = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        imgtk_mask = ImageTk.PhotoImage(image=Image.fromarray(mask_rgb))
        imgtk_result = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(hasil, cv2.COLOR_BGR2RGB)))

        # Update UI tanpa flicker
        self.mask_label.imgtk = imgtk_mask
        self.mask_label.configure(image=imgtk_mask)
        self.result_label.imgtk = imgtk_result
        self.result_label.configure(image=imgtk_result)

        # Jadwalkan refresh frame berikutnya (tanpa while loop)
        self.root.after(30, self.update_frame)

    def close(self):
        self.playing = False
        if self.cap:
            self.cap.release()
        self.root.destroy()

root = tk.Tk()
app = LaneDetectionApp(root, "video panjang 2.mp4")
root.mainloop()
