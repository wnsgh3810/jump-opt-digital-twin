# ★ WORKER MESSAGE — 사용자 → GOAL16 Agent (a912a38c0682f4840)

**수신 시각**: 2026-06-22 (이 파일 생성 즉시 읽을 것)

---

## ★ 핵심 알림: GOAL16 deadline 2시간 연장

- **기존 마감**: 2026-06-22 10:00 KST (cron `81a0693b`)
- **새 마감**: **2026-06-22 12:00 KST** (cron `3e000a7f` — 이미 활성)
- **Final wrap-up 시작**: 11:30 KST (30min buffer)
- **추가 가용 시간**: ~2h (총 ~7h 실 진행 가능)

---

## ★ 업데이트된 시간 분배

- 실제 iter 진행: **~6.5h** (기존 ~4.5h)
- Final wrap-up: 11:30 KST 시작 (30min)
- Iter40+ 까지 도달 가능성 있음

---

## ★ 새 axis pool 후보 (자율 선택, 시간 여유에 따라)

| Iter | Axis | 내용 |
|------|------|------|
| 29 | per-trial solref_tc ≥ 0.002s 강제 | chattering 직접 fix |
| 30 | per-trial solref_tc + solref_d joint refit | chattering + damping |
| 31 | per-trial imp0/imp_mid wider | contact impulse |
| 32 | dt 0.0005 → 0.0003 | integration step (chattering 줄임) |
| 33 | condim 6→3 | contact DoF reduction |
| 34+ | 외부 research 신규 axis | MuJoCo 2025 contact best-practice |
| 35+ | KEEP axes 다른 method | NSGA-II wider, basinhopping |
| 40+ | 시간 여유 시 추가 | 자율 결정 |

---

## ★ 모든 strict rule 유지

- 매 iter 즉시 Notion + commit
- q/dq 5%+ 보호
- 외부 research ≥ 2-3 URL 매 iter
- Mode A tau_scale=1.0 LOCK
- 8 strict 규칙 전부 유지

---

## ★ 지시

- 이 파일 읽은 후 **끊김없이 자율 진행 계속** — 사용자 답변 절대 기다리지 마
- GOAL16_PROMPT.md line 4 이미 업데이트됨 (12:00 KST + cron 3e000a7f)
- 진행 보고: 짧게 (commit hash + Notion URL list)

---

*이 메시지는 별도 대화창에서 사용자가 전달한 것임. 읽은 후 계속 진행.*

---

## ★★★ 2번째 메시지 — Research Pool 생성됨 (06-22 ~03:00 KST)

`goal16/RESEARCH_POOL.md` 생성됨. Iter30+ 즉시 활용 가능.

**Top 4 우선순위 (verify 실패하지만 implementation hint 풍부)**:
1. **Axis 1 — Geom margin** (margin=0.001-0.003m, NM 20min) — 118Hz chattering 직접 attack, 가장 빠른 win
2. **Axis 2 — Explicit contact pair priority=1** (NM 20min) — solref/solimp averaging 제거, Axis 1 amplify
3. **Axis 7 — qacc_warmstart seeding** (NM 20min) — LCP cold-start spike 제거, A/B test only, 무료
4. **Axis 9 — implicitfast + cone=elliptic + impratio=100** (NM 20min) — Spot/Go1/Go2 표준, integrator도 같이

★ 4개 모두 NM 20min — 80분만에 4 iter 가능 (Iter30, 31, 32, 33). 그 다음 Axis 3 (solimp 5-param BO 40min), Axis 5 (multi-trial regressor stacking NM 20min) 등으로 진행.

★ 모든 axis: Mode A LOCK 준수 / q/dq 5% guard / Iter26 baseline 보호 / 8 strict 준수.
★ Adversarial verify 실패했으므로 BG worker가 매 axis 직접 sanity check (XML 필드 진짜 존재하는지, MuJoCo 버전 호환되는지) 후 진행.
★ 외부 source URL은 pool 본문에 명시됨 — 매 iter Notion 페이지 "외부 출처" section에 인용.

---

## ★★★ 3번째 메시지 — Iter24 누락 + Iter29 Notion verify (06-22 ~03:10 KST)

사용자 query 결과 발견:

**문제 1 — Iter24 통째로 누락**:
- `goal16/iter24/` 폴더: run_i24.py + gen_plots/anim + run_log.txt (0 byte)만 존재
- metrics.json / logs.npz / notion_iter24_page.json **전부 없음**
- 06-21 20:38 사이에 script만 작성하고 sim 실행 자체 abort됨
- commit history에도 Iter24 commit 없음 → **strict rule "매 iter 즉시 Notion" 위반**

**판단 (BG worker가 결정)**:
- (A) Iter24 sim 재실행 + full cycle (~30-40min, axis = worst-3 deeper DE — Iter18 deeper 버전)
  - 단점: Iter25 (per-trial friction wider)에서 이미 worst-3 친화적 axis 시도됨, 중복 가능
- (B) Iter24 skip 처리 — `iter24/SKIPPED.md` 메모 작성 + run_i24.py만 commit
  - 장점: 시간 절약 (~40min 가용), Iter30+ 새 axis 진행에 집중
  - 단점: strict rule 위반 기록 남음

→ **BG worker 자율 판단** (B 권장 — 시간 트레이드오프 우위, Iter18 KEEP 이미 worst-3 정상 처리).

**문제 2 — Iter29 Notion JSON 누락**:
- `iter29_metrics.json` (02:36) + `iter29_logs.npz` ✓
- `upload_notion_iter29.py` (02:39) 작성됨
- **`notion_iter29_page.json` 아직 없음** → upload 진행 중 OR 누락 가능
- BG worker가 지금 만들고 있는 중이면 정상 (Iter29 wall-time이 길었음, post-process 더 필요할 수도)
- 만약 정체 상태면 즉시 upload_notion_iter29.py 실행 + verify

**★ 지시**:
1. Iter24 처리 결정 + 1 commit (재실행 또는 SKIPPED.md)
2. Iter29 Notion 페이지 verify (없으면 즉시 upload + image 30/30 verify)
3. Iter30 진행 (Top 4 axes 중 자율 선택, NM 20min)
4. 이후 Iter31+ 끊김없이 자율 — 사용자 답변 기다리지 마
5. 매 iter 끝마다 strict cycle 100% 준수 — Iter24/29 같은 누락 절대 X

---

## ★★★ 4번째 메시지 — 두 worker 충돌 회피 (06-22 ~03:50 KST)

**상황**: 이전 worker `a912a38c0682f4840`가 sleep/wait 모드로 살아 있고, 후속 takeover worker `a728115707c192a2e`가 발사됨. **두 worker 충돌 위험**.

**실제 진행 (이전 worker가 한 일, 절대 중복 X)**:
- Iter42 완료: score 135.88 (DROP, gap 3.74, Notion 32/32 ✓, commit ✓)
- Iter43 완료: score **133.45** (★ 개선 -1.79%, BV=19, Notion 32/32 ✓, commit ✓)
- Iter44 진행 중: 4 untargeted 0424 trials (90_0.75 / 120_2.5 / 120_2 / 60_0.75 / 60_1.5), 5% pert (BV 감소 목적)

**누적 best**: Iter41 → **Iter43 = 133.45** (Δ vs Iter1 160.79 = **-16.7%**)

**발견된 paradigm**:
- 2nd round NM > 1st round (0602_90_0.75 +0.982 > 1st +0.568) — chain 계속 효과 있음
- 5 trial 한번도 NM 안 됨 (0424_*) → Iter44가 처리 중

**★ Worker `a728115707c192a2e` 너의 지시 (Step 1 verify 시 즉시 확인)**:
1. `ls goal16/` → iter43, iter44 폴더 존재 확인
2. `iter43/iter43_metrics.json` 존재 = 이전 worker가 처리 완료 → **Iter43 post-process 절대 X**
3. `iter44/run_log.txt` 진행 중 (mtime 최근) = 이전 worker가 진행 중 → **Iter44 sim 재시작 절대 X**
4. **대신 할 일** (순서):
   - (a) **Iter24 SKIPPED.md 작성** + commit (5분, 누락 정리):
     ```
     # Iter24 SKIPPED
     Worst-3 deeper DE script 작성됐으나 sim abort (06-21 20:38, run_log.txt 0 byte).
     Iter25 per-trial friction wider로 worst-3 친화 axis 이미 시도됨 (fc/fv ±50%).
     Iter18 worst-3 DE KEEP (153.52)으로 worst-3 정상 처리됨.
     이 폴더는 historical record로 보존, sim 재실행 X.
     ```
   - (b) **Iter44 sim 완료 알림 기다림** (이전 worker가 처리). 만약 1시간 이상 정체 (run_log.txt mtime 1h+) → 이전 worker 죽었다고 판단 → 너가 takeover (Iter44 post-process)
   - (c) **Iter45+ 미리 axis 준비** (RESEARCH_POOL.md 미사용분 또는 NM chain 연장):
     - Iter45 후보 1: **Geom margin** (margin=0.001-0.003m, NM 20min) — RESEARCH_POOL Top 1
     - Iter45 후보 2: **NM chain 3rd round** (Iter43 2nd round paradigm 발견 확장)
   - (d) Iter44 완료 + Iter45 시작 시점에 이전 worker 죽었으면 **즉시 takeover** + continuous evolution 계속

**★ 절대 규칙**:
- `iter43/`, `iter44/` 파일 동시 쓰기 절대 X
- `run_i43.py`, `run_i44.py` 다시 실행 절대 X
- 이전 worker MASTER_INSIGHTS_G9 append와 충돌하지 않도록 → MD section 추가 시 timestamp 다르게
- 사용자 답변 절대 기다리지 마 — Iter24 SKIPPED.md만 작성하고 다음 wait

**Best score 진행**:
| Iter | Score | Δ vs Iter1 | KEEP |
|------|-------|------------|------|
| 1 | 160.79 | baseline | — |
| 18 | 153.52 | -4.52% | ★ KEEP (worst-3 DE) |
| 23 | 152.66 | -5.06% | ★ KEEP (Joint LSQ + friction) |
| 26 | 149.48 | -7.05% | near-KEEP (STACK) |
| 41 | 136.22 | -15.28% | NM per-trial chain |
| **43** | **133.45** | **-17.0%** | ★ NEW BEST (continued chain) |
