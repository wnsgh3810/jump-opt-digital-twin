# GOAL4 — Starting Prompt (2026-06-06 작성, GOAL3 V0~V25 완료 후 이어서)

> **GOAL3에서 simulation으로 사용자 metric 완전 통과** (NLP τ_diff < 0.01 Nm, knee self-cons 0.16).  
> **GOAL4**: 실 robot 실험 + 모델 정밀화 + 새 task 통합 + CVT 확장.

---

## 📌 한 줄 Mission

> **GOAL3의 시뮬 결과 (V8/V25 model + V15 robust NLP + AK80 torque mode)를 실 robot으로 검증 + 모델 정밀화 + 다양한 task 일반화.**

---

## 🎯 GOAL3 final stack (이어서 사용)

### Identification Model (선택)
- **Option A — V8 (multi-task balanced, 권장)**: V5 30p + AK80 default sat 21/0.06 (32p)
- **Option B — V25 (jump best)**: V5 + sat fit 17.78/0.30 + **a_hat real motor τ** (32p)

### NLP Recipe
- **V15 robust**: smooth_w=1e-2 + mag_w=1e-3 (saturation 회피, FF only friendly)

### 실 Robot Control
- **AK80 torque control mode** (PD bypass, NLP τ 직접 입력)

### 시뮬레이션 검증 결과 (GOAL3)
- NLP self-cons knee 0.16 Nm (V12 GOAL2 6.3의 -97%)
- NLP→FF replay τ_diff hip 0.0001 / knee 0.003 Nm
- Forward drift T=0.05s (real data) q1 0.11° / q2 2.54°
- 사용자 metric (위치/속도만으로 제어 시 τ 일치) **simulation으로 통과**

---

## ⏰ Time Budget

> **사용자가 시작 시 deadline 명시** (예: "다음날 12:00 KST" 또는 "X시간")

기본: 다음날 12:00 KST  
한도 hit 시: 30분 대기 후 재시도

---

## 🎯 GOAL4 6가지 우선순위 작업

### Priority 1 ★ — 실 robot torque mode 실험 (가장 중요)

GOAL3에서 simulation으로 사용자 metric 통과 확인. 이제 **실 robot 실험으로 진짜 measurement**.

**Protocol**:
```python
1. V15 robust NLP 생성:
   from fit_v20_wider import params_from_theta
   from v15_robust_nlp import solve_nlp_robust
   params = params_from_theta(load_v20_theta())
   res = solve_nlp_robust(params, smooth_w=1e-2, mag_w=1e-3)
   tau_traj = res['U_tau']  # NLP commanded τ
   tau_actual = apply_sat(tau_traj, V)  # post-saturation

2. 실 robot AK80 torque mode 설정:
   - CAN MIT mode 또는 별도 firmware
   - PD gains = 0 (또는 매우 작음)
   - τ_input direct (매 1~2ms)

3. NLP τ_traj를 실 motor에 직접 입력 → 실측 데이터 logging:
   - 실측 q (encoder)
   - 실측 dq (encoder velocity)
   - 실측 τ (motor currentTorque, raw iTM)
   - 실측 GRF (force plate)

4. 데이터 분석:
   - 실측 τ_raw → a_hat 변환 → real output τ
   - real output τ vs NLP τ_actual 비교 → τ_diff
   - 실측 q vs NLP q* → drift
   - 사용자 metric 진짜 measurement (예상 < 0.5 Nm)

5. 검증 + iteration:
   - 만약 τ_diff > 1 Nm: model 정밀화 필요
   - drift > 5°: outer loop adaptive control
   - 또는 V25 model로 재시도
```

### Priority 2 — CVT clutch dynamics 모델링

CVT 3 trial knee 잔차 8-25 Nm (V25 V20 모두 미해결).

**시도**:
- Clutch friction (slip + friction coefficient)
- Body roll DOF (1-DOF base roll)
- Mechanical compliance (4-bar spring stiffness)

### Priority 3 — Multi-task NLP 강화

V18b sit2stand NLP solved but V20에서 worse than V8 (jump 특화). V18b 보강:
- Sit2stand + jump 동일 model로 통합 NLP (한 run에서 두 task)
- Payload variation (no_load, 2kg, 5kg) 모두 generalize

### Priority 4 — LMI physically-consistent ID

[arxiv 1701.04395] Inertia params가 physical (positive definite) 보장.

**Implementation**:
- CasADi에서 inertia matrix M의 sub-determinants > 0 constraint
- 또는 mass parameters의 LMI form
- 결과: V25 + LMI = physical interpretable params

### Priority 5 — Pinocchio migration

URDF + Pinocchio C++ binding으로 NLP solve speedup.

[Pinocchio GitHub](https://github.com/stack-of-tasks/pinocchio):
- RNEA fast inverse dynamics
- Floating base 지원
- Crocoddyl integration (NLP)

### Priority 6 — Per-trial GRF bias estimate

V12 GOAL2 패턴: outlier trial별 GRF scale/bias 추가 fit. 150_500_5 outlier 해결.

### Priority 7 ★ — CAD → URDF → Multi-simulator (MJX / Newton / IsaacLab) gradient-based opt

사용자 명시 추가 (2026-06-06): "CAD 파일을 URDF로 만들어서 MuJoCo / IsaacLab / Newton 같은 simulator에서 지금과 같은 gradient 기반 최적화 + 지금 task들을 새로 진행"

#### Sub-task A: CAD → URDF

- CAD 파일 위치 확인 (Research/4-Bar Link CVT/CAD 또는 SolidWorks 원본)
- 변환 도구:
  - **Onshape-to-robot** (https://github.com/Rhoban/onshape-to-robot) — 가장 정밀
  - **SolidWorks-to-URDF exporter** — SolidWorks 직접
  - 또는 수동 작성 (link mass + inertia + joint + collision/visual meshes)
- 4-bar mechanism (closed loop) 처리:
  - URDF는 tree-only → closed loop은 별도 mimic joint 또는 explicit constraint
  - SDF format은 closed loop 지원

#### Sub-task B: URDF → MuJoCo MJCF

- `urdf2mjcf` Python tool (https://github.com/google-deepmind/mujoco) 
- 또는 MuJoCo Playground (2025-01): https://playground.mujoco.org
  - Legged robot template + sim-to-real workflow 제공
- Contact/friction 파라미터 설정 (V8/V25 alpha=0.85, friction=0.3 그대로)

#### Sub-task C: URDF → IsaacLab USD

- Isaac Sim URDF importer (`omni.importer.urdf`)
- IsaacLab task definition: `IsaacLab/source/isaaclab_tasks/manager_based/locomotion/...`
- Existing IsaacLab template: Unitree Go1, Anymal 참고

#### Sub-task D: URDF → Newton (2026-03 release)

- [NVIDIA Newton blog](https://developer.nvidia.com/blog/announcing-newton-an-open-source-physics-engine-for-robotics-simulation/)
- NVIDIA Warp + Newton physics: differentiable, GPU-accelerated
- IsaacLab integration available

#### Sub-task E: 각 simulator에서 GOAL3 task 구현

GOAL3 task들 (CasADi NLP에서):
1. Max jump h (V8/V25 model)
2. Max payload jump (h 고정)
3. Min energy jump (h 고정)
4. Min stance time jump
5. Sit-to-stand (min time, max payload)
6. Multi-task (jump + s2s)
7. CVT trial (clutch dynamics 포함)

각 simulator에서 동일 task 재구현:
- **MJX**: `mjx.step` 미분, JAX `grad` + Adam optimizer
- **Newton**: `wp.kernel` 미분, gradient backprop
- **IsaacLab**: PyTorch backprop or PPO RL training

#### Sub-task F: Gradient-based optimization 결과 비교

각 simulator의 optimization 결과와 CasADi NLP (GOAL3) 비교:

| 측면 | CasADi (GOAL3) | MJX | Newton | IsaacLab |
|---|---|---|---|---|
| Solver | IPOPT (NLP) | JAX grad+Adam | Warp grad | PyTorch backprop |
| Contact | smooth (penalty) | DiffMJX (smooth) | differentiable | smooth penalty |
| Speed | 1-5s per solve | sub-sec batch | GPU parallel | RL training (h) |
| Sim-to-real | tested (GOAL3) | MuJoCo Playground | new (2026) | tested (Unitree) |

#### 권장 우선순위

1. **MJX 먼저** (MuJoCo Playground 검증됨, sim-to-real 우수)
2. Newton (2026 새 framework, differentiable physics most modern)
3. IsaacLab (RL 통합 + PPO 학습)

#### References

- [MuJoCo Playground 2025-01](https://playground.mujoco.org/assets/playground_technical_report.pdf)
- [DiffMJX (Hard Contacts with Soft Gradients) 2025](https://arxiv.org/html/2506.14186v1)
- [Whole-Body MPC with MuJoCo 2025-03](https://arxiv.org/html/2503.04613v2)
- [NVIDIA Newton announcement 2025-03](https://developer.nvidia.com/blog/announcing-newton-an-open-source-physics-engine-for-robotics-simulation/)
- [Newton GitHub (Linux Foundation)](https://www.linuxjournal.com/content/linux-foundation-welcomes-newton-next-open-physics-engine-robotics)

---

## 📝 Notion 워크플로우 (강화된 GOAL2/GOAL3 패턴 그대로)

### ⭐ 매우 중요한 사용자 명시 (반복 강조)

GOAL2/GOAL3에서 사용자가 명시한 원칙 (반드시 준수):

1. **한 페이지를 한 번에 만든다** — 절대 압축 없이, 자세하게
2. **이해하기 쉽게** — 새로운 용어 모두 정의, 비유 사용, 친절한 그림 설명
3. **다양한 이미지 풍부히** — 각 페이지에 5~10개 이미지 권장 (per-trial plot, summary, decomp, comparison, trajectory 등)
4. **이미지마다 친절한 설명** — "무엇을 보여주나" + "어디 봐야 하나" 두 문단 필수
5. **외부 이미지 호스팅 절대 금지** — Notion file_uploads API only (3-step: create upload → PUT file → attach block)
6. **사용자가 timeline 보고 판단 가능하게** — 새 version은 자식 페이지로 진행, parent에 link 누적

### Parent 페이지 생성 (GOAL4 시작 직후)

**제목**: `GOAL4 — Real Robot Validation + Multi-Simulator Expansion (2026-06-06)`

**Parent location**: 같은 CONCEPT page (GOAL3와 동일 parent: `115ab81d255080fdaae6f28f55e3e205`)

**Parent 내용**:
1. Mission statement (한 줄)
2. GOAL3 final stack 인용 + Notion link (GOAL3 parent: 376ab81d25508123b2ded69787012592)
3. 7가지 우선순위 작업 + 각각 친절한 설명
4. Time budget + 진행 plan
5. 다음 version timeline 자리 (G4V1, G4V2, ... toggle list로 자식 페이지 link 누적)
6. **진행률 progress bar** (Phase 1, 2, ...별)
7. 사용자가 잠깐 봐도 진행 상황 파악 가능

### 자식 페이지 — 각 version 끝나면 1개씩

**필수 9가지 섹션** (각 section마다 자세하게, 압축 X):

#### §1 이 버전 무엇 (intro)
- 한 단락 요약 + 일상 비유 (예: "걷는 사람의 다리 움직임처럼...")
- 도입부에 핵심 결과 hightlight

#### §2 이전 버전 대비 알아낸 점
- 정량 비교 표 (이전 → 현재)
- 핵심 finding 강조

#### §3 추가/달라진 항
- 식 + 코드 인용 (before/after 비교)
- 변화의 시각화 (가능하면)

#### §4 새 용어 설명
- **모든 새 용어를 정의** (사용자: "지금 새로운 용어는 많은데 용어 정의는 하나도 안되어 있고 너무 불친절해")
- 각 용어에 일상 비유 추가 (e.g., "Stribeck friction = 정지된 책 처음 밀 때의 큰 힘")

#### §5 이유 (왜 이 변경)
- 동기 (어떤 문제를 풀려고)
- 가설
- 예상 결과

#### §6 결과 그래프 (이미지 다수)
- **이미지 5~10개 권장**:
  - Summary plot (전체 trial RMSE bar chart)
  - Per-trial plot (각 trial 4-panel: τ_hip, τ_knee, q1 forward, q2 forward)
  - Decomposition (M·ddq, h, g, mom·GRF 별 기여도)
  - Pareto front (trade-off 시각화)
  - Trajectory comparison (NLP vs measured)
  - Residual analysis
- **각 이미지 위/아래에 친절한 설명 두 문단**:
  - "이 그림은 무엇을 보여주나" (1문단)
  - "어디 봐야 하나 — 중요한 포인트" (1문단)

#### §7 다양한 이미지 (참고)
- §6 외 추가 trial별 plot들
- 비교 plot
- 진단 plot

#### §8 추가 정보 (논문/웹/코드 reference)
- 관련 paper 인용
- GitHub 코드 reference
- Web research 결과

#### §9 다음 version 계획
- 다음 시도할 항 정리
- 예상 효과

#### §10 진행 시간
- 시작 시간, 종료 시간, 소요
- Deadline까지 남은 시간

### 페이지 생성 워크플로우 (Sonnet agent 위임)

1. **Plot 먼저 생성** (matplotlib, 한국어 폰트 Malgun Gothic):
   ```python
   import matplotlib.pyplot as plt
   plt.rcParams.update({"font.family": "Malgun Gothic", "axes.unicode_minus": False})
   # 5-10 plots per version
   ```

2. **Content md 작성** (`content_g4v<X>.md`, 9가지 섹션 모두 포함):
   - 압축 없이 자세하게
   - 비유 + 용어 정의
   - 이미지 placeholder 명시 `(image_placeholder — plot1.png)`

3. **Sonnet agent에 위임** (background):
   ```
   - PYTHONIOENCODING=utf-8 (cp949 회피)
   - notion_helper.py 사용 가능
   - Parse md → blocks (헤딩, 표, 코드, 콜아웃 모두 보존)
   - 이미지 file_uploads API (3-step) for each plot
   - Placeholder 위치에 image block 삽입
   - Parent 페이지 toggle list에 자식 link 추가
   - URL + count 보고
   ```

4. **URL 확인 + 다음 version 진행**

### 친절 설명 패턴 예시 (GOAL2/GOAL3에서 검증됨)

```markdown
## 4. 새 용어 설명

| 용어 | 일상 비유 | 의미 |
|---|---|---|
| Motor lag (tau_m) | "리모컨 누른 후 TV 켜지기 0.05초" | 명령 → 실제 응답 1차 시정수 |
| Saturation | "자동차 RPM 최대치" | 토크 한계 (±18 Nm) |
| ...

## 6. 결과 그래프

### 그림 1: V8 NLP trajectory (4-panel)

(image_placeholder — nlp_trajectory.png)

**무엇을 보여주나**: NLP가 푼 q*, dq*, τ*, GRF* trajectory + numpy inverse check.

**어디 봐야 하나**:
- 좌상 (q1, q2): NLP가 만든 trajectory
- 우상 (GRF): force plate impulse
- 좌하 (hip τ): τ_cmd (점선) vs τ_actual (실선) — 거의 겹침
- 우하 (knee τ): 완벽 매치 ★

### 그림 2: ...
```

---

## 🚫 잘못 사용하지 말 것 (GOAL3와 동일)

1. **점프 높이 metric** — 절대 사용 X (사용자 명시)
2. **점프 데이터만 fit** — generalization 망함
3. **inverse RMSE 단독 최저화** — V12 over-fit 함정
4. **mom_h polynomial 추가** — link length 자유 보정 X
5. **2-DOF inverse 분리** — 3-DOF NLP 그대로 사용
6. **외부 이미지 호스팅** — Notion file_uploads only

---

## ✅ 사용할 metric

- **실측 τ vs NLP τ** (Priority 1 진짜 measurement)
- **NLP self-cons** (knee < 1 Nm 목표)
- **Forward sim drift on real** (T=0.05s 점프 < 2°)
- **Hold-out cross-val**
- **Multi-task generalization** (jump + s2s + payload)

---

## ⚠️ 사용자 작업 패턴 (이어서)

1. 점프 높이 X
2. 단편적 fix 거부
3. "다 해보자" pattern
4. 비판적 분석 요구
5. 직접 cross-check
6. Sweep .bat 더블클릭
7. Auto-approve + git commit auto
8. Pure Paper a_hat (sgn(v) only)
9. Notion file_uploads API
10. 친절한 Notion (비유 + 용어 + 그림)

---

## 🚀 사용자가 paste할 시작 메시지 (옵션 B 권장)

```
GOAL4 시작.

C:\Users\junho\Desktop\jump_opt\NEXT_GOAL4_PROMPT.md 읽고 진행.

핵심:
- Mission: GOAL3 결과 (시뮬 metric 통과)를 실 robot 검증 + 모델 정밀화 + 다중 simulator 확장
- 우선순위:
  ① 실 robot torque mode 실험
  ② CVT clutch dynamics
  ③ Multi-task NLP
  ④ LMI physically-consistent ID
  ⑤ Pinocchio migration
  ⑥ Per-trial GRF bias
  ⑦ ★ CAD → URDF → MuJoCo MJX / Newton / IsaacLab gradient-based opt
- Deadline: 다음날 12:00 KST
- 시작 즉시: GOAL4 Notion parent 페이지 생성 (`GOAL4 — Real Robot Validation + Multi-Simulator Expansion (2026-06-06)`)
- 각 G4V1, G4V2... 자식 페이지 (timeline 형식)
- Phase 끝나도 시간 남으면 자율 진화

Phase 1 시작:
- GOAL4 Notion parent 페이지 생성 (Sonnet agent)
- CAD 파일 위치 + 변환 도구 조사 (Priority 7-A)
- 인프라 + 실 robot 실험 protocol 코드 작성
```

### 옵션 C (CAD/simulator 우선)

```
GOAL4 시작 — CAD → multi-simulator 우선.

C:\Users\junho\Desktop\jump_opt\NEXT_GOAL4_PROMPT.md Priority 7 부터.

먼저:
1. CAD 파일 위치 확인 (Research/4-Bar Link CVT 폴더 search)
2. Onshape-to-robot 또는 다른 변환 도구로 URDF 생성
3. URDF → MuJoCo MJCF (urdf2mjcf 또는 MuJoCo Playground)
4. MJX에서 V8 dynamics 검증 (점프 task)
5. Newton, IsaacLab도 시도
6. 각 simulator gradient-based optimization 결과 비교

병행 (시간 남으면):
- 실 robot 실험 protocol
- CVT clutch, LMI 등
```

---

## 📋 GOAL4 시작 시 체크리스트

```
[ ] 현재 KST 시간 확인 + deadline 계산
[ ] NEXT_GOAL4_PROMPT.md 읽기
[ ] GOAL3 NEXT_GOAL_PROMPT.md 참고 (final stack 확인)
[ ] MASTER_INSIGHTS.md §1, §17, §18 + V20-V25 발견 read
[ ] GOAL4 Notion parent 페이지 생성 (Sonnet 위임)
[ ] 우선순위 1번 (실 robot 실험 protocol)부터 시작
[ ] Phase 끝나면 자식 페이지 + commit
```

---

## 📁 파일 위치 (GOAL3 산출물)

```
Code (GOAL3에서 이어 사용):
  dynamics_v0.py ~ dynamics_v11.py
  dynamics_v8.py (CasADi NLP, AK80 sat)
  fit_v20_wider.py (final V20 inverse model)
  fit_v25_ahat_refit.py (V25 best inverse, a_hat refit)
  v15_robust_nlp.py (final NLP recipe)
  v8_self_cons.py (NLP solve framework)

Results:
  goal3/v5_results/theta_v5.npz       (V5 base)
  goal3/v20_wider/theta_v20.npz       (V20 sat fit)
  goal3/v25_ahat_refit/theta_v25.npz  (V25 a_hat refit, BEST)
  goal3/goal3_synthesis_timeline.png  (V0~V23 summary)

Documents:
  MASTER_INSIGHTS.md (§20 19+ findings)
  GOAL3_SUMMARY.md (V0~V23)
  
Notion GOAL3 timeline (참고용):
  Parent: 376ab81d25508123b2ded69787012592
  Child V1~Synthesis: 17 페이지
```

---

## 🎯 GOAL4 성공 기준 (예상)

| 지표 | 목표 | 달성 시 의미 |
|---|---|---|
| **실측 τ vs NLP τ** | < 0.5 Nm | 사용자 metric 진짜 통과 ★★★ |
| **실측 q vs NLP q*** | < 3° | drift 작음 |
| **CVT inv knee** | < 5 Nm | CVT trial 정확 |
| **Multi-task self-cons** | jump/s2s 모두 < 2 Nm | generalization |
| **LMI feasible params** | inertia > 0 | physical realism |
| **NLP solve time** | < 1s (Pinocchio) | speedup |
| **CAD → URDF** | 4-bar 동작 검증 | simulator 입력 준비 |
| **MJX gradient opt** | 점프 max h convergence | differentiable physics 활용 |
| **Newton gradient opt** | 점프 max h convergence | 2026 새 framework 활용 |
| **IsaacLab task** | jump + s2s 학습 | RL/gradient hybrid |
| **Simulator vs CasADi 비교** | 동일 task에서 결과 일치 | cross-validation |

---

**END — 이 prompt는 GOAL3 V25 종료 후 작성. GOAL4가 더 깊은 정밀화 + 실측 검증 단계.**

작성: 2026-06-06 00:42 KST  
GOAL3 완료: V0~V25 (24+ Notion 페이지, 16+ git commits)  
다음 Deadline: 사용자가 명시 (기본 다음날 12:00 KST)
