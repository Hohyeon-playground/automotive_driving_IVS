import rclpy
from rclpy.node import Node
from motor_interfaces.msg import MotorCmd
from gpiozero import OutputDevice, PWMOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

# ── GPIO 설정 ──
GPIO_CHIP  = 4
SERVO_PIN  = 17
DC_IN1     = 23
DC_IN2     = 24
DC_ENA     = 25

# ── 서보 값 ──
SERVO_CENTER = 0.071   # 1.425ms (min=0.5ms, max=2.35ms 기준 중앙)
SERVO_LEFT   = 0.025   # 0.5ms (최대 좌조향)
SERVO_RIGHT  = 0.118   # 2.35ms (최대 우조향)

# ── DC 모터 속도 ──
DC_SPEED      = 0.78
DC_TURN_SPEED = 0.70

# ── 모드 ──
MODE_STOP    = 0
MODE_FORWARD = 1
MODE_ROTATE  = 2

class MotorNode(Node):
    def __init__(self):
        super().__init__('motor_node')

        factory = LGPIOFactory(chip=GPIO_CHIP)

        self.servo = PWMOutputDevice(SERVO_PIN, frequency=50, pin_factory=factory)
        self.in1   = OutputDevice(DC_IN1, pin_factory=factory)
        self.in2   = OutputDevice(DC_IN2, pin_factory=factory)
        self.ena   = PWMOutputDevice(DC_ENA, frequency=1000, pin_factory=factory)

        self.servo.value = SERVO_CENTER
        self.stop()

        self.current_mode  = MODE_STOP
        self.current_steer = 0.0

        self.sub = self.create_subscription(
            MotorCmd, '/motor_cmd', self.motor_cmd_callback, 10
        )

        self.get_logger().info("Motor Node 시작!")

    def set_servo(self, angle):
        angle = max(-1.0, min(1.0, angle))
        if angle >= 0:
            value = SERVO_CENTER + (SERVO_RIGHT - SERVO_CENTER) * angle
        else:
            value = SERVO_CENTER + (SERVO_LEFT - SERVO_CENTER) * (-angle)
        self.servo.value = max(SERVO_LEFT, min(SERVO_RIGHT, value))

    def forward(self):
        self.in1.off()
        self.in2.on()
        self.ena.value = DC_SPEED

    def rotate(self):
        self.in1.on()
        self.in2.off()
        self.ena.value = DC_TURN_SPEED

    def stop(self):
        self.in1.off()
        self.in2.off()
        self.ena.value = 0

    def motor_cmd_callback(self, msg):
        self.set_servo(msg.steer_angle)
        self.current_steer = msg.steer_angle

        if msg.mode == MODE_STOP:
            self.stop()
        elif msg.mode == MODE_FORWARD:
            self.forward()
        elif msg.mode == MODE_ROTATE:
            self.rotate()
        else:
            self.get_logger().warn(f"알 수 없는 mode: {msg.mode}")
            self.stop()
            return

        if msg.mode != self.current_mode:
            mode_name = {MODE_STOP: "정지", MODE_FORWARD: "전진", MODE_ROTATE: "회전"}
            self.get_logger().info(
                f"[{mode_name[msg.mode]}] steer={msg.steer_angle:+.2f}"
            )
            self.current_mode = msg.mode

    def destroy_node(self):
        self.stop()
        self.servo.value = SERVO_CENTER
        self.servo.off()
        self.in1.close()
        self.in2.close()
        self.ena.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MotorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
