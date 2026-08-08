@echo off
REM ============================================================================
REM  G62 : canon_capS 3-parameter sweep  (S x cap_knee x cap_hip)
REM        tau = a_hat + clip( S * canon(raw) - a_hat , +-cap )
REM        S = 1.0 reproduces the current best (J_G 0.7387) exactly.
REM  ASCII only, flat loop (cmd reads cp949 ; nested for + set breaks it).
REM  Run: double-click this file. Output -> _G62_capS_sweep.log
REM ============================================================================
setlocal
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

echo === G62 canon_capS sweep start === > _G62_capS_sweep.log

call :RUN 1.00 3.8 2.6
call :RUN 0.94 3.8 2.6
call :RUN 0.97 3.8 2.6
call :RUN 1.03 3.8 2.6
call :RUN 1.06 3.8 2.6
call :RUN 1.10 3.8 2.6

call :RUN 0.94 3.4 2.4
call :RUN 0.94 3.6 2.6
call :RUN 0.94 4.0 2.8
call :RUN 0.97 3.4 2.4
call :RUN 0.97 3.6 2.4
call :RUN 0.97 3.6 2.6
call :RUN 0.97 4.0 2.6
call :RUN 1.03 3.6 2.6
call :RUN 1.03 4.0 2.6
call :RUN 1.03 4.0 2.8
call :RUN 1.06 4.0 2.8
call :RUN 1.06 4.2 2.8
call :RUN 1.10 4.2 3.0
call :RUN 1.10 4.4 3.0

call :RUN 1.00 3.6 2.4
call :RUN 1.00 3.6 2.8
call :RUN 1.00 4.0 2.4
call :RUN 1.00 4.0 2.8
call :RUN 1.00 3.8 2.4
call :RUN 1.00 3.8 2.8

echo === done === >> _G62_capS_sweep.log
echo.
echo FINISHED. See _G62_capS_sweep.log
pause
exit /b

:RUN
set FS_TCAPS=%1,%2,%3
echo. >> _G62_capS_sweep.log
echo ### S=%1 capK=%2 capH=%3 >> _G62_capS_sweep.log
python _G13_board.py G62_%1_%2_%3 >> _G62_capS_sweep.log 2>&1
echo    S=%1 capK=%2 capH=%3 done
exit /b
