---
name: goal19_final
description: "GOAL19 완료 — 7-dataset 31-exp 통합 Mode A digital twin, 최종 모델·핵심 발견·구조적 한계"
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL19 Final — Unified 7-Dataset Mode A Digital Twin (2026-07-03 완료)

**Repo**: `C:/Users/junho/Documents/jump-opt-digital-twin/` (Desktop과 분리, git + MkDocs + GH Pages)
**Live docs**: https://wnsgh3810.github.io/jump-opt-digital-twin/
**GitHub**: https://github.com/wnsgh3810/jump-opt-digital-twin
**최종 모델 파일**: `code/goal19/goal19_final_model.json`
**invoke**: `/goal19` slash command (`~/.claude/commands/goal19.md`) 또는 GOAL19_PROMPT.md read

## 결과: Pure CAD 41,271 → 15,182 (−63.2%), 21 physical params, per-trial fudge 0개

Ablation: P0 41,271 → P1 로봇동역학 20,368(−50.6%) → P2 friction 15,744(−22.7%) → P3 contact 15,330 → P4 frontier λ=1 15,189 → P6 q_offset제거 15,182.

**최종 21 param**: mass/inertia/CoM 15 (M_foot_ex=0.227, arm_knee=0.020 등) + friction 4 (fv_hip=0.787, fv_knee=0.127, fc_hip=0.095, fc_knee=0.524) + contact 2 (solref_tc=0.00217, imp0=0.371). q_offset=ZERO.

## ★ 4대 핵심 발견 (비자명)

1. **부품 mass 오차가 최대 인자**: foot CAD 누락 +227g, knee armature. drop-test로 foot +24.9%, arm_knee +21.3%. **link inertia scale(I_*) 전부 무의미** — armature가 회전 흡수하므로 link I 재시도 불필요.
2. **마찰 이원성**: hip=점성(fv_hip=0.79), knee=쿨롱(fc_knee=0.52). sit2stand_gnd 발산 안정화.
3. **★★ per-trial q_offset 완전 불필요**: per-trial(62) = date-group(12) = zero(0) 전부 동일 score. 물리 모델이 q-tracking 완전 담당 → **62 fudge를 zero cost로 제거. 진짜 통합 달성.** (이전 GOAL들의 per-trial offset은 불필요했음.)
4. **★★ 점프 under-jump = 구조적 한계**: 점프 절대높이 실측의 44~76% (0424/0602 최악 0.44, 0421/0422 0.73-0.76). 원인 = sit2stand-최적 mass 과중 + friction 소산 + AK80-9 torque under-read 복합. tau_scale 진단 결과 **~1.6배 필요**(금지). h_ratio가 λ=8(friction≈0)에도 0.62 plateau = Mode-A 근본 에너지 결손. digital twin은 "측정 토크가 만드는 것"을 충실 재현; gap은 측정+통합모델 한계이지 sim 버그 아님. [[ak80_9_torque_calibration]]

## Exhaustive ablation (모델이 진짜 최적임을 확인)

Phase 8-9에서 미탐색 axis 전부 DROP → 놓친 개선 없음:
- **arm_hip**: DROP (0이 최적, 증가 시 단조 악화). hip 모터가 base 고정이라 rotor inertia 반사 안 됨 (arm_knee와 대조). Phase 1 lock=0 검증.
- **dt/timestep**: DROP (0.0005 최적, 0.0002·0.001 둘 다 −0.31%). integrator: jump=RK4, s2s=implicitfast 적절.
- **Stribeck 마찰** (velocity-dependent, `mjcb_passive`로 구현): +0.54% DROP. fv_hip 거의 불변(0.787→0.835) — viscous 낮추면 sit2stand 손실 > Stribeck static 보상. **속도-의존 마찰도 trade-off 못 깸.** C-V 균일 마찰 = Stribeck 동등.
- ★ `mujoco.set_mjcb_passive` 콜백은 **model 생성 후** 설정 필수 (from_xml_string 전에 걸면 "Python exception raised" 컴파일 에러). run_jump_sim/run_sit2stand_cycle을 wrap해서 stepping 범위에만 적용.

## 교훈 (코드)

- **clip 버그**: `eval_wrapper.clip_x`가 refine 확장 bound를 silently clip → 가짜 개선. bound 확장 시 clip 범위도 반드시 확장.
- **joint re-opt > sequential**: Phase 4 λ=1 결합 재최적화가 순차 phase(P1→2→3)를 능가 (15,330→15,189). greedy sequential은 미세 suboptimal 남김.
- sim engine `sub_sim_iter6v2.py` monkey-patch로 axis 주입 (S.MTS_LOCK, S.FV_HIP, S.ci_locked 등). 최적화·plot·anim 경로 모두 동일 config 써야 함(불일치 주의).

## 미해결 (구조적, 사용자 결정 필요)

- 점프 절대 높이: tau_scale(금지) 허용 또는 tendon/spring 에너지 물리 추가 필요.
- sit2stand_gnd_0319 q-tracking: friction으로 발산은 잡음, real squat 재현 안 됨 (Mode A GND 한계).

## 인프라

- 31-exp loader: `code/goal19/data_loaders/load_31exp.py` (canonical .npz를 goal18_v4/goal18_v5_unified/goal16/goal18_iter0R/goal12 등 여러 경로에서 탐색)
- 재사용 4-panel plotter: `templates/plot_4panel.py`, canonical anim helper: `templates/make_canonical_anim.py` (v14 LOCKED renderer 사용)
- Notion parent: `391ab81d-2550-81b9-a252-ea9233db7a87` (CONCEPT 아래), 최종 요약 갱신됨
- 금지 전부 준수: tau_scale ✗ / motor_tm LPF ✗ / per-trial fudge ✗(제거) / Mode B ✗ / kneeCurrentTorquePaper ✗
