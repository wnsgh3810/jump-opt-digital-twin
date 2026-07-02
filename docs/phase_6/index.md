# Phase 6 — q_offset ablation (★ per-trial fudge 완전 제거)

**Status**: ✅ 완료 (2026-07-03)
**결과**: per-trial q_offset **완전 불필요** → **62 fudge param 전부 제거, zero cost**

## 동기

사용자 명시: per-trial fudge 회피. 이전 모델은 iter1에서 계승한 per-trial q_offset (31 sub × 2 joint = **62 fudge param**)을 사용. 물리 모델(Phase 1-4)이 완성된 지금, 이 offset이 여전히 필요한가?

## 방법

Phase 4 채택 모델 위에서 3가지 offset 전략 비교:

| 전략 | fudge param | total | s2s | jump |
|---|---:|---:|---:|---:|
| per-trial (현재) | 62 | 15,189 | 3,053 | 12,136 |
| date-group 평균 | 12 | 15,184 | 3,048 | 12,136 |
| **zero (제거)** | **0** | **15,182** | 3,055 | 12,127 |

## ★★★ 발견 — fudge 완전 제거

**zero offset이 per-trial과 동일 (오히려 −0.0% 미세 개선).** 즉 per-trial q_offset은 현재 물리 모델에서 **전혀 기여하지 않음**. 이유: offset은 원래 초기 모델의 q-tracking 오차를 보정하려 fit됐으나, mass+friction+contact가 제대로 fit된 지금은 물리 모델이 q-tracking을 완전히 담당 → offset은 잔여 noise.

**→ 62개 per-trial fudge를 zero cost로 전부 제거. 사용자가 원한 "완전 통합 single param set" 달성.**

## GOAL19 최종 통합 모델

```
21 physical params, 0 fudge:
  mass/inertia/CoM (15): M_base=1.152, M_thigh=0.949, M_calf=0.906, M_p=1.411,
                          M_c=0.944, M_foot_ex=0.227, I_thigh=1.181, I_calf=1.325,
                          I_p=1.042, I_c=1.073, com_dz_thigh=-0.005, com_dx_thigh=0.001,
                          com_dz_calf=-0.018, com_dx_calf=-0.010, arm_knee=0.020
  friction (4):          fv_hip=0.787, fv_knee=0.127, fc_hip=0.095, fc_knee=0.524
  contact (2):           solref_tc=0.00217, imp0=0.371
  q_offset:              ZERO (fully unified)
```
→ `code/goal19/goal19_final_model.json`. **Score 15,182 (−63.2% vs Pure CAD 41,271).**

**금지 준수**: tau_scale ✗, motor_tm LPF ✗, per-trial fudge ✗ (제거), Mode B ✗.

## Files

- Runner: `code/goal19/phase6/run_phase6_qoffset.py`
- Result: `phase6_qoffset.json`
- **최종 모델**: `code/goal19/goal19_final_model.json`
