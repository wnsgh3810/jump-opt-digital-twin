---
name: goal7-base-model
description: GOAL7 base model 정의 — CAD 모델 + joint friction 0.1만 있던 초기 baseline
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL7 Base Model (비교 기준)

**모든 stage 변경사항은 이 base model에 무엇을 추가/변경했는지로 설명한다.**

## Base Model 구성

- **Body**: CAD 모델 (M=1.02kg base, m1=1.05kg thigh, m2=0.237kg calf, m_c=0.81kg motor on calf, m_p=0.15kg payload, 그 외 r1/r2/r_c/r_p 및 I1/I2/I_c/I_p CAD 그대로)
- **Joint**: hinge × 2 (hip, knee), base slide z
- **★ Friction**: joint friction (frictionloss) = **0.1** (모든 joint 동일)
- **Damping**: 없음 (또는 0)
- **Stiffness**: 없음
- **Contact**: sphere foot 1 point (radius 0.023m), MuJoCo default solref/solimp
- **Motor model**: 없음 (실측 토크 또는 PD 명령 직접 ctrl로)
- **Integrator**: Euler, dt=0.002, cone=pyramidal

## Why

- **Why**: GOAL7 모든 BO 변경사항은 이 base model 대비 무엇을 추가했는지로 설명되어야 함. 사용자가 명확히 지시한 비교 기준점.
- **How to apply**: 새 stage 페이지/설명/문서 작성 시 항상 "base model (CAD + jf=0.1) 대비" 형식으로 변경사항 기술.

## 적용 위치

- `goal6/stage*.py` 모든 BO 스크립트
- Notion stage 페이지 "📌 Base Model" 섹션
- MASTER_FINDINGS.md 모든 비교

[[goal7-final-results]]
