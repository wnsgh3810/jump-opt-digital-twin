---
name: Attempts History (4/15-4/25)
description: 10일간의 Sim-to-Real Gap 분석 시도들의 시간순 narrative — 무엇을 시도했고 왜 다음 단계로 갔는지
type: project
originSessionId: c82aa01d-1bc5-42d3-ad69-d2998821e712
---
# 10일 세션 주요 시도 기록 (2026-04-15 ~ 2026-04-25)

전체 흐름: **Hard contact 분석 → Soft contact + Alpha 모델 식별 → 945-config sweep으로 최적화 파라미터 확정 → 새 실험(26.04.21-22) 검증 → PD sim 개발(궤적 매칭) → 169M sweep으로 dynamics+friction 동시 식별 → System ID(sit2stand+jumping) → ALPHA=1.0 재sweep**.

자세한 결과 수치는 `analysis_findings.md`, `exp_validation_results.md`, `sysid_findings.md` 참고.

---

## Phase 1: Hard Contact Gap 정량화 (4/15-4/17)

이전 클로드의 작업(soft contact K_C=5665, B_C=62.2 식별, R²=0.845)을 인계받음.

- `혹시2.py`에서 `CONTACT_MODEL='alpha'`일 때 GRF가 alpha 미곱 raw값임을 확인 → 사용자가 alpha 곱해진 값이 출력되도록 수정 요청 → 수정 완료
- 이때까지의 핵심 발견: `E_ratio ≈ (Imp_ratio)²` (스프링 모델 시그니처)

## Phase 2: Notion 페이지 생성 + 검증 (4/18 오전)

- `Identify_Contact_Params.py` 정밀 분석 → `Identify_Contact_Params_Analysis.md` 작성 → Notion 페이지 18개 블록으로 생성 (CONCEPT 하위)
- 사용자가 M_tot 오류 지적: 2.469 → **3.268 kg** 수정. "몫통"→"몸통" 오타 13곳 수정
- Notion 토큰: `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`

## Phase 3: Gap 다각도 분석 (4/18 오후)

여러 각도에서 Sim-to-Real Gap 원인 파악:

1. **gap_analysis.py**: tau 포화(60% 샘플), Knee 추가 에너지 +13~18J 발견 — 사용자가 "PD 분석 불필요, 동역학만 봐달라" 피드백
2. **gap_physics_analysis.py + alpha=0.712 검증**: P40 impulse 오차 0.1%로 alpha 모델 검증
3. **liftoff_analysis.py / liftoff_analysis2.py** (확장 데이터 ±0.4s 사용): **v_spring_release ≈ +2.0 m/s 일관**, M_grf ≈ 3.0 kg < M_model 3.268 kg 발견
4. **dynamics_decomp.py**: ddz_kin 수치미분 노이즈로 정량 분석 한계 확인

## Phase 4: Param Sweep (15→320→945 configs) (4/18 저녁 - 4/19)

체계적 파라미터 탐색:

- **param_sweep.py** (15 configs) → **param_sweep2.py** (32) → **param_sweep3.py** → **param_sweep4.py** (비대칭 토크+마찰)
- 사용자 피드백: "peak보다 적분값(Impulse, Energy) 비율 중요"
- **friction_sweep.py / friction_sweep2.py** (320 configs): α=0.95, k_c=5665, b_c=62, rf=10, jf=0.3
- **friction_sweep3.py** (945 configs, alpha 0.7~1.0): **새 1위 α=0.90, k_c=5000, b_c=50, rf=5, jf=0.3** — 모든 지표 2% 이내, h 오차 0.9%
- **3600 config sweep** (`pd_refit2.py`): 수렴 안정성 확보 위해 입력 토크 기준으로 에너지 재계산 (jf×dq² + rf×dz² 추가)
- 결과를 `final.py`에 적용. 자세한 수치는 `analysis_findings.md`

## Phase 5: 신규 실험 검증 (4/22 오전)

26.04.21 위치제어 6개(P60-P200), 26.04.22 토크제어 3개(P40, P70, P100) 실험 데이터 도착.

- **exp_analysis.py / deep_analysis.py / deep_analysis2.py / profile_analysis.py / gap_reduction_analysis.py**: 다양한 시간 구간(전후반, 4분할, 10분할, GRF peak ±25/50ms)에서 RMS/적분/추적오차/지연 분석
- 핵심 발견: P200(고게인)이 시뮬과 가장 가까움(에너지 0.2% 차이), P80(중게인)이 점프 최고(0.89m), 토크제어는 GRF 25% 부족(점프 0.71-0.74m)
- 자세한 결과는 `exp_validation_results.md`

## Phase 6: PD Sim 개발 — 궤적 매칭 전환 (4/22 저녁 - 4/23 새벽)

위치제어 실험을 시뮬레이션으로 재현하기 위한 PD 시뮬레이터 개발.

- **pd_sim.py** 첫 버전: PD 게인 P200_D3 추정값 사용 → Imp 14.3 (실측 21.4) 너무 낮음
- 실험 데이터에서 PD 게인 역추정 (`tau = Kp(q_des-q) + Kd(dq_des-dq)` 회귀): P200에서 Kp_hip=71, Kp_knee=47 Nm/rad
- **pd_param_fit.py** (300 configs): 모두 Imp≈13으로 수렴 → tau_lim=15가 saturation 원인 발견
- **pd_param_fit2.py / 3.py / 4.py / 5.py**: tau_lim 확장, back-EMF 모델 시도 (사용자: 최적화 코드에 이미 토크-속도 제약 있음)
- **결정적 발견**: 모든 sweep에서 **stance가 268ms로 고정** — `T=ref_data['T']`로 sim 시간이 reference 길이로 제한된 버그
- 수정: sim 시간을 reference+150ms로 연장, reference 끝나면 마지막 위치 유지

**궤적 매칭 방식 전환** (사용자 제안): aggregate 지표(Imp, E, stance) 매칭 대신 `|q_sim - q_real|` 직접 최소화

- **pd_param_fit_traj.py** (21.6K) → **pd_param_fit_traj2.py** (43K): kph=500, kpk=130, kdk=1.5 → q2=0.57°, T=300ms
- 사용자 지적: hip Kp=500 vs knee Kp=130인데 실험은 모두 P=200. 비대칭이 비물리적 → hip 모델 부정확 의심

## Phase 7: System ID v1-v2 — sit2stand 데이터로 (4/23)

26.03.24 sit2stand 데이터(공중 매달림, GRF=0)로 순수 2DOF dynamics 식별.

- **sys_id.py v1**: linear regression, R² 0.2~0.66
- **v2 (Butterworth filtfilt)**: R² 0.66→0.75 약간 개선
- **v3 (비선형 마찰: tanh + dq³ + Stribeck + offset)**: R² 0.62~0.77로 크게 개선
- 핵심 발견: **Is2 모델의 3배** (CVT 메커니즘 관성 과소평가), **마찰은 Coulomb이 지배적** (jf=0.014~0.039 << 0.2 가정)
- 자세한 ID 결과는 `sysid_findings.md`

## Phase 8: PD Sim에 Sys ID 적용 + 다양한 sweep (4/23)

- pd_sim.py에 ID 파라미터 적용 → **GRF 70→110N, dq2 17.6→27.8 (real 21.0)** — 너무 빠름
- 원인: Kp가 새 dynamics에 맞지 않음
- **pd_refit.py** (5,400) → **pd_refit2.py** (10.8K, 모터 지연 추가) → **pd_refit3.py** (14.4K) → **pd_refit_full.py** (16.2K, gAv/gBv도 sweep)
- 결과: **gAv=0.80, gBv=-0.30** — sys ID(2.43/0.71)도 CAD(1.36/-0.07)도 아닌 새 값
- 여전히 sim이 stance의 70%만에 이륙 → 사용자: "Knee 속도 왜 30 vs 21?"

## Phase 9: AK80-9 MIT 모드 발견 → 결정적 개선 (4/23 오후)

`D:\Out of Research\Manual\ak80-9 manual.pdf`에서 MIT 모드 확인:
- **`tau = Kp*(p_des - p_cur) + Kd*(v_des - v_cur) + t_ff`**
- 실제 위치제어에서 **v_des=0**으로 보냄 → `Kd*(0-dq) = -Kd*dq` 순수 댐핑
- pd_sim을 v_des=0으로 수정 + **드라이버 값 그대로**(P=200, D_h=1.5, D_k=4.0) 사용

→ **stance 297→301ms, dq2 29.6→24.5** 즉각 개선.

## Phase 10: pd_refit_final.py + alpha sweep (4/23)

- **pd_refit_final.py** (86.4K): alpha=1로 시작, 점진 개선
- **pd_refit_alpha.py** (136K configs): **alpha=0.5가 1위로**, Imp 17.7→19.7
- 5번 결과: sp=1.0, sd=1.0 (드라이버 값 그대로)
- **pd_refit_imp.py** (sweep 코드 RK4 alpha 버그 수정): 사용자 요청으로 alpha 0.5-1.0, kc 3000-7000, bc 30-80 좁혀서 1.9M configs

## Phase 11: 1.9M Sweep 최종 (4/24 새벽)

**Best**: gAv=0.30, gBv=0.50, alpha=0.8, Kp=300, Kd_k=6.0, kc=3000, bc=30, tl=20
- q1=2.65°, q2=0.69°, **Imp 21.2 ≈ Real 21.4 (99%)**, T=300ms 정확
- pd_sim.py 반영 + 6개 실험 검증(`pd_sim_validate.py`) → Imp 89~102% 일관
- tau_lim=20→30 시도: stance time 모든 실험에서 real에 근접

## Phase 12: 정리 + Hip Torque 문제 (4/24 오후)

- 사용자 지시로 바탕화면 정리: 중간 sweep 스크립트들, 모든 .png, .txt 결과 파일 삭제
- 사용자: "knee torque 에러도 크지만 hip torque는 너무 심해"
- 원인: **gAv=0.30 (CAD의 22%)** → hip 동작이 real과 다름

## Phase 13: 169M Mega-Sweep (4/24 밤 - 4/25 오전)

평가에 hip torque + 중간 1/3 구간 토크 추가, dynamics 파라미터(Is1, Is2, Kv) + 마찰(cf, jf) 모두 sweep:

- 13 파라미터 × 169M configs = numba JIT + 14 cores multiprocessing
- 메모리 이슈 해결 과정: 16코어 too slow → 14코어 / batch=50K → 10K → imap_unordered + heap top-K → np.interp 대체 (rate 2300 → 10,500/s)
- 실행 시간: ~6시간

**Best**: Is1=0.065, Is2=0.005, Kv=0.011, gAv=0.30, gBv=0.50, **alpha=0.85**, **kc=7000, bc=80**, sp=1.5, **sd=2.0**, **tm=10ms**, **cf=0.40, jf=0.080**, tl=30
- P200: q1=1.4°, q2=0.7°, hip torque RMSE 4.2Nm (이전 ~10Nm)

## Phase 14: System ID v4-v6 — Jumping 데이터 (4/25 오전)

사용자: "PD sim의 hip torque 여전히 부정확. 모델이 틀린 것 아닌가?" → **Direction B**: jumping 데이터로 직접 ID

- **sys_id_jump.py v1** (17 params, free Av/Bv): **hip R²=-0.70**, condition number 8.5e5 (kinematic degeneracy)
- **v2** (Av/Bv CAD 고정): R²=0.87/0.94이지만 gAv=-31, off_h=27 비물리적
- **v3** (5 params, friction sit2stand 고정): Is1=-0.04 음수, hip R²=-0.70

**근본 원인**: rigid contact `z = -l1·s1 - l2·s12` → ddz가 ddq의 함수 → Is1과 Av가 degenerate.

- **sys_id_jump4.py** (soft contact ddz: `ddz_real = ddz_kin - ddelta`, kc/bc=7000/80 사용): Av=0.131이 CAD(0.139)와 일치하지만 hip R²=-0.17
- **sys_id_sanity.py** (forward sim으로 합성 데이터 검증): regressor 식 자체는 100% 정확. ddelta 재구성 + np.gradient 2번 미분 노이즈가 boundary에서 ddz_kin과의 상쇄를 망침. tight mask(60-240ms)로 Av 19% 오차로 회복
- **sys_id_jump_multi.py** (P60-P200 6개 trial 결합, friction 고정): **knee R²>0.98, hip R² 0.5-0.7, gAv=1.57 ≈ CAD 1.36** ← 핵심 발견
- **sys_id_jump_full.py** (friction 자유): in-window R² 0.84~0.99이지만 mask 밖에서 폭주 (overfitting)

자세한 결과는 `sysid_findings.md`.

**핵심 결론**: sweep의 gAv=0.30은 비물리적 (ALPHA=0.85가 보상). Multi-trial v5의 **gAv≈1.57이 CAD에 가까움**. **ALPHA가 진짜 물리 효과를 가리고 있다는 증거**.

## Phase 15: ALPHA=1.0 재 Sweep (4/25 오후 - 진행 중)

- **pd_sweep_mp_a1.py** (58M configs, ALPHA=1.0 고정, gAv 범위 0.8~1.9 = CAD 중심)
- 14 cores 백그라운드 실행, 약 2시간 예상
- 30분마다 체크 (사용자 지시)
- 목적: 진짜 물리적 sim 만들고 v5 ID 결과(gAv≈1.4)와 비교

세션 끝 시점에서 진행 중.
