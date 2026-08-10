<!-- STATUS -->
# CURRENT_STACK — 현행 디지털 트윈 스택 (수치의 단일 출처)

**현행: p24** — P22~P24 3연전 산물: 측정 유지-지지 법칙+부하연동 스프링+게이트 상승항+hip 지지층+CVT 손실. FIT 36.1/HO CL 33.1 역대최고/재생 0429 2.61(-21%)/J_v6 0.826/자유상수 0. 사용자 승격 확정 2026-07-17  (승격 2026-07-17)
- 후보 파일: `code\goal22\p23_veins\fourbar_p24a_candidate.json`  (judge: p19)

- 3계층: 플랜트(x) × 커맨드층(p19_cmdlayer.json: α·클립±35.5·지연) × 변환식 A=Paper

**현행 런타임 스택: G26_0811** (베이스 p24) — 마라톤G 강체판: 정본곡선 토크맵(캡 무릎3.8/힙2.6) + 실측질량 3.28 + 발 r=20mm + 인공층 4종 절제 + 발 예비활주. 무릎 SEA 는 게이트 미달로 미채택(REJECTED #81)  (승격 2026-08-11)
- 러너: `code/goal23_fullspan/fs_runner.py` · env 레시피:
```
FS_TMAP=canon_cap
FS_TDCAP=3.8,2.6
FS_MASS=3.28
FS_FOOTR=0.020
FS_NOSUPP=1
FS_NOSPR=1
FS_NOBIAS=1
FS_NODEEP=1
FS_PRESLIDE=0.86,0.85,0.02,1.0
```
- ModeA 전채널 3.12→1.73 (-45%), 세션 10/10 승 (56 trial)
- CL 전채널 3.05→1.89 (-38%), 세션 8/9 승 (53 trial)
- 점프높이 |오차|평균 5.39%→3.68%, 치우침 +0.58%→-0.36%, 흩어짐 7.08%→4.78% (55 trial)
- 게이트 0324 ModeA -47% · 0421 ModeA -41%/CL -80% · CVT 0429 ModeA 10/10
- 미해결: 폐루프 무릎토크 세션 4승5패 (배포모델 우세) — 상승 기울기의 세션별 차이

<!-- END-STATUS -->

## 후보 레지스트리

| key | 상태 | FIT | HO | judge | 파일 | note |
|---|---|---|---|---|---|---|
| p13f | ARCHIVED | — | — | p14 | `code/goal22/fourbar_p13f_candidate.json` | dq-weighted refit (07-08) |
| p13h | ARCHIVED | — | — | p14 | `code/goal22/fourbar_p13h_candidate.json` | corrected-metrology refit, sens_delay=-1.5ms (07-08) |
| p13i | ARCHIVED | — | — | p14 | `code/goal22/p13i/fourbar_p13i_candidate.json` | CL τ-채널 심판 refit (07-09) |
| p14 | ARCHIVED | — | — | p14 | `code/goal22/p14_ahat/fourbar_p14_candidate.json` | dual-judge + free a_hat (07-09) |
| p15 | ARCHIVED | — | — | p14 | `code/goal22/p15_vterm/fourbar_p15_candidate.json` | 속도텀 A5 (기각 계열, 07-09) |
| p16 | SUPERSEDED | — | — | p14 | `code/goal22/p16_structure/fourbar_p16_candidate.json` | P14+springref free — 직전 canonical (07-09) — 직전 canonical, Mode A/구세대 비교 기준점 |
| p18b | SUPERSEDED | — | — | p19 | `code/goal22/p18_cvt/fourbar_p18b_candidate.json` | 스프링 정체 규명 + 프리로드 (07-09) — 발견(스프링 배치·프리로드)은 P19에 계승 |
| p19 | SUPERSEDED | 38.1% | 35.7% | p19 | `code\goal22\p19_jump\fourbar_p19_candidate.json` | τ-fidelity 마라톤 최종 (커맨드층 포함 3계층). 사용자 승격 확정 2026-07-12 |
| p24 | CURRENT | 36.1% | 33.1% | p19 | `code\goal22\p23_veins\fourbar_p24a_candidate.json` | P22~P24 3연전 산물: 측정 유지-지지 법칙+부하연동 스프링+게이트 상승항+hip 지지층+CVT 손실. FIT 36.1/HO CL 33.1 역대최고/재생 0429 2.61(-21%)/J_v6 0.826/자유상수 0. 사용자 승격 확정 2026-07-17 |

## 변경 로그

- 2026-08-11: 런타임 스택 **G26_0811** 등재 (베이스 p24) — 마라톤G 강체판: 정본곡선 토크맵(캡 무릎3.8/힙2.6) + 실측질량 3.28 + 발 r=20mm + 인공층 4종 절제 + 발 예비활주. 무릎 SEA 는 게이트 미달로 미채택(REJECTED #81) (이전: 없음)
- 2026-08-02: 런타임 스택 **fs16 해제** → 기준선 = 플랜트 후보 + α 커맨드층 — 점프높이 지표 정의 오류(지면 기준 베이스 중심 최고높이 ↔ GRF 체공 상승분 혼동)로 마라톤 D·E·F의 1급-b 근거가 무효 — 사용자 지시로 기준선을 OLD α(p24+커맨드층)로 원복하고 재정합 착수 (2026-08-02)
- 2026-08-02: 런타임 스택 **fs16** 등재 (베이스 p24) — 마라톤 C·D·E 산물 (4ms qd 스큐 + 실게인 + 관측 lpf + 발 Karnopp stick-slip). 사용자 승격 2026-08-02. **마라톤F(08-02) 후 CVT 폐쇄 초기화 버그픽스 반영** — 승격 후보는 0건 (이전: fs16)
- 2026-08-02: 런타임 스택 **fs16** 등재 (베이스 p24) — 마라톤 C·D·E 산물: 4ms qd 스큐 보정 + 실게인 + 관측 lpf + 발 Karnopp stick-slip 이력 마찰. 사용자 승격 지시 2026-08-02 (이전: 없음)
- 2026-07-17: **p24** 승격 (FIT 36.1% / HO 33.1%) — P22~P24 3연전 산물: 측정 유지-지지 법칙+부하연동 스프링+게이트 상승항+hip 지지층+CVT 손실. FIT 36.1/HO CL 33.1 역대최고/재생 0429 2.61(-21%)/J_v6 0.826/자유상수 0. 사용자 승격 확정 2026-07-17 (이전: p19)
- 2026-07-12: **p19** 승격 (FIT 38.1% / HO 35.7%) — τ-fidelity 마라톤 최종 (커맨드층 포함 3계층). 사용자 승격 확정 2026-07-12 (이전: 없음)