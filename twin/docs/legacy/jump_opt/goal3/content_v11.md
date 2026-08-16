# V11 — V8 + Hip cross-coupling (32p) — Negative finding

> **Phase 6b**. V8에 hx1·q2·ddq1 + hx2·dq1·dq2 (MASTER_INSIGHTS 보더라인 정당 항)을 추가. **Jump inverse hip 3.48→2.77 (-20%)**, **boundary 90%→75% 개선**. 그러나 **NLP self-cons hip 2.74→2.93 / knee 0.16→1.82 악화** — V12 GOAL2의 over-fit 함정 재현.

---

## 1. 이 버전 무엇

V11 = V8 (30p+sat) + Hip cross-coupling 2종 = **32p**:
- `hx1·q2·ddq1` (M22 q2-의존, link COM 이동)
- `hx2·dq1·dq2` (Coriolis 일반화)

MASTER_INSIGHTS §17 "보더라인 정당" 카테고리 (over-fit 의심이지만 fit에 도움). hx3 (over-fit 의심)은 제외.

---

## 2. V8 대비 결과

### ✅ Inverse RMSE 개선
| Metric | V8 | V11 | Change |
|---|---|---|---|
| Jump hip MEAN | 3.48 | **2.77** | -20% ↓ |
| Jump knee MEAN | 1.65 | 1.65 | 동일 |
| Boundary chase | 90% | **75%** | -15% (over-fit 감소) |
| hx1 fitted | - | -0.038 | 식별됨 |
| hx2 fitted | - | -0.036 | 식별됨 |

### ❌ NLP Self-cons 악화
| Self-cons | V8 | V11 | Change |
|---|---|---|---|
| Hip | 2.74 | 2.93 | +7% (악화) |
| Knee | **0.16** | **1.82** | **+1.66 Nm (악화!)** |

→ **inverse가 좋아졌는데 forward consistency가 악화** = V12 GOAL2의 **over-fit 함정 재현**.

---

## 3. 이유 분석

hx1, hx2는 학습 데이터의 ddq, dq trajectory에 적합. 그러나:
- NLP가 만든 q*, dq*, ddq*는 학습 데이터와 다른 distribution (NLP는 optimal trajectory, real은 PD 추적)
- hx terms가 학습 trajectory의 특이 패턴을 fit → NLP trajectory에선 다른 dynamics
- → forward consistency 악화

**MASTER_INSIGHTS §17 보더라인 정당 항의 진짜 의미 확인**: 학습 데이터에서 fit 도움 ≠ forward consistency 도움.

---

## 4. 결론 — V8이 GOAL3 BEST stack

V11 결과로부터:
- V8 (V5 30p + AK80 saturation 2 fixed)이 **forward consistency**에서 best
- hx1, hx2 같은 추가 항은 inverse는 좋아지지만 forward에선 trade-off
- **사용자 진짜 metric (forward consistency)** 관점에서 V8 stack 유지

---

## 5. V11 → Master Insights 추가

```
[2026-06-06] V11 negative finding:
hx1, hx2 추가 → inverse RMSE -20% but NLP self-cons knee +1.66 Nm 악화.
보더라인 정당 항은 학습 데이터에 over-fit이지 forward에 도움 안 됨.
V12 GOAL2 (boundary 57%)의 함정 재현.
→ V8 (saturation만 추가) 유지가 best.
```

---

## 6. 진행

- 시작: 2026-06-06 00:00 KST
- 종료: 2026-06-06 00:08 KST
- 소요: 8분 (fit 76초 + NLP 5.5초)
- Deadline까지: ~12h
