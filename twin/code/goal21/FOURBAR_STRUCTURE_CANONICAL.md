# ★ 4-BAR 링키지 확정 구조 — 2026-07-07 LOCKED (이 문서가 정본)

> 이 구조는 사용자 하드웨어 확인(07-07) + 사용자의 해석적 CAD 유도
> (Notion `302ab81d255080b4811ae496b9bbca56`)와 **기계 정밀도(1e-16) 일치 검증**으로 확정됐다.
> 4-bar를 만지는 모든 미래 작업은 이 문서를 먼저 읽을 것.

## 1. 위상 (제일 중요 — 두 번 틀렸던 부분)

```
              base (수직 레일, slide z)
               │ hip축 = knee모터축 (동축, knee모터 고정자는 thigh에 실림)
   crank 30mm ↑│                ← crank는 "정강이 반대방향" (정강이각 + 180°)
               ├─── thigh 250mm ───┐
   coupler 250mm (푸시로드, thigh와 평행·같은 방향 θ1,
                  thigh의 反정강이 쪽을 지나감)
               │                   knee (수동 힌지)
               │       rocker 30mm ↑  ← 무릎에서 "정강이 반대방향" = 무릎 위/뒤쪽
               │                   │
               └── connect 구속 ───┘   coupler 끝 == rocker 끝
                                   │
                                calf 250mm → 발 (실린더 r=21mm)
```

- **crank(l_i)=30mm, rocker(l_o)=30mm, thigh=coupler=250mm** → 평행사변형
- 따라서 **crank각 ≡ calf각 (1:1, 같은 부호)** → 엔코더(모터각)=q2 매핑 그대로 유효
- CVT = l_i를 바꾸는 것 (식별에 쓴 실험 세션은 전부 30mm 고정)

## 2. 올바른 XML (정본 빌더)

- **`code/goal21/g21_fourbar_flip.py :: build_xml_fourbar_flip()`**
- 핵심 라인: crank geom `fromto="0 0 0  0 0 +LC"` · crank inertial `pos=(0,0,+RC)` ·
  coupler body `pos=(0,0,+LC)` · coupler geom −z 방향 L1 · connect anchor `(0,0,-L1)`
  (coupler frame) → calf-local `(0,0,+LC)` 에 결합
- qpos 초기화 `[bz, q1, q2, -q2, q2]` — 폐루프 잔차 1e-16

### ⚠️ 구(잘못된)위상 — 사용 금지
`code/goal19/phase11/mshoot_fourbar.py :: build_xml_fourbar_jump()`는 crank가 정강이와
**평행**, rocker가 **발쪽** 30mm — 사용자 CAD식과 |dM| 3.5e-2 모순.
G20-A~G21 P9의 canonical(`fourbar_refit_best.json`)이 이 위상으로 fit됐다.
**재현 목적 외에 새 작업에 절대 사용 금지.**

## 3. 검증 기록 (g21_userEq_check.py)

| 대조 | |dM|max | |dbias|max |
|---|---|---|
| 뒤집힌 모델 vs 사용자 해석식 (컴파일 계수) | **4.4e-16** | 3.6e-14 |
| 구위상 모델 vs 사용자 해석식 | 3.5e-2 | — |

사용자 식 계수 @ pure CAD (사용자 기호):
`A=0.1289, B=−0.0037, K=+0.0029, IΣ1=0.0339, IΣ2=0.0036, Mtot=3.20`

### 물리 함의 (기억할 것)
- **B ≈ 0 (거의 완전 상쇄)**: 정강이의 질량모멘트를 crank+coupler가 반대로 상쇄.
  serial 뭉침 모델은 +0.175 (부호 반대, 48배)로 잘못 갖고 있었음 — 유령 병진질량의 정체.
- **무릎축 중력토크 ≈ |B|g ≈ 0.04 Nm** → 전원 꺼도 무릎이 안 움직인 실물 관찰의 설명
  (hip은 A 기준 ~2.8Nm → 스르르 낙하). K≈0.003 → base-무릎 관성결합도 미미.

## 4. 파라미터 현황 (07-07)

- **작업 기준(교체 확정) = P10-selected**: `fourbar_flip_result.json["selected"]`
  = `fourbar_flip_canonical.json` (obj 6.698 / held-out 0.938;
  갤러리 0421 q2 47.3° h 1.076 · 0424 11.8° · 0602 3.48° · 0324 10.8°)
- v2 (`fourbar_flip_result_v2.json`): 궤적 최고(0421 dq2 −26%, 0324 dq2 −37%)지만
  **h_ratio 전 토크날짜 하락**(0.856/0.917/0.880) — h가 목적함수에 없어 생긴 편향.
  → **다음 폴리시 필수: h/에너지 항을 목적에 포함하고 재적합**
- 미해결: M_p (coupler 질량 스케일) 1.7→2.0 — 실물 푸시로드+너트 저울 측정으로 확정 필요

## 5. 무영향 확인
- 렌더링 파이프라인(goal18 v14, serial `leg.xml`)은 q 궤적만 사용 — 위상 무관, 변경 불필요.
- 엔코더 q2 매핑, 좌표 변환(q1m=−q1c−π/2, q2m=−q2c), a_hat 변환 — 전부 그대로.
