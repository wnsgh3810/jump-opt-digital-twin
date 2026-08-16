@echo off
REM ==========================================================================
REM  G62 : canon_capS sweep  (S x cap_knee x cap_hip)
REM    tau = a_hat + clip( S * canon(raw) - a_hat , +-cap )
REM    S = 1.00 reproduces the current best (J_G 0.7387) EXACTLY.
REM  NOTE: this file MUST be CRLF. LF-only breaks cmd.exe label jumps
REM        (first version ran only 2 of 26 lines, out of order).
REM  Flat structure - no 'call :LABEL', no nested for. ASCII only.
REM  Run: double-click.  Output -> _G62_capS_sweep.log
REM ==========================================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set P25_CLIP_RAW=35.5
set FS_TMAP=canon_capS
set FS_MASS=3.28
set FS_NOSUPP=1
set FS_NOSPR=1
set FS_NOBIAS=1
set FS_NODEEP=1
set FS_PRESLIDE=0.86,0.85,0.02,1.0
echo === G62 canon_capS sweep === > _G62_capS_sweep.log

echo [1/28] S=1.00 capK=3.8 capH=2.6
set FS_TCAPS=1.00,3.8,2.6
echo. >> _G62_capS_sweep.log
echo ### S=1.00 capK=3.8 capH=2.6 >> _G62_capS_sweep.log
python _G13_board.py G62_1.00_3.8_2.6 >> _G62_capS_sweep.log 2>&1

echo [2/28] S=0.94 capK=3.8 capH=2.6
set FS_TCAPS=0.94,3.8,2.6
echo. >> _G62_capS_sweep.log
echo ### S=0.94 capK=3.8 capH=2.6 >> _G62_capS_sweep.log
python _G13_board.py G62_0.94_3.8_2.6 >> _G62_capS_sweep.log 2>&1

echo [3/28] S=0.97 capK=3.8 capH=2.6
set FS_TCAPS=0.97,3.8,2.6
echo. >> _G62_capS_sweep.log
echo ### S=0.97 capK=3.8 capH=2.6 >> _G62_capS_sweep.log
python _G13_board.py G62_0.97_3.8_2.6 >> _G62_capS_sweep.log 2>&1

echo [4/28] S=1.03 capK=3.8 capH=2.6
set FS_TCAPS=1.03,3.8,2.6
echo. >> _G62_capS_sweep.log
echo ### S=1.03 capK=3.8 capH=2.6 >> _G62_capS_sweep.log
python _G13_board.py G62_1.03_3.8_2.6 >> _G62_capS_sweep.log 2>&1

echo [5/28] S=1.06 capK=3.8 capH=2.6
set FS_TCAPS=1.06,3.8,2.6
echo. >> _G62_capS_sweep.log
echo ### S=1.06 capK=3.8 capH=2.6 >> _G62_capS_sweep.log
python _G13_board.py G62_1.06_3.8_2.6 >> _G62_capS_sweep.log 2>&1

echo [6/28] S=1.10 capK=3.8 capH=2.6
set FS_TCAPS=1.10,3.8,2.6
echo. >> _G62_capS_sweep.log
echo ### S=1.10 capK=3.8 capH=2.6 >> _G62_capS_sweep.log
python _G13_board.py G62_1.10_3.8_2.6 >> _G62_capS_sweep.log 2>&1

echo [7/28] S=0.90 capK=3.8 capH=2.6
set FS_TCAPS=0.90,3.8,2.6
echo. >> _G62_capS_sweep.log
echo ### S=0.90 capK=3.8 capH=2.6 >> _G62_capS_sweep.log
python _G13_board.py G62_0.90_3.8_2.6 >> _G62_capS_sweep.log 2>&1

echo [8/28] S=0.94 capK=3.4 capH=2.4
set FS_TCAPS=0.94,3.4,2.4
echo. >> _G62_capS_sweep.log
echo ### S=0.94 capK=3.4 capH=2.4 >> _G62_capS_sweep.log
python _G13_board.py G62_0.94_3.4_2.4 >> _G62_capS_sweep.log 2>&1

echo [9/28] S=0.94 capK=3.6 capH=2.6
set FS_TCAPS=0.94,3.6,2.6
echo. >> _G62_capS_sweep.log
echo ### S=0.94 capK=3.6 capH=2.6 >> _G62_capS_sweep.log
python _G13_board.py G62_0.94_3.6_2.6 >> _G62_capS_sweep.log 2>&1

echo [10/28] S=0.94 capK=4.0 capH=2.8
set FS_TCAPS=0.94,4.0,2.8
echo. >> _G62_capS_sweep.log
echo ### S=0.94 capK=4.0 capH=2.8 >> _G62_capS_sweep.log
python _G13_board.py G62_0.94_4.0_2.8 >> _G62_capS_sweep.log 2>&1

echo [11/28] S=0.97 capK=3.4 capH=2.4
set FS_TCAPS=0.97,3.4,2.4
echo. >> _G62_capS_sweep.log
echo ### S=0.97 capK=3.4 capH=2.4 >> _G62_capS_sweep.log
python _G13_board.py G62_0.97_3.4_2.4 >> _G62_capS_sweep.log 2>&1

echo [12/28] S=0.97 capK=3.6 capH=2.4
set FS_TCAPS=0.97,3.6,2.4
echo. >> _G62_capS_sweep.log
echo ### S=0.97 capK=3.6 capH=2.4 >> _G62_capS_sweep.log
python _G13_board.py G62_0.97_3.6_2.4 >> _G62_capS_sweep.log 2>&1

echo [13/28] S=0.97 capK=3.6 capH=2.6
set FS_TCAPS=0.97,3.6,2.6
echo. >> _G62_capS_sweep.log
echo ### S=0.97 capK=3.6 capH=2.6 >> _G62_capS_sweep.log
python _G13_board.py G62_0.97_3.6_2.6 >> _G62_capS_sweep.log 2>&1

echo [14/28] S=0.97 capK=4.0 capH=2.6
set FS_TCAPS=0.97,4.0,2.6
echo. >> _G62_capS_sweep.log
echo ### S=0.97 capK=4.0 capH=2.6 >> _G62_capS_sweep.log
python _G13_board.py G62_0.97_4.0_2.6 >> _G62_capS_sweep.log 2>&1

echo [15/28] S=0.90 capK=3.4 capH=2.4
set FS_TCAPS=0.90,3.4,2.4
echo. >> _G62_capS_sweep.log
echo ### S=0.90 capK=3.4 capH=2.4 >> _G62_capS_sweep.log
python _G13_board.py G62_0.90_3.4_2.4 >> _G62_capS_sweep.log 2>&1

echo [16/28] S=0.90 capK=3.6 capH=2.4
set FS_TCAPS=0.90,3.6,2.4
echo. >> _G62_capS_sweep.log
echo ### S=0.90 capK=3.6 capH=2.4 >> _G62_capS_sweep.log
python _G13_board.py G62_0.90_3.6_2.4 >> _G62_capS_sweep.log 2>&1

echo [17/28] S=1.03 capK=3.6 capH=2.6
set FS_TCAPS=1.03,3.6,2.6
echo. >> _G62_capS_sweep.log
echo ### S=1.03 capK=3.6 capH=2.6 >> _G62_capS_sweep.log
python _G13_board.py G62_1.03_3.6_2.6 >> _G62_capS_sweep.log 2>&1

echo [18/28] S=1.03 capK=4.0 capH=2.6
set FS_TCAPS=1.03,4.0,2.6
echo. >> _G62_capS_sweep.log
echo ### S=1.03 capK=4.0 capH=2.6 >> _G62_capS_sweep.log
python _G13_board.py G62_1.03_4.0_2.6 >> _G62_capS_sweep.log 2>&1

echo [19/28] S=1.03 capK=4.0 capH=2.8
set FS_TCAPS=1.03,4.0,2.8
echo. >> _G62_capS_sweep.log
echo ### S=1.03 capK=4.0 capH=2.8 >> _G62_capS_sweep.log
python _G13_board.py G62_1.03_4.0_2.8 >> _G62_capS_sweep.log 2>&1

echo [20/28] S=1.06 capK=4.0 capH=2.8
set FS_TCAPS=1.06,4.0,2.8
echo. >> _G62_capS_sweep.log
echo ### S=1.06 capK=4.0 capH=2.8 >> _G62_capS_sweep.log
python _G13_board.py G62_1.06_4.0_2.8 >> _G62_capS_sweep.log 2>&1

echo [21/28] S=1.06 capK=4.2 capH=2.8
set FS_TCAPS=1.06,4.2,2.8
echo. >> _G62_capS_sweep.log
echo ### S=1.06 capK=4.2 capH=2.8 >> _G62_capS_sweep.log
python _G13_board.py G62_1.06_4.2_2.8 >> _G62_capS_sweep.log 2>&1

echo [22/28] S=1.10 capK=4.2 capH=3.0
set FS_TCAPS=1.10,4.2,3.0
echo. >> _G62_capS_sweep.log
echo ### S=1.10 capK=4.2 capH=3.0 >> _G62_capS_sweep.log
python _G13_board.py G62_1.10_4.2_3.0 >> _G62_capS_sweep.log 2>&1

echo [23/28] S=1.00 capK=3.6 capH=2.4
set FS_TCAPS=1.00,3.6,2.4
echo. >> _G62_capS_sweep.log
echo ### S=1.00 capK=3.6 capH=2.4 >> _G62_capS_sweep.log
python _G13_board.py G62_1.00_3.6_2.4 >> _G62_capS_sweep.log 2>&1

echo [24/28] S=1.00 capK=3.6 capH=2.8
set FS_TCAPS=1.00,3.6,2.8
echo. >> _G62_capS_sweep.log
echo ### S=1.00 capK=3.6 capH=2.8 >> _G62_capS_sweep.log
python _G13_board.py G62_1.00_3.6_2.8 >> _G62_capS_sweep.log 2>&1

echo [25/28] S=1.00 capK=4.0 capH=2.4
set FS_TCAPS=1.00,4.0,2.4
echo. >> _G62_capS_sweep.log
echo ### S=1.00 capK=4.0 capH=2.4 >> _G62_capS_sweep.log
python _G13_board.py G62_1.00_4.0_2.4 >> _G62_capS_sweep.log 2>&1

echo [26/28] S=1.00 capK=4.0 capH=2.8
set FS_TCAPS=1.00,4.0,2.8
echo. >> _G62_capS_sweep.log
echo ### S=1.00 capK=4.0 capH=2.8 >> _G62_capS_sweep.log
python _G13_board.py G62_1.00_4.0_2.8 >> _G62_capS_sweep.log 2>&1

echo [27/28] S=1.00 capK=3.8 capH=2.4
set FS_TCAPS=1.00,3.8,2.4
echo. >> _G62_capS_sweep.log
echo ### S=1.00 capK=3.8 capH=2.4 >> _G62_capS_sweep.log
python _G13_board.py G62_1.00_3.8_2.4 >> _G62_capS_sweep.log 2>&1

echo [28/28] S=1.00 capK=3.8 capH=2.8
set FS_TCAPS=1.00,3.8,2.8
echo. >> _G62_capS_sweep.log
echo ### S=1.00 capK=3.8 capH=2.8 >> _G62_capS_sweep.log
python _G13_board.py G62_1.00_3.8_2.8 >> _G62_capS_sweep.log 2>&1

echo === done === >> _G62_capS_sweep.log
echo.
echo FINISHED. See _G62_capS_sweep.log
pause
