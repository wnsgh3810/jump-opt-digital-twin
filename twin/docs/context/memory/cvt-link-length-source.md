---
name: cvt-link-length-source
description: CVT 링크 길이 l_i 는 trial 별 Clutch.xlsx 실측 — 구 코드의 0.02499 는 실측이 아니라 점수 튜닝값이었다
metadata:
  type: project
---

**l_i 는 `fs_data.cvt_li(trial폴더)` 로 읽는다** (그 trial 의 `Clutch.xlsx` 중앙값).
Clutch 가 없으면 `L_I_NOM = 0.030`(무변속). `load2` 가 `d["l_i"]` 로 실어 준다.
0429 실측: 25.075~25.102mm (trial 내 표준편차 0.004mm · trial 간 퍼짐 0.027mm).

**과거 사고 (08-09 발견)**: 코드에 `0.02499` 가
`# Clutch.xlsx 실측` 주석과 함께 박혀 있었다. **센서 범위 25.06~25.10 밖이다.**
진짜 출처는 `fs_uboard` 주석 — "25.08 대신 24.99 가 ModeA 전수 개선" = **점수 튜닝값**.
게다가 모델은 25.08 로 짓고 `cvt_init`/`rtab` 은 24.99 를 써서 **모델과 초기화가 불일치**했다.

바로잡은 뒤 0429 ModeA: q1 4.173→3.974(−4.8%) · q2 24.040→22.626(−5.9%), **10/10 개선**.
분해하면 **24.99→25.08 이 −4.4/−5.6%**, trial 분리는 −0.4/−0.3% (10개 중 7개 개선 3개 미세악화).
⇒ trial 별 유지 근거는 **성능이 아니라 장부** (손으로 고를 값을 없앤다). 두 근거를 섞어 적지 말 것.

`l_i` 는 링크 **치수**라 `build_cvt_pair(li)` 로 모델까지 다시 지어야 한다
(검증: l_i 2mm 차 → body_pos 2mm 차. 이 2mm 는 **빌더 검증용 탐침**이지 trial 차이가 아니다).

**Why:** 튜닝값이 "실측"으로 기록되면 다음 사람이 고정점으로 믿고 다른 축을 거기 맞춘다.
**How to apply:** CVT 관련 코드에서 l_i 를 상수로 쓰지 말 것. 관련 [[measurement-vs-computation]] · [[metric-provenance-rule]]
