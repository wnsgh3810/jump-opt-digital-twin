<!-- STATUS -->
# CURRENT_STACK — 현행 디지털 트윈 스택 (수치의 단일 출처)

**현행: p24** — P22~P24 3연전 산물: 측정 유지-지지 법칙+부하연동 스프링+게이트 상승항+hip 지지층+CVT 손실. FIT 36.1/HO CL 33.1 역대최고/재생 0429 2.61(-21%)/J_v6 0.826/자유상수 0. 사용자 승격 확정 2026-07-17  (승격 2026-07-17)
- 후보 파일: `code\goal22\p23_veins\fourbar_p24a_candidate.json`  (judge: p19)

- 3계층: 플랜트(x) × 커맨드층(p19_cmdlayer.json: α·클립±35.5·지연) × 변환식 A=Paper

**현행 런타임 스택: fs16** (베이스 p24) — 마라톤 C·D·E 산물: 4ms qd 스큐 보정 + 실게인 + 관측 lpf + 발 Karnopp stick-slip 이력 마찰. 사용자 승격 지시 2026-08-02  (승격 2026-08-02)
- 러너: `code/goal23_fullspan/fs_runner.py` · env 레시피:
```
FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0 FS_PRESLIDE=0.86,0.85
```
- J_push (fit 8세션 push 6채널, fs14 정규화) **0.8243** (fs15 0.8543 · fs14 1.000)
- 그래프 규약 CL 세션합 (OLD→fs16): q1 −73% · q2 −61% · dq1 −56% · dq2 −58% · τ1 −31% · τ2 −21%
- 102칸(세션×모드×채널) 중 OLD 대비 개선 85 · 악화 17 — 악화는 전부 fs 계열 상속, fs16 신규 0
- 가드: held-out 0324 MA 비악화(fs15 대비) · 배포 앵커 27일/100_1.5_250_3 6채널 비악화 · μ_s≥0.85 · 정적 홀드 문턱 0.86>0.853
- 잔여 대가(차기 과제): held-out 0324 MA q2 13.00→14.91 · 22·24일 CL τ2 +37% · dq2(ModeA) 무개선

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

- 2026-08-02: 런타임 스택 **fs16** 등재 (베이스 p24) — 마라톤 C·D·E 산물: 4ms qd 스큐 보정 + 실게인 + 관측 lpf + 발 Karnopp stick-slip 이력 마찰. 사용자 승격 지시 2026-08-02 (이전: 없음)
- 2026-07-17: **p24** 승격 (FIT 36.1% / HO 33.1%) — P22~P24 3연전 산물: 측정 유지-지지 법칙+부하연동 스프링+게이트 상승항+hip 지지층+CVT 손실. FIT 36.1/HO CL 33.1 역대최고/재생 0429 2.61(-21%)/J_v6 0.826/자유상수 0. 사용자 승격 확정 2026-07-17 (이전: p19)
- 2026-07-12: **p19** 승격 (FIT 38.1% / HO 35.7%) — τ-fidelity 마라톤 최종 (커맨드층 포함 3계층). 사용자 승격 확정 2026-07-12 (이전: 없음)