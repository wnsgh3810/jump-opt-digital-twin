@echo off
chcp 65001 > nul
title Marathon-H joint refit sweep
cd /d "%~dp0"

rem ===========================================================================
rem  ASCII ONLY.  cmd.exe parses .bat in the system codepage (cp949 here), so
rem  any Korean text in this file is read as garbage commands.  All Korean
rem  explanation is printed by the Python script instead (it runs under
rem  PYTHONIOENCODING=utf-8 with the console already switched to 65001 above).
rem  2026-08-11: first version had Korean comments and broke on the user's box.
rem ===========================================================================

set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

set HOURS=%1
if "%HOURS%"=="" set HOURS=6

rem keep the previous run's output instead of overwriting it
if exist _GHB_sweep.log          move /y _GHB_sweep.log          _GHB_sweep.prev.log   > nul
if exist _GHB_sweep_trials.jsonl move /y _GHB_sweep_trials.jsonl _GHB_sweep.prev.jsonl > nul
if exist _GHB_sweep.json         move /y _GHB_sweep.json         _GHB_sweep.prev.json  > nul

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
echo   files:  _GHB_sweep.json  _GHB_sweep.log  _GHB_sweep_trials.jsonl
echo ==========================================================================
pause
