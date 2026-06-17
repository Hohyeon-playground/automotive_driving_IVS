import cv2
import subprocess

result = subprocess.run(["rpicam-hello", "--list-cameras"], capture_output=True, text=True)
cams = [line.split('(')[1].split(')')[0] for line in result.stdout.split('\n') if '/base/axi' in line]

if len(cams) < 2:
    exit()

opts = "! video/x-raw,width=640,height=480,framerate=15/1,format=RGBx ! videoconvert ! video/x-raw,format=BGR ! appsink max-buffers=1 drop=true sync=false"

pipe0 = f"libcamerasrc camera-name={cams[0]} {opts}"
pipe1 = f"libcamerasrc camera-name={cams[1]} {opts}"

cap0 = cv2.VideoCapture(pipe0, cv2.CAP_GSTREAMER)
cap1 = cv2.VideoCapture(pipe1, cv2.CAP_GSTREAMER)

try:
	while True:
		ret0, img0 = cap0.read()
		ret1, img1 = cap1.read()

		if not ret0 or not ret1:
			break

		cv2.imshow("Camera 1", img0)
		cv2.imshow("Camera 2", img1)

		if cv2.waitKey(1) & 0xFF == 27:
			break
except KeyboardInterrupt:
    pass

cap0.release()
cap1.release()
cv2.destroyAllWindows()
