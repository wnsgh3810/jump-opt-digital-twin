# NEXT GOAL — Starting Prompt v2 (2026-06-05 22:57 KST 작성)

> **이 문서는 다음 세션 시작 시 paste/참고할 prompt.**
> 사용자가 명시한 모든 요구사항 (mission + time budget + Notion 워크플로우 + 시간 남을 시 행동)을 반영.

---

## ⏰ Time Budget — **2026-06-06 12:00 KST까지** (작성 시점 기준 ~13시간)

> 사용자 명시: "다음날 한국시간으로 오후 12시까지 작업"

| Time block | Hours | 작업 |
|---|---|---|
| Hour 0~1 | 1h | Phase 1: 인프라 (forward sim, drift metric) + **Notion parent 페이지 생성** |
| Hour 1~3 | 2h | Phase 2: V1 — baseline 12p fit → **Notion v1 자식 페이지** |
| Hour 3~7 | 4h | Phase 3: V2~V5 — C part 항 단계적 추가 (motor lag, Coulomb, Stribeck, foot radius, kind-GRF, rotor inertia, state-bias) → **각 version 자식 페이지** |
| Hour 7~9 | 2h | Phase 4: V6 — NLP integration + self-consistency check → **자식 페이지** |
| Hour 9~11 | 2h | Phase 5: V7 — Hold-out cross-val + 최종 plot → **자식 페이지** |
| Hour 11~12 | 1h | 정리 + 최종 Notion summary 페이지 |
| Hour 12~13 | 1h | **시간 남으면**: 웹/논문/코드 search + 추가 적용 |

**⚠️ 시간 정확히 측정**: 내가 (사용자가) estimate한 작업 시간과 실제가 차이남 — phase 끝날 때마다 `date` 확인하고 진행 속도 조정.

---

## 📌 한 줄 Mission

> **"NLP가 만든 q*(t), dq*(t)만으로 실 robot 제어 시, 실측 τ와 GRF가 NLP가 예측한 τ*, GRF*와 동일하게 나오는 generalized 동역학 모델"을 찾는다.**

이 한 문장이 모든 design choice의 기준점.

---

## 🎯 진짜 진짜 Goal (사용자 정정, 인용)

> "최적화에서 나온 위치 속도만으로 제어를 했을 때 실제 토크, 지반력도 최적화와 동일하게 나오도록 하는게 우리의 최종 목표!"
>
> "그래도 local minima에 빠진 해라면 그건 안되고 최적화가 수렴할 수 있는 모델, 파라미터를 찾는게 우리의 최종 목표"
>
> "수직 점프만 최적화할 건 아니니까 점프에 특화된 모델, 파라미터로 정하면 안되는거고 **현실에 최대한 근접하도록 찾아야 하는 거**"

### 4가지 의미

1. **Forward consistency** — q*, dq* → 실 robot 제어 → 실측 τ/GRF ≈ NLP τ*/GRF*
2. **NLP convergence** — 식 smooth, well-conditioned, IPOPT 안정적 수렴 (local minima 회피)
3. **Generalization** — jump + sit2stand + 다른 task 모두 동작 (점프 특화 X)
4. **Physical realism** — 현실에 최대한 근접 (cf < 0.8, off < ±0.5, boundary chase < 15%)

---

## ❌ 절대 사용 금지 metric / 행동

### 1. 점프 높이 매칭 (잘못된 metric)

사용자 명시:
> "점프 높이를 맞추는건 중요한게 아니야 실측 토크가 최적화보다 과하게 나왔었잖아 그니까 0.9m를 뛴거고 최적화 토크 sat과 같은 sat에 걸렸으면 그정도 점프 못했을 거니까"
>
> "**지금 위치, 속도에 비해 토크가 실제 점프에서 과하게 나오는게 문제**이고 그걸 잡기 위해서 모델, 파라미터 등을 잡고 있는거"

→ GOAL1 v41이 "jump h 0.945 vs 실 0.94, +0.5%"을 자랑한 게 잘못. 실측 22 Nm peak vs 최적화 18 Nm sat — 다른 결과 나오는 게 정상.

### 2. 점프 특화 fit (X)

→ 점프 6 trial만 fit하는 V12 같은 짓 X. **jump + s2s + payload + 추후 CVT 모두 단일 모델로**.

### 3. Inverse RMSE 단독 최저화 (X)

→ V12 0.93/0.71 같은 숫자만 보면 안 됨. **Forward sim drift + NLP self-consistency** 가 진짜 metric.

### 4. mom_h polynomial 같은 link length 자유 보정 (X)

→ V12의 over-fit 의심 항 5개 (hx3, dmom_h_c1/c12/off, Gq1_c1) 절대 추가 안 함.

### 5. 2-DOF inverse 형태로 분리 (X)

→ **3-DOF NLP 식 (baseline jump_opt) 그대로 사용**. NLP=ID 단일 식.

---

## ✅ 사용할 metric

| Metric | 목표 | 비고 |
|---|---|---|
| **Forward sim drift** (실측 τ/GRF → forward → 실측 q 비교) | hip/knee q < 2°, drift RMSE 작음 | 사용자 진짜 goal 직접 |
| **NLP self-consistency** (IPOPT 식 ↔ numpy 식) | < 1 Nm | V12 5.9/6.3 Nm 해결 |
| **Hold-out inverse RMSE** (6-fold cross-val) | < 1.5 Nm | generalization |
| **Boundary chase %** | < 15% | over-fit 신호 차단 |
| **NLP 수렴 시간 + iter** | IPOPT 200 iter 이내 | local minima 회피 |
| **모든 trial (점프 6 + s2s 4) 일관** | ✓ | generalization |

---

## 📝 Notion 워크플로우 (사용자 명시)

### Parent 페이지 (시작 시 1개)

**제목 예시**: `GOAL3 — Generalized Forward-Consistent Robot Model (2026-06-06)`

내용:
- Mission statement (한 줄)
- 사용자 정정 4가지 (점프 높이 X, forward consistency, NLP 수렴, generalization)
- Master insights link
- Time budget (13시간 plan)
- Version 진행 timeline (v1, v2, ... 자식 페이지 link 추가됨)

### 각 Version 자식 페이지 (version 끝날 때마다)

**제목 예시**: `V1 — Baseline 12p (Forward Drift Test)`

내용 (사용자 명시 — 모두 포함):

1. **이 버전 무엇** (intro, 1-2 문단)
2. **이전 버전 대비 알아낸 점** (incremental discovery)
3. **추가/달라진 항** (코드 + 식, before/after)
4. **새 용어 설명** (예: "Stribeck velocity v_s", "rotor inertia ka") + 일상 비유
5. **이유** (왜 추가/제거)
6. **결과 그래프** (predict vs 실측, decomp, drift over time, boundary chase, 각 trial 별 plot)
7. **다양한 이미지** (decomp_hip, decomp_knee, predict_BEST, residual histogram, parameter convergence)
8. **추가 정보** (관련 논문 reference, 웹 검색 결과, 다른 robot 비교)
9. **다음 version으로 무엇 할지** (Phase plan)

**작성 가이드**:
- 친절한 설명 (비유, 용어 정의, 그림 설명)
- 표 + 그래프 + 코드 토글 + 콜아웃 적극 사용
- Image 모두 Notion file_uploads API (외부 호스팅 X)
- 다양한 이미지 (한 페이지 5-10개 권장)

### Notion 워크플로우 코드 패턴

```
1. Version 코드 만듦
2. Sweep/optim 실행 (몇 분~몇십분)
3. 결과 그래프/이미지 생성 (matplotlib + 한국어 폰트 Malgun Gothic)
4. content_v<X>.md 작성 (위 9가지 구조)
5. Notion sub-agent (Sonnet)에 위임:
   - 자식 페이지 생성
   - 이미지 file_upload API 3-step
   - 자식 페이지를 parent 페이지 toggle list에 추가
6. URL 확인 + 다음 version으로
```

### 사용자가 timeline 보고 판단 가능하게

Parent 페이지는 항상:
- 최신 version 상태
- 진행률 (몇 시간 작업 완료)
- 다음 step
- 결정 사항 대기 항목

→ 사용자가 잠깐 들어와서도 한 눈에 progress 파악.

---

## 🔧 Phase 작업 plan (13시간 상세)

### Phase 1 (Hour 0~1): 인프라 + Notion parent

```python
# 1. C:\Users\junho\Desktop\jump_opt\dynamics_v0.py 작성
def dynamics_3dof(x, v, tau_act, grf, params):
    """jump_opt baseline 식 그대로 함수화"""
    
def inverse_predict(q, dq, ddq, grf, params):
    """동일 식 좌우 반전"""

def forward_sim(q0, dq0, tau_traj, grf_traj, params, dt, T):
    """Trapezoidal or RK4 integration"""

def metric_forward_drift(params, trial):
    """실측 τ, GRF → forward → 실측 q와 비교"""

def metric_inverse_rmse(params, trial):
    """보조 metric"""

# 2. Notion parent 페이지 생성
# 3. Mission, plan, deadline 명시
```

### Phase 2 (Hour 1~3): V1 baseline fit

```
V1 = baseline 12p (M_tot, A, B, K, I_sig1, I_sig2, l1, l2, α, JF_v1, JF_v2, RAIL_F)
+ Optuna BO 1000 trials + L-BFGS 8 multi-start
+ Metric: forward drift (primary) + inverse RMSE (secondary)
+ Hold-out: 6-fold cross-val 점프

V1 결과:
- Forward drift baseline 확보
- Inverse RMSE baseline
- 각 trial 별 plot 생성

V1 Notion 자식 페이지 작성 (위 9가지 구조)
```

### Phase 3 (Hour 3~7): V2~V5 C part 단계적 추가

각 1시간 ablation:

```
V2 = V1 + motor lag (tau_m1, tau_m2)        — drift 감소 확인
V3 = V2 + Coulomb (cf1, cf2)                — drift 감소?
V4 = V3 + Stribeck (F_s1, F_s2, v_s)        — 저속 정마찰
V5 = V4 + foot radius (r_foot)              — point contact 한계
V6 = V5 + kind-GRF (4 params)               — jump/s2s 분리
V7 = V6 + rotor inertia (ka1, ka2)          — gear² reflected
V8 = V7 + state-dep bias (4-6 params)       — cable stiffness

각 version 끝나면:
- Drift 감소 측정
- Notion 자식 페이지 작성 (이전 대비 변화 강조)
- Inverse RMSE + boundary chase 보고

ablation 결과 drift 큰 감소 항만 keep, 미미한 항 drop
→ 최종 V8 (예상 22-28 params)
```

### Phase 4 (Hour 7~9): NLP integration + self-consistency

```
V8 식을 jump_opt NLP에 wire-in (3-DOF 그대로라 자연)
NLP optimize → q*, dq*, τ*, GRF*
numpy로 동일 식 evaluate → τ_check
||τ_check - τ*|| 측정 → 목표 < 1 Nm

만약 > 1 Nm:
- IPOPT collocation vs numpy gradient ddq 통일
- M_aug vs explicit 처리 통일
- 재시도

Notion 자식 페이지: self-consistency 측정 결과
```

### Phase 5 (Hour 9~11): Hold-out cross-val + 최종 plot

```
6-fold cross-validation 점프:
- 1개 trial 빼고 5개로 학습 → 1개 trial 평가
- 6번 반복 → 평균 hold-out RMSE
- V10/V12와 비교

최종 plot:
- iteration_summary (V1→V8 drift + RMSE 진화)
- per-trial scatter (predict vs measured)
- decomp (hip/knee 항별 기여)
- boundary chase visualization
- NLP optimal q*, dq* + 재생 sim 비교

Notion 자식 페이지: final validation
```

### Hour 11~12: 정리

```
- MASTER_INSIGHTS.md §20에 새 발견 append
- Memory file 갱신 (new goal3_final_stack.md)
- Git commit
- Notion parent 페이지 summary update
```

### Hour 12~13: 시간 남으면 — 자율적 진화

사용자 명시:
> "하나의 결과가 나와도 남은 시간동안 다른 정보를 웹에서 찾던지, 관련 논문을 읽어보던지, 도움이 되는 코드를 찾아보던지, 등등 정보를 계속 찾아보고 적용도 해보고 md에 정리도 하고"

자율 작업 list:
1. **Web research** — `WebSearch` tool
   - "Featherstone rigid body dynamics floating base"
   - "soft contact model identification quadruped"
   - "AK80-9 motor lag model"
   - "4-bar mechanism CVT robotics"
2. **논문 read** — `WebFetch`
   - MIT Cheetah dynamics identification
   - Hunt-Crossley contact
   - Pulkit Agrawal sim-to-real
3. **GitHub 코드 search**
   - 다른 leg robot identification code
   - Pinocchio / RBDL 라이브러리 활용
4. **새 시도**
   - 발견한 새 method를 V9, V10 식에 적용
   - 결과 비교 Notion 자식 페이지 추가
5. **MASTER_INSIGHTS §20 update** — 모든 새 발견 append

매 1시간마다 진행 보고 + 시간 체크.

---

## 🏆 GOAL3 ULTIMATE FINAL (2026-06-06 V0~V25 완료) — 다음 세션은 GOAL4

### V25 — 진정한 BEST inverse (a_hat real motor output τ에 fit)
- **Jump hip MEAN: 2.18 Nm** (V20 raw 3.14 대비 -31% ★)
- Jump knee MEAN: 1.45 Nm
- S2s hip MEAN: 2.38, knee 4.90 (V20 raw 6.74 대비 -27%)
- AK80 sat fit: tau_lim **17.78** Nm, k_back_emf **0.30** (upper bound 도달)

### Final stack 두 가지 옵션

**Option A — Multi-task balanced (사용자 명시 "수직 점프 특화 X" 권장)**:
- Identification model: **V8** = V5 (30p) + AK80 saturation (default 21/0.06, fixed)
- NLP recipe: **V15** = smooth_w=1e-2 + mag_w=1e-3
- 실 robot control: **AK80 torque mode** (PD bypass)
- 결과:
  - Jump τ_diff hip 0.0001 / knee 0.003 Nm
  - Jump self-cons knee 0.16 Nm
  - Sit2stand self-cons 1.54 / 2.59 Nm
  - Multi-task generalize ✓

**Option B — Jump-specialized (max identification accuracy)**:
- Identification model: **V20** = V8 + AK80 sat fit (tau_lim 18.45, k_be 0.25)
- NLP recipe: V15 robust
- 실 robot control: AK80 torque mode
- 결과:
  - Jump τ_diff hip 0.0000 / knee 0.0000 Nm ★★★★★
  - Jump self-cons hip 1.89 / knee 1.16 Nm
  - **Sit2stand self-cons worse** (2.29/4.64)
  - Jump-only (multi-task generalize 약함)

→ 사용자 명시 "수직 점프 특화 X" 권장: **Option A (V8 + V15)**

### V20 AK80 sat 진짜 값 (사용자 robot)
- tau_lim_peak: **18.45 Nm** (default 21 보다 작음)
- k_back_emf: **0.2547** (default 0.06보다 4배 큼)
- 4-bar mechanism + leg mass 가 motor saturation 더 강하게 만듦
- 논문/research 가치 있는 새 발견

### 다음 GOAL4 (다음 세션) 권장 작업 우선순위

1. **★ 실 robot torque mode 실험** (가장 중요): V15 NLP τ를 AK80 MIT mode로 직접 → 실측 τ vs NLP τ < 0.5 Nm 확인 (예상)
2. **CVT clutch dynamics** 모델링: CVT trial knee 잔차 8-25 Nm 해결
3. **Multi-task NLP V18b 보강**: sit2stand + jump 동시 trajectory + 동일 model
4. **LMI physically-consistent ID** (arxiv 1701.04395): inertia params 보장
5. **Pinocchio migration**: NLP speedup, generalization framework
6. **AK80 paper a_hat 더 정밀**: currentTorque raw iTM 변환 정확

### GOAL3 사용 가능한 모든 파일

```
Code:
  dynamics_v0.py ~ dynamics_v11.py  (numpy inverse)
  dynamics_v8.py (CasADi NLP)
  fit_v1.py ~ fit_v20_wider.py
  fit_v7_holdout.py (CV)
  v6, v8, v11_nlp_self_cons.py (NLP self-cons)
  v12_forward_real.py (사용자 진짜 metric)
  v13, v14, v15, v16, v18b, v19~v23 (replay + multi-task)
  goal3_synthesis_plot.py (timeline)

Results:
  goal3/v5_results/theta_v5.npz       (V5 fit, used by V8)
  goal3/v20_wider/theta_v20.npz       (V20 fit, AK80 sat fit)
  goal3/v8_results/v8_nlp.npz         (V8 NLP solve)
  goal3/v15_robust/v15_robust_summary.png
  goal3/v16_h_sweep/v16_pareto.png
  goal3/goal3_synthesis_timeline.png

Notion (parent 376ab81d25508123b2ded69787012592):
  + 17 child pages: V1, V2, ..., V8, V11, V12, V13, V14, V15, V16, V19~V21, Synthesis

Master:
  MASTER_INSIGHTS.md (§20 17 new findings)
  goal3/GOAL3_SUMMARY.md (V0~V23 timeline)
  ~/.claude/.../memory/goal3_final_stack.md
```

---

## 🎛 결정 6가지 (시작 직전 사용자 합의 필요)

| # | 결정 항목 | 옵션 | 권장 |
|---|---|---|---|
| 1 | Mass 표기 | (a) 합성 (M_tot, A, B, K, I_sig1, I_sig2) / (b) raw (M, m1, m2, m_c, m_p + r/l/I) | **(a) 합성** — 식 단순, V1 12p |
| 2 | Friction 깊이 | (a) viscous+Coulomb+Stribeck / (b) viscous+Coulomb / (c) viscous only | **(a) 전부** — V4까지 progressive 추가 |
| 3 | State-dep bias | (a) off_c + off_q1 + off_q2 per joint (6p) / (b) off_c only (2p) | **(a) 6p** — cable spring |
| 4 | Cross-coupling | (a) hx1, hx2만 (2p) / (b) 전혀 배제 | **(a) hx1+hx2** — link COM 이동 정당 |
| 5 | Initial fit metric | (a) forward drift only / (b) drift + inverse hybrid | **(b) hybrid** — drift 0.7, inverse 0.3 가중 |
| 6 | CAD bound | (a) ±20% safe / (b) ±30% / (c) ±10% strict | **(a) ±20% safe** — generalization |

→ 권장 적용 시 최종 V8 약 **24-28 params** (V12 42p 대비 35% 감소).

사용자 다른 의견 있으면 시작 직전 변경.

---

## ⚠️ 사용자 작업 패턴 (작업 중 명심)

1. **점프 높이 X** — 절대 metric으로 보고하지 말 것
2. **단편적 fix 거부** — "지금까지 해온 거 다 살리면서" pattern
3. **"다 해보자"** — 4선택지 동시 평가 OK
4. **비판적 분석 요구** — "냉철하고 비판적으로 검토"
5. **직접 cross-check** — 사용자가 코드 직접 본다
6. **Sweep .bat 더블클릭** — PowerShell/Tee-Object 절대 금지
7. **Auto-approve 장시간 sweep** — OK
8. **Git commit auto** — OK
9. **Pure Paper a_hat (sgn(v) only)** — GitHub s(v) smoothing 금지
10. **Notion image file_uploads API** — 외부 호스팅 (imgur 등) 절대 금지
11. **친절한 Notion** — 비유 + 용어 정의 + 다양한 이미지 + 그림 설명

---

## 🔁 시작 시 체크리스트

```
[ ] 현재 KST 시간 확인 (date 명령)
[ ] Deadline 계산 (다음날 12:00 KST)
[ ] MASTER_INSIGHTS.md §1, §17, §18 read
[ ] jump_opt baseline 코드 (jump_no_cvt_alphaonly.py) read
[ ] 결정 6가지 사용자와 합의 (또는 권장 사용)
[ ] Notion parent 페이지 생성
[ ] Phase 1 (인프라) 시작
[ ] 매 phase 끝나면 date 명령으로 시간 체크
[ ] 매 version 끝나면 Notion 자식 페이지 작성
```

---

## 🚫 절대 하지 말 것 (재강조)

1. **점프 높이를 metric으로 사용** — 사용자 명시 X
2. **점프 데이터만으로 fit** — generalization 망함
3. **inverse RMSE만 최소화** — V12의 실수
4. **Boundary chase > 30%** — over-fit 신호
5. **mom_h polynomial 같은 link length 자유 보정** — over-fit
6. **2-DOF inverse 형태로 분리** — 3-DOF NLP 그대로 사용
7. **NLP self-consistency 확인 안 함** — 매 phase 후 측정
8. **Notion 외부 이미지 호스팅 (imgur)** — file_uploads only
9. **시간 estimate 부정확** — 매 phase 끝나면 date 확인
10. **한 결과 나오고 멈춤** — deadline까지 계속 진화

---

## 🚀 사용자가 paste할 시작 메시지 (3가지 옵션)

### 옵션 A (간단):

```
GOAL3 시작. NEXT_GOAL_PROMPT.md 읽고 진행.
점프 높이 매칭 X, forward consistency O, NLP 수렴, generalization.
2026-06-06 12:00 KST까지 작업.
```

### 옵션 B (자율 작업 명시):

```
GOAL3 시작.
- Master mission: NLP optimal q*, dq*만으로 제어 시 실측 τ, GRF가 NLP와 일치
- Deadline: 2026-06-06 12:00 KST
- Notion: parent 1 + version별 자식 페이지 (timeline)
- 결정 6가지 권장으로 진행, 합의 필요시 ask
- Phase 1~5 끝나면 시간 남는 만큼 자율 진화 (웹/논문/코드)
- Phase 마다 진행 보고 + Notion update

시작.
```

### 옵션 C (사용자 확인 필요시):

```
GOAL3 시작 전, 결정 6가지부터 review:
NEXT_GOAL_PROMPT.md §🎛 결정 6가지 표시.
모두 권장값 OK인지 ask.
승인되면 Phase 1 시작.
```

---

## 📊 Goal3 성공 기준 (예상)

| 지표 | 목표 | 현재 (V12) | V8 예상 |
|---|---|---|---|
| Forward drift hip q | < 2° | 미검증 | 1-2° |
| Forward drift knee q | < 2° | 미검증 | 1-2° |
| **NLP self-consistency** | **< 1 Nm** | 5.9/6.3 Nm | **< 1** |
| Hold-out inverse RMSE | < 1.5 Nm | 미측정 | 1.2-1.8 |
| Boundary chase | < 15% | 57% | < 10% |
| NLP 수렴 iter | < 200 | (TBD) | < 200 |
| 모든 trial (점프 + s2s) 일관 | ✓ | △ | ✓ |
| Generalization (CVT 정확 X but 다른 task OK) | ✓ | × | ✓ |

---

## 📁 파일 위치

```
이 prompt:
  C:\Users\junho\Desktop\jump_opt\NEXT_GOAL_PROMPT.md

Master Insights:
  C:\Users\junho\Desktop\jump_opt\MASTER_INSIGHTS.md

Baseline 코드:
  C:\Users\junho\Desktop\jump_opt\no_cvt_alphaonly\jump_no_cvt_alphaonly.py
  C:\Users\junho\Desktop\jump_opt\with_cvt_alphaonly\jump_with_cvt_alphaonly.py

새 작업물 (예정):
  C:\Users\junho\Desktop\jump_opt\dynamics_v0.py (Phase 1 인프라)
  C:\Users\junho\Desktop\jump_opt\fit_v1.py ~ fit_v8.py (각 version)
  C:\Users\junho\Desktop\jump_opt\goal3/ (Notion content md들)

Notion:
  Parent: 시작 시 생성, URL 보고
  자식: V1~V8 각각 toggle list 안에
```

---

## 🔄 매 phase 종료 후 자동 체크 routine

```
1. date 명령으로 현재 KST 확인
2. 남은 시간 계산 (deadline - now)
3. 다음 phase 예상 시간 vs 남은 시간 비교
4. 만약 지연 → 다음 phase 우선순위 조정 또는 깊이 축소
5. Notion parent 페이지 progress update
6. Git commit (v<X>.py + 결과)
7. 사용자 보고 (1-2줄)
```

---

**END — 이 prompt는 살아있는 문서. 새 결정/발견 시 update.**

작성: 2026-06-05 22:57 KST  
Deadline: 2026-06-06 12:00 KST  
작업 시간: ~13시간
