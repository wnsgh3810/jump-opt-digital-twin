# p25_task0 — AVT task0 제약 캠페인 (P25)

## 폴더 구조
- `graphs/` — **기준양식 그림** (g22_p24a_all_results 2×3 규약, sim 파랑/plan 주황, 게인당 1장):
  `t0nc_<계획>_std_<게인>.png` 40장 + 합본 (`t0_li_synthesis` l_i 4방법, `t0_cvt_gain` CVT 이득,
  `t0wc_li_curve`/`t0wc_nlp_sweep` h(l_i) 곡선)
- `graphs/task0_style/` — AVT task0 문법 그림 (3×2 fig1·에너지 fig2·스틱) — 보조
- `sims/canonical/` — **정본 시뮬레이션** (goal18 canonical MuJoCo 렌더, 640×480 iso):
  `mjc_<계획>_{plan,deploy}.gif` 9종 + 렌더-수치 대조 `mjc_render_summary.json`
- `sims/stickfigure/` — AVT animate_results 스틱피겨 GIF + 입력 xlsx — 보조
- 루트 — 계획 npz + 감사 json (`t0nc_*`, `t0wc_*`), 제약 스펙 `t0_spec.py`, 하네스
  (`t0_deploy/t0_figs/t0_export/t0_make_all/t0_ours/t0_mjc_render/t0_li_synthesis`),
  배포 원장 `t0_deploy_results.json`, 로그

## 규약
- 제약: t0_spec.py (τ̂≤15Nm=raw 25.5810 · T-N · 각도박스 · dq50), 배포 클립 동일
- 그림 재생성: `P25_CLIP_RAW=25.5810 P25_GAINS_FULL=1 python t0_ours.py [계획스템]`
- 렌더 재생성: `python t0_mjc_render.py` (canonical 렌더러 import-only)
