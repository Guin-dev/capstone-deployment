# 🚗 Lane Detection Web UI

Modern web interface untuk monitoring lane detection system dari Raspberry Pi.

## ✨ Features

- 🎥 **Real-time Video Streaming** - MJPEG stream dari Flask backend
- 📊 **Live Metrics** - Offset, direction, gamma, lux, brightness, FPS  
- 🎨 **Modern UI** - Glassmorphism design dengan dark theme
- 📱 **Responsive** - Desktop & mobile friendly
- ⚙️ **Configurable** - Ganti IP Raspberry Pi dengan mudah
- 🖥️ **Fullscreen Mode** - Untuk monitoring yang lebih fokus

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd lane-detection-ui
npm install
```

### 2. Run Development Server

```bash
npm run dev
```

Buka browser ke: **http://localhost:3000**

### 3. Configure Raspberry Pi IP

1. Klik tombol **"Configure"** di dashboard
2. Masukkan IP address Raspberry Pi (contoh: `192.168.1.100`)
3. Klik **"Save & Reconnect"**

## 📋 Prerequisites

### Di Raspberry Pi

1. **Copy `stream_server.py`** ke Raspberry Pi
2. **Install dependencies:**
   ```bash
   pip install flask flask-cors opencv-python picamera2
   ```
3. **Run Flask server:**
   ```bash
   python stream_server.py
   ```
4. **Verify** - Akses http://<PI_IP>:5000/ dari browser untuk test

### Di Mac (Development)

1. Next.js sudah ready (folder ini)
2. Pastikan Mac dan Pi dalam **network yang sama**
3. Pastikan **port 3000 available** untuk Next.js

## 🎯 How It Works

```
Raspberry Pi Camera → Lane Detection (OpenCV) → Flask Server (MJPEG) → Next.js (Browser)
```

## 🐛 Troubleshooting

**Video tidak muncul:**
1. Check Flask server running di Pi: `http://<PI_IP>:5000/`
2. Check network connectivity (ping Pi dari Mac)
3. Check browser console untuk error

**Metrics tidak update:**
1. Check `/api/status` endpoint: `http://<PI_IP>:5000/api/status`

## 📝 Next Steps

- [ ] Deploy Flask server ke Raspberry Pi
- [ ] Test MJPEG streaming
- [ ] Test Next.js frontend

## 👨‍💻 Credits

Built with Next.js, React,TailwindCSS, and Flask.
