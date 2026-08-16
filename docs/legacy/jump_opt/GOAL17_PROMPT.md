# GOAL17 — 0424 trials 구조적 axis + dq paradigm continuation

> **시작**: 2026-06-22 12:00 KST 이후 (사용자 starting prompt)
> **종료**: 사용자 지정 (default 16-24h 자율 추정)
> **모드**: Mode A 단일 (★ tau_scale=1.0 + paper_a_hat LOCK)
> **데이터**: 15 trial (`0424_*` 9 + `0602_*` 6)
> **Baseline**: **GOAL16 Iter56 = 128.6465** (-20.0% vs Iter1 160.79, 32.14 pt absolute)
> **목표**: 0424 trials 구조적 한계 깸 + GOAL16 dq+17D paradigm 확장

ultrathink, 자율, continuous evolution.

---

## ★ 한 줄 미션

GOAL16 dq+17D virtuous cycle paradigm을 **더 fundamental physics axes** (motor LPF, CVT inertia, contact margin)와 combine. **0424 trials 구조적 한계** (현재 +0.014~0.028 개선만, 0602와 다름)가 핵심 진입점.

---

## ★ GOAL16 확정 결과 (잘 알고 시작)

**Best**: Iter56 = **128.6465** (-20.0%, 32.14 pt absolute)
**KEEP chain (8)**: Iter49 131.80 → 50 130.39 → 51 129.64 → 52 129.32 → 53 129.00 → 54 128.91 → 55 128.68 → **56 128.65**
**Iter56 best params**: `goal16/iter56/iter56_metrics.json` (15 trial dq bias + 17D params)

**Virtuous cycle 검증** (oscillation, monotonic decay 아님):
- dq (Iter50): +2.17 / 17D (51): +0.76 / dq (52): +0.31 / 17D (53): +0.32
- dq (54): +0.10 / **17D (55): +0.22 ← oscillation 발견** / dq (56): +0.04 saturate

**핵심 paradigm**: 17D NM saturation = wrong-axis artifact. dq bias (Iter26 LOCK 22+ iter 잠겨있던 axis) 해제가 결정타.

---

## ★ 우선 axis pool (확신 순)

### Tier 1 — 즉시 시도 (먼저 6 iter, ~3h)

1. **★ Motor LPF (motor_tm)** — memory `goal7_stage20_motor_tm.md` 8.37ms 발견
   - 0424 trials 구조적 한계 직접 attack
   - BO 1D (motor_tm), Iter56 base에서 NM 20-30min
   - 예상: 0424 trials +0.1~+0.3 (0602 영향 X)

2. **★ CVT gear inertia** — memory `mode_A_purpose.md` paper_a_hat 후처리
   - CVT 변환 후 effective rotor inertia (현재 default 0?)
   - NM 1D scale factor, Iter56 base
   - 예상: +0.05~+0.2

3. **★ dq bias 5th round + 17D 4th round** — virtuous cycle 1-2 more
   - oscillation 패턴이라 saturation 깰 가능성 있음
   - 짧게 시도 (각 NM 20min)

### Tier 2 — RESEARCH_POOL Top 4 (`goal16/RESEARCH_POOL.md` 참조, 4 iter ~2h)

4. **Geom margin** (margin=0.001-0.003m, NM 20min) — 118Hz chattering 직접
5. **Explicit contact pair priority=1** (NM 20min) — solref/solimp averaging 제거
6. **qacc_warmstart seeding** — LCP cold-start spike (A/B test only)
7. **implicitfast + cone=elliptic + impratio=100** (NM 20min) — integrator + cone

### Tier 3 — 외부 research 신규 (시간 남으면)

8. **Stribeck friction** — sit2stand 저속 + jump 고속 결합 (LuGre)
9. **Multi-trial regressor stacking** — cross-trial PE
10. **Sensor noise model** — encoder + torque ripple injection

---

## ★ 절대 규칙 (GOAL16 유지, 모두 strict)

1. **Mode A LOCK**: tau_scale_h = tau_scale_k = 1.0, paper_a_hat 변경 X
2. **CAD L1/L2/LC LOCK** (실측 정확)
3. **arm_hip = 0 LOCK**
4. **Foot cylinder 42×13mm y-axis LOCK**
5. **W_GRF = 0.2**
6. **q/dq Iter56 baseline 5% guard** (1 trial이라도 5%+ 악화 → AXIS REJECT)
7. **매 iter 즉시 Notion + commit** (placeholder 절대 X, batch 절대 X)
8. **외부 research ≥ 2-3 URL 매 iter** (Tier 1은 memory + RESEARCH_POOL.md OK)
9. **8 strict**: 한국어 / 색 X (l1.get_color()) / 2-way plot (Real solid + sim dashed) / **MuJoCo Renderer anim** (matplotlib animation 절대 X) / h_sim abs / Locked Template 22 sections / image 32/32 verify / boundary guardrail 20% + BV ≤ 10
10. **사용자 답변 절대 기다리지 마** — 매 iter 자율 결정, 즉시 다음 iter

---

## ★ 진행 패턴 (매 iter strict cycle)

1. MD read (이전 commit + WORKER_MESSAGE.md if exists + STRICT rules)
2. Axis 결정 (위 Tier 우선, 자율)
3. WebSearch ≥ 2-3 URL (Tier 2/3 신규 axis 시)
4. `goal17/iterN/run_iN.py` 작성 + 실행 → metrics.json + logs.npz
5. q/dq Iter56 baseline 5% guard verify (1 trial 5%+ → REJECT)
6. 4-panel plot 15 + MuJoCo Renderer anim 15
7. `upload_notion_iterN.py` Locked Template 22 sections (한국어)
8. image 32/32 verify
9. MASTER_INSIGHTS_G9.md "## Iter[N] (GOAL17)" section append
10. git commit
11. **즉시 다음 iter** — 사용자 답변 절대 기다리지 마

---

## ★ Base params (Iter56 best, GOAL17 시작점)

`goal16/iter56/iter56_metrics.json`에서 추출:
- 15 trial dq biases (-0.89° ~ +1.00° 이상, Iter50 이후 expand)
- 17D global params (per-trial frozen at Iter55 best)
- Mode A LOCK fields 모두 base

Iter56 sim 재실행 → baseline score 128.6465 확인 후 axis 추가.

---

## ★ 사용자 인사이트 지속 적용

- "**q offset 최대 1° 가능, dq offset은 없을 듯**" → Iter50의 "dq1_bias"는 misnamed, 실제는 **q-offset (각도)** — ±3° wider 결정타 (GOAL17도 동일하게 wider 허용). dq (velocity)는 건드리지 X
  - ★ 코드 변수명 fix 권장: `dq1_bias` → `q1_offset`, `dq2_bias` → `q2_offset` (명명 혼란 방지)
- "**mass scale에도 오차**" → CAD scale ±15% 시도 가능 (Iter30 GOAL12 패턴)
- "**L_VAL, LC_VAL은 정확**" → LOCK 유지
- "**CAD 파라미터 부정확 가능**" (개별 측정 후 합 — 오차 누적) → R/I refit OK
- "**dq에 offset은 없을 듯, 노이즈는 가능**" → dq bias는 fit OK, sensor noise model 시도

---

## ★ 시간 분배 (예시 24h 자율 가정)

- Phase 1 (Tier 1, 6 iter × 30min = 3h)
- Phase 2 (Tier 2 RESEARCH_POOL, 4 iter × 30min = 2h)
- Phase 3 (Tier 3 외부 신규, 시간 남으면 5+ iter)
- Final wrap-up 마지막 30min

---

## ★ 다음 GOAL18 진입 조건

- Tier 1+2+3 모두 시도 후 score plateau (3 iter 연속 <0.05 개선)
- 또는 -22% 도달
- 또는 사용자 interrupt

ultrathink, 자율, dq paradigm + fundamental physics. 끊김없이 사용자 답변 안 기다림.
