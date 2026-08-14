@echo off
chcp 65001 > nul
title Marathon-H joint refit sweep - RUN 6 (three loss axes + normalized score)
cd /d "%~dp0"

rem ===========================================================================
rem  ASCII ONLY.  cmd.exe parses .bat in the system codepage (cp949 here), so
rem  any Korean text in this file is read as garbage commands.  All Korean
rem  explanation is printed by the Python script instead.
rem
rem  RUN 6 (2026-08-14) -- what changed vs RUN 5, and why.
rem
rem  BACKGROUND: RUN 5 spent 488 min / 30,720 evaluations and contributed
rem  EXACTLY ZERO to jump prediction.  Component split (same board, both points):
rem      jump injection  0.17466 -> 0.17479   (+0.1%  worse)
rem      jump cl-angle   0.12332 -> 0.12723   (+3.2%  worse)
rem      jump cl-torque  0.34032 -> 0.34463   (+1.3%  worse)
rem      jump height     0.04163 -> 0.04481   (+7.6%  worse)
rem      hanging  (new)  1.35527 -> 0.76762   (-43.4% better)
rem      sit2stand(new)  3.16279 -> 2.29503   (-27.4% better)
rem  All of the -25% headline came from the two NEWLY ADDED data sets.
rem  Cause: parameters moved hugely (knee dry friction x3.7, hip viscous x38)
rem  while jump predictions moved <3% -- friction and the command-to-shaft
rem  torque map CANCEL each other inside a jump push.  Jump data alone cannot
rem  separate them.  Scanning jump axes harder is proven waste.
rem
rem  ---------------------------------------------------------------------
rem  CHANGE 1 -- THREE NEW AXES, opened TOGETHER (19 axes total).
rem
rem  They substitute for one another, so opening them one at a time gives
rem  different answers.  Measured 08-14 (sit-to-stand, whole-window replay,
rem  0 = perfect, 0.43 = pass line; 16 other axes held at deployed values):
rem
rem     knee transmission loss   sit2stand   no-cvt case   jump injection
rem       (old structure)
rem       0.00 (= deployed)        6.281        8.880          0.1747
rem       0.30                     3.440        3.819          0.2203
rem       0.45 + cvt loss x1       0.670        0.367          0.4830
rem
rem  0.367 on the no-cvt case is BELOW the 0.43 pass line -- the first time
rem  sit-to-stand has ever passed in this project.  What remains is the
rem  cvt cases (0.58-0.88).
rem
rem   (a) KNEE TRANSMISSION LOSS  (0 .. 0.60, starts at 0)
rem       loss = fc1 * |command torque| * tanh(speed/0.3)
rem       Physics: contact force in the four-bar pins and gear teeth is
rem       proportional to transmitted torque, so Coulomb friction is too.
rem       That IS transmission efficiency.  Weight-drop measurement 26.08.07:
rem         knee 0.135 + 0.1197*|cmd|  (efficiency 88%)
rem         hip  0.278 + 0.0029*|cmd|  (efficiency ~100%)  <- hip untouched
rem       The quasi-static measurement is a LOWER bound (high-speed losses are
rem       invisible in a command channel), so the range opens well above it.
rem
rem   (b) TRANSMISSION POSE-DEPENDENT LOSS SCALE  (0 .. 4.0, starts at 1)
rem       loss = C * |cmd| * (1/|ratio| - 1) * tanh(knee speed)
rem       Already implemented in both replay paths; only the scale is new.
rem       The no-cvt case has ratio exactly 1, so this term is ZERO there by
rem       construction -- verified in the 08-14 scan (the no-cvt column did
rem       not move by a single digit across the whole scale sweep).
rem
rem   (c) KNEE CEILING SPEED DEPENDENCE  (-0.25 .. +0.05, starts at 0)
rem       ceiling(v) = cap + c1*|joint speed| .  Negative = closes with speed.
rem       Physics: finite supply voltage.  User confirmed 48 V.  With gear
rem       ratio 9 and back-EMF constant 0.091 V/(rad/s) the no-load joint
rem       speed is 58.6 rad/s.  Measured knee speeds in the push:
rem         at peak torque command   14.15 rad/s -> 11.59 V (24% of 48 V)
rem                                  -> only 76% of stall torque available
rem         top 5% of speed          22.17 rad/s -> 18.16 V (38%) -> 62%
rem       Hip is far milder (10-17%).  Expected physical value c1 ~ -0.07.
rem       Positive side is left slightly open: a positive answer would itself
rem       be a verdict (back-EMF killed on this board).
rem       Standalone scan gave sit2stand -29% and cl-torque -2% but jump
rem       height error x3.8 -- so it only makes sense jointly refitted.
rem
rem   REGRESSION IMPOSSIBLE: with (a)=0, (b)=1, (c)=0 the new torque structure
rem   is BIT-IDENTICAL to the deployed one (checked over command -40..+40 N.m
rem   and speed -20..+20 rad/s: max difference 0.000e+00 N.m).  The starting
rem   point is exactly the deployed stack, so the score starts at exactly
rem   1.000000.  If the new axes are useless the search can return to zero.
rem
rem  ---------------------------------------------------------------------
rem  CHANGE 2 -- SCORE NORMALIZATION (the weights were lying).
rem
rem  RUN 5 weights were 0.27/0.15/0.27/0.07/0.14/0.10 but because the boards
rem  have different value SIZES the actual share was sit-to-stand 47%,
rem  hanging 28%, all jump boards 24% combined.  Each term is now divided by
rem  its value at the deployed stack, so every term starts at 1.0 and the
rem  weight IS the share.  "0 = perfect" is preserved.
rem  ==> THE SCORE IS NOT COMPARABLE TO RUN 5.  New baseline is 1.000000.
rem  FS_SWEEP_NORM=0 reproduces the RUN-5 scoring exactly.
rem
rem  ---------------------------------------------------------------------
rem  CHANGE 3 -- SIT-TO-STAND IS SCORED WHOLE, NOT IN PIECES.
rem
rem  The user's standing rule is "no window splitting" and RUN 5 broke it.
rem  Re-measured 08-14 across a properly wide range of models:
rem      deployed -> best      whole 6.281 -> 0.783  = 8.0x separation
rem                            split 3.163 -> 1.401  = 2.3x separation
rem  The split board has a FLOOR near 1.40 and cannot see below it (short
rem  windows -> small denominator -> start transient and noise dominate).
rem  So splitting literally fails to recognise a good model.  The rule was
rem  right on measurement grounds too.  FS_S2S_NWIN=4 restores the RUN-5 form.
rem
rem  ---------------------------------------------------------------------
rem  EXPECTED FIRST LINES (verified 08-14 by a short dry run):
rem    - data line: "56 trial (cvt 10) . torque wrap fix 46 . hanging 15
rem      records . sit-to-stand 4 cases".  If wrap fix is 0, close and report.
rem    - "normalization ON" with reference values
rem        injection 0.1747 / cl-angle 0.1233 / cl-torque 0.3403 /
rem        height 0.0416 / hanging 1.3553 / sit-to-stand 6.2813
rem      (sit-to-stand 6.2813 is the WHOLE-window number; RUN 5 showed 3.1628
rem       because it was split into pieces.)
rem    - "wiring check: normalized score of deployed stack = 1.000000  PASS"
rem    - deployed stack penalty 0.000, total 1.00000
rem    - "canon_mixv - 19 axes", last three listed as
rem        knee transmission loss   0 ~ 0.6    (now 0)
rem        cvt loss scale           0 ~ 4      (now 1)
rem        knee ceiling speed dep  -0.25~0.05  (now 0)
rem    - "start values: all 19 axes match the starting point"
rem
rem  PRE-REGISTERED PREDICTIONS (written before the run, see
rem  NEXT_ROUND6_DESIGN.md section 10):
rem    P6: opening all three together drives sit-to-stand (whole) below 0.7
rem        WHILE jump injection recovers to 0.22 or better.  Standalone best
rem        was 0.4830, so under half recovery means one axis is still missing.
rem    P7: if the ceiling speed dependence pins at 0, the back-EMF hypothesis
rem        dies on this board.
rem
rem  Outputs are tagged "6" so RUN-1..5 artifacts are NEVER touched.
rem ===========================================================================

set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

set FS_SWEEP_TAG=6
set FS_SWEEP_CVT=1
set FS_SWEEP_AIR=1
set FS_SWEEP_S2S=1
set FS_SWEEP_MODES=canon_mixv
set FS_SWEEP_NORM=1
set FS_S2S_NWIN=0

rem  Default 10 hours.  RUN 5 used 8 h with 16 axes; RUN 6 has 19 axes and the
rem  whole-window sit-to-stand replay is longer per candidate.
rem  Pass a number to override, e.g. _GHB_sweep6.bat 14
set HOURS=%1
if "%HOURS%"=="" set HOURS=10

rem keep this run's own previous output (RUN-1..5 files are untouched)
if exist _GHB_sweep6.log          move /y _GHB_sweep6.log          _GHB_sweep6.prev.log   > nul
if exist _GHB_sweep6_trials.jsonl move /y _GHB_sweep6_trials.jsonl _GHB_sweep6.prev.jsonl > nul
if exist _GHB_sweep6.json         move /y _GHB_sweep6.json         _GHB_sweep6.prev.json  > nul

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
echo     1. "torque wrap fix N spots" must not be 0 (expect 46).
echo     2. data line: "hanging 15 records" and "sit-to-stand 4 cases".
echo     3. "wiring check ... = 1.000000  PASS"  -- if this fails, close it.
echo     4. deployed stack penalty 0.000, total 1.00000
echo     5. 19 axes; last three start at 0 / 1 / 0 (= identical to today's model)
echo.

%PY% -u _GHB_sweep.py %HOURS%
set RC=%ERRORLEVEL%

echo.
echo ==========================================================================
if not "%RC%"=="0" echo   [ERROR] python exited with code %RC%
echo   RUN 6 files:  _GHB_sweep6.json  _GHB_sweep6.log  _GHB_sweep6_trials.jsonl
echo   RUN 1 / 2 / 3 / 4 / 5 files are untouched.
echo   Rollback instructions:    _GHB_ROLLBACK.md
echo ==========================================================================
pause
