@echo off
chcp 65001 > nul
title Marathon-H joint refit sweep - RUN 3 (unwrap fixed + 2 new loss axes)
cd /d "%~dp0"

rem ===========================================================================
rem  ASCII ONLY.  cmd.exe parses .bat in the system codepage (cp949 here), so
rem  any Korean text in this file is read as garbage commands.  All Korean
rem  explanation is printed by the Python script instead (it runs under
rem  PYTHONIOENCODING=utf-8 with the console already switched to 65001 above).
rem
rem  RUN 3 (2026-08-12 night)  -- why this run exists
rem    RUN 2 started 15:15 but the data reader (fs_data.py) was fixed at 18:47,
rem    so RUN 2 scored the CVT session with 46 torque samples that were off by
rem    exactly 36 N.m.  Python reads the code once at startup, so the fix could
rem    not reach a run already in flight.  RUN 3 restarts with the fix in place.
rem
rem  What changed vs RUN 2
rem    1. Torque wrap fix is now active.  The script prints how many samples it
rem       corrected right after loading; it must NOT be 0.  If it prints 0,
rem       close the window and tell Claude -- do not let it run 6 hours.
rem    2. Two new axes (11 common + 2 extra = 13 total):
rem         - rail friction        FS_RAIL   range 0.000 .. 0.030  start 0.012
rem         - speed-squared loss   FS_W2     range 0.0000.. 0.0020 start 0.0005
rem       Both were found on 08-12 to give -1.40%% together, improving all three
rem       boards at once and passing the held-out gates.
rem    3. Knee dry friction range narrowed to 0.10 .. 0.20 (was 0.15 .. 0.60).
rem       The dead-weight measurement says 0.135 at zero load; RUN 2 landed on
rem       0.153, which sat almost on the old lower bound.
rem
rem  Outputs are tagged "3" so RUN-1 and RUN-2 artifacts are NEVER touched:
rem    RUN 1 keeps  _GHB_sweep.json   _GHB_sweep.log
rem    RUN 2 keeps  _GHB_sweep2.json  _GHB_sweep2.log
rem    RUN 3 writes _GHB_sweep3.json  _GHB_sweep3.log  _GHB_sweep3_trials.jsonl
rem ===========================================================================

set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

set FS_SWEEP_TAG=3
set FS_SWEEP_CVT=1
set FS_SWEEP_MODES=canon_cap

rem  Default is 4 hours, not 6.  RUN-2 log shows the score was already within
rem  0.03%% of its 6-hour value at the 4-hour mark, and within 0.15%% at 2 hours.
rem  The last improvement landed at 300 min and the final 60 min changed nothing.
rem  Pass a number to override, e.g.  _GHB_sweep3.bat 6
set HOURS=%1
if "%HOURS%"=="" set HOURS=4

rem keep this run's own previous output (RUN-1 / RUN-2 files are untouched)
if exist _GHB_sweep3.log          move /y _GHB_sweep3.log          _GHB_sweep3.prev.log   > nul
if exist _GHB_sweep3_trials.jsonl move /y _GHB_sweep3_trials.jsonl _GHB_sweep3.prev.jsonl > nul
if exist _GHB_sweep3.json         move /y _GHB_sweep3.json         _GHB_sweep3.prev.json  > nul

set PY=python
where python > nul 2>&1
if errorlevel 1 set PY=py -3
where %PY% > nul 2>&1
if errorlevel 1 (
  echo.
  echo   [ERROR] python not found on PATH.
  echo.
  pause
  exit /b 1
)

echo.
echo   CHECK THE FIRST LINES: "torque wrap fix N spots" must not be 0.
echo.

%PY% -u _GHB_sweep.py %HOURS%
set RC=%ERRORLEVEL%

echo.
echo ==========================================================================
if not "%RC%"=="0" echo   [ERROR] python exited with code %RC%
echo   RUN 3 files:  _GHB_sweep3.json  _GHB_sweep3.log  _GHB_sweep3_trials.jsonl
echo   RUN 1 / RUN 2 files are untouched.
echo   Rollback instructions:    _GHB_ROLLBACK.md
echo ==========================================================================
pause
