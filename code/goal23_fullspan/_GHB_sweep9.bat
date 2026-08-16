@echo off
chcp 65001 > nul
title Marathon-H joint refit sweep - RUN 9 (22 axes, CVT lock, s2s weight x2)
cd /d "%~dp0"

rem ===========================================================================
rem  ASCII ONLY.  cmd.exe parses .bat in the system codepage (cp949 here).
rem  All Korean explanation is printed by the Python script instead.
rem
rem  RUN 9 (2026-08-16) -- RUN 8 was NOT promoted.  Here is why, and what changed.
rem
rem  ---------------------------------------------------------------------
rem  WHY RUN 8 WAS HELD BACK
rem
rem  RUN 8 passed all four promotion gates and improved the final goal for the
rem  first time (hip -5.1%, knee -6.3%).  But two defects surfaced afterwards:
rem
rem   (a) THE ONLY CVT SESSION GOT MUCH WORSE.  26.04.29 is the single geared
rem       (link 25 mm) session among the nine fitted sessions.  It had been
rem       INVISIBLE -- the comparison plotter skipped CVT sessions entirely,
rem       so nobody could see it.  Fixed 2026-08-16 (commit 08230f5).  With the
rem       figures finally drawn, RUN 8 vs the deployed stack on that session:
rem           injection replay   knee speed  2.69 -> 4.11  (+53%)
rem           closed-loop        knee angle  3.48 -> 6.57  (+89%)
rem                              hip torque  3.98 -> 6.51  (+64%)
rem                              knee torque 4.88 -> 9.23  (+89%)
rem       Cause, verified by reverting only those two values: RUN 8 raised the
rem       LINK-JOINT VISCOUS DAMPING 13x (pin) and 4.4x (knee).  Viscous drag is
rem       amplified up to 80x by the geared four-bar geometry but exactly 1x by
rem       the parallelogram.  So the same number only explodes on the CVT side.
rem       Reverting just those two improved that session on all three channels
rem       (knee angle 4.60 -> 3.36, knee speed 4.94 -> 4.33).
rem
rem   (b) SIT-TO-STAND GOT WORSE, and the board let it.  Score +27.3%, hold
rem       time +11.2%.  Its combined weight was only 0.10, so the search sold
rem       sit-to-stand to buy jump.
rem
rem  ---------------------------------------------------------------------
rem  CHANGE 1 -- CVT SESSION LOCK (new).  User decision: "the CVT is the whole
rem  point of this research, it has to fit."
rem
rem  26.04.29 closed-loop TORQUE may not worsen by more than 0.5% (weight 30),
rem  and its closed-loop ANGLE+SPEED may not worsen by more than 2% (weight 20).
rem  Same mechanism as the deployment-session lock added in RUN 7.
rem  Rationale: only 1 of 9 fitted sessions is geared, so the average is pulled
rem  by the 8 ungeared ones -- yet the geared session is the ONLY one that can
rem  see the geometry-amplified axes at all.  FS_SWEEP_CVTLOCK=0 disables it.
rem
rem  ---------------------------------------------------------------------
rem  CHANGE 2 -- SIT-TO-STAND WEIGHT DOUBLED, 0.10 -> 0.19.
rem      score 0.05 -> 0.11   .   hold time 0.05 -> 0.08
rem  It is one of the three final tasks; 0.10 was too little to defend itself.
rem
rem  ---------------------------------------------------------------------
rem  CHANGE 3 -- NEW SCORE TERM: KNEE AT ITS FASTEST 10% ONLY (weight 0.09).
rem
rem  Measured 2026-08-16: the knee-speed error of a session correlates +0.840
rem  with that session's TOP knee speed, and RUN 8 made that correlation
rem  STRONGER (deployed stack was +0.415).  Median speed correlates +0.082 --
rem  essentially zero.  So the defect lives only in the fastest moments.
rem  Why the board could not see it: pooled over the whole window there are
rem  4,135 slow samples against 168 fast ones (25x).  The search fixed the slow
rem  ones with viscous drag and sold the fast ones cheaply -- which is exactly
rem  what broke the CVT session.  The new term scores ONLY each trial's own
rem  top-10% speed samples (per-trial threshold, never a fixed one).
rem
rem  ---------------------------------------------------------------------
rem  CHANGE 4 -- TWO AXES OPENED (21 -> 22).
rem
rem   (a) HIP SPRING DAMPING, 0 ~ 6, starting 1.5.  The knob (FS_BS) already
rem       existed; it was simply never in the sweep.  In the model the hip motor
rem       and the thigh are NOT rigidly joined -- a spring plus a damper sits
rem       between them.  The spring stiffness has been fitted every round; its
rem       partner, the damping, sat hard-coded at 1.5 in fs_model.py with no
rem       recorded origin.  Measured over 8 sessions of injection replay: the
rem       deflection rate is 0.588 rad/s median and 2.520 rad/s at the top 5%,
rem       so this term produces 0.88 N.m median and 3.78 N.m at the top 5%.
rem       Hip commands run 5-15 N.m, so that is not small.
rem       1.5 = bit-identical to today, so regression is impossible.
rem
rem   (b) THIGH CENTRE-OF-MASS upper bound 0.050 -> 0.100 m.  RUN 8 landed at
rem       0.0450 = 90% of the old bound, so the bound was deciding the value.
rem       This axis sets how the hip's gravity load changes with posture, and
rem       the closed-loop sit-to-stand figures show exactly that failure: the
rem       measured hip torque is flat while the simulated one drifts one way
rem       (-2.0 to +1.5 N.m) and is worst at the end of the motion.
rem       Note honestly: hip spring damping and thigh CoM are the TWO candidates
rem       for that drift and they have not been separated yet.  Both are open.
rem
rem  ---------------------------------------------------------------------
rem  UNCHANGED: transmission ratio still read live from the loop-closure
rem  constraint (NO lookup table -- user decision: keep the physics engine
rem  computing it naturally).  Link-joint friction stays exactly as RUN 8 left
rem  it as an open axis (user: no need to move where the loop is cut).
rem  Deployment-session lock, score normalization, whole-window sit-to-stand
rem  and hanging replay all unchanged.
rem
rem  ---------------------------------------------------------------------
rem  EXPECTED FIRST LINES:
rem    - data: "56 trial (cvt 10) . torque wrap fix 46 . hanging 15 records
rem      . sit-to-stand 4 cases".  If wrap fix is 0, close and report.
rem    - "normalization ON" with EIGHT reference values, the last being the new
rem      "fast knee" term.
rem    - "wiring check: normalized score of deployed stack = 1.000000  PASS"
rem    - deployed stack penalty 0.000, total 1.00000
rem    - "canon_mixv - 22 axes", the last one listed as
rem        hip spring damping   0 ~ 6   (now 1.5)
rem      and thigh centre-of-mass now reading  -0.01 ~ 0.10
rem    - "start values: all 22 axes match the starting point"
rem
rem  PRE-REGISTERED PREDICTIONS (written before the run):
rem    P15: the link-joint VISCOUS damping comes DOWN from RUN 8's values
rem         (pin 0.0052, knee 0.1014) by at least half, and the link-joint
rem         COULOMB friction goes UP.  Reason: measurement says the model is
rem         too slow at high speed and too fast at low speed, which is the
rem         signature of too much speed-proportional and too little constant
rem         friction.  If instead the viscous terms stay high, my diagnosis is
rem         wrong and the next place to look is INERTIA, not friction.
rem    P16: the CVT session's closed-loop torque ends at or below the deployed
rem         value (the lock forbids worse).  If the lock is hit constantly and
rem         the total score barely moves, the geared and ungeared sessions want
rem         genuinely different values -- which would mean a missing axis, not
rem         a bad search.
rem    P17: sit-to-stand improves this time (it got worse in RUN 8), because
rem         its weight nearly doubled.  If it STILL worsens at weight 0.19,
rem         no available axis can move it and a new mechanism is required.
rem    P18: hip spring damping does NOT land at 1.5.  It has never been fitted,
rem         so 1.5 sitting still would itself be surprising.
rem
rem  Outputs are tagged "9" so RUN-1..8 artifacts are NEVER touched.
rem ===========================================================================

set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

set FS_SWEEP_TAG=9
set FS_SWEEP_CVT=1
set FS_SWEEP_AIR=1
set FS_SWEEP_S2S=1
set FS_SWEEP_MODES=canon_mixv
set FS_SWEEP_NORM=1
set FS_S2S_NWIN=0
set FS_SWEEP_DEPLOCK=1
set FS_SWEEP_CVTLOCK=1

rem  Default 12 hours.  22 axes, one more than RUN 8.
rem  To change the duration, edit the number on the next line.
set HOURS=12

rem keep this run's own previous output (RUN-1..8 files are untouched)
if exist _GHB_sweep9.log          move /y _GHB_sweep9.log          _GHB_sweep9.prev.log   > nul
if exist _GHB_sweep9_trials.jsonl move /y _GHB_sweep9_trials.jsonl _GHB_sweep9.prev.jsonl > nul
if exist _GHB_sweep9.json         move /y _GHB_sweep9.json         _GHB_sweep9.prev.json  > nul

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
echo   MAKE SURE RUN 8 IS NOT STILL RUNNING.
echo.
echo   CHECK THE FIRST LINES:
echo     1. "torque wrap fix N spots" must not be 0 (expect 46).
echo     2. data line: "hanging 15 records" and "sit-to-stand 4 cases".
echo     3. "wiring check ... = 1.000000  PASS"  -- if this fails, close it.
echo     4. deployed stack penalty 0.000, total 1.00000
echo     5. 22 axes; the last one is hip spring damping starting at 1.5,
echo        and thigh centre-of-mass now reads -0.01 ~ 0.10
echo.

%PY% -u _GHB_sweep.py %HOURS%
set RC=%ERRORLEVEL%

echo.
echo ==========================================================================
if not "%RC%"=="0" echo   [ERROR] python exited with code %RC%
echo   RUN 9 files:  _GHB_sweep9.json  _GHB_sweep9.log  _GHB_sweep9_trials.jsonl
echo   RUN 1..8 files are untouched.
echo   Rollback instructions:    _GHB_ROLLBACK.md
echo ==========================================================================
pause
