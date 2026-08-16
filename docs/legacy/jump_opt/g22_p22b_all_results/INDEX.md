# g22_p22b_all_results — P22 최종 후보 p22b 전 데이터 결과 (2026-07-16)

**모델**: p22b (`code/goal22/p22_beyond/fourbar_p22b_candidate.json`, judge p22, REPRODUCED)
= P19에서 **소산 재배치** (fv_hip −34% → knee 점성/쿨롱·부드러운 접촉 solref +35%) + pre30 1.95
+ 소형 어시스트 c_qs 0.064 + **관성 4종(M_c·I_th·I_ca·dz_ca) P19 동결** (널스페이스 차단).
NSGA-II 158세대 (2목적: CLτ vs 전체 재생 dq) 세그먼트 5 승자 (엄격 게이트 20/20 중 J_v5 최저 0.9489).
생성 코드: `code/goal22/p22_beyond/p22b_all_results.py` (정본 p19_all_results 재사용).

## P19 대비 (동일 규격 그래프는 g22_p19_all_results와 파일명 1:1 대응)

| 지표 | P19 | p22b |
|---|---|---|
| CL τ-갭 FIT / held-out | 38.1% / 35.7% | **37.0% / 34.5%** |
| A 재생 dq2 (0424/0602/0421) | 1.89 / 1.26 / 1.48 | **1.72 / 1.18 / 1.37** |
| A 재생 dq2 (0429) | **3.31** | 3.45 (+4.3% — 정직: 소폭 후퇴) |
| A 재생 dq2 (0324 held-out, 진단) | **2.93** | 3.84 (+31% — 감쇠삭감 방향의 비용) |
| 점프높이 오차 평균 | 4.8% | **3.8%** |

폴더 구조·그래프 규격은 g22_p19_all_results/INDEX.md와 동일 (png_v2 표준, CL/A 모드).
비교 오버레이: `g22_p22_results/overlay_p19_p22b.png`. 상세 서사: 노션 P22 root(39eab81d…) 6개 child.
