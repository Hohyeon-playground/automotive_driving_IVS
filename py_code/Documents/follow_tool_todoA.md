# Follow-Tool 할 일 목록

## [완료]
- [x] OS 환경 구성 (Ubuntu 24.04 + ROS2 Jazzy)
- [x] OpenCV 설치 (4.13.0)
- [x] GStreamer + libcamera + GTK 연동
- [x] ArUco 마커 calibration
- [x] 카메라 테스트 (Picamera, USB 카메라 2종)
- [x] 손 인식 구현 및 동작 확인 (라즈비안 환경, Hailo hef 모델)
- [x] ArUco 마커 출력 및 부착 (발 마커 ID / 홈 마커 ID 구분)

## [사전 확인 필요] — 오늘 중 확정
- [ ] 2번 완료 제스처 팀 내 합의
- [ ] 사용 중인 Hailo 모델명 확인 (손모양팀) — `hand_gesture_node` import 경로에 필요
- [ ] 발 마커 ID / 홈 마커 ID 번호 확인 (마커팀) — `aruco_node` 분기 조건에 필요

## [단위 구현] — 06.15 (오늘) 목표
- [ ] `hand_gesture_node` — Ubuntu 직접 환경에서 Hailo 재확인 후 /gesture 토픽 퍼블리시
- [ ] `aruco_node` — 아래 카메라로 발/홈 마커 ID별 tvec_x, tvec_z 퍼블리시
- [ ] `motor_node` — /motor_cmd 수신 → 서보 조향각, DC ON/OFF/PWM 제어

## [통합] — 06.16 목표
- [ ] `state_machine_node` — 4개 상태, 전환 조건 구현
- [ ] 전체 노드 연결
- [ ] 개별 상태 단위 테스트 (② 접근만, ④ 복귀만 등)

## [전체 루프 테스트] — 06.17 목표
- [ ] 실제 차량에서 ①→②→③→④→① 루프 1회 완주
- [ ] tvec_z 임계값 초기 설정 (발 마커 / 홈 마커)
- [ ] 서보 조향각 범위 초기 설정

## [튜닝 + 검증] — 06.18~20
- [ ] 서보 조향각 fine-tuning
- [ ] 1번 제스처 N프레임 값 조정 (오인식 vs 반응속도 균형)
- [ ] 마커 소실 디바운싱 (잠깐 소실 시 상태 유지)
- [ ] 엣지 케이스 검증 (마커 소실, 오인식, 홈 마커 탐색 실패 등)
- [ ] 장애물 회피 (초음파, 여유 있을 때)

## [마무리] — 06.21~22
- [ ] 발표 자료 준비
- [ ] 시연 리허설
