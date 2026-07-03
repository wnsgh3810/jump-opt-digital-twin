# Jump-Opt Digital Twin — GOAL19

**Unified 7-dataset Mode A digital twin for a 2-DoF single-leg jump robot.**

> **최종 결과: Pure CAD 41,271 → 통합 모델 15,182 (−63.2%). 21 physical params, per-trial fudge 0개.**

## 🎬 Digital twin in action

v14 canonical animation, Mode A (실측 토크 replay). **점프 높이 sim vs real 라벨 표시** (Hsim / Hreal). 정수기: jump 접촉 integrator `implicitfast` 채택 (RK4 GRF chattering 제거).

| Position-PD jump (재현 우수, h_ratio 0.82) | Torque-command jump (under-jump, h_ratio 0.50) |
|---|---|
| ![pos jump](assets/anim/jump_position_0421_P70_phase1.gif) | ![torque jump](assets/anim/jump_0424_90_torque_phase1.gif) |

> **★ 핵심 진단 (재검증)**: 점프 under-jump은 균일하지 않다. **위치제어 점프(0421)는 h를 0.82로 잘 재현**하지만, **토크명령 점프(0424/0602)는 0.50으로 크게 미달**하며 *명령 토크가 클수록 더 나빠진다* (60_0.75: 0.56 → 150_2.2_500: 0.49). 이 split은 **AK80-9 전류→토크 under-read(포화)**의 지문이다 — 위치제어 τ는 PD로 계산돼 정확하고, 토크명령 τ는 포화 시 측정 전류토크가 실제 출력보다 작게 읽힌다. Mode A는 이 작게 읽힌 τ를 충실히 replay → 낮은 점프. **sim 버그가 아니라 측정 한계**이며, 유일한 보정 수단은 `tau_scale`(현재 금지, 이전 GOAL들의 "MASSIVE WIN" 축).

**Sim vs Real (최종 모델, 4-panel: q / dq / τ / GRF)** — 대표 예시:

| 좋은 점프 (position PD) | 고-PD 점프 | sit2stand |
|---|---|---|
| ![P70](assets/plots/jump_position_0421__P70_D0p75_P70_D2.png) | ![P100D3](assets/plots/jump_torque_0422__P100_D3.png) | ![s2s](assets/plots/sit2stand_0324__P20_D1.png) |

**Trade-off frontier** (jump vs sit2stand, Phase 4):

![frontier](assets/frontier.png)

전체 31개 sub-experiment plot은 각 [Phase 페이지](#phase)에 있습니다.

## 🏁 Ablation (Phase 0 → 6)

| Phase | Axis 추가 | Score | Δ | 핵심 |
|---|---|---:|---:|---|
| **0** | Pure CAD baseline | 41,271 | — | CAD only, no fudge |
| **1** | 로봇 동역학 (15D mass/inertia/CoM) | 20,368 | **−50.6%** | foot mass(+227g) + knee armature 지배 |
| **2** | joint friction (fv/fc 4D) | 15,744 | **−22.7%** | hip 점성 + knee 쿨롱; sit2stand_gnd 발산 안정화 |
| **3** | contact (solref/imp0 2D) | 15,330 | +2.6% | stiffer contact = sharp push-off |
| **4** | frontier re-opt (λ=1) | 15,189 | +0.9% | 결합 재최적화 > 순차 phase |
| **6** | per-trial q_offset 제거 (62→0) | **15,182** | fudge 0 | **완전 통합 달성** |

## 📊 최종 성적 (그룹별)

| 그룹 | n | mean score | jump h_ratio |
|---|---:|---:|---:|
| sit2stand | 7 | 436 | — (우수 재현) |
| jump_position_0421 | 6 | 251 | 0.734 |
| jump_torque_0422 | 3 | 467 | 0.761 |
| jump_0602 | 6 | 523 | 0.493 |
| jump_0424 | 9 | 676 | 0.442 |

## 🔑 핵심 발견

1. **부품 mass 오차가 최대 인자**: CAD가 foot에 ~227g, thigh/paddle mass를 놓침. drop-test로 확인 (foot mass +24.9%, knee armature +21.3%). Link inertia scale은 무의미 (armature가 회전 흡수).

2. **관절 마찰의 이원성**: hip = 점성(viscous) 지배, knee = 쿨롱(Coulomb) 지배. 물리적으로 타당하며 sit2stand_gnd 발산을 안정화.

3. **★ per-trial fudge 완전 불필요**: 62개 per-trial q_offset을 zero cost로 제거. 물리 모델이 q-tracking을 완전히 담당 → 진짜 통합 single param set.

4. **★ 점프 under-jump = 측정 한계 (재검증으로 정밀화)**: 이전엔 "mass 과중+friction+torque 복합"이라 했으나, 재검증 결과 **원인이 측정 방식별로 깔끔히 갈린다**. 위치제어 점프(PD 계산 τ)는 h_ratio 0.82로 잘 재현; 토크명령 점프(전류측정 τ)는 0.50이며 명령 토크↑일수록 악화 → **AK80-9 전류→토크 under-read(포화)**가 지배 원인. `tau_scale`(금지)로만 보정 가능. **digital twin은 "측정된 토크가 만드는 것"을 충실히 재현** — gap은 측정 한계이지 sim 버그가 아님 ([Phase 5 진단](phase_5/index.md)).

5. **재검증에서 반증된 가설들** (사용자 지적 축 전수 테스트): foot slip(μ 0.4→3.0) · real jump init pose · base_z offset — **모두 h_ratio 무변화 또는 악화**. GRF chattering(RK4)은 실재하나 **cosmetic** — `implicitfast`로 제거해도 h_ratio 0.563 불변 (score 15182→15121 소폭 개선만). 즉 under-jump의 원인은 이들이 아니라 위 4번(측정 한계)로 수렴.

## 🤖 최종 통합 모델 (21 params, 0 fudge)

```
mass/inertia/CoM (15): M_base=1.152 M_thigh=0.949 M_calf=0.906 M_p=1.411 M_c=0.944
                        M_foot_ex=0.227 I_thigh=1.181 I_calf=1.325 I_p=1.042 I_c=1.073
                        com_dz_thigh=-0.005 com_dx_thigh=0.001 com_dz_calf=-0.018
                        com_dx_calf=-0.010 arm_knee=0.020
friction (4):          fv_hip=0.787 fv_knee=0.127 fc_hip=0.095 fc_knee=0.524
contact (2):           solref_tc=0.00217 imp0=0.371
q_offset:              ZERO
```
→ `code/goal19/goal19_final_model.json`

**금지 준수**: `tau_scale` ✗ · `motor_tm` LPF ✗ · per-trial fudge ✗(제거) · Mode B ✗ · `kneeCurrentTorquePaper` CSV ✗

## 📖 Phase 상세

- [Phase 0 — Pure CAD Baseline](phase_0/index.md)
- [Phase 1 — 로봇 동역학](phase_1/index.md)
- [Phase 2 — Joint friction](phase_2/index.md)
- [Phase 3 — Contact compliance](phase_3/index.md)
- [Phase 4 — Trade-off frontier ★](phase_4/index.md)
- [Phase 5 — Torque-deficit 진단 ★](phase_5/index.md)
- [Phase 6 — q_offset 제거 ★](phase_6/index.md)
- [Phase 8 — untested axes ablation (완전성)](phase_8/index.md)
- [Phase 9 — Stribeck friction (DROP, torque ceiling 확인)](phase_9/index.md)
- [Phase 10 — LODO cross-validation ★ (일반화 입증, ratio 1.04)](phase_10/index.md)

## 🚧 미해결 (구조적, 사용자 결정 필요)

- **점프 절대 높이**: tau_scale(금지) 허용 또는 tendon/spring 에너지 물리 추가 필요.
- **sit2stand_gnd q-tracking**: 발산은 잡았으나 real squat 재현 안 됨 (Mode A GND 한계).

## 🔗 Repository / Data

- Source: [GitHub](https://github.com/wnsgh3810/jump-opt-digital-twin)
- Data: `Desktop/jump_opt/` (canonical .npz, 31 sub-experiments)
- Renderer: v14 canonical (`goal18_CANONICAL/code/make_anim.py`, LOCKED)
