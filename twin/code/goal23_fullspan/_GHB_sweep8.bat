@echo off
chcp 65001 > nul
title Marathon-H joint refit sweep - RUN 8 (link joints opened, 21 axes)
cd /d "%~dp0"

rem ===========================================================================
rem  ASCII ONLY.  cmd.exe parses .bat in the system codepage (cp949 here).
rem  All Korean explanation is printed by the Python script instead.
rem
rem  ***** DO NOT START THIS UNTIL RUN 7 HAS FINISHED. *****
rem  Running both at once halves the CPU for each.
rem
rem  RUN 8 (2026-08-16) -- what changed vs RUN 7.
rem
rem  ---------------------------------------------------------------------
rem  CHANGE 1 -- THE FOUR LINK-JOINT AXES ARE OPENED (17 -> 21 axes).
rem
rem  Until now the two motor-shaft joints (hip, crank) had their friction
rem  refitted every round, but the two joints of the linkage itself -- the
rem  coupler pin and the knee -- were never fitted at all:
rem     Coulomb friction : BOTH EXACTLY ZERO.  The place where the loss
rem                        physically happens was empty.
rem     Viscous damping  : pin 0.00040, knee 0.02309 N.m.s/rad, hard-coded in
rem                        the model file.  The knee value came from a
rem                        different campaign two years ago; the pin value has
rem                        NO TRACEABLE ORIGIN.  Their ratio is 58x and nobody
rem                        wrote down why.
rem
rem  Why this matters -- measured 2026-08-16 from the loop-closure constraint.
rem  "Amplification per unit knee motion" = (angle that joint rubs through)
rem  divided by (angle the knee moves).  1.0 means no amplification at all.
rem  At knee angle -176 deg:
rem       crank motor shaft  73.0x
rem       COUPLER PIN        80.2x     <-- the largest, and never fitted
rem       knee joint          1.0x     (it is the knee itself, so always 1)
rem  So the joint with the LARGEST amplification was exactly the one nobody
rem  was fitting.  Note also that at -177 deg the knee ratio goes NEGATIVE
rem  (-0.017): past the dead point the knee reverses while the crank keeps
rem  turning.  A hand-written loss formula using absolute values cannot
rem  express that; the engine handles it because it is what actually happens.
rem
rem  IMPORTANT -- these axes act on NO-CVT sessions too.  The linkage joints
rem  exist in the parallelogram (no-CVT) model as well, so the pins rub there
rem  too.  What differs is only the AMPLIFICATION: no-CVT has ratio exactly 1,
rem  so amplification is exactly 1.0 and the same friction has a much smaller
rem  effect.  This is NOT the structural isolation that the transmission-loss
rem  scale term has -- it is physical asymmetry.  Same physics everywhere,
rem  amplified only where the geometry amplifies it.
rem
rem  Pre-scan (one axis at a time, then combinations; 16 other axes held):
rem     setting                  cvt0   cvt2.5  cvt5   no-cvt  hold[s]  jump-inj
rem     current (all at today)   4.378  3.339   9.074  8.880   0.590    0.1934
rem     pin fric 0.15            3.893  0.638   8.993  8.360   0.666    0.2005
rem     knee damp 0.18           4.470  0.834   8.592  5.877   0.657    0.2204
rem     pin 0.08 + knee damp .10 3.622  0.697   8.951  7.230   0.663    0.2092
rem     pin 0.15 + knee damp .18 3.125  0.382   8.550  5.463   0.734    0.2287
rem  Read: PIN FRICTION fixes the CVT cases, KNEE DAMPING fixes no-CVT and the
rem  5 kg case, and together they beat either alone.  Sit-to-stand mean
rem  6.418 -> 4.380 (-32%), hold time 0.590 -> 0.734 s (+24%), and the jump
rem  closed-loop TORQUE does not get worse (0.3474 -> 0.3433..0.3478).
rem  Ranges were narrowed from that scan; starting values are today's values,
rem  so the starting point is bit-identical to the deployed stack (verified).
rem
rem  ---------------------------------------------------------------------
rem  CHANGE 2 -- SIT-TO-STAND NOW HAS A SECOND, SATURATION-FREE TERM.
rem
rem  Problem found 2026-08-16: with the 5 kg payload, three of the four
rem  channels sit exactly at the per-channel cap of 10, so that case CANNOT
rem  MOVE THE SCORE AT ALL.  Uncapped it reads knee-angle 20.68 with a peak
rem  error of 2452 deg -- that is 6.8 full turns, i.e. a completely different
rem  motion, not a slightly wrong one.  Raising the cap is the WRONG fix: it
rem  would make the board listen harder to post-divergence noise.
rem
rem  Values after divergence cannot be trusted, but WHEN divergence starts
rem  can.  So the sit-to-stand weight 0.10 is split into two halves:
rem     0.05  the existing accuracy score (capped at 10 per channel)
rem     0.05  "how long it kept up" = 1 - (time until the knee-angle error
rem           crosses a threshold) / (window length), averaged over four
rem           thresholds 5 / 10 / 30 / 90 deg.  0 = never diverged, 1 = it
rem           diverged instantly.  No cap is possible by construction.
rem  Sanity check on the sensitivity: adding link-joint friction moves the
rem  accuracy score by -9.6% but the hold time by +31% at the 10 deg
rem  threshold -- far sharper.
rem
rem  Honest note kept in the record: at 1.9 s of open-loop replay, EVERY case
rem  diverges within 0.12-0.51 s, so 74-94% of the window is post-divergence.
rem  A realistic near-term goal is to push "kept up" from 0.2-0.5 s past 1 s,
rem  not to match the whole trajectory.
rem
rem  ---------------------------------------------------------------------
rem  UNCHANGED FROM RUN 7: deployment-session lock (26.07.27 closed-loop
rem  torque may not worsen by more than 0.5%, weight 30), score normalization
rem  (each term divided by its deployed value so weight = share), whole-window
rem  sit-to-stand and hanging replay (no window splitting), transmission ratio
rem  read live from the loop-closure constraint (no lookup table).
rem
rem  ---------------------------------------------------------------------
rem  EXPECTED FIRST LINES:
rem    - data: "56 trial (cvt 10) . torque wrap fix 46 . hanging 15 records
rem      . sit-to-stand 4 cases".  If wrap fix is 0, close and report.
rem    - "normalization ON" with SEVEN reference values:
rem        injection 0.1934 / cl-angle 0.1250 / cl-torque 0.3474 /
rem        height 0.0582 / hanging 1.3553 / sit-to-stand 6.4177 /
rem        sit-to-stand hold 0.6813
rem      (These differ from RUN 7 because the transmission table was removed
rem       in between -- that changed the one CVT session.)
rem    - "wiring check: normalized score of deployed stack = 1.000000  PASS"
rem    - deployed stack penalty 0.000, total 1.00000
rem    - "canon_mixv - 21 axes", last four listed as
rem        pin Coulomb friction   0 ~ 0.25   (now 0)
rem        knee Coulomb friction  0 ~ 0.12   (now 0)
rem        pin viscous damping    0 ~ 0.04   (now 0.0004)
rem        knee viscous damping   0 ~ 0.25   (now 0.02309)
rem    - "start values: all 21 axes match the starting point"
rem
rem  PRE-REGISTERED PREDICTIONS:
rem    P12: the pin Coulomb friction lands above 0.05 (the pre-scan wanted
rem         0.08-0.15).  If it pins at 0, the pre-scan was reading something
rem         other axes can supply more cheaply, and I should find out what.
rem    P13: sit-to-stand hold improves by at least 15% (0.6813 -> below 0.579
rem         on the score scale, i.e. the robot keeps up longer).
rem    P14: jump closed-loop torque does NOT get worse than 0.3474, because
rem         the pre-scan showed these axes leave it flat or slightly better.
rem         If it worsens, the deployment lock should catch it -- watch the
rem         penalty line.
rem
rem  Outputs are tagged "8" so RUN-1..7 artifacts are NEVER touched.
rem ===========================================================================

set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

set FS_SWEEP_TAG=8
set FS_SWEEP_CVT=1
set FS_SWEEP_AIR=1
set FS_SWEEP_S2S=1
set FS_SWEEP_MODES=canon_mixv
set FS_SWEEP_NORM=1
set FS_S2S_NWIN=0
set FS_SWEEP_DEPLOCK=1

rem  Default 12 hours.  21 axes, four more than RUN 7.
rem  To change the duration, edit the number on the next line.
set HOURS=12

rem keep this run's own previous output (RUN-1..7 files are untouched)
if exist _GHB_sweep8.log          move /y _GHB_sweep8.log          _GHB_sweep8.prev.log   > nul
if exist _GHB_sweep8_trials.jsonl move /y _GHB_sweep8_trials.jsonl _GHB_sweep8.prev.jsonl > nul
if exist _GHB_sweep8.json         move /y _GHB_sweep8.json         _GHB_sweep8.prev.json  > nul

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
echo   MAKE SURE RUN 7 HAS FINISHED BEFORE STARTING THIS.
echo.
echo   CHECK THE FIRST LINES:
echo     1. "torque wrap fix N spots" must not be 0 (expect 46).
echo     2. data line: "hanging 15 records" and "sit-to-stand 4 cases".
echo     3. "wiring check ... = 1.000000  PASS"  -- if this fails, close it.
echo     4. deployed stack penalty 0.000, total 1.00000
echo     5. 21 axes; the last four are the link-joint friction and damping,
echo        starting at 0 / 0 / 0.0004 / 0.02309 (= today's values)
echo.

%PY% -u _GHB_sweep.py %HOURS%
set RC=%ERRORLEVEL%

echo.
echo ==========================================================================
if not "%RC%"=="0" echo   [ERROR] python exited with code %RC%
echo   RUN 8 files:  _GHB_sweep8.json  _GHB_sweep8.log  _GHB_sweep8_trials.jsonl
echo   RUN 1..7 files are untouched.
echo   Rollback instructions:    _GHB_ROLLBACK.md
echo ==========================================================================
pause
