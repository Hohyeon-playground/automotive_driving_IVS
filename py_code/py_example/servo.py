from gpiozero import AngularServo
from time import sleep

servo = AngularServo(17, min_angle=0, max_angle=180,
                    min_pulse_width=0.5/1000, max_pulse_width=2.35/1000)

print("Servo Control... Press Ctrl+C to exit")

try:
    while True:
        print("Angle: 0")
        servo.angle = 0
        sleep(1)

        print("Angle: 90")
        servo.angle = 90
        sleep(1)

        print("Angle: 180")
        servo.angle = 180
        sleep(1)

except KeyboardInterrupt:
    print("Stopping...")
    servo.detach()
