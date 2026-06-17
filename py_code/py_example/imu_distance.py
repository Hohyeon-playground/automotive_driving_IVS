import time
from mpu6050 import mpu6050

sensor = mpu6050(0x68)

vx = 0.0
dx = 0.0
last_t = time.time()

bx = 0.0
cal_s = 100

for _ in range(cal_s):
    acc = sensor.get_accel_data()
    bx += acc['x']
    time.sleep(0.01)
    
bx /= cal_s

try:
    while True:
        cur_t = time.time()
        dt = cur_t - last_t
        last_t = cur_t

        acc = sensor.get_accel_data()
        
        ax = acc['x'] - bx

        if abs(ax) < 0.2: 
            ax = 0.0

        vx += ax * dt
        dx += vx * dt

        print(f"Accel: {ax:5.2f} | Vel: {vx:5.2f} | Dist: {dx:5.2f}")
        
        time.sleep(0.05) 

except KeyboardInterrupt:
    pass