# g22_p23a_all_results — P23 최종 후보 p23a 전 데이터 결과 (2026-07-16)

**모델**: p23a (`code/goal22/p23_veins/fourbar_p23a_candidate.json`, judge p23, NSGA-II v6 gen80 min-F2)
= **측정 유지-지지 법칙**이 P19의 pre30(상수 프리로드)+준정적층을 세대 교체 + 구조 2수술 (Phase 4b/4c).

## 구조 3층 (측정 법칙 수식)

1. **유지-지지 법칙 (P23-2 측정 적합)** — 구 pre30/c_qs 자리를 대체, 전 세션 보편:
   `supp(τ̂₂, dq₂) = A + min(B·x + C·x², 3.5)·g(dq₂; v0)`,  `x = min(|τ̂₂|, x_pk)`, `g(v;v0)=1/(1+(v/v0)²)`
   (A=-0.0946, B=0.6304, C=−0.02814 고정, v0=7.272)
2. **부하연동 인루프 스프링 (Phase 4b, spring_gated)** — XML 상시 스프링 무장해제 후
   `τ_spr = k·(k_ref − q_knee)·h`, `h = x/(x+T_SPR)`, x=|ahat 무릎토크|, T_SPR=2.959 Nm
   (k=0.7486, ref=2.1280 — springref 도(°)-해석 유령 규명 후 컴파일값 사용)
3. **게이트 너머 상승항 (Phase 4c, rise_gated)** — `rise = K_RISE·dq₂·(1−g(dq₂; v0))`, K_RISE=0.1881
   (Phase 3 측정 λ₂≈+0.216·dq₂ CI 내). + CVT 가지 전달손실 C_CVT=0.3955 (coulomb형).
플랜트 동결 3축 (M_c/I_ca/dz_ca)은 P19 값으로 강제 (apply_freeze — 심판 규약).

## P19 / p22b 대비 (동일 규격 그래프는 두 아카이브와 파일명 1:1 대응)

| 지표 | P19 | p22b | **p23a** |
|---|---|---|---|
| CL τ-갭 FIT / held-out | 38.1% / 35.7% | 37.0% / 34.5% | **36.7% / 34.8%** |
| A 재생 dq2 (0424 / 0602) | 1.89 / 1.26 | 1.72 / 1.18 | **1.88 / 1.33** |
| A 재생 dq2 (0429 CVT) | 3.31 | 3.45 | **4.33** (+31% vs P19 — 정직: 법칙 구조의 비용) |
| A 재생 dq2 (0324 held-out, 진단) | 2.93 | 3.84 | **2.92** |
| 공중 s2s AIR (q2+0.1·dq2, P19비) | 1.0 | — | **0.35× (−65%)** |
| s2s_gnd 창 점수 (Ŝ2S, P19비) | 1.0 | — | **0.37× (−63%)** |
| J_v6 (v6 종합, P19=1) | 1.0 | — | **0.898** (게이트 전부 PASS) |

## 교차검증 (침묵실패 방역 — npz 재계산 vs 심판 신선값): **PASS**

| 검증 | 세션 | npz 재계산 | 심판 | 판정 |
|---|---|---|---|---|
| CL τ-갭 (±0.2%p) | jump_0324 | 34.79% | 34.79% | PASS |
| CL τ-갭 (±0.2%p) | jump_0424 | 34.63% | 34.63% | PASS |
| CL τ-갭 (±0.2%p) | jump_0429 | 42.57% | 42.57% | PASS |
| CL τ-갭 (±0.2%p) | jump_0602 | 34.21% | 34.21% | PASS |
| CL τ-갭 (±0.2%p) | jump_position_0421 | 32.30% | 32.30% | PASS |
| CL τ-갭 (±0.2%p) | FIT | 36.66% | 36.66% | PASS |
| A dq2 RMSE (±0.02) | jump_0424 | 1.884 | 1.884 | PASS |
| A dq2 RMSE (±0.02) | jump_0602 | 1.327 | 1.327 | PASS |
| A dq2 RMSE (±0.02) | jump_0429 | 4.333 | 4.333 | PASS |

## 1:1 비교 안내

폴더 구조·파일명·그래프 규격(png_v2 = `bench/render_kit.fig_trial_std`)·GIF(goal18_CANONICAL+표준 오버레이)
모두 g22_p19_all_results / g22_p22b_all_results와 동일 — 같은 상대경로 파일을 나란히 열면 모델만 다른 비교가 됨.
파일명 `<트라이얼>__<모드>.{png,gif,npz}`, 모드 **CL**=폐루프 PD(커맨드층 α·클립·tm) / **A**=실측 τ replay.

| 폴더 | 파일 수 (png/gif/npz) | 비고 |
|---|---|---|
| `jump_0319tau/` | 2/2/2 | **신규 세션** (P19/p22b 아카이브에 없음 — CL(FF)+A) |
| `jump_0324_heldout/` | 6/6/6 | **held-out** (fit 미포함) |
| `jump_0422/` | 6/6/6 | **신규 세션** (P19/p22b 아카이브에 없음 — CL(FF)+A) |
| `jump_0424/` | 18/18/18 | |
| `jump_0429_cvt/` | 20/20/20 | CVT l_i=25.08mm |
| `jump_0602/` | 12/12/12 | |
| `jump_position_0421/` | 12/12/12 | |
| `s2s_0604_payload/` | 8/8/8 | 페이로드 s2s (cvt 0/2.5/5kg + no_cvt 0kg) |
| `s2s_air_0319/` | 14/14/14 | **신규 세션** (공중 14사이클, 용접 베이스, A만) |
| `s2s_gnd_0319/` | 3/3/3 | Mode A만 (mshoot 창 리셋 replay) |

## 읽는 법 (함정 — P19 INDEX의 함정 + p23a 고유)

- **A 모드 knee τ 패널**: sim 곡선은 replay 주입 총량 = 측정 ahat + **supp(법칙)** — 실측 곡선과의
  간극이 곧 법칙 층의 크기 (P19 아카이브에서 s2s_gnd만 pre30 간극을 보이던 것과 달리, p23a는
  법칙이 전 세션 보편이라 점프 A에서도 부하 구간에 간극이 보임. CL의 sh는 종전과 동일하게
  supp 미포함 사후-ahat 명령 — τ-갭 지표 정의 불변).
- **held-out 0324 오프셋 규약 차이**: P19/p22b 아카이브는 0324에 레거시 OFFK 오프셋을 적용했지만
  p23a는 심판(eval_p23/oldq_ff23) 규약대로 **o=0** (적합 산물 미사용) — q 패널 비교 시 참고.
- 0429 CL q-오프셋 = x[17],x[18] = (+0.1006, -0.0680) rad / A = P18b 고정 (3.14°, −3.0°).
- s2s_gnd_0319의 knee τ에서 sim−real 간극 = supp(법칙) 층 (구 pre30 자리) + 게이트 스프링은 qfrc라 τ 패널 밖.
- s2s_air_0319는 용접 베이스(base z=1m 고정) — bz/GRF 패널은 상수(1.0/0). GIF 카메라만 상향.
- 신규 세션(0422/0319tau)의 CL은 α=1 + FF(hip+knee — p23_anchors 동결 프로토콜), 적합 커맨드층 없음.
- 나머지 함정 (a_hat 변환·크랭크측 knee·CL 실효게인)은 g22_p19_all_results/INDEX.md와 동일.

생성 코드: `code/goal22/p23_veins/p23a_all_results.py` (러너 = p23_v6_runners의 로그 미러 변형,
기존 함수 불변). 교차검증 원장: `p23a_crosscheck_ref.json` / `p23a_crosscheck_result.json`.
