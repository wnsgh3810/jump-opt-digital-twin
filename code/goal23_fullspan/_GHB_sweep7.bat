@echo off
chcp 65001 > nul
title Marathon-H joint refit sweep - RUN 7 (deployment-session lock, 17 axes)
cd /d "%~dp0"

rem ===========================================================================
rem  ASCII ONLY.  cmd.exe parses .bat in the system codepage (cp949 here), so
rem  any Korean text in this file is read as garbage commands.  All Korean
rem  explanation is printed by the Python script instead.
rem
rem  RUN 7 (2026-08-15) -- what changed vs RUN 6, and why.
rem
rem  BACKGROUND -- RUN 6 was NOT promoted, and the reason was not physics.
rem  RUN 6 (607 min, 37,888 evals) improved ALL SIX score components for the
rem  first time ever, total 1.0000 -> 0.8977 (-10.2%), penalty 0.000:
rem      jump injection   0.1747 -> 0.1680  (-3.8%)
rem      jump cl-angle    0.1233 -> 0.1199  (-2.8%)
rem      jump cl-torque   0.3403 -> 0.3356  (-1.4%)
rem      jump height      0.0416 -> 0.0358  (-14.0%)
rem      hanging          1.3553 -> 0.7008  (-48.3%)
rem      sit-to-stand     6.2813 -> 5.8625  (-6.7%)
rem  But the FINAL GOAL got WORSE.  Planned torque vs measured torque on
rem  26.07.27 (7 trials, 0 = perfect):
rem      hip   0.139 -> 0.151  (+8.5%)
rem      knee  0.199 -> 0.221  (+11.1%)
rem
rem  Splitting the cl-torque term per session showed exactly where it went:
rem      26.07.25  -14.1%   26.07.22  -12.5%   26.07.23  -6.0%   (better)
rem      26.07.24  +8.5%    26.04.29  +5.3%    26.07.27  +7.1%   (worse)
rem  The average is -1.4% and passes.  But 26.07.27 is the ONLY session where
rem  a plan was actually deployed to the robot -- it is where the final goal is
rem  measured.  **The average hid the one session that matters.**
rem
rem  ---------------------------------------------------------------------
rem  CHANGE 1 -- DEPLOYMENT-SESSION LOCK (the fix for the above).
rem
rem  26.07.27's closed-loop TORQUE channels (hip + knee) may not get worse than
rem  the deployed stack by more than 0.5%.  Weight 30 -- deliberately heavy.
rem  Sanity check on the number: RUN 6's winner was +7.1%, which under this lock
rem  earns 30 * 0.066 = 1.98 of penalty.  That completely swamps its 0.10 total
rem  gain, so the RUN-6 winner would have been rejected outright.  That is the
rem  intended behaviour and it is verified before this run (see expected lines).
rem
rem  Note the lock looks at TORQUE CHANNELS ONLY, not angle+speed.  If angles
rem  were included, a candidate could let torque rot while angles improve and
rem  slip through on the average -- the same failure mode one level down.
rem  FS_SWEEP_DEPLOCK=0 reproduces RUN 6 (no lock).
rem
rem  ---------------------------------------------------------------------
rem  CHANGE 2 -- TWO AXES CLOSED (19 -> 17).  The data answered them.
rem
rem   (a) KNEE TRANSMISSION LOSS: opened 0..0.60, landed at **0.0132** -- pinned
rem       at the bottom.  Why: fixing sit-to-stand through this axis costs the
rem       jump 3x.  Arithmetic on the normalized board: driving sit-to-stand
rem       6.28 -> 1.0 earns 0.10 * 0.84 = 0.084, while jump injection 0.17 ->
rem       0.52 loses 0.27 * 2.02 = 0.55.  The board correctly refused the trade.
rem       (My pre-registered prediction P6 said it would take it.  P6 was wrong;
rem        the board was right.)
rem
rem   (b) KNEE CEILING SPEED DEPENDENCE: opened -0.25..+0.05, landed at
rem       **+0.0117** -- effectively zero AND the sign is opposite to physics.
rem       This kills the back-EMF / supply-voltage-limit hypothesis on this
rem       board.  It is the 4th rejection of that idea and by far the strongest:
rem       this time it was opened as a SAFE SUPERSET (0 = bit-identical to the
rem       current model) and the data chose 0 by itself.  Pre-registered
rem       prediction P7 called this exactly.  Consistent with the 48 V recompute:
rem       at the knee speeds that actually occur, torque headroom is 62-76%,
rem       not the near-total starvation a 24 V assumption suggested.
rem
rem  With both closed the torque map is bit-identical to the deployed one again.
rem  Only the four-bar pose-dependent loss scale survives as a new axis (RUN 6
rem  put it at 0.758, comfortably away from either bound).
rem
rem  ---------------------------------------------------------------------
rem  CHANGE 3 -- THIGH CENTRE-OF-MASS UPPER BOUND WIDENED 0.025 -> 0.050 m.
rem  RUN 6 pinned it at 99.3% of the old bound, so the old bound, not the data,
rem  was deciding the value.
rem
rem  ---------------------------------------------------------------------
rem  UNCHANGED ON PURPOSE -- SIT-TO-STAND STAYS IN THE SCORE (user decision
rem  2026-08-15, overriding my proposal to demote it to monitoring).  It keeps
rem  weight 0.10 and whole-window scoring.  Note the honest expectation: with
rem  the transmission-loss axis closed there is no known axis that moves it far,
rem  so it will likely improve only a few percent again.  Fixing it properly
rem  needs a NEW physical mechanism, not a re-weighting.
rem
rem  Also unchanged: score normalization (each term divided by its value at the
rem  deployed stack, so every term starts at 1.0 and weight = share), and
rem  whole-window sit-to-stand / hanging replay (no window splitting).
rem
rem  ---------------------------------------------------------------------
rem  EXPECTED FIRST LINES:
rem    - data line: "56 trial (cvt 10) . torque wrap fix 46 . hanging 15
rem      records . sit-to-stand 4 cases".  If wrap fix is 0, close and report.
rem    - "normalization ON" with reference values
rem        injection 0.1747 / cl-angle 0.1233 / cl-torque 0.3403 /
rem        height 0.0416 / hanging 1.3553 / sit-to-stand 6.2813
rem    - "wiring check: normalized score of deployed stack = 1.000000  PASS"
rem    - deployed stack penalty 0.000, total 1.00000, and in its gate line
rem      "deployment-session cl-torque 1.0000"
rem    - "canon_mixv - 17 axes", last one listed as
rem        cvt loss scale   0 ~ 4   (now 1)
rem      and thigh centre-of-mass now reading  -0.01 ~ 0.05
rem    - "start values: all 17 axes match the starting point"
rem
rem  PRE-REGISTERED PREDICTIONS (written before the run):
rem    P8: with the deployment-session lock on, the winner's final-goal numbers
rem        (planned vs measured torque on 26.07.27) do NOT get worse than
rem        hip 0.139 / knee 0.199.  If they still worsen, the lock is aimed at
rem        the wrong quantity and the next step is to score the final goal
rem        directly instead of a proxy.
rem    P9: sit-to-stand improves by less than 15% (6.2813 -> above 5.34).
rem        If it beats that, some axis I have not identified is moving it and
rem        that axis is worth finding.
rem    P10: total score lands between 0.93 and 0.99 -- worse than RUN 6's 0.8977
rem        because the lock forbids the trade RUN 6 made.  A total BETTER than
rem        0.8977 while the lock holds would mean RUN 6 simply searched badly.
rem
rem  Outputs are tagged "7" so RUN-1..6 artifacts are NEVER touched.
rem ===========================================================================

set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

set FS_SWEEP_TAG=7
set FS_SWEEP_CVT=1
set FS_SWEEP_AIR=1
set FS_SWEEP_S2S=1
set FS_SWEEP_MODES=canon_mixv
set FS_SWEEP_NORM=1
set FS_S2S_NWIN=0
set FS_SWEEP_DEPLOCK=1

rem  Default 10 hours.  17 axes (two fewer than RUN 6) at the same evaluation
rem  cost, so the search density per axis is a little higher than RUN 6.
rem  To change the duration, edit the number on the next line.
set HOURS=10

rem keep this run's own previous output (RUN-1..6 files are untouched)
if exist _GHB_sweep7.log          move /y _GHB_sweep7.log          _GHB_sweep7.prev.log   > nul
if exist _GHB_sweep7_trials.jsonl move /y _GHB_sweep7_trials.jsonl _GHB_sweep7.prev.jsonl > nul
if exist _GHB_sweep7.json         move /y _GHB_sweep7.json         _GHB_sweep7.prev.json  > nul

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
echo     5. 17 axes; the last one is the cvt loss scale starting at 1
echo.

%PY% -u _GHB_sweep.py %HOURS%
set RC=%ERRORLEVEL%

echo.
echo ==========================================================================
if not "%RC%"=="0" echo   [ERROR] python exited with code %RC%
echo   RUN 7 files:  _GHB_sweep7.json  _GHB_sweep7.log  _GHB_sweep7_trials.jsonl
echo   RUN 1..6 files are untouched.
echo   Rollback instructions:    _GHB_ROLLBACK.md
echo ==========================================================================
pause
