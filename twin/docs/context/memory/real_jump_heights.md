---
name: real-jump-heights
description: 26.06.02 실 robot 점프 높이 데이터 (Real Data.txt) — 정확한 값 출처
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# 실제 점프 높이 (26.06.02 Real Data.txt)

**위치**: `C:\Users\junho\CVT\Data\26_06_02\position\{trial}\Real Data.txt`
(2026-08-16 이사 반영. 폴더 이름의 점이 밑줄로 바뀌었다: `26.06.02` → `26_06_02`)

각 파일 첫 줄에 `실제 점프 높이 : X.XXm` 또는 `Estimated final jump height` 표기.

| Trial | 실제 점프 높이 |
|---|---|
| 60_0.75_60_2 | **0.94 m** |
| 60_1.5_60_1.5 | **0.96 m** |
| 90_0.75_90_2 | **0.98 m** |
| 120_2_120_2 | **0.94 m** |
| 150_2.2_250_3 | **0.90 m** |
| 150_2.2_500_5 | **0.85 m** (Estimated) |

**범위**: 85-98 cm

**★★★ 중대 정정 (2026-07-04): 이 숫자들은 firmware의 "Estimated final jump height" projection이지, base apex 실측이 아님.** Real Data.txt를 뜯어보니(예: 26.04.24/90_0.75_90_2) firmware가 그 순간 **base 수직속도 0.076 m/s, base 높이 0.415m**라 기록하면서도 **"Estimated jump height 0.995m"**라 적음 — 0.076 m/s로는 0.0003m밖에 못 뜨므로 이 "높이"는 base apex가 아니라 **무릎 속도 spike(24.4 rad/s)에서 뽑은 projection이고 near-full-extension 특이점을 무시해 ~1.6-1.9배 과대추정**함. **측정 관절각을 로봇 기구학(발 planted FK)으로 전파하면 실제 도약높이 ≈0.56m** (0424=0.564, 0602=0.466). Jacobian: 측정 관절속도→base 도약속도 2.39 m/s(0.89m는 4.19 요구). **→ 점프 "under-jump"은 sim/모델 결함이 아니라 이 firmware 지표가 부풀려진 탓. 디지털 트윈의 0.56-0.75m가 물리적으로 정직한 높이.** 상세: [[goal19_underjump_diagnosis]].

**★ 미확인 (사용자 확인 필요)**: 0.89m를 외부측정(영상/자/모캡)으로 검증했으면 series compliance 실재(SEA 필요), firmware 값만이면 지표 artifact(트윈이 정답).

**Why:** Phase 14-16 Notion 페이지에 "62-74 cm"라고 잘못 적었음. 임의 추정값이었고, 실제 데이터와 다름. (단 위 firmware 값도 base apex 실측 아님 — 위 정정 참조.)

**How to apply:** 점프 높이 언급 시 firmware 값(85-98cm)은 "firmware projection"으로 명시. 물리적 도약높이는 기구학상 ~0.56m. 둘을 구분할 것.

관련: [[goal8_findings]] [[next_goal8_mission]]
