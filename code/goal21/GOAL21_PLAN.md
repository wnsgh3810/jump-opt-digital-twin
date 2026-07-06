# GOAL21 — 백지 해석적 System ID (regression-based, 2-DOF single-leg floating base)

사용자 제안 (2026-07-06): a_hat은 그대로 두고, dynamics 모델을 백지에서 —
해석적 EoM + 회귀 기반 system ID로 재구축. joint 마찰, 발끝 마찰/미끄러짐,
q offset, 4-bar compliance, **레일 마찰**(신규 축) 포함. sit2stand_gnd도 fit.

## 왜 (기존 shooting fit과의 차별점)
- 강체 역동역학은 base inertial params에 **선형** → LS 한 방 + SVD 식별성 분석
- **잔차 지도**: 샘플별 잔차를 (q, dq, τ, phase) 공간에 → whip 집중 잔차의 정확한 형태 가시화
- 현 canonical 트윈(4-bar MuJoCo)과 독립 교차검증

## 데이터 전략 (접촉력 회피가 핵심)
1. **s2s_air 15 cycles = 주력** (무접촉, 2-DOF 방정식 깨끗) — 단 저토크 stiction 영역이므로
   마찰 모델은 여기서 풍부하게 식별됨 (기존 twin의 사각지대가 여기선 자산)
2. **jump/s2s_gnd 스탠스 = 구속 투영**: foot pinned(2 구속) + base rail(x 고정) → 1-DOF
   투영 방정식 (contact force 소거). 투영 방향의 정보만 사용
3. jump 비행 직전 whip 구간: foot 접촉 이완 → 취급 주의 (잔차 지도의 관심 영역)

## GRF-프리 보장 (사용자 확정 07-06: q/dq/τ/h만 맞추면 됨)
- GRF는 fit에 0% — ① s2s_air는 무접촉이라 식에 GRF 자체가 없음, ② 스탠스는 구속 투영으로
  접촉력 항을 수학적으로 소거 (측정도 fitting도 불필요)
- GRF 유일 용도 = 이륙 이벤트 감지 (문턱 통과, 캘리브레이션 무관; FK 발높이로 대체 가능)
- q/dq/τ = 회귀 본체 (샘플별 τ 잔차 최소화) · h = held-out 심판 (G20과 동일 철학)
- 한계 명시: 접촉 강성(solref/imp0)은 회귀 식별 불가 → q/dq 창 fit에서 이월 (현행도 GRF 아닌
  q/dq로 식별된 것); 발 μ는 약식별 → 슬립은 모델 아닌 투영-잔차 스파이크 감지기로 취급(1단계)

## 모델 항 (1단계: 선형)
- 링크별 base inertial params (m, m·c, I) — thigh/calf(+crank/coupler는 4-bar 기하 고정 후 lumping 재도출)
- 관절 점성+쿨롱 (hip/knee), **레일 쿨롱** f_rail·sign(dz) (base 방정식/투영에 등장)
- q offset (소각도 선형화로 회귀에 포함 가능, ±2° 물리 제약)
- ★ **ddq 미사용 확정 (사용자 우려 07-06 → 검증 완료)**: 적분형(모멘텀) 회귀 —
  ∫τdt = [M(q)dq]₂−[M(q)dq]₁ + ∫(C+G+마찰)dt, 우변에 q·dq만. 실측 노이즈 바닥
  (air 정지 구간): q 0.0054°, dq 0.053 rad/s, τ 0.014 Nm → 모멘텀-창 SNR = 37(최악: air
  0.5Nm/30ms) ~ 3400(점프 15Nm/100ms). 창 길이 영역별 가변(air 100ms/점프 30-50ms),
  whip 구간은 추정 하향가중 + 잔차 지도 전용 (4중 기각 잔차의 거주지 — 관찰 대상)

## 2단계 (잔차 지도 이후, 비선형)
- 4-bar compliance (connect 강성), stiction(비평활), 발 미끄러짐, 접촉 순응
- 잔차 지도가 가리키는 곳만 — 추측 금지

## 검증
- 회귀 θ vs CAD vs 현 canonical 트윈 파라미터 3자 비교
- 식별성: regressor SVD 조건수, base parameter set
- 최종: 회귀 θ를 MuJoCo 트윈에 넣고 multiple shooting 창 점수 + held-out h로 기존과 대결

## 신규 실험 제안 (이 계획과 별도로 즉효)
- **레일 낙하 시험 (30초)**: 다리 고정, 베이스 자유낙하 → f_rail 직접 측정
  (비행 데이터로는 불가 확인됨: 이륙속도 추출 불확실성이 효과보다 큼 — B 논쟁도 같은 이유로
  방법 의존적, 0324만 robust하게 B>1)
- 카메라-관절 이중측정, 유형C 재실행, t_ff/dq_des 전송 검증, 저속 breakaway, 모터 벤치 whip 영역

## 상태
- 2026-07-06: 계획 수립. 착수는 새 세션 권장 (regressor 유도 + 필터 파이프라인 = 집중 작업).
