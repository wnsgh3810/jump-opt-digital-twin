@echo off
REM P25-task0 0.5ms 전면 비교 스윕 (사용자 확정 07-19) - 더블클릭 시동 (철칙 3)
REM 런 4개: fix:24:0.5 / fix:25.08:0.5 / fix:28:0.5 (CVT) + nc05 (no_cvt) -> 합본 곡선
REM 26.25@0.5ms는 프로브 기확보(1.0978) 재사용. 드라이버 = t0_05ms_sweep.py
REM (수확 완료 점 자동 스킵, ckpt 있는 점 T0_RESUME 자동 재개, 점별 subprocess 격리)
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set P23_SPRING_GATED=1
set P23_RISE_GATED=1
set P24_HIP_LAW=1
set P24_REFIT=1
echo ===== 05ms sweep start %date% %time% =====>> t0_05ms_sweep.log
python t0_05ms_sweep.py >> t0_05ms_sweep.log 2>&1
echo SWEEP-05MS-DONE>> t0_05ms_sweep.log
echo.
echo SWEEP-05MS-DONE  (log: t0_05ms_sweep.log)
pause
