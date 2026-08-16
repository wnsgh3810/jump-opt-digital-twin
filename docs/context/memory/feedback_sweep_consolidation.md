---
name: Multi-trial Sweep 결과 자동 통합 선호
description: Multi-trial sweep(v9~)이 완료될 때마다 multi_trial_top_combined.npz 업데이트해야 함
type: feedback
originSessionId: cb42ed46-5d3f-447a-94f6-732ce10d7dfc
---
**규칙: Multi-trial sweep 완료 시 자동으로 `multi_trial_top_combined.npz` 업데이트**

**Why**: 사용자가 26.04.29에 명시적으로 요청. 매 sweep 결과 누적해서 비교 분석 가능하게 하기 위함. 새 버전 결과 누락되면 비교 가치 떨어짐.

**How to apply**:
- v9, v10, v12, v13, v14 같은 multi-trial sweep이 완료되면 (`pd_sweep_a1_v*_best.npz` 또는 `_checkpoint.npz` 저장된 시점) 즉시:
  1. `combine_multi_trial_top500.py` 실행
  2. 결과 `multi_trial_top_combined.npz` 갱신 확인 (rows 증가했는지)
  3. 사용자에게 통합 결과 짧게 보고 (총 rows, 새 버전의 best score, top-N에서 새 버전 등장 여부)
- 신규 버전(v15, v16 ...)이 추가되면 `combine_multi_trial_top500.py`의 `VERSIONS` 리스트에 추가
- v9, v10은 11 dim → M_tot=3.268, fb=0 기본값으로 채워서 19 컬럼 표준화 (이미 처리됨)

**파일 위치**:
- 통합 파일: `C:\Users\junho\Desktop\multi_trial_top_combined.npz`
- 통합 스크립트: `C:\Users\junho\Desktop\combine_multi_trial_top500.py`

**npz 구조**:
- `data`: shape (N, 19), columns = [sc_mean, sc_max, alpha, gAv, gBv, Is1, Is2, Kv, kc, bc, sp, sd, tm, M_tot, fb, q1e_avg, q2e_avg, tau1e_avg, tau2e_avg]
- `versions`: shape (N,), 'v9'/'v10'/'v12'/...
- `columns`: 19 field name array
- 정렬: sc_mean ascending (best 먼저)
