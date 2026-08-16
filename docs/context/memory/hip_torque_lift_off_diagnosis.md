---
name: Hip Torque Lift-Off Spike Diagnosis
description: Sim hip 토크 lift-off transient에 +20Nm spike 발생 원인의 정량 분석 — 5°×Kp(300)=26Nm 산술과 foot length 부재로 설명됨
type: project
originSessionId: cb42ed46-5d3f-447a-94f6-732ce10d7dfc
---
# Hip Torque Lift-Off Spike — 진단 정리

## 증상

| 시간 영역 | Real hip torque | Sim hip torque | 비고 |
|---|---|---|---|
| 0~270ms | ±2 Nm 진동 | 부드러움 (0Nm 근처) | 평균값 비슷, 진동 양상만 다름 |
| **270~286ms (lift-off 직전)** | **+5 Nm 수준** | **+20 Nm까지 spike** | **15Nm 차이 — 핵심 문제** |

## 산술적 근거 — 5° × Kp = 26 Nm

PD law는 sim과 real이 동일하게 `tau = Kp*(q_des - q) - Kd*dq`. 따라서 토크가 다르면 q 또는 dq가 다르다는 뜻.

그래프에서 hip angle이 **250ms 이후 분기**:
- Real: -73° 근처에서 부드럽게 종료
- Sim: -78°까지 더 뻗어나감 (5° 차이)

5° = 0.0873 rad × **Kp_hip = 300 Nm/rad** ≈ **26 Nm 오차** — 그래프의 spike 크기와 정확히 일치.

→ Sim의 hip이 실제보다 더 펴지면서 PD law가 큰 토크 명령 → spike 발생.

## 근본 원인 — Foot length 부재 (point contact 가정)

현재 모델 운동학:
```
hip ──l1── knee ──l2── 발끝(점) = 접촉점
접촉점 위치: z = -l1·s1 - l2·s12
```

실제 로봇:
```
hip ──l1── knee ──l2── ankle ──l_foot── toe
접촉점은 발바닥 따라 이동 (heel → toe로 ZMP 굴러감)
```

**Lift-off 순간**:
- **실제**: 발바닥 길이만큼 토크를 더 받을 수 있어 (toe push-off) hip이 천천히 펴짐
- **점 접촉 sim**: toe push-off 효과 없음 → sim hip이 먼저 풀리며 PD law 큰 에러 → 26Nm spike

## Foot length 추가의 복잡함

| 추가 요소 | 부담 |
|---|---|
| `z_foot = -l1·s1 - l2·s12` (ankle 위치) | OK |
| `toe = z_foot - l_foot·sin(q_ankle)` | **ankle DOF 추가 필요** |
| 또는: 발바닥 평평 가정 + 접촉점이 heel/toe 사이 미끄러짐 (CoP 이동 모델링) | 복잡 |
| 간단화: 그냥 l2 살짝 늘려서 effective shank+foot으로 처리 | 가능 |

## 4가지 진단 방향 (선택지 분석)

문제는 **sweep으로는 한계**임 — 같은 모델 구조에서 변수 더 추가해도 수렴 limit 있음. 모델 구조 자체에 빠진 게 있으면 어떤 파라미터 조합도 못 맞춤.

빠진 모델 요소들:
| 빠진 것 | 영향 |
|---|---|
| **Foot geometry** (현재 point contact) | 이륙 transient |
| Body pitch DOF (현재 z축만) | 실제 body 회전 |
| Time delay (현재 1차 lag만) | 실제 PD 응답 |
| CVT 컴플라이언스 | 4-bar 링크 |
| Encoder quantization | 14bit → 진동 |
| 모터 백래시 | 기어 백래시 |
| PD 실제 구조 | AK80-9 MIT mode |

방향 A (모델 구조 개선): foot length / body pitch / pure delay 추가 — sim 복잡도 ↑, 효과 보장 못 함  
방향 B (Jumping 데이터로 직접 System ID): 채택됨 → v1~v6 narrative

## 결론 (현재 sim 받아들이기 옵션)

q 오차 ~1°, hip torque RMSE ~4Nm. 대부분 잘 맞고 **lift-off transient만 틀림**. 분석에는 충분히 유용 — Phase 16 이후로 확장하지 않으면 이걸로 학위/논문 가능.

## 데이터에서 z/dz 직접 측정 가능?

사용자 질문: "ddz는 속도 아니까 dz 알 수 있잖아 그거 미분하면 되는거 아냐?"  
**답**: real data엔 q1, q2, dq1, dq2, tau1, tau2, GRF만 있음. z, dz, ddz는 모두 kinematic 가정(z = -l1·s1 - l2·s12)으로 계산해야 함 → ddz가 ddq의 함수 → System ID 축퇴(degeneracy) 발생.

**해결**: IMU body acceleration 측정이 있으면 직접 ID 가능. 현재 데이터엔 IMU 없음.
