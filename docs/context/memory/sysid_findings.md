---
name: System ID Findings (26.04.25)
description: Multi-trial system ID 분석 — gAv≈1.57이 CAD(1.36)에 일치, sweep의 0.30이 ALPHA fudge factor 보상이었음
type: project
originSessionId: c82aa01d-1bc5-42d3-ad69-d2998821e712
---
## 배경
PD sweep의 최적 파라미터(gAv=0.30 등)가 물리적으로 합리적인지 검증하기 위해 multi-trial system ID 수행.

## 시도 정리 (sys_id_jump v1~v6)

| 시도 | Knee R² | Hip R² | 비고 |
|---|---|---|---|
| v1-v3 (rigid ddz) | -0.7~0.92 | -0.7 | kinematic degeneracy |
| v4 (soft, single) | 0.86 | -0.17 | Av=0.131이 CAD 일치 (✓) |
| v5 (multi, fric fixed) | 0.94-0.99 | 0.5-0.7 | **gAv=1.57≈CAD(1.36)** |
| v6 (multi, free fric) | 0.94-0.99 | 0.84-0.98 in-window | overfitting, 비물리적 |

## Sanity check 결과 (sys_id_sanity.py)
- **수식 자체는 완벽** (Test 1: TRUE ddz 사용 시 100% 정확)
- 문제는 ddz 재구성 — 키네마틱 항등식 때문에 Is1과 Av가 거의 degenerate
- **해결책**: tight mask (boundary transient 제거) → Av 19% err, gAv -4% err

## 핵심 결론
1. **수식 자체는 맞음** — boundary transient만 마스킹하면 ID 가능
2. **Multi-trial v5의 gAv=1.57**이 CAD(1.36)에 가깝고 물리적으로 합리적
3. **Sweep의 gAv=0.30이 비물리적**이었음 — ALPHA=0.85 fudge factor가 이를 보상
4. **데이터 한계**: jumping 중 dq 부호가 안 바뀜 → friction params 분리 안됨 (조건수 1.9e5)

## v5 mask 내부 vs 외부 동작 (overfitting 진단)

Multi-trial v5의 fit을 시간 영역별로 보면:
- **마스크 내부 (60~240ms)**: hip/knee 둘 다 매우 잘 맞음 — knee R² 0.94~0.99, hip R² 0.5~0.7
- **마스크 외부 (0~60ms 및 240~300ms)**: 발산 — hip 120Nm까지 폭주

→ **전형적인 overfitting**. boundary transient(impact, lift-off)에서 ddelta 재구성이 망가지면서 회귀가 못 맞추는 영역이 됨. tight mask가 본질적 해결이 아니라 회피.

## Sanity check 상세 결과 (sys_id_sanity.py)

Forward sim으로 합성 데이터 만든 후 regressor 검증:

| Test | 입력 ddz | 결과 |
|---|---|---|
| Test 1 | TRUE ddz (sim에서 직접) | **100% 정확** — regressor 식 자체는 완벽 |
| Test 2 | 재구성된 ddz (ddz_kin - ddelta) | ddz_recon이 진짜의 10배 (325 vs 32) → **ddz 재구성 망감** |
| Test 2b | tight mask 60-240ms | Av 19% err, gAv -4% err (vs Test 2의 -85%/+110%) — 회복 |

**구체적 발견**:
- delta 적분 자체는 정확 (RMSE 0.56mm)
- 하지만 TRUE delta 써도 ddz 재구성 RMSE 35 m/s² (망함)
- np.gradient의 2번 미분이 노이즈 증폭 → boundary 영역에서 ddz_kin과의 상쇄가 안 됨
- 작은 ddelta 오차가 큰 ddz_kin과 상쇄 안 되면 ddz 폭주 → kinematic 항등식 때문에 Is1과 Av가 거의 degenerate

**플롯 진단**: ddz_kin - ddelta_should (검정 점선)은 ddz_true (sim)와 정확 일치. 동역학 식 자체는 맞음. 문제는 ddelta 재구성의 boundary error.

## Foot length 와의 관계

Hip torque +20Nm spike는 foot length 부재가 가장 의심되는데, foot length 추가는 sim 복잡도가 크게 올라가고 hip transient 5° 차이를 완벽히 잡을 보장 못 함. **A안 (soft contact ddz로 ID 재시도)이 더 빠르게 답이 나올 가능성** → A 채택했고 결과적으로 v4~v6 진화. 자세한 진단은 `hip_torque_lift_off_diagnosis.md` 참고.

## ID 결과 (v5, friction 고정, 7 dyn params)
- **Av = -0.0085** (CAD 0.139)
- **gAv = 1.57 (CAD 1.36에 매우 근접!)** vs sweep의 0.30
- gBv = 3.95 (CAD -0.07, 안 맞음)

## 다음 단계 (선택 B 진행 중이었음)
**B) ALPHA=1로 고정하고 sweep 다시 실행**: 진짜 물리적 sim을 만들고 v5 ID 결과(gAv≈1.4)와 비교

### v1: `pd_sweep_mp_a1.py` (58M configs)
- 14코어 × 58M → **MemoryError로 크래시**, Claude Code 본체도 같이 죽음
- 결과: `pd_sweep_a1_results_oom.txt` 보존, best=16.2까지 도달

### v2: `pd_sweep_mp_a1_v2.py` (588M configs, ~14h)
- 사용자 요구 "과감하게, 오래 걸려도 됨" → Mega Stage 1 12 dims 설계
- **Ranges (정밀)**:
  - gAv 8pts: 0.2, 0.5, 0.8, 1.1, **1.36**(CAD), 1.6, 1.9, 2.4
  - gBv 7pts: -0.5, -0.25, **-0.07**(CAD), 0.15, 0.4, 0.7, 1.0
  - Is1 6 / Is2 5 / Kv 4 / kc 5 (2000~14000) / bc 5 (20~200)
  - sp 5 / sd 4 / **tm 7pts (0~65ms)** / cf 5 / jf 5
  - Total 8×7×6×5×4×5×5×5×4×7×5×5 = 588M
- **2026-04-25 04:03 (KST 13:03)**: 17M/588M, 13,406/s, ETA 11.8h, best=16.5, OOM 조짐 없음 ← 마지막 보고
- **24M 즈음 또 OOM 크래시** (numpy `_ArrayMemoryError: Unable to allocate 2.11 KiB`), best=15.7
- 결과: `pd_sweep_a1_v2_results.txt` (31KB, 24M까지 진행률 로그)

### tm 파라미터 의미 (v2에서 도입)
- 모터 토크 1차 지연 시상수 — `tau_actual += (dt/tm)·(tau_cmd - tau_actual)`
- 도입 이유: Hip 토크 270~286ms에 sim +20Nm spike vs Real +5Nm (lift-off transient)
- tm 7점(0~65ms)으로 단조감소 vs 골짜기 판별 가능하게 설계됨

### 재실행 시 필요 대책
- **Claude Code 외부 cmd 창에서 sweep** (sweep이 Claude를 같이 죽이지 못하게)
- cores 14 → 8, TOP_K 500 → 100, chunksize 100 → 50
- 50M마다 heap을 npz로 dump (체크포인트), 재시작 가능하게
- 그리드 분할: 588M을 4개 슬라이스로 순차 실행

### 세션 백업
- 모든 jsonl 살아있음 (`C:\Users\junho\.claude\projects\...\No-Tr\`)
- 텍스트 timeline 3개: `C:\Users\junho\Desktop\session_timeline_{af8c5d47,b0a02628,c82aa01d}.txt`
- 추출 스크립트: `C:\Users\junho\Desktop\extract_sessions_all.py`
