@echo off
REM P25-task0 0.5ms 4점 연장 재개 (사용자 승인 07-20) - 더블클릭 시동 (철칙 3)
REM 24/25.08/28/nc30 전부 기존 ckpt에서 T0_RESUME 재개 (예산버그 픽스판:
REM eval 주기 sim-시간 등가 x4, patience 60, 96M cap 실효). nc05는 q1 마진 벌점.
REM 재클릭 재개 가능 (감사 steps>=30M 점은 자동 스킵). 드라이버 = t0_05ms_ext.py
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set P23_SPRING_GATED=1
set P23_RISE_GATED=1
set P24_HIP_LAW=1
set P24_REFIT=1
echo ===== 05ms ext start %date% %time% =====>> t0_05ms_ext.log
python t0_05ms_ext.py >> t0_05ms_ext.log 2>&1
echo EXT-05MS-DONE>> t0_05ms_ext.log
echo.
echo EXT-05MS-DONE  (log: t0_05ms_ext.log)
pause
