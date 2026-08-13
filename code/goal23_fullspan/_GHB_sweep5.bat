@echo off
chcp 65001 > nul
title Marathon-H joint refit sweep - RUN 5 (hanging data + torque-conversion shape)
cd /d "%~dp0"

rem ===========================================================================
rem  ASCII ONLY.  cmd.exe parses .bat in the system codepage (cp949 here), so
rem  any Korean text in this file is read as garbage commands.  All Korean
rem  explanation is printed by the Python script instead.
rem
rem  RUN 5 (2026-08-13) -- what changed vs RUN 4.
rem
rem    1. NEW DATA: 16 hanging/ground sit-to-stand records join the score.
rem       Why: all 8 fitted sessions are jumps, so SLOW motion was never
rem       constrained by data (knee speed median 5.31 rad/s; only 18% of the
rem       time below 1 rad/s -- vs 41-63% for slow stand-ups).  Hanging records
rem       have the foot off the ground, so foot friction / slip / contact
rem       stiffness are absent; what remains is gravity, inertia, joint
rem       friction -- exactly what we are trying to fix.
rem       Scored by measured-torque injection replay only (no PD imitation):
rem       gains are unrecorded for 26.03.19 and gain recovery on the old
rem       sessions is off by 14-26%, so we do not lean on gains.
rem
rem    2. TWO NEW AXES: the SHAPE of the command-to-shaft torque ratio.
rem       The logged torque is the COMMAND, not a shaft measurement.  The real
rem       ratio varies with command size:
rem         weight-drop experiment 26.08.07 : 1.26x (small) -> 0.86x (large)
rem         hanging equation-of-motion fit  : 1.23x / 1.42x (small), 2 paths
rem       The model used a FLAT 0.65-0.68 everywhere.  That is 1.3x off in the
rem       jump band (10-15 N.m) and 1.9x off in the hanging band (0.2-1.2 N.m).
rem       Axis 12 scales the linear term, axis 13 the high-torque droop.
rem       1.0 / 1.0 reproduces the old model exactly; 1.85 / 13 reproduces the
rem       weight-drop curve (1.257 at 0.2 N.m, 0.882 at 15 N.m).
rem       NOTE: setting 1.85/13 BY HAND makes both boards worse (jump 0.1944 ->
rem       0.2505) because friction and inertia have already absorbed the error.
rem       That is precisely why it must be refitted jointly, not set by hand.
rem
rem    3. WEIGHTS rebalanced (sum 1.00):
rem         injection replay (jump, angle+speed)   0.30
rem         closed-loop angle+speed (jump)         0.17
rem         closed-loop TORQUE      (jump)         0.30
rem         jump height                            0.08
rem         hanging injection replay (16 records)  0.15
rem
rem    4. FIXED before this run (both were my own bugs, see git log):
rem       - hanging replay let the WHOLE robot free-fall during each step, so
rem         the leg never rotated (0.00 deg in 0.5 s under 1.262 N.m gravity).
rem         Now the body is truly pinned; the leg falls 75.21 deg as it should.
rem       - 8 call sites were switched to a helper that was never written,
rem         which silently killed ALL closed-loop scoring (score 900).
rem
rem  Expected first lines (verify before leaving it to run):
rem    - "torque wrap fix 46" spots.  If 0, close the window and report it.
rem    - starting point penalty must be 0.000 and total about 0.3656
rem      (injection 0.1747 / cl-angle 0.1233 / cl-torque 0.2984 /
rem       height 0.0416 / hanging 1.3291)
rem    - 16 axes listed, axis 12 and 13 starting at 1.0
rem
rem  Outputs are tagged "5" so RUN-1..4 artifacts are NEVER touched.
rem ===========================================================================

set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

set FS_SWEEP_TAG=5
set FS_SWEEP_CVT=1
set FS_SWEEP_AIR=1
set FS_SWEEP_MODES=canon_cap

rem  Default 8 hours.  RUN 4 used 4 h with 14 axes; RUN 5 has 16 axes and a
rem  heavier evaluation (16 extra replays per candidate), so allow more.
rem  Pass a number to override, e.g. _GHB_sweep5.bat 12
set HOURS=%1
if "%HOURS%"=="" set HOURS=8

rem keep this run's own previous output (RUN-1..4 files are untouched)
if exist _GHB_sweep5.log          move /y _GHB_sweep5.log          _GHB_sweep5.prev.log   > nul
if exist _GHB_sweep5_trials.jsonl move /y _GHB_sweep5_trials.jsonl _GHB_sweep5.prev.jsonl > nul
if exist _GHB_sweep5.json         move /y _GHB_sweep5.json         _GHB_sweep5.prev.json  > nul

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
echo     2. starting-point penalty must be 0.000, total about 0.3656
echo     3. 16 axes; axis 12 and 13 (torque ratio shape) start at 1.0
echo.

%PY% -u _GHB_sweep.py %HOURS%
set RC=%ERRORLEVEL%

echo.
echo ==========================================================================
if not "%RC%"=="0" echo   [ERROR] python exited with code %RC%
echo   RUN 5 files:  _GHB_sweep5.json  _GHB_sweep5.log  _GHB_sweep5_trials.jsonl
echo   RUN 1 / 2 / 3 / 4 files are untouched.
echo   Rollback instructions:    _GHB_ROLLBACK.md
echo ==========================================================================
pause
