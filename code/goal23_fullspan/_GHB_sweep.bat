@echo off
chcp 65001 > nul
title 마라톤H 공동 재적합 (질량·탄성·마찰·변환식)
cd /d "%~dp0"

REM ── 마라톤H 공동 재적합 스윕 ───────────────────────────────────────────────
REM  왜: 매달림 실측이 준 관절 마찰값을 하나씩 넣으면 전부 나빠진다.
REM      특히 속도비례 항을 실측대로(거의 0) 줄이면 점프 높이가 +144% 무너진다.
REM      그 항은 관절 마찰이 아니라 다른 손실을 대신 떠맡는 층이므로,
REM      진짜 물리로 바꾸려면 변환식·마찰·질량·탄성을 같이 움직여야 한다.
REM
REM  무엇을: 두 구조를 각각 최적화해서 맞대결시킨다.
REM    (1) 지금 구조  = 분동 저울 곡선 + 보정폭 상한
REM    (2) 새 구조    = 곡선 전액 - 하중에 비례하는 마찰
REM
REM  기준선 = 배포 스택(H2_260811) 그대로. 점수 1.0000 = 현행과 동일, 낮을수록 개선.
REM  게이트 = 별도 보관본(0324)과 위치제어(0421)를 포함한 5종, +2% 초과 시 벌점.
REM  안 건드림 = 발 미끄럼 축(FS_PRESLIDE·FS_IMPRATIO). 이 점수에 미끄러짐이 안 들어가서
REM             같이 풀면 점수만 좋아지고 미끄러짐이 조용히 망가진다.
REM
REM  시간: 기본 6시간 (구조당 3시간). 바꾸려면 아래 숫자를 고칠 것.
REM  결과: _GHB_sweep.json (최적값·게이트) · _GHB_sweep.log (전 과정) ·
REM        _GHB_sweep_trials.jsonl (세대별 기록 — 중간에 꺼도 여기까지는 남는다)
REM ──────────────────────────────────────────────────────────────────────────

set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

REM 지난 실행 결과는 .prev 로 밀어두고 새로 시작한다 (덮어써서 잃지 않도록)
if exist _GHB_sweep.log            move /y _GHB_sweep.log            _GHB_sweep.prev.log    > nul
if exist _GHB_sweep_trials.jsonl   move /y _GHB_sweep_trials.jsonl   _GHB_sweep.prev.jsonl  > nul
if exist _GHB_sweep.json           move /y _GHB_sweep.json           _GHB_sweep.prev.json   > nul

echo.
echo   마라톤H 공동 재적합을 시작합니다. 6시간 예정입니다.
echo   창을 닫지 마세요. 중간에 꺼도 _GHB_sweep_trials.jsonl 까지는 남습니다.
echo.

python -u _GHB_sweep.py 6

echo.
echo ==========================================================================
echo   끝났습니다. 결과 파일:
echo     _GHB_sweep.json          최적값과 게이트 결과
echo     _GHB_sweep.log           전 과정 기록
echo     _GHB_sweep_trials.jsonl  세대별 기록
echo ==========================================================================
pause
