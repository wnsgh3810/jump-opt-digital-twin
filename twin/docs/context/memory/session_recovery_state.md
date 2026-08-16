---
name: Session Recovery State (2026-04-25)
description: OOM 두 차례로 죽은 세션 상태 복구 — 어디까지 했고 어디서 다시 시작하는지
type: project
originSessionId: cb42ed46-5d3f-447a-94f6-732ce10d7dfc
---
# Session Recovery State — 2026-04-25 14:51 KST 시점

## 진행 중이던 일

**목표**: ALPHA=1.0 고정 mega sweep으로 진짜 물리 baseline 확보, sys_id v5 multi-trial 결과(gAv≈1.57)와 비교

**진행 중 sweep**: `pd_sweep_mp_a1_v2.py` (588M configs, 12 dims). 04:03 마지막 보고 17M/588M, OOM 조짐 없음 → **24M에서 numpy `_ArrayMemoryError: Unable to allocate 2.11 KiB`로 크래시**. best=15.7에서 멈춤.

## 두 차례 OOM 사망 패턴

| 시도 | configs | 죽은 시점 | best 도달 | 메모 |
|---|---|---|---|---|
| v1 (`pd_sweep_mp_a1.py`) | 58M | 새벽 | 16.2 | 첫 OOM, Claude까지 같이 사망 |
| v2 (`pd_sweep_mp_a1_v2.py`) | 588M | 24M (4%) | 15.7 | 또 OOM, Claude도 또 사망 |

두 번 다 Claude Code까지 같이 죽었기 때문에 `claude --continue`가 빈 디렉토리를 봤음.

## --continue 안 먹힌 진짜 이유 (PowerShell history로 확정)

세션 jsonl은 **cwd별로 디렉토리 분리**됨. PowerShell `ConsoleHost_history.txt`에서 사용자의 cwd 변경 추적:
```
cd C:\Users\junho\Desktop\Research\4-Bar Link CVT\Data\26.03.24\Jump\Jump_No_Tr   ← 이전 작업
clear
cd C:\Users\junho\Desktop\Research\4-Bar Link CVT\Data\26.03.24\Jump\Jump_No_Tr   ← 잠시
cd C:\Users\junho\Desktop\Research\4-Bar Link CVT\Data\26.03.24\Jump              ← OOM 후 한 단계 위로 이동
```

- 이전 작업 cwd `Jump_No_Tr\` → `C--Users-junho-Desktop-Research-...-Jump-Jump-No-Tr\` 폴더에 jsonl
- 새 세션 cwd `Jump\` (한 단계 위) → `C--Users-junho-Desktop-Research-...-Jump\` 폴더 (빈 디렉토리)
- → `--continue`가 새 cwd 폴더를 보고 "No conversation found"

해결: `cd "...\Jump\Jump_No_Tr"` 후 `claude --resume c82aa01d-1bc5-42d3-ad69-d2998821e712`

## 보존된 자료

- 모든 세션 jsonl 살아있음
- `C:\Users\junho\Desktop\session_timeline_{af8c5d47,b0a02628,c82aa01d}.txt` (텍스트 추출, 105/599/40 KB)
- `pd_sweep_a1_v2_results.txt` 31KB (v2 진행률 + crash traceback)
- `pd_sweep_a1_results_oom.txt` 12KB (v1 진행률)
- 메모리 13개 파일 모두 백업되어 있음

## 다음에 sweep 재시작할 때 반드시 적용할 것 — v3 코드로 해결됨

`pd_sweep_mp_a1_v3.py` (2026-04-25 작성)에 모두 적용됨:
1. **Cores 14 → 10** (안전 마진. RAM 64GB라 사실 14도 가능하지만 보수)
2. **`Pool(maxtasksperchild=10000)`** — 워커 누수 방지
3. **체크포인트 50M마다 npz dump** + 시작 시 자동 resume
4. **외부 cmd 창 실행 launcher**: `run_sweep_safe.bat` — Claude와 sweep 프로세스 완전 분리

## 현재 설정

- **Sweep 실행 launcher**: `C:\Users\junho\Desktop\run_sweep_safe.bat`
- **Sweep 코드**: `C:\Users\junho\Desktop\pd_sweep_mp_a1_v3.py`
- **결과 출력**: `pd_sweep_a1_v3_results.txt`
- **체크포인트**: `pd_sweep_a1_v3_checkpoint.npz` (50M마다 갱신)
- **최종 best**: `pd_sweep_a1_v3_best.npz`
- **자동 백업 hook**: `settings.json`의 `Stop` hook이 매 응답 끝마다 `backup_all_claude.py`를 hidden background로 실행 → Claude OOM되어도 직전까지의 모든 jsonl/메모리/file-history가 Desktop에 보존된 상태

## 현재 세션 ID 정보 (cwd 흔들려도 복귀 가능)

- **현재 활성 세션**: `cb42ed46-5d3f-447a-94f6-732ce10d7dfc` (cwd: `Jump\`)
- 이전 메인 세션: `c82aa01d-1bc5-42d3-ad69-d2998821e712` (cwd: `Jump\Jump_No_Tr\`)
- 더 이전 메인: `b0a02628-9140-4ea8-8458-a65729caabce` (cwd: `Jump\Jump_No_Tr\`)
- 첫 세션: `af8c5d47-d3af-4b43-a307-d070f489ce3b` (cwd: `Jump\Jump_No_Tr\`)

복귀 명령:
```cmd
cd "C:\Users\junho\Desktop\Research\4-Bar Link CVT\Data\26.03.24\Jump"
claude --resume cb42ed46-5d3f-447a-94f6-732ce10d7dfc
```
어느 cwd든 `--resume <id>`로 직접 복귀 가능.

## Open Questions

- 24M에서 죽기 전 best=15.7이 어느 config인가? results.txt에는 진행률만 있고 best params는 없음 → npz dump 없으면 손실
- gAv=0.30 (sweep) vs 1.57 (sys_id) 결정은 sweep 완주 후 best params에서 gAv 분포 봐야 결론
