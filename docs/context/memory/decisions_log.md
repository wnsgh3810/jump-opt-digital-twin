---
name: Major Decisions Log
description: Sim-to-Real gap 연구 진행 중 내려진 주요 모델링/파라미터/방법 결정과 그 근거
type: project
originSessionId: c82aa01d-1bc5-42d3-ad69-d2998821e712
---
# 주요 의사결정 기록

각 결정의 맥락, 선택, 근거, 결과를 기록. 코드 수정 같은 routine 결정은 제외하고 architectural / 모델링 결정만 정리.

---

## Decision 1: alpha 모델에서 GRF에 alpha 곱하기 (2026-04-17)
**Context:** `혹시2.py`에서 `CONTACT_MODEL='alpha'`일 때 그래프와 impulse 계산이 alpha 곱해지지 않은 raw GRF를 사용 중이었음.
**Choice:** `u_grf_val[1,:] *= params['alpha']`로 결과 추출 직후 alpha 곱하도록 수정. 플롯/impulse/에너지 모두 body가 받는 GRF 기준으로 변경.
**Rationale:** 사용자가 "지면이 로봇을 미는 힘"의 정의를 명확히 하고 싶어함. alpha 모델의 물리적 의미는 "GRF의 α만큼이 body로 전달, 나머지는 접촉 컴플라이언스에 흡수".
**Outcome:** 후속 분석에서 alpha=0.712가 P40 impulse 0.1% 오차로 매칭 확인.

## Decision 2: M_tot = 3.268 kg (2026-04-18)
**Context:** Notion 페이지에 M_tot=2.469로 잘못 표기되어 있던 것을 사용자가 발견.
**Choice:** 정확한 값 `M(1.02) + m1(1.05213) + m2(0.237) + m_c(0.80898) + m_p(0.14977) = 3.268 kg` 사용.
**Rationale:** 모든 동역학 분석의 기준이 되는 값.
**Outcome:** 노션, .md 파일, 메모리 모두 수정. 단, 이후 4/22-23 분석에서 GRF 기반 실측 질량 M_grf ≈ 3.0 kg과 5-9% 차이가 있음을 발견 (레일 마찰 + 모델 오차).

## Decision 3: 분석 기준은 적분값(Impulse, Energy), peak 무시 (2026-04-18)
**Context:** 시뮬레이션은 토크 saturation에 계속 붙어있지만, 실제 토크는 잠깐 peak를 찍음. peak 매칭 시도들이 실패.
**Choice:** Scoring에서 peak는 무시하고 **Impulse 적분값과 Energy 적분값을 매칭**. 사용자 명시적 요청.
**Rationale:** "각 수치의 최대값은 너무 신경 안써도 되지 않을까? Real Data를 보면 토크도 올라가다가 한순간만 최고점을 찍고..."
**Outcome:** 모든 후속 sweep이 적분값 기반으로 동작. param_sweep series, friction_sweep series, pd_param_fit, 169M sweep 등.

## Decision 4: PD 게인 분석 불필요 (2026-04-18)
**Context:** 초기 분석에서 PD 추적 오차가 +14J 추가 에너지를 만든다고 분석.
**Choice:** PD 분석 빼고 동역학(위치/속도/토크/GRF)만 분석.
**Rationale:** 사용자: "위치 속도 토크, GRF로 동역학을 분석하는데 PD 분석이 꼭 필요할까? 시뮬레이션에서의 임펄스, 모터 에너지의 갭이 실제와 크게 차이나는 이유, 조건, 원인을 분석하는거니까"
**Outcome:** 분석 방향이 동역학 모델 자체(접촉, 마찰, 질량) + 토크 saturation 변경에 집중. PD 시뮬레이션은 4/22 토크 프로파일 형태 매칭 단계에서 다시 도입됨.

## Decision 5: 945-config sweep 결과 → final.py 파라미터 (2026-04-19)
**Context:** Soft+alpha+마찰 945개 조합 sweep 완료.
**Choice:** **alpha=0.90, k_c=5000, b_c=50, rail_friction=5, joint_friction=0.3, tau_lim=15** 채택.
**Rationale:** 모든 지표(h, Imp, E, dq2, E/(Imp)²) 2% 이내, 점프 높이 오차 0.9%. score=4로 압도적 1위.
**Outcome:** `final.py`에 반영. 후속 모든 분석/실험의 baseline.

## Decision 6: 입력 토크 기준으로 에너지 계산 (2026-04-19)
**Context:** Sweep에서 W = ∫τ_shaft·dq를 사용했는데, real data의 currentTorque는 입력 토크(전류 기반)임. 비교가 불공정.
**Choice:** Sweep 코드 수정하여 `E_input = ∫|τ·dq| + ∫(jf·dq²) + ∫(rf·dz²)`로 마찰 손실 포함.
**Rationale:** Real의 currentTorque는 모터 전류로 추정한 토크라 마찰 이기는 토크까지 포함. 시뮬도 같은 기준이어야 함.
**Outcome:** Sweep 다시 돌림. 결과적으로 alpha 모델 + 마찰 조합이 크게 변하지 않음 (이미 마찰이 작아서).

## Decision 7: 토크 saturation = 입력 토크 기준 (2026-04-22)
**Context:** 최적화에서 출력 토크에 saturation 걸려 있었음.
**Choice:** `|τ_out + jf·dq| <= τ_lim`로 입력 토크에 saturation.
**Rationale:** 사용자 명시: "saturation이 입력 토크에 걸려야". 실제 모터는 최종 출력(전류)이 제한됨.
**Outcome:** final.py 수정. 기존 결과는 비슷하지만 더 물리적으로 정확.

## Decision 8: z_kin (foot at z=0) 사용, z_pos 아님 (2026-04-22)
**Context:** Excel 저장에서 base_height를 z_pos(soft contact 시 body 높이, delta 포함)로 저장했었음.
**Choice:** `z_kin_arr = -(l1·sin(q1) + l2·sin(q1+q2))` 사용. 발이 z=0에 고정된 가정의 운동학적 높이.
**Rationale:** 하드웨어에서 발이 지면에 닿아있고 base가 따라 움직이는 물리적 조건. 사용자: "하드웨어 물리적 조건때문".
**Outcome:** final.py와 sweep.py 모두 수정. base_height 정의가 일관됨.

## Decision 9: PD sim에서 v_des=0 (Pure Damping) (2026-04-23)
**Context:** PD sim의 dq_peak가 real보다 30% 빠름 (sim 30 vs real 21 rad/s).
**Choice:** `tau = Kp*(q_des-q) - Kd*dq` (v_des=0). MIT mode 매뉴얼 확인 후 적용.
**Rationale:** AK80-9 매뉴얼에서 위치제어 시 v_des=0으로 보내는 것이 표준. Kd 항이 순수 댐핑(`-Kd·dq`)으로 작동. 사용자가 "0으로 보내고 있어" 확인.
**Outcome:** Stance 297→301ms, dq2 29.6→24.5로 즉각 개선. PD sim 발전의 결정적 전환점.

## Decision 10: 드라이버 값(P=200, D_h=1.5, D_k=4.0) 직접 사용 (2026-04-23)
**Context:** PD gain을 회귀로 추정한 값(Kp=140) 사용 중이었으나, v_des=0 적용 후 새로 검증 필요.
**Choice:** AK80-9 드라이버 설정값을 그대로 Nm/rad 단위로 사용 (sp=sd=1.0).
**Rationale:** 회귀 추정값은 v_des를 따라가는 PD 가정 하에서 fitted된 값이라 v_des=0에서는 무의미. 드라이버 값 그대로가 가장 단순하고 hip/knee 일관성 있음.
**Outcome:** 모든 6개 실험에서 Impulse 89~102%로 일관 매칭 확인.

## Decision 11: tau_lim = 30 Nm (2026-04-24)
**Context:** AK80-9 매뉴얼 토크 범위 -18~+18 Nm. 초기 sweep에서 tau_lim=15 saturation이 문제였고, tau_lim=20이 best로 나옴.
**Choice:** **tau_lim = 30 Nm** (매뉴얼 한계의 1.67배).
**Rationale:** Saturation이 풀려야 stance time이 real(300ms)에 가까워짐. 사용자 지시: "30까지 올려서 모든 실험 시뮬레이션 해봐". 실측 peak 토크가 18~20 Nm까지 가는 것 관찰됨.
**Outcome:** 6개 실험 stance time 크게 개선 (P60: 393→315ms, real 320ms). 모든 실험 95-105% impulse 매칭. pd_sim.py에 반영.

## Decision 12: 169M Sweep — Dynamics + Friction 동시 식별 (2026-04-24)
**Context:** Sweep best가 hip torque ~10Nm RMSE로 큰 오차. gAv=0.30이 CAD(1.36)와 너무 다름.
**Choice:** Scoring에 hip torque + 중간 1/3 구간 토크 추가. dynamics 파라미터(Is1, Is2, Kv) + 마찰(cf, jf) 모두 sweep 변수에 포함. 13개 파라미터 × 169,344,000 configs.
**Rationale:** Sweep best가 sys ID 결과와 다르다는 것은 dynamics 모델 자체가 부정확하다는 신호. 한꺼번에 다 식별.
**Outcome:** Numba JIT + 14 cores multiprocessing으로 ~6시간 소요. **Best**: Is1=0.065, Is2=0.005, Kv=0.011, gAv=0.30, gBv=0.50, alpha=0.85, kc=7000, bc=80, sp=1.5, sd=2.0, tm=10ms, cf=0.40, jf=0.080. P200에서 q1=1.4°, q2=0.7°, hip torque RMSE 4.2 Nm. 그러나 여전히 lift-off transient에서 hip torque +20Nm spike.

## Decision 13: System ID Direction B — Jumping 데이터 직접 ID (2026-04-25)
**Context:** Hip torque 한계가 모델 구조 문제일 가능성. Sweep으로 한계.
**Choice:** Sit2stand ID 결과 대신 **jumping 데이터로 직접 regressor 회귀**.
**Rationale:** 사용자: "지금 다이나믹스가 틀린거일 수도 있잖아... 다른 방법이 있을까? 반복해서 오래 고심하고 냉철하게 분석 비판해봐". Sit2stand는 free dynamics만 식별 가능. Jumping의 contact + body coupling은 jumping 데이터에서만 정확히 식별됨.
**Outcome:** v1-v3 실패 (kinematic degeneracy: rigid contact ddz가 ddq의 함수). v4 (soft contact ddz, kc/bc=7000/80) → Av=0.131이 CAD와 일치. **v5 (multi-trial P60-P200, friction 고정): gAv=1.57 ≈ CAD 1.36**. Sweep의 gAv=0.30이 비물리적이고 ALPHA=0.85가 보상 구조임을 확인.

## Decision 14: ALPHA=1.0 고정 + 재 Sweep (2026-04-25)
**Context:** Multi-trial ID에서 gAv≈CAD가 합리적. ALPHA가 진짜 물리값을 가리고 있다는 의심. 이전에 4가지 선택지(A/B/C/D)를 제시함:
- **A) 현재 sweep 유지**: fit은 좋지만 ALPHA fudge factor가 물리적으로 의심됨
- **B) ALPHA=1.0 고정 후 재 sweep**: 진짜 물리적 sim 만들어 v5 ID 결과(gAv≈1.4)와 비교 ← 채택됨
- **C) 데이터 보강**: sit2stand + jumping 합친 ID (friction 분리 가능)
- **D) Iterative**: ID → sim 검증 → 안 맞으면 Av,Bv만 fine-tune

**Choice:** **B 채택**, gAv 범위를 CAD 중심(0.8, 1.0, 1.2, 1.36, 1.5, 1.7, 1.9)으로 변경. 58M configs sweep.
**Rationale:** 사용자: "B로 해보자 범위도 합지적으로 키우고". 진짜 물리적 sim을 만들어 v5 ID 결과(gAv≈1.4)와 비교 가능한 baseline 확보. ALPHA=1로 GRF 100% body 전달 = 진짜 물리값.
**Outcome:** v1 58M는 OOM 사망 → v2 588M (밤새 14h ETA) 24M(4%)에서 또 OOM. 두 번 다 Claude Code도 같이 사망. ALPHA=1.0 baseline은 미확보 — 미해결 상태.

## Decision 15: A안 (Soft contact ddz로 ID 재시도) 우선 (2026-04-25)
**Context:** 사용자 "Foot length가 뭐야" 질문 → foot length 추가는 sim 복잡도 크게 올라가고 hip transient 5° 차이 완벽히 잡을 보장 없음.
**Choice:** **A안 (soft contact ddz로 System ID 재시도)이 더 빠르게 답이 나올 가능성** → A 채택.
**Rationale:** 사용자: "A로 가자". Foot length 추가는 ankle DOF + heel/toe 두 점 GRF + CoP 이동 모델링 필요해 복잡. Soft contact ddz_real = ddz_kin - ddelta는 kc/bc 알고 있으니 즉시 가능.
**Outcome:** v4에서 Av=0.131이 CAD와 일치 (효과 있음 확인) but hip R²=-0.17 — 이후 sanity check + tight mask 60-240ms + multi-trial로 진화 (v5에서 gAv=1.57 도달).

---

## 진행 중 결정 / Open Questions

- ALPHA=1.0 sweep 결과가 좋으면 진짜 물리 모델로 확정. 결과가 나쁘면 모델 구조 문제 (foot length, body pitch DOF, time delay).
- Hip torque lift-off spike 원인은 여전히 미해결. Sweep으로는 한계 확인됨.
- Sys ID에서 friction 자유롭게 두면 overfitting (jumping 중 dq 부호 안 바뀜 → friction params degenerate). Sit2stand + jumping 합친 ID가 본질적 해결책일 수 있음.
