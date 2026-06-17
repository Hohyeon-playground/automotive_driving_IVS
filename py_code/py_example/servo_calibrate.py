from gpiozero import AngularServo
from time import sleep

min_pw = 0.5 / 1000
max_pw = 2.5 / 1000
center_pw = (min_pw + max_pw) / 2

servo = AngularServo(17, min_angle=0, max_angle=180,
                     min_pulse_width=min_pw, max_pulse_width=max_pw)

print("서보를 90도(정중앙)로 이동합니다.")
print("+ : 중앙 펄스 증가 (시계방향)")
print("- : 중앙 펄스 감소 (반시계방향)")
print("q : 종료 후 현재 값 출력\n")

servo.angle = 90

while True:
    print(f"현재 center_pw = {center_pw*1000:.4f} ms  (min={min_pw*1000:.4f}, max={max_pw*1000:.4f})")
    cmd = input("입력 (+/-/q): ").strip()

    if cmd == '+':
        center_pw += 0.05 / 1000
    elif cmd == '-':
        center_pw -= 0.05 / 1000
    elif cmd == 'q':
        break
    else:
        continue

    min_pw = center_pw - 1.0 / 1000
    max_pw = center_pw + 1.0 / 1000
    servo.close()
    servo = AngularServo(17, min_angle=0, max_angle=180,
                         min_pulse_width=min_pw, max_pulse_width=max_pw)
    servo.angle = 90

servo.close()
print(f"\n완료! servo.py에 적용할 값:")
print(f"  min_pulse_width={min_pw*1000:.4f}/1000, max_pulse_width={max_pw*1000:.4f}/1000")
