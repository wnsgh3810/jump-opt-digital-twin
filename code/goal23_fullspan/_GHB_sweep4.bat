@echo off
chcp 65001 > nul
title Marathon-H joint refit sweep - RUN 4 (new ruler + torque 35%% + gate vs deployed stack)
cd /d "%~dp0"

rem ===========================================================================
rem  ASCII ONLY.  cmd.exe parses .bat in the system codepage (cp949 here), so
rem  any Korean text in this file is read as garbage commands.  All Korean
rem  explanation is printed by the Python script instead (it runs under
rem  PYTHONIOENCODING=utf-8 with the console already switched to 65001 above).
rem
rem  RUN 4 (2026-08-13)  -- what changed vs RUN 3.  Three user decisions.
rem
rem    1. NEW RULER.  The score is no longer "my error / two-generations-old
rem       model's error over the whole window".  It is now the raw quantity
rem         (RMS error over the FIRST 80%% of the window) / (std of that signal)
rem       so 0.00 is perfect and the number is directly comparable to the pass
rem       line the user's own eye produced: hip torque 0.24 / knee torque 0.08
rem       = "excellent", hip 0.53 / knee 0.43 = "unusable".
rem       Note: keeping the old ratio structure and merely inserting the std
rem       would change NOTHING - the std cancels top and bottom.  Dropping the
rem       reference-model division is the substance of this change.
rem       The old-ruler score is still computed and printed side by side.
rem
rem    2. TORQUE WEIGHT 13%% -> 35%%.  Of 22 complaints the user wrote while
rem       reviewing 139 figures, 14 were about torque, yet torque carried only
rem       2 of 6 closed-loop channels x 0.40 = 13%% of the score.
rem         injection replay (angle+speed, 4ch)   0.35
rem         closed-loop angle+speed  (4ch)        0.20
rem         closed-loop TORQUE       (2ch)        0.35
rem         jump height                           0.10
rem
rem    3. PENALTY BASELINE -> DEPLOYED STACK.  Until RUN 3 the held-out
rem       sessions were compared against a two-generations-old model, so a
rem       candidate could be 5-6%% worse than the stack we actually ship and
rem       still show penalty 0.000.  The RUN 3 winner did exactly that.
rem
rem    4. AXES 13 -> 12.  Dropped "loss growing with speed squared" (knee speed
rem       squared).  That axis alone at 0.0005 blew the score from 0.953 to
rem       38.58, and RUN 3's own search drove it to zero.  Rail friction
rem       survived: removing it from the winner takes 0.9466 -> 3.8733.
rem
rem    Also fixed on 08-13: _apply did not clear FS_RAIL / FS_W2, so a value
rem    from the previous evaluation could silently survive into the next one.
rem
rem  Expected first lines (verify before leaving it to run):
rem    - "torque wrap fix 46" spots.  If 0, close the window and report it.
rem    - deployed stack penalty must be exactly 0.000 (it IS the baseline).
rem    - starting point (RUN 3 winner) penalty will NOT be 0 - that is correct
rem      and is the whole point of change 3.
rem
rem  Outputs are tagged "4" so RUN-1/2/3 artifacts are NEVER touched:
rem    RUN 1 keeps  _GHB_sweep.json   _GHB_sweep.log
rem    RUN 2 keeps  _GHB_sweep2.json  _GHB_sweep2.log
rem    RUN 3 keeps  _GHB_sweep3.json  _GHB_sweep3.log
rem    RUN 4 writes _GHB_sweep4.json  _GHB_sweep4.log  _GHB_sweep4_trials.jsonl
rem ===========================================================================

set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

set FS_SWEEP_TAG=4
set FS_SWEEP_CVT=1
set FS_SWEEP_MODES=canon_cap

rem  Default 4 hours.  RUN-3 log shows the score was within 0.03%% of its final
rem  value at the 4-hour mark.  Pass a number to override, e.g. _GHB_sweep4.bat 6
set HOURS=%1
if "%HOURS%"=="" set HOURS=4

rem keep this run's own previous output (RUN-1/2/3 files are untouched)
if exist _GHB_sweep4.log          move /y _GHB_sweep4.log          _GHB_sweep4.prev.log   > nul
if exist _GHB_sweep4_trials.jsonl move /y _GHB_sweep4_trials.jsonl _GHB_sweep4.prev.jsonl > nul
if exist _GHB_sweep4.json         move /y _GHB_sweep4.json         _GHB_sweep4.prev.json  > nul

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
echo   CHECK THE FIRST LINES:
echo     1. "torque wrap fix N spots" must not be 0.
echo     2. deployed-stack penalty must be 0.000
echo.

%PY% -u _GHB_sweep.py %HOURS%
set RC=%ERRORLEVEL%

echo.
echo ==========================================================================
if not "%RC%"=="0" echo   [ERROR] python exited with code %RC%
echo   RUN 4 files:  _GHB_sweep4.json  _GHB_sweep4.log  _GHB_sweep4_trials.jsonl
echo   RUN 1 / 2 / 3 files are untouched.
echo   Rollback instructions:    _GHB_ROLLBACK.md
echo ==========================================================================
pause
