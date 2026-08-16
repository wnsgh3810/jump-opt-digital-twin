---
name: Sweep wakeup report format
description: V16+ sweep loop wakeup마다 표 형식 + 바운더리 양상 포함 보고
type: feedback
originSessionId: cb42ed46-5d3f-447a-94f6-732ce10d7dfc
---
When reporting from a sweep monitoring wakeup, use this exact structure (Korean, with table + boundary analysis):

```
## V16 N차 체크 (HH:MM)

| 항목 | 값 | 평가 |
|------|-----|------|
| 진행률 | X.YM / 1.26B (Z.ZZ%) | 정상 / 우려 |
| Rate | ~XXXX/s | 정상 범위 / 하락 추세 |
| ETA | XXh (Y일) | — |
| Best score | XX.XX | ▼ 변화 / 동일 |
| 메모리 | python XX GB / system XX/63.7 GB | ✓ |
| 체크포인트 | XM 저장 (HH:MM) / 미완 | — |

**Best=XX.XX 해석**: 짧은 1-2 문장 (이전 best 대비, 의미)

**Top 1 best 파라미터**:
| param | best | range | pos | CAD |
|-------|------|-------|-----|-----|
... 13 dims ...

**Top 100 바운더리 양상**:
- ⚠ chasing (≥80%): list dims
- (lean 50-79%): list dims
- mid (정상): list dims

**다음 wakeup**: HH:MM
```

**Why:** User explicit on 5/6: "루프 보고할 때 이 이미지처럼 하고 바운더리 양상도 같이 보고해". The previous one-line summary ("done=X, best=Y, rate=Z. HH:MM wakeup.") was too terse — user wants full table format with status评가 + boundary 양상 every time, like a structured report.

**How to apply:** Every wakeup-triggered report uses this structure. Do not collapse to one-liner. Top-100 boundary breakdown must include the chasing flags (≥80%) so user can spot fudge zones at a glance. Skip rendering whole 13-dim table only if all dims are mid (no★) — but always include boundary summary.
