# Jump-Opt Digital Twin — GOAL19

**Unified 7-dataset Mode A digital twin for a 2-DoF single-leg jump robot.**

> **최종 결과: Pure CAD 41,271 → 통합 모델 15,182 (−63.2%). 21 physical params, per-trial fudge 0개.**

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

4. **★ 점프 under-jump = 구조적 한계**: 점프 절대 높이는 실측의 44~76% (데이터셋별). 원인 = sit2stand-최적 mass(과중) + friction 소산 + AK80-9 torque under-read 복합. tau_scale(금지)로만 보정 가능. **digital twin은 "측정된 토크가 만드는 것"을 충실히 재현** — gap은 측정·통합모델 한계이지 sim 버그가 아님 ([Phase 5 진단](phase_5/index.md)).

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

## 🚧 미해결 (구조적, 사용자 결정 필요)

- **점프 절대 높이**: tau_scale(금지) 허용 또는 tendon/spring 에너지 물리 추가 필요.
- **sit2stand_gnd q-tracking**: 발산은 잡았으나 real squat 재현 안 됨 (Mode A GND 한계).

## 🔗 Repository / Data

- Source: [GitHub](https://github.com/wnsgh3810/jump-opt-digital-twin)
- Data: `Desktop/jump_opt/` (canonical .npz, 31 sub-experiments)
- Renderer: v14 canonical (`goal18_CANONICAL/code/make_anim.py`, LOCKED)
