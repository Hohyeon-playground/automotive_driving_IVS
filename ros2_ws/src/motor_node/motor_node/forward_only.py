import rclpy
from rclpy.node import Node
from gpiozero import OutputDevice, PWMOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

GPIO_CHIP = 4
SERVO_PIN = 17
DC_IN1    = 23
DC_IN2    = 24
DC_ENA    = 25

SERVO_CENTER = 0.071
DC_SPEED     = 0.78


class ForwardOnlyNode(Node):
    def __init__(self):
        super().__init__('forward_only_node')

        factory = LGPIOFactory(chip=GPIO_CHIP)

        self.servo = PWMOutputDevice(SERVO_PIN, frequency=50, pin_factory=factory)
        self.in1   = OutputDevice(DC_IN1, pin_factory=factory)
        self.in2   = OutputDevice(DC_IN2, pin_factory=factory)
        self.ena   = PWMOutputDevice(DC_ENA, frequency=1000, pin_factory=factory)

        self.servo.value = SERVO_CENTER
        self.in1.off()
        self.in2.on()
        self.ena.value = DC_SPEED

        self.get_logger().info("전진 시작!")

    def destroy_node(self):
        self.in1.off()
        self.in2.off()
        self.ena.value = 0
        self.servo.value = SERVO_CENTER
        self.servo.off()
        self.in1.close()
        self.in2.close()
        self.ena.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ForwardOnlyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
