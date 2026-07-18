# p25_task0 — AVT task0 제약 캠페인 (P25)

## 폴더 구조 (방법론별 정리, 07-18)
```
graphs/
  OL-CMA/ CL-CMA/ NLP/ PPO/ PPO_long/   # 기준양식(2×3, sim파랑/plan주황) 배포 그림
      deploy_gain_<게인>.png × 8게인      #   게인당 1장
  PPO*/train_diag/, CVT/train_diag/      # 학습 진단 (커브·궤적·licurve)
  summary/                               # 방법 종합
      li_optimal_4methods.png            #   l_i 최적화 4방법 합본
      cvt_gain_by_method.png             #   변속 없음 vs CVT 이득
      li_curve_CMA.png / li_sweep_NLP.png
  task0_style/<방법|CVT>/                # AVT task0 문법 그림 (보조)
      plan_3x2 / deploy_best_3x2 / deploy_gains8_3x2 / energy / stick
sims/
  canonical/<방법|CVT>/                  # ★정본: goal18 canonical MuJoCo 렌더
      plan.gif / deploy_best.gif         #   (CVT는 CL_li25.08_plan.gif)
  stickfigure/<방법|CVT>/                # AVT 스틱피겨 (보조) + 입력 xlsx
(루트) 계획 npz·감사 json (t0nc_*/t0wc_*), t0_spec.py 제약, 하네스 스크립트,
       배포 원장 t0_deploy_results.json, 로그, _rejected/(감사 무효 산출물)
```

## 규약
- 제약: t0_spec.py (τ̂≤15Nm=raw 25.5810 · T-N 포락선 · 각도박스 · dq50), 배포 클립 동일
- 그림 재생성: `P25_CLIP_RAW=25.5810 P25_GAINS_FULL=1 python t0_ours.py [계획스템]`
  (파일은 루트에 생성됨 → graphs/<방법>/으로 이동 규약)
- 렌더 재생성: `python t0_mjc_render.py` (canonical 렌더러 import-only)
