# jump-opt-digital-twin — 코드 지도 (≤60줄 유지)

> ## ▶ 새 세션이면 `docs/context/HANDOFF.md` 를 먼저 끝까지 읽어라.
> 연구 배경 · 경로 지도 · **지금 돌아가고 있는 작업** · 누적 발견 41건 · 절대 규칙 · 보고 형식이 거기 있다.
> 이 파일은 그 다음이다 (코드 구조 전용).
> Codex 등 다른 에이전트용 진입점은 루트의 `AGENTS.md`.

연구 헌법 = `docs/context/CONSTITUTION.md` — **이 파일이 정본**. (옛 원본 `C:/Users/junho/Desktop/CLAUDE.md` 는 2026-07-12 판에서 멈췄다. 참고만.)
데이터 사전 = `docs/context/DATA_DICT.md` (원본 `Data/CLAUDE.md`) — 데이터 만지기 전 필독.
현행 스택/지표 수치는 `code/bench/CURRENT_STACK.md`가 단일 출처.
누적 발견은 `docs/context/memory/MEMORY.md` 색인 → 개별 문서.

## 코드 지도
```
code/
├─ bench/            평가 하네스 (bench.py CLI, safe.py, p19_adapter, registry, PLAYBOOK/REJECTED)
├─ goal18_CANONICAL/ 시각화 "규격" 정본 v14 — LOCK (수정 금지, import 전용).
│                    주의: 내부 leg.xml은 pre-4bar 2링크 모델 — 4-bar 렌더 정본은
│                    goal22/p18_cvt/cvt_anim.py::build_anim_model (canonical 규격 상속)
├─ goal21/           4-bar 구조 정본 (g21_fourbar_flip.py = 모델 빌더 정본, g21_p13_linkage 등)
├─ goal22/
│   ├─ p14_ahat/     p14_judge.py = 이중 심판 (Mode A 창 + CL τ-채널, winit() 트라이얼 캐시)
│   ├─ p16_structure/ P16 후보 + springref 패치 (p16a_spring.build_with_ref)
│   ├─ p18_cvt/      CVT(l_i 가변) 빌더/러너 (cvt_core, cvt_run2) + P18b 후보
│   ├─ p19_jump/     τ-fidelity 심판/러너 (p19_judge, p19_run, 커맨드층 p19_cmdlayer.json) + P19 후보
│   └─ p20_rise/     pre30 해체 마라톤 (PLAN/HYPOTHESES, exp 프로브, 노션 빌더)
└─ goal19/           GOAL19 유산 (참조용)
```

## import 규약 (ModuleNotFoundError 예방)
- sys.path는 **절대경로**로: p19_jump·p18_cvt·p14_ahat·p16_structure·goal21 (bench/p19_adapter.py 상단이 정본 부트스트랩 — 복붙 말고 import 하라).
- 모든 심판/러너 사용 전 `p19_judge.winit()` (또는 p14_judge.winit) 선행 필수.
- 함정: `cvt_run2.A`는 모듈 전역 변환식 — 다른 A로 평가하려면 주입 후 복원 (p19_judge.eval_cl_cvt 패턴 참조).
- 데이터 로더가 실행 시 산출물(JSON)을 쓰는 모듈 있음 — 다중 워커는 safe.read_json/atomic 사용.

## 평가 하네스 (모든 후보 평가는 이걸로)
```
python code/bench/bench.py eval <candidate.json>      # per-ds τ-갭 + FIT/HO + 재현판정
python code/bench/bench.py compare <a> <b> ...        # 맞대결 매트릭스
python code/bench/bench.py promote <cand> --note ".." # 게이트(재현+held-out) 통과 시만 승격
python code/bench/bench.py list | stack
```

## 후보 JSON 규약
- 네이밍: `fourbar_pXX_candidate.json` (goal 하위 폴더에), **기존 파일 덮어쓰기 금지** (safe.candidate_save가 거부).
- 스키마: `CANDIDATE`(라벨) · `names[]`/`x[]`(파라미터) · `A`("paper" 등) · 선택: `cmdlayer`, `metric_full/metric_push/heldout`(bench가 재현 대조에 사용), `rows`.
- 3계층 구조: 플랜트 물리(x) × 커맨드층(α·클립·지연) × 변환식 A — 승격 시 세 계층 모두 명시.

## 결과물 관례
- 그림/GIF 결과 폴더: `C:/Users/junho/CVT/jump_opt/g22_<이름>_results/` (repo에 대용량 바이너리 커밋 금지)
- GIF는 goal18_CANONICAL 규격으로만 (새 렌더러 금지) — cvt_anim.py가 상속 실례.
- GIF 텍스트 오버레이는 `bench/render_kit.draw_overlay`만 (표준 7필드: trial/t/base_z/hip/knee/h_sim/h_real
  + **l_i 상시 표기** — 사용자 선호 2026-07-13). CL 렌더/그래프는 커맨드층(α+클립) 반영 필수 (훅이 경고).
- **sim vs real 트라이얼 그래프는 `bench/render_kit.fig_trial_std`만** (png_v2 규격 = cvt_results_v2 출처,
  2×3: q(deg)+q_des/dq1/dq2/hipτ/kneeτ/GRF). 새 그림 포맷 발명 금지 — 지표는 `cvt_run2.metrics2` 재사용 (훅이 경고).
- 일반 원칙: **새 러너/그림/지표 함수를 쓰기 전에 정본(cl_run·sim_run·metrics2·render_kit)을 import** —
  기준 코드가 있으면 그걸 쓰고, 없을 때만 새로 만들어 bench에 정본화.
- 커밋: 발견 단위로 즉시, 메시지에 수치 포함 (사용자 선호: 자동 커밋).
