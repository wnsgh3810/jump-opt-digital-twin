---
name: mass-ledger-truth
description: "부위별 질량의 진짜 출처와 경계 (사용자 확정 08-02) — thigh 1.05kg은 knee모터 포함 묶음, crank/base는 적합, \"CAD VERIFIED\" 블록은 실은 적합값"
metadata: 
  node_type: memory
  type: project
  originSessionId: fcd547c7-41bc-4112-9159-2d1f317a3cc9
  modified: 2026-08-02T11:13:47.369Z
---

**사용자 확정 (2026-08-02)** — 마라톤 G Phase 1 질량 파라미터의 단일 출처.

| 부위 | 값 | 성격 | 취급 |
|---|---|---|---|
| **thigh + knee 모터 (한 묶음)** | **1.05 kg** | 실측 (묶음으로만 잼) | 허벅지와 knee모터가 **붙어서 함께 회전** → 한 바디 |
| ↳ knee 모터 단독 | **480 g** | 실측 | 묶음 내 분해용 (구조분 ≈ 570 g) |
| coupler (푸시로드) | **150 g** | 실측 (07-07 채팅, 코드 LOCK) | 고정 |
| shank (발 포함) | **≈0.237 kg** | CAD | ±경계 (조립 해석 불확실) |
| **crank** | **최소 0.4 kg** | 정확히 못 잼 | **적합** (하한 0.40) |
| **base** | — | 실측 없음 | **적합** |
| rocker | 별도 질량 없음 | — | **shaft와 한 몸** |
| 총질량 | **3.26~3.30 kg** | 실측 (케이블 제거) | 등식 제약 |

**사용자 단서**: "결합하는 과정에서 동역학에서 어떻게 해석될지 정확하지 않아서 **바운더리를 갖고
해석**해야 한다" → 실측값도 하드 고정이 아니라 경계로 다룰 것.

**함의**: 구 Notion 원본 `m1 = 1.05213, r1 = 0.05646`이 이미 **묶음 기준으로 옳았다**.
GOAL9 Iter4 적합이 이걸 0.91281(−13.2%)로 깎았고, 그 값이 `build_xml_i38_standalone.py`에
"CAD constants — VERIFIED, DO NOT CHANGE"라는 헤더로 굳어 있다 → **CAD 아님, 적합값**.
같은 블록에서 `M_C_CAD`는 실제 crank, `M_P_CAD`는 실제 coupler로 **라벨이 뒤바뀌어** 있다.
"crank 360g 실측"도 실측이 아니라 P13e CMA-ES 적합 출력이 문서를 거치며 승격된 것.

관련: [[robot-mass-slip-facts]] · [[metric-provenance-rule]] · [[goal23-knowledge-inventory]]
