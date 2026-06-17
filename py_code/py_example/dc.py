from gpiozero import OutputDevice, PWMOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory
from time import sleep

GPIO_CHIP = 4
IN1_PIN = 23
IN2_PIN = 24
ENA_PIN = 25

factory = LGPIOFactory(chip=GPIO_CHIP)

in1 = OutputDevice(IN1_PIN, pin_factory=factory)
in2 = OutputDevice(IN2_PIN, pin_factory=factory)
ena = PWMOutputDevice(ENA_PIN, frequency=1000, pin_factory=factory)

def forward():
    in1.off()
    in2.on()
    ena.value = 0.78

def backward():
    in1.on()
    in2.off()
    ena.value = 0.70

def stop():
    in1.off()
    in2.off()
    ena.value = 0

print("DC Motor Test... Press Ctrl+C to exit")

try:
    while True:
        print("Forward")
        forward()
        sleep(2)

        print("Stop")
        stop()
        sleep(1)

        print("Backward")
        backward()
        sleep(2)

        print("Stop")
        stop()
        sleep(1)

except KeyboardInterrupt:
    print("Stopping...")
    stop()
    in1.close()
    in2.close()
    ena.close()
