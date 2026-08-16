# GOAL4 — Real Robot Validation + Multi-Simulator Expansion (2026-06-06)

> **GOAL3에서 simulation으로 사용자 metric 완전 통과** (NLP τ_diff 0.0001/0.003 Nm, knee self-cons 0.16).
> 
> **GOAL4**: 실 robot 실험 + 모델 정밀화 + **CAD → URDF → MuJoCo MJX / Newton / IsaacLab** gradient-based opt 확장.

---

## 📌 한 줄 Mission

> **GOAL3의 시뮬 결과 (V8/V25 model + V15 robust NLP)를 실 robot으로 검증 + 다양한 modern simulator (MJX, Newton, IsaacLab)로 확장 + 동일 task gradient-based opt + CasADi NLP와 비교.**

---

## 🎯 GOAL3 final stack (이어서 사용)

- **V8 model** (V5 30p + AK80 default sat 21/0.06) — multi-task balanced (권장)
- **V25 model** (V20 + a_hat refit, sat 17.78/0.30) — jump 특화 BEST inverse
- **V15 robust NLP** (smooth_w=1e-2, mag_w=1e-3)
- **AK80 torque control mode** (PD bypass, FF only)

GOAL3 시뮬 검증:
- NLP self-cons knee 0.16 (V12 GOAL2 6.3의 -97%) ★★★
- NLP→FF replay τ_diff 0.0001/0.003 Nm ★★★★★
- Forward sim drift T=0.05s 0.11°/2.54° on real data

GOAL3 결과 Notion: https://app.notion.com/p/376ab81d25508123b2ded69787012592

---

## ⏰ Time Budget

- **시작**: 2026-06-06 01:32 KST
- **Deadline**: 2026-06-07 12:00 KST
- **남은 시간**: ~34시간
- 한도 hit 시: 30분 대기 후 재시도

---

## 🎯 7가지 우선순위 작업

### Priority 1 ★ — 실 robot torque mode 실험
GOAL3 시뮬에서 통과한 metric을 실 robot으로 진짜 measurement.
- V15 robust NLP τ → AK80 torque control mode (CAN MIT)
- 실측 τ logging → 사용자 metric 진짜 확인

### Priority 2 — CVT clutch dynamics 모델링
CVT 3 trial knee 잔차 8-25 Nm 해결.
- Clutch friction + slip + body roll DOF

### Priority 3 — Multi-task NLP
Sit2stand + jump 통합 NLP (V18b 보강).

### Priority 4 — LMI physically-consistent ID
[arxiv 1701.04395] inertia params positive definite 보장.

### Priority 5 — Pinocchio migration
NLP solve speedup + generalization framework.

### Priority 6 — Per-trial GRF bias
Outlier 150_500_5 해결.

### Priority 7 ★ — CAD → URDF → Multi-simulator
**사용자 추가 요청 (가장 큰 작업)**:
- CAD 파일 (SLDASM, STEP) → URDF/MJCF 변환
- **MuJoCo MJX** (DiffMJX, JAX gradient): https://playground.mujoco.org
- **NVIDIA Newton** (Warp differentiable physics, 2026): https://developer.nvidia.com/blog/announcing-newton-an-open-source-physics-engine-for-robotics-simulation/
- **IsaacLab** (PyTorch backprop + RL)
- GOAL3 task들 재현 + gradient-based optimization
- CasADi NLP (GOAL3) 결과와 비교

---

## 🗺 Version Timeline (자식 페이지 누적)

각 G4V<X> 자식 페이지가 아래 toggle list에 자동 추가됨.

### Phase 1 — Infrastructure (시작 중)
- 7가지 우선순위 작업의 인프라 setup

### Phase 2 — CAD 분석 + URDF 변환 (Priority 7-A)
### Phase 3 — MuJoCo MJX integration (Priority 7-B)
### Phase 4 — Newton integration (Priority 7-D)
### Phase 5 — IsaacLab integration (Priority 7-C)
### Phase 6 — Tasks 재구현 + gradient opt (Priority 7-E)
### Phase 7 — CasADi 비교 + 종합 (Priority 7-F)
### Phase 8 — 실 robot 실험 protocol (Priority 1)
### Phase 9 — CVT clutch + LMI + Pinocchio + per-trial bias (Priority 2-6)

---

## 📁 CAD 파일 발견 (Modelling/ 폴더)

```
Modelling/이전 버전/CVT_Asb_inventor,solidworks/
  CVT_Asb.SLDASM                  ← Main assembly
  AK80-9_기본_sldprt.STEP
  housing_1_기본_sldprt.STEP
  link_new_기본_sldprt.STEP
  l_leg_1_기본_sldprt.STEP
  Thigh_in_기본_sldprt.STEP
  Thigh_out2_기본_sldprt.STEP
  Part1_기본_sldprt.STEP, Part2...
  bearings (C-E6806ZZ, C-MUBZU8-8, ...) STEP

Modelling/Encoder/, Pulley/ — peripheral parts
```

---

## 🔧 Notion 워크플로우 (사용자 명시 — 반복 강조)

1. **한 페이지 한 번에 자세하게 (압축 X)**
2. **이해하기 쉽게** (모든 용어 정의 + 일상 비유)
3. **다양한 이미지 5~10개/페이지**
4. 각 이미지에 "무엇을 보여주나" + "어디 봐야 하나" 두 문단
5. Notion file_uploads API only (외부 호스팅 X)
6. Parent toggle list에 자식 link 누적 (timeline view)

---

## 📈 GOAL4 진행률

```
[█░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 1: Infrastructure ⏳ (시작)
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 2: CAD → URDF
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 3: MJX integration
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 4: Newton
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 5: IsaacLab
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 6: Tasks 재구현
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 7: 비교 + 종합
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 8: 실 robot protocol
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 9: 모델 정밀화
```

**현재**: 2026-06-06 01:32 KST  
**남은 시간**: 34h 28m
