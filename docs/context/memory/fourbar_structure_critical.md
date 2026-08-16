---
name: fourbar-structure-critical
description: ★★★★★ 4-bar 링키지 확정 구조 (2026-07-07) — crank/rocker는 정강이 반대방향(무릎 위/뒤). 구위상 XML 사용 금지. 모든 4-bar 작업의 기준.
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# ★★★★★ 4-bar 링키지 확정 구조 (2026-07-07 LOCKED — 절대 잊지 말 것)

## ★ 하드웨어 사실 (2026-07-09 사용자 확인 — 추측 금지 항목)
- **무릎 모터는 thigh에 없음** — hip 모터와 **직렬(동축)로 base 중앙에** 장착. 그래서 4-bar가 필요한 것
  (base의 무릎 모터 → crank(고관절 축) → coupler → calf rocker로 원격 구동)
- **벨트 텐셔너 없음** (07-09 어시스턴트가 지어냈던 허구 — 재발 금지)
- 발 = 실린더 실물 그대로 (형상 개선 여지 없음, 07-09 확인)
- → thigh에 무거운 부착물 없음 = com_dz_th +3cm 상한 추격의 물리적 정당화 없음
  → 미모델 흡수의 정직한 경계로 분류, 케이지 ±3cm 유지 (P17 off-axis도 기각됨)

## 확정 위상 (사용자 하드웨어 확인 + 사용자 CAD 해석식과 기계 정밀도 일치 검증)
- **crank (l_i = 30mm, hip에서 knee 모터가 돌림): 정강이 방향의 반대 (= 정강이 각도 + 180°)**
- **rocker (l_o = 30mm, calf 쪽 부착 레버): 무릎에서 정강이 반대방향 = 무릎 위/뒤쪽으로 30mm** (발쪽 아님!)
- **coupler (푸시로드 250mm): thigh와 평행, 같은 방향(θ₁) — thigh의 반(反)정강이 쪽을 지나감**
- 30-250-30-250 평행사변형 → crank각 ≡ calf각 (1:1, 같은 부호) → 엔코더=crank=q2 매핑 유효
- 링크: thigh=calf=250mm, l_i=l_o=30mm (실험 세션 전부), 발 실린더 r=21mm

## MuJoCo XML 정의 (올바른 빌더)
- **정본 빌더: `Documents/jump-opt-digital-twin/code/goal21/g21_fourbar_flip.py :: build_xml_fourbar_flip`**
- crank geom `fromto 0,0,0 → 0,0,+LC`, crank inertial pos `+RC` / coupler body pos `(0,0,+LC)`, geom −z로 L1 / connect anchor `(0,0,-L1)` (coupler frame) → calf-local `(0,0,+LC)`에 결합
- qpos 초기화 `[bz, q1, q2, -q2, q2]` 그대로 폐루프 성립 (잔차 1e-16)
- ⚠️ **`code/goal19/phase11/mshoot_fourbar.py::build_xml_fourbar_jump`는 구(잘못된)위상** — crank가 정강이와 평행, rocker가 발쪽. G20-A~P9의 canonical(`fourbar_refit_best.json`)이 이 위상으로 fit됨. **새 작업에 사용 금지** (재현용으로만 보존)

## 검증 근거 (P11a, g21_userEq_check.py)
- 사용자 유도 페이지(Notion `302ab81d255080b4811ae496b9bbca56` "수정된 4-bar linkage dynamics")의 구속조건 = crank 정강이+180°, coupler ∥ thigh — **처음부터 옳았음**
- 뒤집힌 MuJoCo vs 사용자 식: 무작위 300상태 |dM|max **4.4e-16**, |dbias|max 3.6e-14 (컴파일 모델 계수로)
- 구위상 vs 사용자 식: |dM|max **3.5e-2** (회전항 ~100% 상대오차) — 모순 정량화

## CAD 계수 (사용자 식 기호, @ pure CAD)
A=0.1289, **B=−0.0037 (거의 완전 상쇄!)**, K=+0.0029, IΣ1=0.0339, IΣ2=0.0036, Mtot=3.20
- serial 뭉침 시절 무릎측 질량모멘트는 +0.175 (부호 반대·48배) — 유령 병진질량의 정량 증거
- **무릎축 중력토크 ≈ |B|g ≈ 0.04 Nm → 전원-off 시 무릎 정지 관찰의 독립 설명** (hip은 A→2.8Nm급, 스르르 낙하)

## P12 재검 결과 (07-07) — 새 구조 위에서 역대 축 전부 재기각
- **connect solref (폐루프 컴플라이언스, 사용자 질문 발): 0.3ms ≡ 0.8ms 완전 동일 (강성 포화) — 0.8ms 하드코딩 검증됨. ≥2ms부터 급격 악화. MuJoCo closed loop = equality connect 구속 (외력 수동정의 아님)**
- arm_hip/motor_tm/sens_delay/strib_knee(옳은 위상에서 재기각)/foot_dz/mu_floor 전부 DROP — **옳은 구조는 레거시 fudge가 하나도 필요 없음**
- ★ 지표 교훈: fs-apex h 항(스탠스 이륙 상태의 탄도 apex)은 full-replay h와 **반상관** — h를 목적에 넣으려면 심판과 같은 프로토콜(full-replay)로 계산해야 함
- P12 Stage-A 해는 0421 특화 (q2 41.9°, h 1.012 역대최고)지만 0424/0602 h 악화 — 비지배

## ★★★ P13e 정직-물리 canonical (07-08) — 권장 작업 기준 교체
- **`fourbar_honest_canonical.json`** = 전 질량 실측/CAD (crank 360g<CAD ✓클러치 교체 정합, calf=CAD(발 포함, 사용자 확인), coupler 150g, m_foot≤10g, **총질량 3.2kg 강제**), I/CoM CAD 케이지, offset ≤3°
- **갤러리 h_ratio 토크날짜 대약진: 0424 0.866→0.902, 0602 0.930→0.961, 0324 0.895→0.961 (under-jump 절반)** + held-out fs_0324 절대최고 (364.5 vs 457.6). 마찰도 물리 소값으로 붕괴 (fv_hip 0.29, fc ~0.01) — 이전 마찰은 유령관성 보상이었음
- 비용: 0602/0324 트레이스·s2s 창 수 % (유령질량 = 창 점수를 사느라 에너지 충실도를 팔던 과적합이었음이 확정)
- 유령 최종 잔여: 0324-knee·0424 offset 3° 레일 + 0421 h 1.18 과대 — 세션 계측 + whip 토크 축 (벤치행)
- m_foot 172g 사건: 질량 아닌 **관성 변장** (m·L²=CAD calf 관성 6배)이었음 — 발은 calf CAD에 포함 (사용자 확인)

## ★ 실측 반영 + M_base 죽은 파라미터 버그 (07-08)
- **버그: 모든 fourbar 빌더에서 M_base 스케일이 읽히고 안 쓰임** (base 항상 1.2598kg 고정) — canonical M_base=1.048은 노이즈였음. g21_fourbar_flip.py에 수정 + TOTAL_MASS 모드 추가
- **실측 (사용자)**: coupler 어셈블리 **150g** (M_p=1.098 LOCK) · **전체 3.2kg** (base 역산 모드) · calf ≈ CAD ±5g · crank < CAD (클러치 모터 교체 — fit의 M_c 0.66~0.89와 정합)
- **P13d 물리-우리 모델** (`p13d_physical.json`): 전 질량 물리·offset ≤3° 클램프 상태에서 obj 7.469/ho 0.938 — 유령질량 모델과 동급 성능 (h만 ~2%p 낮음). 갤러리 0421 41.4°(역대최고)/0424 10.8°/0602 3.77°/0324 11.6°. **물리적 정당성 최강 후보**
- 유령 잔여 거주지: **m_foot 172g** (실측 요청 대상!), offset 4/8이 3° 클램프에 레일 (0324/0424), com_dz_ca −7cm 부호 반전

## 현재 파라미터 (교체 확정, 07-07)
- **작업 기준 = P10-selected**: `code/goal21/fourbar_flip_result.json["selected"]` (obj 6.698/ho 0.938; 갤러리 0421 47.3°/h1.076, 0324 10.8°, 0602 3.48°, 0424 11.8°) — 정본 사본 `fourbar_flip_canonical.json`
- v2(`..._v2.json`): 궤적 최고(0421 dq2 −26%, 0324 −37%)나 h 전날짜 하락 — h가 목적에 없던 편향. **다음 폴리시 = h/에너지를 목적에 포함 후 재적합**
- 미해결: M_p 1.7→2.0 (coupler 질량 CAD 2배 요구) — 실물 저울 측정 대기

관련: [[next-goal21-mission]] [[goal20-marathon-state]] [[goal18_canonical_pipeline]] (렌더링은 serial leg.xml이라 무영향)
