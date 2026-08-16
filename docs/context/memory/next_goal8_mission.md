---
name: next-goal8-mission
description: "GOAL8 미션 — Mode B Digital Twin 정밀화. PD sim 기반 fit, q/dq/τ/GRF 매칭 목적"
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# ★ GOAL8 Mission — Mode B 정밀화

## 미션
**Mode B를 진짜 PD sim (공중 hold + dq_des=0) 기준으로 다시 fit. 디지털 트윈 완성도 ↑.**

## 핵심 원칙
- **목적**: 위치(q) + 속도(dq) + 토크(τ) + 지반력(GRF) 매칭. 점프 높이는 검증 지표일 뿐 목표 아님
- **이유**: 점프 높이만 맞추면 overfit. 물리적 정확한 모델이 실 robot 배포 시 generalize
- **공중 phase ref**: last q_des hold + dq_des=0 (실 robot 제어와 동일)

## 출발점
- Mode B FINAL: Stage 39, BO score 371.70 (옛 sim 기준)
- PD sim 결과: q1=0.028, q2=0.053, τ1=6.40, GRF=25.36 (평균 RMSE), jump 62-74 cm
- Mode A FINAL 206.48 대비 80% 큼 → 큰 잠재력

## Phase 전략 (8+단계, open-ended 발전)
1. **★★★ BO 재실행** (가장 큰 효과): 옛 sim → PD sim score function으로 다시 BO
2. **★★★ Torque saturation ±18 Nm**: 실 motor 한계 명시
3. **★★ D term LPF**: firmware derivative noise filter
4. **★ Gear backlash**: 정/역 전환 dead zone
5. **★ Per-phase PD**: stance vs flight 다른 gain
6. **Weighting 재조정**: τ weight 추가
7. **Non-linear PD scaling**: αkp(error) 의존
8. **Final ablation**
9+. **Stage 2 baseline 재BO** (점프보다 q/GRF 우선)
10. **Contact 정밀화** (cone elliptic, impratio, margin)
11. **m_foot_extra** (GOAL7 S20 axis)
12. **Multi-seed verification**
13. **Sensor delay** (q feedback)
14. **Per-PD αkp scaling** (GOAL7 S23)
15. **Residual learning** (small NN)
16+. **계속 발전** — q1<0.020, GRF<15 N 달성까지 phase 추가

## 목표 수치
- Mode B score ~250대 (Mode A 수준)
- q1 RMSE ~0.020, q2 RMSE ~0.035, τ RMSE ~3 Nm, GRF RMSE ~15 N

## 페이지 작성 규칙 (요약)
- Mode B callout 맨 위
- 자세한 narrative (개요/변경/Why/결과/해석/용어/학습)
- 6 trial × 4-panel 비교 plot (자연 색 auto cycle)
- 6 trial × anim (T_after=0.8s, V25 스타일)
- 점프 높이 = max base_z (바닥부터)
- 새 용어 항상 보충 설명
- **★ Variable Base/BO Best 비교 표** (GOAL7 Stage 53 형식) — Variable / Base (CAD+jf=0.1) / BO Best / 단위 / 의미. **Base = GOAL7 Base Model (CAD + jf=0.1, 다른 axis 모두 0/∞) — 모든 stage 동일 기준**. BO Best = 현재 stage의 best params. → stage 진화 추적 가능
- **★ Animation V25 스타일**: skybox(gradient), headlight(diffuse 0.6/ambient 0.3), groundplane reflectance=0.2, malgun.ttf, 흰글자+검은 stroke, 검은 박스 ❌, cam az=135 el=-15 dist=1.2, 80f 60ms

## 참조 문서
- 전체 프롬프트: `C:\Users\junho\CVT\jump_opt\NEXT_GOAL8_MODE_B_REFINEMENT.md`
- 점프 높이 정의: 바닥 z=0부터 max base_z 절대 거리
- Plot 색: matplotlib auto, sim/real 매칭은 get_color()
- 애니메이션 스타일: V25 (흰글자+검은 outline, malgun.ttf, 검은 박스 없음)

[[goal7-final-results]] [[feedback-plot-colors]]
