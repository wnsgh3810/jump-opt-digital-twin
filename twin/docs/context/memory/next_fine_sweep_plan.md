---
name: Next Fine Sweep Plan (after v3)
description: v3 sweep 완료 후 fine grid sweep으로 최적값 정밀 탐색하는 계획 — best 중심 narrow ranges
type: project
originSessionId: cb42ed46-5d3f-447a-94f6-732ce10d7dfc
---
# Fine Sweep Plan — v3 완료 후 (사용자 4/27 결정)

**목적**: v3 sweep (588M, ALPHA=1.0)이 best=11.9에서 수렴. 이 best 근방을 더 정밀하게 탐색하여 진짜 optimum 찾기.

## 시점
- v3 sweep 끝나면 즉시 (예상: 4/27 새벽 ~ 오전)
- v3 best params는 `pd_sweep_a1_v3_best.npz`에 저장됨

## 설계 원칙
1. **각 dim의 v3 grid step의 1/3 ~ 1/4 간격** — 정밀 탐색
2. **best 중심 ± 2~3 step** — narrow range
3. **Total ~10M~30M configs** — ETA 30분~2시간
4. **체크포인트 5M마다** — 손실 cap 작게
5. **동일 안전 패턴**: try/except, atomic .tmp.npz, maxtasksperchild=4000, cores 14, 외부 cmd

## 구현 단계
1. v3 완료 시 `pd_sweep_a1_v3_best.npz` 자동 로드
2. 각 dim의 v3 grid에서 best 위치 찾기
3. best ± 2~3 grid step 영역에 새 grid (각 dim 4~5 points)
4. `pd_sweep_mp_a1_v4_fine.py` 자동 생성 (v3 코드 base, ranges만 변경)
5. `run_fine_sweep.bat` 만들고 외부 cmd 실행

## 코드 위치 (만들 예정이었음 — **실제로 만들어지지 않았다**)
> 2026-08-16 확인: 아래 세 파일은 CVT 어디에도 없다. 옛 Desktop 시절 계획으로만 남은 것이다.
- `generate_fine_sweep.py` — v3 best 읽고 fine sweep 코드 생성
- `pd_sweep_mp_a1_v4_fine.py` — 실제 fine sweep
- `run_fine_sweep.bat` — launcher
- 결과: `pd_sweep_a1_v4_fine_results.txt`, `pd_sweep_a1_v4_fine_best.npz`

## 예상 ranges (v3 best가 가령 gAv=1.36일 때)
| param | v3 grid step | fine grid step | 개수 |
|---|---|---|---|
| gAv | 0.3 | 0.075 | 5 |
| gBv | 0.25 | 0.06 | 5 |
| Is1 | 0.04 | 0.01 | 5 |
| Is2 | 0.005 | 0.002 | 4 |
| Kv | 0.005 | 0.002 | 3 |
| kc | 1500 | 500 | 5 |
| bc | 30 | 10 | 5 |
| sp | 0.5 | 0.2 | 4 |
| sd | 0.7 | 0.3 | 3 |
| tm | 0.01 | 0.003 | 5 |
| cf | 0.2 | 0.07 | 4 |
| jf | 0.07 | 0.02 | 4 |

Total: 5×5×5×4×3×5×5×4×3×5×4×4 ≈ 18M

## v3 완료 검증 후 진행할 명령
```
python generate_fine_sweep.py
# 자동으로 v4_fine.py + .bat 만들어줌
# 사용자가 .bat 더블클릭으로 시작
```

## 만일 v3 best가 grid 경계에 있다면
경계 dim은 그 방향으로 더 확장한 grid 사용 (best가 진짜 optimum 안 쌌을 가능성 — 더 넓혀야 함). 이건 자동 detect 후 사용자에게 보고.
