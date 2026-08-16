---
name: slip-measurement-facts
description: "발 슬립 전수 측정(55 trial) 확정 사실 — 하강=세션상수, 푸시=59fps에서만 측정가능, CVT는 슬립 무영향"
metadata: 
  node_type: memory
  type: project
  originSessionId: fcd547c7-41bc-4112-9159-2d1f317a3cc9
  modified: 2026-08-08T18:38:03.208Z
---

2026-08-09 전수 측정 완료 (55 trial · 10세션 · 육안 220컷 검증).
산출물: `C:/Users/junho/CVT/jump_opt/G_slip_all_260809/`

**확정 사실 넷**

1. **하강 슬립 = 세션 상수.** 세션 안 재현성 0.4~1.3mm, 세션 사이 폭 20mm (−13.1 ~ +7.1).
   게인을 60→250 으로 바꿔도 안 변한다 → "그날 바닥"을 재는 양. 지표로 쓸 수 있다.

2. **푸시 슬립은 59fps 세션에서만 측정 가능.** 24fps 는 푸시가 5프레임뿐이라
   동기 ±1프레임이 ±8~10mm 를 흔드는데 게인 효과는 ~5mm 다. 원리적으로 못 잰다.
   59fps(0424·0429·0421)는 15프레임 → ±4mm. 0424 에서 푸시~kp1 r=+0.81, kp1≈120 포화.

3. **CVT 는 발 슬립을 바꾸지 않는다.** 0429(CVT) vs 0424(무변속) 같은 게인 8쌍이 ±2mm 이내.
   앞서 보인 "3배"는 `Reduced._fw` 의 knee=crank(평행사변형) 가정 때문 —
   l_i=25.08 에서 무릎각 18° 오차. `fs_slipmeas.ReducedCVT`(폐쇄 솔버)로 수정 완료.

4. **현행 J_G 는 하강을 볼 수 없다.** 채점 창(plot_window)이 0.16초인데 하강은 3.8초 앞이고,
   ModeA 개루프는 하강 3초를 못 버틴다(q2 RMSE 29~40°). 하강 채점은 CL 로 옮겨야 한다.
   `rollout_cl_fs` 가 이미 `fx`·`slipv` 를 로깅하므로 경로는 뚫려 있다.

**Why:** 이 넷이 Ê_slip 재정의의 전제다. 특히 3번은 하마터면 "CVT 3배 슬립"으로 보고할 뻔했다.
**How to apply:** 슬립 수치를 쓸 때 ① 푸시는 59fps 세션만 ② CVT 세션은 ReducedCVT 경유 확인
③ 하강 채점을 하려면 CL 심판이 먼저다. 관련 [[video-scale-foot-ruler]] · [[metric-provenance-rule]]
