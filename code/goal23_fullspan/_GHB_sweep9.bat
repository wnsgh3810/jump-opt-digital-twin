@echo off
chcp 65001 > nul
title Marathon-H joint refit sweep - RUN 9 (32 axes, CVT lock, s2s weight x2)
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
rem  CHANGE 4 -- TWELVE AXES OPENED (21 -> 32).
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
rem
rem   (c) MASS DISTRIBUTION AND INERTIA -- three axes, user question "shouldn't we
rem       add M, C, G too?".  Until now the only mass-side axes were TOTAL mass,
rem       THIGH centre-of-mass, and the two motor-shaft inertias.  The BODY
rem       inertias and everything about the CALF have never been fitted at all --
rem       they sit at their CAD values.
rem       Why now: today's diagnosis points here.  The error grows as a constant
rem       ABSOLUTE amount per unit time, independent of how fast the joint turns.
rem       That is the signature of a wrong ACCELERATION, i.e. torque divided by
rem       inertia.  It can be confused with friction, but the two do separate:
rem       inertia only acts while the speed CHANGES, friction acts even at
rem       constant speed -- and this board already looks at fast jumps, slow
rem       sit-to-stand and hanging swings together.
rem         calf centre-of-mass z   -0.05 ~ 0.05 m  (added to the current value,
rem                                 0 = unchanged).  The calf runs all the way to
rem                                 the foot and its centre of mass sets the
rem                                 gravity load on BOTH joints -- a third
rem                                 candidate for the hip-torque drift.
rem         thigh inertia scale      0.6 ~ 1.8  (multiplies today's value, 1 = same)
rem         calf inertia scale       0.6 ~ 1.8  (same)
rem       Regression check run 2026-08-16: with all three at their neutral start
rem       the body mass / inertia / CoM arrays differ from RUN 8 by exactly
rem       0.000e+00.  The starting point is bit-identical.
rem       Note honestly: hip spring damping, thigh CoM and calf CoM are now THREE
rem       candidates for the hip-torque drift and they are not separated yet.
rem
rem   (d) MASS DISTRIBUTION AND THE REMAINING LINKS -- seven more axes, user
rem       follow-up "what about crank, coupler, l_o -- and mass too?".
rem       Measured today, current values and share of the whole robot:
rem         base 1.388 (43.4%) . thigh 0.986 (30.8%) . CRANK 0.437 (13.7%) .
rem         calf 0.239 (7.5%) . coupler 0.150 (4.7%)      total 3.201 kg
rem       The crank is 13.7% of the robot and its mass has NEVER been fitted.
rem       IMPORTANT -- total mass stays pinned at 3.26~3.30 kg (a measurement)
rem       and the leftover goes to the base.  So these axes do not ADD weight;
rem       they MOVE it.  Same total, but weight further from the joint is far
rem       harder to swing -- that is what inertia means.
rem       New: thigh / crank / coupler / calf mass, crank and coupler CoM z,
rem            coupler inertia scale.
rem       l_o (the output link) is NOT a separate body -- it lives inside the
rem       calf, so the calf mass / CoM / inertia axes already cover it.
rem       CRANK INERTIA IS DELIBERATELY NOT OPENED.  The crank body and the knee
rem       motor rotor sit on the SAME joint, so their inertias simply add on that
rem       degree of freedom; opening both would split one physical quantity
rem       across two axes.  The motor-shaft term (0.00795) is already 12.7x the
rem       crank body's own (0.000628), so the crank is buried in it anyway.
rem       env_of therefore pins crank inertia scale at exactly 1.0.
rem       Regression check 2026-08-16: with all twelve new axes at their neutral
rem       start, body mass / inertia / CoM differ from RUN 8 by 0.000e+00.
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
rem  CHANGE 5 -- AUDIT FINDINGS, FIXED BEFORE THE RUN (2026-08-16).
rem  User asked: "check properly whether any task is under-weighted, and review
rem  the code -- this run is long, I want it done right."  Two real holes found.
rem
rem   (A) A QUARTER OF THE SIT-TO-STAND SCORE WAS DEAD.  The per-channel cap was
rem       a hard min(x, 10).  Measured at the deployed stack, 4 of 16 channels
rem       sit AT the cap:
rem         payload 5 kg (CVT)  knee angle 20.68 . hip speed 10.31 . knee speed 23.56
rem         no-CVT 0 kg         knee speed 13.53
rem       A capped channel cannot move the score AT ALL, however much it
rem       improves.  So doubling the sit-to-stand weight (0.10 -> 0.19) would
rem       have delivered only three quarters of that.  Raising the cap is wrong
rem       (post-divergence values are noise, not information).
rem       FIX: keep 0..10 EXACTLY as before, and above 10 grow logarithmically:
rem         20.68 -> 12.46 . 23.56 -> 12.68 . 100 -> 14.5
rem       The 0..10 gradient is bit-identical, and above 10 the gradient is no
rem       longer zero, so improvement is rewarded while noise stays compressed.
rem
rem   (B) SILENT DROP -- DIVERGING TRIALS VANISHED FROM THE AVERAGE.
rem       Four places did "if max(v) < 1e3: append(v)".  A trial that blew past
rem       that was not scored badly -- it was DISCARDED.  Discarding removes it
rem       from the session mean, so a candidate that makes one trial diverge
rem       gets a BETTER score.  Divergence was profitable.
rem       FIX: the same soft cap replaces the drop, in the injection-replay
rem       board, the new fast-knee term, the closed-loop board and the hanging
rem       board (all four feed the score).  The two remaining 1e4 filters are on
rem       the LEGACY metric that is displayed only, and are marked as such.
rem
rem  Effect on the reference values: sit-to-stand score 6.4177 -> 6.8498 (the
rem  previously-capped channels now report their real, compressed size).
rem  Wiring re-verified after all edits: normalized deployed stack = 1.000000.
rem
rem  ---------------------------------------------------------------------
rem  CHANGE 6 -- SIT-TO-STAND IS NOW SCORED ON TWO BOARDS (user's design).
rem
rem  User's proposal, adopted: "score it two ways -- one whole window, and one
rem  chopped into 0.2 s pieces that keep resetting."
rem      whole window 1.9 s        -> does it KEEP UP over time
rem      0.2 s pieces, each restarted from the measured pose -> is the PHYSICS
rem                                   right moment to moment, with no build-up
rem  Each board plugs the other's hole.  Whole-window alone carries no
rem  information after the first blow-up (74-94% of the window is post-
rem  divergence noise).  Pieces alone cannot see whether it keeps up at all,
rem  since every piece resets the error to zero -- which is exactly why window
rem  splitting is normally FORBIDDEN here.  Keeping the whole-window board
rem  closes that hole, so the two together do not violate the rule.
rem
rem  MY EARLIER PROPOSAL WAS REJECTED BY THE USER, CORRECTLY.  I had suggested
rem  "score only up to the moment the foot leaves the ground".  That makes
rem  taking off PROFITABLE: an early take-off shortens the scored window, so the
rem  error shrinks.  It is the same shape of hole as the silent drop fixed in
rem  CHANGE 5.  Not doing it.
rem
rem  Sit-to-stand keeps its total share of 0.19, now split three ways:
rem      whole-window score  0.07 . keep-up time 0.06 . 0.2 s pieces 0.06
rem  Reference values at the deployed stack: 6.8498 / 0.6813 / 1.7425.
rem  The pieces board reads much lower (1.74 vs 6.85) precisely because nothing
rem  accumulates -- that is the point, not a bug.
rem
rem  ALSO WITHDRAWN: "divide the error by how far the joint moved".  The scorer
rem  ALREADY divides by the standard deviation of the measured signal over the
rem  window, which is the same normalization.  My proposal was a duplicate.
rem
rem  COST NOTE: the pieces board runs many short replays per case, so each
rem  evaluation is slower.  20 hours will therefore cover fewer candidates than
rem  a run without it.  That is the trade accepted for seeing sit-to-stand
rem  properly.
rem
rem  ---------------------------------------------------------------------
rem  EXPECTED FIRST LINES:
rem    - data: "56 trial (cvt 10) . torque wrap fix 46 . hanging 15 records
rem      . sit-to-stand 4 cases".  If wrap fix is 0, close and report.
rem    - "normalization ON" with NINE reference values, including the new
rem      "fast knee" term (0.5023) -- NINE reference values in total, the last
rem      being the sit-to-stand 0.2 s pieces board (1.7425).
rem    - "wiring check: normalized score of deployed stack = 1.000000  PASS"
rem    - deployed stack penalty 0.000, total 1.00000
rem    - "canon_mixv - 32 axes", among the last ones
rem        hip spring damping    0 ~ 6      (now 1.5)
rem        calf centre-of-mass  -0.05 ~ 0.05 (now 0)
rem        thigh inertia scale   0.6 ~ 1.8   (now 1)
rem        calf inertia scale    0.6 ~ 1.8   (now 1)
rem      and thigh centre-of-mass now reading  -0.01 ~ 0.10
rem        thigh/crank/coupler/calf mass  (now 0.98583 / 0.437 / 0.15002 / 0.23934)
rem    - "start values: all 32 axes match the starting point"
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
rem    P19: at least one of the mass/inertia axes moves more than 10% from
rem         its neutral start.  They have never been fitted, so sitting still
rem         would mean the CAD values are already right -- possible, but it
rem         would be the first time any never-fitted axis did that.
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

rem  Default 20 hours.  32 axes, eleven more than RUN 8.
rem  HONEST NOTE ON COST: search density per axis drops as axes are added.  32 is
rem  a lot.  The saving grace is that EVERY new axis starts bit-identical to the
rem  deployed stack, so the run cannot end up worse than where it began -- the
rem  worst case is that some axes simply do not move.  Watch for axes that pin at
rem  a bound: that means the bound decided the value, not the data.
rem  To change the duration, edit the number on the next line.
set HOURS=20

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
echo     5. 32 axes; among them hip spring damping (1.5), calf
echo        centre-of-mass (0), thigh inertia scale (1), calf inertia scale (1),
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
