import time
import rclpy
from rclpy.node import Node
from motor_interfaces.msg import MotorCmd
from gpiozero import OutputDevice, PWMOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

# ── GPIO 설정 ──
GPIO_CHIP  = 4
SERVO_PIN  = 17        # 서보 Signal
DC_IN1     = 23        # L298N IN1
DC_IN2     = 24        # L298N IN2
DC_ENA     = 25        # L298N ENA (PWM)

# ── 서보 값 (실측 캘리브레이션) ──
SERVO_CENTER = 0.071   # 중립 (직진)
SERVO_LEFT   = 0.040   # 최대 좌조향
SERVO_RIGHT  = 0.095   # 최대 우조향

# ── DC 출력 튜닝값 ──
DRIVE_BASE     = 0.50   # 직진 순항 PWM
DRIVE_TURN_SLOW = 0.15  # 조향각 비례 출력 감산 (회전 반경 축소)
DRIVE_MIN      = 0.35   # 회전 중 최소 출력 (스크럽 저항 극복, 스톨 방지)
KICK_STRAIGHT = 0.70   # 정지→전진 기동킥 (직진)
KICK_STEER    = 0.85   # 정지→전진 기동킥 (조향 중 출발)
KICK_T        = 0.20   # 기동킥 지속 시간 (초)
DC_TURN_SPEED = 0.70   # MODE_ROTATE 탐색 출력

# ── 모터 모드 (state_machine_node 규약과 동일) ──
MODE_STOP    = 0
MODE_FORWARD = 1
MODE_ROTATE  = 2

class MotorNode(Node):
    def __init__(self):
        super().__init__('motor_node')

        # gpiozero LGPIOFactory로 통일 (서보/DC 충돌 방지)
        factory = LGPIOFactory(chip=GPIO_CHIP)

        # 서보모터 초기화
        self.servo = PWMOutputDevice(SERVO_PIN, frequency=50, pin_factory=factory)
        self.servo.value = SERVO_CENTER

        # DC모터 초기화
        self.in1 = OutputDevice(DC_IN1, pin_factory=factory)
        self.in2 = OutputDevice(DC_IN2, pin_factory=factory)
        self.ena = PWMOutputDevice(DC_ENA, frequency=1000, pin_factory=factory)

        # 초기 정지
        self.stop()

        # 현재 상태 저장
        self.current_mode  = MODE_STOP
        self.current_steer = 0.0

        # /motor_cmd 구독
        self.sub = self.create_subscription(
            MotorCmd, '/motor_cmd', self.motor_cmd_callback, 10
        )

        self.get_logger().info("Motor Node 시작!")
        self.get_logger().info("mode: 0=정지 / 1=전진 / 2=제자리회전")
        self.get_logger().info(
            f"서보: 중립={SERVO_CENTER} 좌={SERVO_LEFT} 우={SERVO_RIGHT}"
        )
        self.get_logger().info(
            f"DC: base={DRIVE_BASE} turn_slow={DRIVE_TURN_SLOW} min={DRIVE_MIN} "
            f"kick_s={KICK_STRAIGHT} kick_t={KICK_T}s"
        )

    # ── 서보 제어 ──
    def set_servo(self, angle):
        """
        angle: -1.0(최대 좌) ~ 0.0(중립) ~ 1.0(최대 우)
        state_machine_node calc_steer() 출력 범위와 동일
        """
        angle = max(-1.0, min(1.0, angle))
        if angle >= 0:
            value = SERVO_CENTER + (SERVO_RIGHT - SERVO_CENTER) * angle
        else:
            value = SERVO_CENTER + (SERVO_LEFT - SERVO_CENTER) * (-angle)
        self.servo.value = max(SERVO_LEFT, min(SERVO_RIGHT, value))

    # ── DC모터 속도 계산 ──
    def drive_speed(self, steer_angle):
        """
        직진 = DRIVE_BASE (0.50)
        많이 꺾을수록 출력 감소 → 관성/언더스티어 억제로 회전 반경 축소
        DRIVE_MIN으로 하한 보호 (바퀴 정지 방지)
        """
        return max(DRIVE_MIN, DRIVE_BASE - DRIVE_TURN_SLOW * abs(steer_angle))

    # ── DC모터 제어 ──
    def forward(self, steer_angle=0.0):
        """전진: IN1=OFF, IN2=ON"""
        self.in1.off()
        self.in2.on()
        self.ena.value = self.drive_speed(steer_angle)

    def forward_kick(self, steer_angle):
        """
        정지→전진 전환 시 1회 기동킥
        정지마찰 극복을 위해 순간 높은 출력 인가
        """
        self.in1.off()
        self.in2.on()
        self.ena.value = KICK_STEER if abs(steer_angle) > 0.15 else KICK_STRAIGHT
        time.sleep(KICK_T)

    def rotate(self):
        """제자리 회전: IN1=ON, IN2=OFF (홈 마커 탐색용)"""
        self.in1.on()
        self.in2.off()
        self.ena.value = DC_TURN_SPEED

    def stop(self):
        """정지: IN1=OFF, IN2=OFF, ENA=0"""
        self.in1.off()
        self.in2.off()
        self.ena.value = 0

    # ── /motor_cmd 콜백 ──
    def motor_cmd_callback(self, msg):
        """
        state_machine_node로부터 /motor_cmd 수신
        msg.mode        : 0=정지 / 1=전진 / 2=제자리회전
        msg.steer_angle : -1.0(좌) ~ 0.0(중립) ~ 1.0(우)
        """
        # 1) 조향 적용 (항상)
        self.set_servo(msg.steer_angle)

        # 2) 주행 모드 적용
        if msg.mode == MODE_STOP:
            self.stop()

        elif msg.mode == MODE_FORWARD:
            # 정지→전진 전환 시 기동킥 1회 적용
            if self.current_mode != MODE_FORWARD:
                self.forward_kick(msg.steer_angle)
            self.forward(msg.steer_angle)

        elif msg.mode == MODE_ROTATE:
            self.rotate()

        else:
            self.get_logger().warn(f"알 수 없는 mode: {msg.mode}")
            self.stop()
            self.current_steer = msg.steer_angle
            return

        # 3) 모드 변경 시 로그 출력
        if msg.mode != self.current_mode:
            mode_name = {
                MODE_STOP:    "정지",
                MODE_FORWARD: "전진",
                MODE_ROTATE:  "회전"
            }
            self.get_logger().info(
                f"[{mode_name[msg.mode]}] "
                f"steer={msg.steer_angle:+.2f} "
                f"spd={self.drive_speed(msg.steer_angle):.2f}"
            )
            self.current_mode = msg.mode

        self.current_steer = msg.steer_angle

    # ── 종료 처리 ──
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
