# 점프 로봇 디지털 트윈 연구 — 헌법 (얇게 유지, ≤50줄)

## 목적 (모든 판단의 기준)
2-DOF 4-bar CVT 단족 점프 로봇의 MuJoCo 디지털 트윈을 정밀화 → 그 위에서 궤적 최적화 →
**최적화 궤적(q_des, dq_des)으로 실로봇 PD 제어 시 측정 토크 ≈ 계획 토크(τ\*)** (τ-fidelity).
지표·현행 스택 수치는 여기 적지 않는다 → CURRENT_STACK.md가 단일 출처.

## 경로 지도
- 코드/하네스(git): `C:/Users/junho/Documents/jump-opt-digital-twin/` (repo CLAUDE.md 필독)
- 현행 스택/지표: `<repo>/code/bench/CURRENT_STACK.md` · 방법론: `<repo>/code/bench/PLAYBOOK.md`
- 기각된 가설: `<repo>/code/bench/REJECTED.md` (새 축 시도 전 필독)
- 실험 데이터: `C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data/<YY.MM.DD>/` (읽기 전용)
- 레거시 결과/문서: `C:/Users/junho/Desktop/jump_opt/` (MASTER_INSIGHTS*, g22_* 결과 폴더)

## 철칙 10 (훅이 상당수 기계적으로 강제함)
1. 후보 JSON(`fourbar_*_candidate.json`)은 불변 — 갱신은 새 pXX 파일 + `bench promote`로만.
2. `goal18_CANONICAL/`(양쪽 사본)과 `CANONICAL_LOCK.md`는 불가침 — 렌더링은 import해서 쓰기만.
3. 장시간 sweep은 사용자 .bat 더블클릭으로만 시동 (PowerShell/Tee-Object 직접 실행 금지).
4. python 실행 시 `PYTHONIOENCODING=utf-8` (cp949 크래시) — bash면 `export`, 스크립트면 `safe.utf8_console()`.
5. XML 문자열 치환은 `safe.xml_patch`(치환수 검증), qpos/qvel 인덱스는 `safe.qadr/dofadr`(이름 조회)만.
6. 다중 프로세스가 읽는 JSON은 `safe.atomic_json_write`/`safe.read_json`으로만.
7. matplotlib 색 명시 금지 (auto cycle; sim/real 매칭은 get_color 패턴).
8. 노션 업로드 후 이미지 상태 검증 필수 (notion_kit.verify_images).
9. held-out(jump_0324)은 fit에 절대 포함 금지 — 게이트 전용. CL 단독 fit 금지 (Mode A 가드 동반).
10. 개루프(재구성/replay) 최적 ≠ 폐루프 최적 — 커맨드층·지연류는 반드시 물리와 폐루프 공동적합.

## 세션 시동
새 GOAL/마라톤은 `/goal` 커맨드로 시작 (절차 내장). 데이터 폴더 규약은 Data 루트 CLAUDE.md 참조.
