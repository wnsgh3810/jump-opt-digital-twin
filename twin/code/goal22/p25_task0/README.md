# p25_task0 — AVT task0 제약 캠페인 (P25)

## 폴더 구조 (방법론별 정리 · CVT 배포 완비 07-21)
```
graphs/  (총 284장)
  OL-CMA/ CL-CMA/ NLP/ PPO/ PPO_long/    # no_cvt 방법 — 기준양식 2×3 (sim파랑/plan주황/des초록)
      ffpd/       gain_<게인>.png × 12    #   FF+PD 배포 (실세션 8게인 + 확장 4게인)
      pd_only/    gain_<게인>.png × 12    #   순수 PD 배포
      pd_shaped/  gain_<게인>.png × 8     #   성형 순수 PD (q_des=q+raw*/Kp)
      (PPO*/train_diag/ — 학습 커브·궤적)
  CVT/  (82장)                            # CVT — no_cvt와 대등한 배포 데이터셋
      plan/       <계획>.png × 5          #   계획 시각화 (li2508/liopt/ol_li2508/li20/li15)
      ffpd/ pd_only/ pd_shaped/  × 24 각  #   CVT 배포 (3계획 × 8게인, 크랭크 tau/dq)
      train_diag/                         #   PPO 학습 진단
  summary/  (8장)                         # 방법 종합
      li_ppo_05ms.png                     #   ★ CMA vs PPO 2ms vs 0.5ms (액션주기 대장정)
      li_ppo_fair_sweep.png               #   공정 스윕 + 이산화 프로브
      li_optimal_4methods.png             #   l_i 최적화 4방법 합본
      cvt_gain_by_method.png              #   변속 없음 vs CVT 이득
      gain_trend.png                      #   게인 12종 F_τ 추세
      real_vs_twin_dq_tracking.png        #   실기 vs 트윈 dq 추종
      li_curve_CMA.png / li_sweep_NLP.png
  task0_style/<방법|CVT>/                 # AVT task0 문법 그림 (보조): plan_3x2/energy/stick

sims/  (canonical 101 + stickfigure 10)
  canonical/<방법>/                       # ★정본: goal18 canonical MuJoCo 렌더 (렌더 h 전부 0.0mm 대조)
      {ffpd,pd_only}/gain_*.gif           #   방법별 배포 게인 8종
      plan.gif / deploy_best.gif          #   대표 계획·배포
  canonical/CVT/                          # CVT 4절링크 렌더
      plan: <계획>_plan.gif × 5           #   계획 시각화
      {ffpd,pd_only}/<계획>_gain_*.gif    #   CVT 배포 (최적게인)
  stickfigure/<방법|CVT>/                 # AVT 스틱피겨 (보조) + 입력 xlsx

(루트) 계획 npz·감사 json (t0nc_*/t0wc_*), t0_spec.py 제약, 하네스 스크립트,
       배포 원장 t0_deploy_results.json / t0_cvt_deploy_results.json / t0_shaped_results.json,
       로그, _rejected/(감사 무효 산출물)
```

## 규약
- 제약: t0_spec.py (τ̂≤15Nm=raw 25.5810 · T-N 포락선 · 각도박스 · dq50)
- 배포 클립 = 하드웨어 천장 35.5 (계획 캡 15Nm는 계획 npz에 이미 반영 — PD 제어 무제약)
- no_cvt 그림 재생성: `P25_GAINS_FULL=1 python t0_ours.py [계획스템]` (그림 graphs/<방법>/<모드>/)
- CVT 배포 재생성: `python t0_cvt_deploy.py` (deploy_cvt: cl_run23 is_cvt=True 정본 배선)
- 고게인 확장: `python t0_hi_gains.py` · 성형: `python t0_shaped.py`
- canonical 렌더: `python t0_mjc_render_all.py` (no_cvt) · `t0_fill_A.py` (CVT 계획) · CVT 배포는 t0_cvt_deploy 내장
- l_i 스윕/PPO 실험: t0_fix_sweep.py · t0_05ms_sweep.bat · t0_05ms_ext.bat (철칙3 .bat 시동)
```
```
