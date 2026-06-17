import cv2

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("카메라 열기 실패!")
    exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

print("USB 카메라 미리보기 시작!")
print("q: 종료 / s: 이미지 저장")

count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("프레임 읽기 실패")
        break

    cv2.putText(frame, "Press 's' to save, 'q' to quit",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 255, 0), 2)
    cv2.putText(frame, f"Saved: {count}",
                (10, 60), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 255, 0), 2)

    cv2.imshow("USB Camera Preview", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        filename = f"/home/ivs/calib_images_usb/calib_{count:03d}.jpg"
        cv2.imwrite(filename, frame)
        print(f"저장: {filename}")
        count += 1

cap.release()
cv2.destroyAllWindows()
