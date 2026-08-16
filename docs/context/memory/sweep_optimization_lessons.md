---
name: Sweep Optimization Lessons (169M validated)
description: 대규모 multiprocessing sweep에서 OOM/속도 문제 해결한 패턴들 — 169M sweep으로 검증됨
type: project
originSessionId: c82aa01d-1bc5-42d3-ad69-d2998821e712
---
## 검증된 패턴 (`pd_sweep_mp.py`, `pd_sweep_mp_a1.py`에 적용됨)

이 패턴들이 다 들어있는 코드는 **169M configs까지 안정적으로 완주** (10,500/s, ~4.5h). 손대지 말 것.

### 1. 결과 누적 방지 — `imap_unordered` + `heapq` top-K
- ❌ `pool.map`은 모든 결과를 메모리에 보관 → OOM
- ✅ `imap_unordered` + `heapq.heappush`로 TOP_K(예: 500)만 유지
- 메모리 누적 = 0, 속도도 7700/s → 10,500/s

### 2. Worker 통신 데이터 — raw arrays
- ❌ shared dict → 워커 간 직렬화 오버헤드
- ✅ shared dict 안에 numpy raw arrays만 (매 호출 시 새로 직렬화 안 됨)

### 3. 보간 — `np.interp`
- ❌ `scipy.interpolate.interp1d` → multiprocessing에서 불안정 + 느림
- ✅ `np.interp`로 대체 (3배 빠름)

### 4. 결과 전송 — chunksize 적당히
- `chunksize=100` (너무 작으면 큐 빈도 ↑, 너무 크면 `MaybeEncodingError`)
- 50K 한번에 보내면 터짐

### 5. Pool 정리
- 반드시 `try/finally`로 `pool.close(); pool.join()`
- 없으면 좀비 프로세스 남고 다음 실행에서 메모리 안 풀림

### 6. Numba JIT
- `@njit(cache=True)` + 워커별 `init_worker`에서 dummy 호출로 워밍업
- 워밍업 안 하면 첫 batch가 느림 (사용자 진행률 보고 멈춘 줄 알 수 있음)

## OOM 발생 시 디버깅 순서

1. **이미 위 패턴들이 적용됐는지 확인** — 적용됐으면 시스템 요인 의심
2. 시스템 메모리 상태 확인 (다른 프로세스, Claude Code 자체 누적)
3. 코어 수 일시 축소 (14 → 10) — 코드 변경은 마지막
4. 그래도 안 되면 그리드 분할 실행

## 진행률 패턴 (정상)
- 첫 batch: 2,000~3,000/s (numba warmup)
- 안정화: 7,700~10,500/s
- 169M 완주 시간: 4.5h

**Why 메모리에 남기나**: 169M 때 디버깅하느라 4시간 이상 들였고, a1 sweep에서 OOM 났을 때 "또 처음부터?"가 되지 않게.

## 169M 안정화까지의 디버깅 narrative (스크린샷 4장에서 복원)

이 패턴들은 한 번에 떠오른 게 아니라 5~6단계의 실패를 거쳐 도달:

| 단계 | 증상 | 진단 | 처방 | 효과 |
|---|---|---|---|---|
| 1 | 14코어 raw 시작, ETA 20h, 첫 batch numba warmup으로 2,300/s | (baseline) | — | best 19.4→17.4 진행 |
| 2 | 1시간 동안 진행률 정지, sweep 죽음 | **`MaybeEncodingError`** — 50K 결과를 한 번에 큐 전송이 너무 큼 | chunksize↓, 루프 뒤 `pool.close()` 추가 | — |
| 3 | 또 죽음 | **scipy `interp1d`가 multiprocessing에서 불안정** | **`np.interp`로 대체** + shared dict를 raw arrays로 | 2,200→3,558/s, ETA 13h |
| 4 | 또 `MemoryError`, 결과 쌓이며 메모리 부족 | `pool.map`이 모든 결과를 메모리에 보관 | **`imap_unordered` + top-K heap**으로 결과 즉시 처리, sort 중복 제거 | **2,300→7,700→10,500/s, ETA 20h→6h** |
| 5 | 39M(23%) → 77M(46%) → 116M(68%) → 154M(91%) | 안정 | 그대로 완주 | 169M 4.5h 완주 |

**핵심 교훈**: 169M sweep은 *디버깅 chain*이지 한 번에 만든 코드가 아니다. 다음 sweep 실패 시 어느 단계 증상인지 매핑부터 할 것.

## v2 (588M, ALPHA=1.0) 24M에서 OOM — 같은 패턴인데 왜 죽었나

`pd_sweep_mp_a1_v2.py`는 위 6개 패턴 모두 적용됐는데 4% 시점에서 `numpy._ArrayMemoryError: Unable to allocate 2.11 KiB`. 169M(4.5h)는 됐고 588M(예상 14h)은 안 된 차이의 가설:

1. **워커 누수가 시간 비례** — numba JIT 캐시, RK4 trial buffer 등이 워커 lifetime 동안 천천히 자라는 것. 4.5h 안에는 안 터지지만 14h에는 터짐. 169M보다 3.5배 긴 게 결정적.
2. **Claude Code 자체 메모리** — 30분마다 사용자가 진행률 체크하면서 jsonl·cache가 자람. 14h × 28 체크 = jsonl 큰 폭으로 부풀어 → 16GB RAM 한계 단축
3. **Windows pagefile 동적 확장 실패** — swap 폭주 시 OS가 page allocation 거부. 2.11 KiB도 못 받는 건 OS-level 한계

## v3 만들 때 추가로 적용할 것 (위 패턴 외)

- **워커 lifetime 제한**: `Pool(maxtasksperchild=10000)` — 10K configs마다 워커 재생성, 누적 메모리 0
- **체크포인트**: 50M마다 heap 상태를 npz로 dump → 죽어도 재시작 가능
- **그리드 분할**: 588M을 4슬라이스(147M씩) 순차 실행. 한 슬라이스 죽어도 나머지 살림
- **외부 cmd 창 실행**: Claude Code와 분리. Claude가 죽어도 sweep은 살고, sweep이 죽어도 Claude는 살음
- **Cores 14 → 8 또는 10**: 워커당 ~1.5GB × 14 = 21GB가 16GB RAM 한계. 8 × 1.5 = 12GB로 4GB 여유
