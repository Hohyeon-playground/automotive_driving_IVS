import cv2
import numpy as np
from picamera2 import Picamera2
from time import sleep

picam2 = Picamera2()

config = picam2.create_preview_configuration(main={"size": (320, 240), "format": "RGB888"})
picam2.configure(config)
picam2.start()

w = 320
h = 240

while True:
    image = picam2.capture_array()
    rgb_img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    hsv_img = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([40, 255, 255])
    
    mask = cv2.inRange(hsv_img, lower_yellow, upper_yellow)
    
    search_top = 3 * h // 4
    search_bot = 3 * h // 4 + 20
    mask[0:search_top, :] = 0
    mask[search_bot:, :] = 0

    M = cv2.moments(mask)
    
    if M["m00"] > 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        
        cv2.circle(image, (cx, cy), 10, (0, 0, 255), -1)
        
        err = cx - w // 2
        print(f"Yellow center x: {cx}, y: {cy}, err: {err}")
    
    cv2.imshow("test", image)
    cv2.imshow("mask", mask) 

    if cv2.waitKey(3) & 0xFF == 27: 
        break

cv2.destroyAllWindows()
picam2.stop()
