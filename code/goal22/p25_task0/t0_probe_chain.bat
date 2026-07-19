@echo off
REM P25-task0 이산화 프로브 체인 (코디 07-19) - 사용자 더블클릭 시동 (철칙 3)
REM 남은 체인: 프로브 1ms @26.25 (T0_RESUME, 1.72M ckpt 재개) -> 0.5ms -> 합본 곡선
REM 드라이버 = t0_fix_sweep.py (수확 완료 점 자동 스킵, ckpt 있는 점 자동 재개, 점별 격리)
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set P23_SPRING_GATED=1
set P23_RISE_GATED=1
set P24_HIP_LAW=1
set P24_REFIT=1
echo ===== probe chain start %date% %time% =====>> t0_probe_chain.log
python t0_fix_sweep.py >> t0_probe_chain.log 2>&1
echo PROBE-CHAIN-DONE>> t0_probe_chain.log
echo.
echo PROBE-CHAIN-DONE  (log: t0_probe_chain.log)
pause
