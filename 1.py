import cv2, time, csv, os
import numpy as np
from picamera2 import Picamera2
import board, busio, adafruit_tsl2591

# ========================== SETUP SISTEM ==========================
durasi = int(input("Durasi logging (detik): "))

i2c = busio.I2C(board.SCL, board.SDA)
tsl = adafruit_tsl2591.TSL2591(i2c)

cam = Picamera2()
cam.configure(cam.create_video_configuration(main={"size": (640,480)}))
cam.start(); time.sleep(0.3)

test = cam.capture_array()
IS_RGB = np.mean(test[:,:,0]) > np.mean(test[:,:,2])

out = "/home/mbasis/output_integrated_fast"
os.makedirs(out, exist_ok=True)
ts = int(time.time())
csv_path = f"{out}/log_{ts}.csv"
vid_path = f"{out}/vid_{ts}.mp4"
writer = cv2.VideoWriter(vid_path, cv2.VideoWriter_fourcc(*"mp4v"), 30, (640,480))

# ========================== FUNGI UTAMA ==========================
def fuzzy_gamma(lux, b):
    L = np.clip(lux/1500, 0, 1); B = np.clip(b/100, 0, 1)
    td = (1-L)*(1-B); tb = L*B; n = 1-abs(L-B)
    g = (1.6*td + n + 0.4*tb)/(td+n+tb+1e-6)
    return float(np.clip(g,0.4,1.6))

def gamma_corr(f, g):
    inv = 1/g
    lut = np.array([((i/255)**inv)*255 for i in range(256)],dtype="uint8")
    return cv2.LUT(f,lut)

def bird_eye(frame):
    h,w,_ = frame.shape
    src = np.float32([[0,h],[w,h],[w*0.2,h*0.3],[w*0.8,h*0.3]])
    dst = np.float32([[0,h],[w,h],[0,0],[w,0]])
    M = cv2.getPerspectiveTransform(src,dst)
    return cv2.warpPerspective(frame,M,(w,h))

def lane_offset(frame):
    h,w,_ = frame.shape
    mask = cv2.inRange(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV),
                       np.array([0,0,200]), np.array([180,70,255]))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5),np.uint8))
    cnt,_ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cx_list=[]
    for c in cnt:
        if cv2.contourArea(c)>300:
            M=cv2.moments(c)
            if M["m00"]!=0: cx_list.append(int(M["m10"]/M["m00"]))
    if not cx_list: return None,None
    cx = int(sum(cx_list)/len(cx_list))
    off = (w//2)-cx
    return cx, off

# ========================== LOOP UTAMA ==========================
fps = 0.0
start=time.time()
fps_t = time.time(); fps_c=0

with open(csv_path,"w",newline="") as f:
    log = csv.writer(f); log.writerow(["time","lux","gamma","offset"])

    while time.time()-start < durasi:
        lux = tsl.lux or 0
        frm = cam.capture_array()
        if IS_RGB: frm=cv2.cvtColor(frm,cv2.COLOR_RGB2BGR)

        bri = np.mean(cv2.cvtColor(frm, cv2.COLOR_BGR2GRAY))
        g = fuzzy_gamma(lux,bri)
        frm = gamma_corr(frm,g)

        bev = bird_eye(frm)
        cx,off = lane_offset(bev)

        # overlay
        cv2.putText(bev,f"Lux:{lux:.1f}  gamma:{g:.2f}",(10,25),
                    cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)
        if off is not None:
            arah = "KIRI" if off>5 else "KANAN" if off<-5 else "TENGAH"
            cv2.putText(bev,f"Offset:{off}px {arah}",(10,55),
                        cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,255),2)

        # FPS
        fps_c+=1
        if time.time()-fps_t>=1:
            fps=fps_c/(time.time()-fps_t)
            fps_t=time.time(); fps_c=0
        cv2.putText(bev,f"FPS:{fps:.1f}",(10,85),
                    cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,0,0),2)

        cv2.imshow("FAST Lane + Gamma + BEV", bev)
        writer.write(bev)
        log.writerow([time.strftime("%H:%M:%S"), lux, g, off])
        f.flush()

        if cv2.waitKey(1)&0xFF==ord('q'): break

writer.release()
cv2.destroyAllWindows()
cam.stop()

print("\n[DONE] Video:", vid_path)
print("      CSV  :", csv_path)
