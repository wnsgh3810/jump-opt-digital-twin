@echo off
chcp 65001 > nul
title Marathon-H joint refit sweep - RUN 2 (CVT included)
cd /d "%~dp0"

rem ===========================================================================
rem  ASCII ONLY.  cmd.exe parses .bat in the system codepage (cp949 here), so
rem  any Korean text in this file is read as garbage commands.  All Korean
rem  explanation is printed by the Python script instead (it runs under
rem  PYTHONIOENCODING=utf-8 with the console already switched to 65001 above).
rem
rem  RUN 2 (2026-08-12 evening)
rem    - CVT session 26.04.29 (10 trials) is now IN the fit set (8 sessions).
rem    - Start point moved to the RUN-1 winner (current stack H3).
rem    - Only the current torque-map structure is swept (canon_fric was
rem      rejected in RUN 1: REJECTED #82 / #83).
rem    - Outputs are tagged "2" so RUN-1 artifacts are NEVER touched:
rem        RUN 1 keeps  _GHB_sweep.json  _GHB_sweep.log  _GHB_sweep_trials.jsonl
rem        RUN 2 writes _GHB_sweep2.json _GHB_sweep2.log _GHB_sweep2_trials.jsonl
rem ===========================================================================

set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

set FS_SWEEP_TAG=2
set FS_SWEEP_CVT=1
set FS_SWEEP_MODES=canon_cap

set HOURS=%1
if "%HOURS%"=="" set HOURS=6

rem keep this run's own previous output (RUN-1 files are untouched by design)
if exist _GHB_sweep2.log          move /y _GHB_sweep2.log          _GHB_sweep2.prev.log   > nul
if exist _GHB_sweep2_trials.jsonl move /y _GHB_sweep2_trials.jsonl _GHB_sweep2.prev.jsonl > nul
if exist _GHB_sweep2.json         move /y _GHB_sweep2.json         _GHB_sweep2.prev.json  > nul

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

%PY% -u _GHB_sweep.py %HOURS%
set RC=%ERRORLEVEL%

echo.
echo ==========================================================================
if not "%RC%"=="0" echo   [ERROR] python exited with code %RC%
echo   RUN 2 files:  _GHB_sweep2.json  _GHB_sweep2.log  _GHB_sweep2_trials.jsonl
echo   RUN 1 files (untouched):  _GHB_sweep.json  _GHB_sweep.log
echo   Rollback instructions:    _GHB_ROLLBACK.md
echo ==========================================================================
pause
