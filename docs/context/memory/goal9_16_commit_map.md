---
name: goal9_16_commit_map
description: "GOAL9~16 git 커밋 맵 (repo C:\\Users\\junho\\Desktop, 677 commits). GOAL14/15는 final 커밋 2개씩 존재"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 63705ea5-db81-4f09-83d9-aa9b74dfbbc4
---

git repo `C:\Users\junho\Desktop` (677 commits). GOAL9~16 전 구간이 하나의 연속 세션(rolling **"GOAL9 checkpoint t+Nh"** 커밋, t+48h~t+144h = 6일+ = 283MB jsonl 세션과 일치).

**주요 milestone 커밋**:
- GOAL12: Final `a74c0e0a`, overfit-진단 `c8bdd6c1` (Iter38 176.41 공식 / Iter42 128.57 기각)
- GOAL13: prep `a1935ca8` (Iter1-8 전부 DROP)
- GOAL14: **`c538b5f1`** "Final Conclusion — Iter28 89.847"(공식 KEEP) + **`a65c8a7b`** "FINAL summary — Iter32 84.13"(post-stop raw, keep=False) + checkpoint `3dd41813`. (Iter30 KEEP `ae489629`, Iter32 `1d6eca68`, Iter22 `d459692c`)
- GOAL15: **`5d9ec6b7`** "Final Conclusion — best 160.79(Iter2 DE 2D, BV=16)"(authoritative) + **`c630a59e`** "method diversity chain". (Iter2 `f2347ffc`, Iter5 basinhopping `ce35185f`)
- GOAL16: Iter17 best `2e09122d`(157.42), Iter16 `432c7492`(159.15), 종합표 `9b8b05ba`, Iter5/6/7 복구 `9998df1b`, Iter8 NSGA-II `d91f0067`, Iter9 LOTO `c85a7c57`, Iter13 MJX `02ae2246`. **공식 final 커밋 아직 없음**(진행 중 스냅샷).

**⚠️ 주의**: GOAL14/GOAL15 모두 "Final Conclusion" 커밋이 2개. GOAL14는 공식 KEEP(Iter28)와 post-stop raw best(Iter32)가 다른 커밋. "best score" 인용 시 항상 KEEP 여부 확인.

**날짜**: GOAL12 06-17, GOAL13 06-18, GOAL14 06-18, GOAL15 06-19, GOAL16 06-21~22.

[[goal14_findings]] [[goal15_findings]] [[goal16_findings]] [[feedback_git_commit]]
