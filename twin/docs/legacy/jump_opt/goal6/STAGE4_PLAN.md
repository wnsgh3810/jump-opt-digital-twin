# Stage 4 — Mode A Deep Model Search

## 목표
실제 토크 (tau_real) 직접 입력 + q/dq/GRF 매칭하는 robot dynamics / contact model / 다른 모델 탐색

## 시도할 model variation

### A. Robot 구조
1. **Baseline**: V25 single thigh + calf + spherical foot
2. **Foot length** 추가 — capsule foot (point contact 대신 stick contact)
3. **Base에 distributed mass** — base box 더 정확히 (4-bar linkage 무게중심)
4. **Hip joint offset** — 실 robot의 hip joint 위치 미세조정
5. **Multi-body base** — base를 여러 part로 분리

### B. Contact model
1. **Default soft (V25)** — solref=(0.02, 1), solimp=(0.9, 0.95, 0.005)
2. **Hertz contact** — Hertz pressure model (radius/Young's modulus parametrize)
3. **Hunt-Crossley** — non-linear damping (1.5·k·δ·δ_dot)
4. **Multi-point contact** — foot capsule 2 spheres
5. **Friction cone elliptic vs pyramid**
6. **Rolling/spinning friction**

### C. Friction model
1. **Linear viscous (V25)** — F = c·v
2. **Coulomb + viscous** — F = μ·N·sign(v) + c·v
3. **Stribeck** — F = (Fs + (Fc-Fs)·exp(-(v/vs)²))·sign(v) + c·v
4. **LuGre** — internal state friction model

### D. Motor / drivetrain
1. **No motor model (Mode A 그대로)**
2. **AK80-9 paper a_hat** (5-param model)
3. **Simple LPF (1st order delay)**
4. **2nd order: LPF + inertia**

### E. 좌표/sign 검증
1. **Transform B 가정 재검증** — alternative sign conventions

## 진행
- 각 model variation × Mode A BO (15-20 dim, 200-300 trials)
- Score: w_q1·q1 + w_q2·q2 + w_dq·dq + w_grf·GRF (균등 + GRF 강조)
- Best 결과 → 노션 Stage 4 페이지 (model 변형별 결과 + 비교 표)

## 노션 페이지 구조
- Stage 4 parent: "Stage 4: Mode A Deep Model Search"
- Variation별 sub-section (또는 sub-page)
- 비교 표 (각 model variation × 6 trial × 4 metric RMSE)
- 최종 best model 결론
