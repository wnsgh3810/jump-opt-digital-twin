# Iter24 SKIPPED

## 상태
- run_i24.py: worst-3 deeper DE script 작성됨 (06-21 20:38 KST)
- gen_plots_i24.py, gen_anim_i24.py: asset script 작성됨
- run_log.txt: 0 byte (sim 시작 직후 abort)
- iter24_metrics.json, iter24_logs.npz: 생성 안 됨 (sim 결과 없음)
- notion_iter24_page.json: 생성 안 됨 (데이터 없음)
- git commit: 없음

## 원인
GOAL16 워크플로우가 Iter24 RUNNING 중 종료 (BG worker 토큰 한도 추정).
이후 워커들은 다음 axis (Iter25 per-trial friction wider) 진행, Iter24 재실행 안 함.

## Iter24 axis가 cover된 대체 iter
- **Iter18 worst-3 DE** (153.52, ★ KEEP) — worst-3 axis 이미 정상 처리
- **Iter25 per-trial friction wider** (Iter18 base, fc/fv ±50%) — Iter24 worst-3 deeper와 같은 trial 친화 axis

→ Iter24 미실행이 GOAL16 결과에 미치는 영향 minimal.

## 보존 이유
- script 파일은 historical record로 유지 (run_i24.py, gen_*.py)
- sim 재실행 X (Iter25에서 충분히 cover, 시간 낭비)

생성: 2026-06-22 사용자 요청 후 (Iter47/56 누락 fix와 함께)
