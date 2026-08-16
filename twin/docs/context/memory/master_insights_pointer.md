---
name: master-insights-pointer
description: 2-DOF jump robot 프로젝트의 모든 깨달은 점/발견을 한 곳에 모은 master 문서의 위치 + 사용법. 새 goal 시작 시 반드시 read.
metadata: 
  node_type: memory
  type: reference
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# Master Insights 문서 위치

## ★ 현행 메인 위치 (2026-06-09 이후, GOAL9~16)

**`C:\Users\junho\CVT\jump_opt\MASTER_INSIGHTS_G9.md`** (10,239줄, 548K, 2026-06-09~ 계속 append)

이게 **현재 authoritative 마스터 문서**. 새 goal(GOAL17+) 시작 시 **반드시 read**. 구조맵(line 기준):
- 1–124 Header/Base model/Score fn | GOAL9 125–1512 (Final stack @893, 5 Mode-A insights @940)
- GOAL10 1613–4374 (Final v3 @3700) | GOAL11(=Final v4, goal10 dir) 4375–4541 (@4394 score 132.84)
- **GOAL12** 4543–6862 (★ Iter38 @6549 = 176.41, Final @6766, Iter42 overfit @6782)
- GOAL13 7003–7589 (8축 DROP, Final @7621) | **GOAL14** 7732–8867 (Iter28 @8379 clean / Final @8635)
- **GOAL15** 8904–9580 (Iter2 DE best, Final @9357) | GOAL16 9735–tail (진행 중 스냅샷)

§20.x = 각 GOAL 중간분석, §20 template으로 새 발견 append.

## 구버전 (superseded)

`MASTER_INSIGHTS.md`(1,966줄, GOAL5 이전) + `MASTER_FINDINGS_UNIFIED.md`(3,908줄)는 **G9이 대체**. Mode-A 디지털트윈 재정의·per-trial mass-scale·CAD m_calf/R-I 발견 이전 문서라 아래 highlights는 역사 참고용.

## (구버전) 무엇이 있나

`MASTER_INSIGHTS.md`는 2026-04 ~ 2026-06-05 발견을 21 section으로 정리:

1. 사용자 진짜 goal vs 우리 metric (구조적 잘못)
2. 시스템 기본 정보 (CAD, AK80-9, 4-bar CVT, 측정)
3. Floating base 동역학 표준 (J^T·F_ext)
4. 정적+Jacobian 토크 vs 측정 τ 갭 (3-4 Nm origin 분해)
5. 접촉 모델 (alpha/soft/hard/surrogate, GRF RMSE 33→10 N)
6. 마찰 진화 (viscous → Coulomb → Stribeck)
7. AK80-9 motor (paper a_hat 5-param, lag, back-EMF saturation)
8. CVT 4-bar (TR, clutch dynamics 누락, body roll)
9. 채터링 (with_cvt, NLP GRF, contact 발진)
10. v2~v51 + GOAL2 v5~v12 identification narrative
11. NARX/observer 탐색 (별개 path, ref-only NARX 8.83 N GRF)
12. 사용자 5가지 비판 + 응답
13. 최적화 방법론 (BO TPE, L-BFGS, multi-start, boundary chase)
14. Forward vs Inverse 구분
15. NLP self-consistency 5.9/6.3 의미
16. V10/V12 stack 정리 + 한계
17. **미검증/미해결 17가지** (다음 작업 시 우선)
18. 다음 작업 권장 — A+C 융합 plan (29 params, 3~4일)
19. 사용자 작업 패턴 (참고)
20. **미래 발견 append template**
21. 참고 자료 인덱스

## 언제 사용?

### When to read

- 새 goal 시작 시 → §1 → §17 → §18 → §19 순서
- 특정 문제 만났을 때 → §17 list에서 관련 항목 찾기
- 어떤 발견 이전에 있었는지 확인 → §10 narrative
- 사용자가 "이 발견 어디 있었지?" 물어볼 때 → §21 인덱스

### When to update

새 발견/insight/web research/논문 결과 시 §20 template으로 append:

```markdown
### YYYY-MM-DD: <제목>
**발견**: <1줄>
**증거**: 숫자 + 파일 + git commit
**의미**: <왜 중요한가>
**관련 section**: §X, §Y
**발견 환경**: <어디서>
```

기존 sections도 발견에 따라 update.

## 핵심 발견 highlights (최우선 인지)

### 1. 우리 measured metric ≠ 사용자 진짜 goal
- 우리: inverse RMSE on training data
- 사용자: NLP optimal trajectory를 실 로봇에 재생 시 forward consistency
- 차이: NLP self-consistency 5.9/6.3 Nm가 증거 — 모델이 NLP에 그대로 못 들어감

### 2. mom·GRF은 baseline에도 표준 J^T·F_ext로 존재
- V12 추가가 아님 — link length의 polynomial 보정 (dmom_h_*)이 추가, 이건 over-fit 의심

### 3. AK80-9 paper a_hat 필수
- 5-param model (UMich 실측), currentTorque는 raw iTM
- Pure Paper 식 (sgn(v) only) 사용, GitHub s(v) smoothing 금지

### 4. Motor lag tau_m ~25 ms는 essential (v14 breakthrough)
- 이전 v2-v13은 motor lag 모르고 offsets로 보상
- 50% jump inverse RMSE 감소
- per-folder variation 24-43 ms = driver mode switch 신호

### 5. Saturation cannot be curve-fit away
- Knee 50-70% saturated in jumps
- weighted LS (v17/18) 또는 strict weight=0 (v9+) 만 동작

### 6. 150_2.2_500_5는 측정 outlier
- Local fit 가능하지만 다른 regime (tau_m 2.6ms vs 26ms)
- LOO에서 제외 권장

### 7. NARX/observer는 physics-based보다 좋을 수 있음
- Ref-only NARX: GRF 8.83 N vs contact surrogate 10.1 N
- Contextual RLS: GRF 5.13 N (warmup 100-200ms 필요)

### 8. 다음 작업 = A+C 융합 (사용자 합의)
- jump_opt baseline 식 + V1~V12 중 명백 정당 7-10개 distill
- 예상 29 params, 3-4일, forward sim drift metric

## 관련 메모리

- [[ak80_9_torque_calibration]] — motor 5-param
- [[goal2_final_stack]] — V10/V12 정리
- [[high_pd_outlier_150_500_5]] — outlier 진단
- [[sysid_findings]] — gAv=1.57 발견
- [[analysis_findings]] — sim-to-real gap
- [[decisions_log]] — 15 major decisions
- [[hip_torque_lift_off_diagnosis]] — foot length 한계
- [[position_data_26_06_02_model]] — v15 motor lag
- [[sweep_optimization_lessons]] — 169M sweep
- [[pd_sim_purpose]] — 디지털 트윈 본질
- [[digital_twin_priority]] — 매칭 우선순위
