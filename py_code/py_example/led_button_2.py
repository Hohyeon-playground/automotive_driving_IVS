from gpiozero import LED, Button
import time

led = LED(17)
button = Button(2)
print("Press button.")
button.when_pressed = led.toggle

try:  
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Done")
finally:
    led.close()
    button.close()
