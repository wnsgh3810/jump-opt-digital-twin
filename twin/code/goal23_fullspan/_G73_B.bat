@echo off
REM ==========================================================================
REM  G73 : (B) 24fps session group -- slip/rolling, then MuJoCo foot r board
REM   part 1: slip/rolling for 24fps sessions (0723/0602/0724/0725/0727)
REM           ruler = foot metal disc 30mm re-measured per video; r = 20mm
REM   part 2: proof sheets (visual verification -- caught 6 of 11 defects)
REM   part 3: ModeA board with FS_FOOTR=0.020 (foot contact radius fix)
REM           vs frozen best (0.021) -- before/after on J_G
REM  NOTE: this file MUST be CRLF. LF-only breaks cmd.exe.
REM  Run: double-click.  Output -> _G73_B.log
REM ==========================================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set P25_CLIP_RAW=35.5
echo === G73 (B) 24fps slip + foot radius board === > _G73_B.log

echo [1/3] slip 24fps group (23 trials)
echo   (1/23) 26.07.23 150_2.2_250_3
python fs_slipmeas.py 26.07.23 150_2.2_250_3 >> _G73_B.log 2>&1
echo   (2/23) 26.07.23 150_2.2_500_5
python fs_slipmeas.py 26.07.23 150_2.2_500_5 >> _G73_B.log 2>&1
echo   (3/23) 26.07.23 60_0.75_60_2
python fs_slipmeas.py 26.07.23 60_0.75_60_2 >> _G73_B.log 2>&1
echo   (4/23) 26.07.24 150_2.2_250_3
python fs_slipmeas.py 26.07.24 150_2.2_250_3 >> _G73_B.log 2>&1
echo   (5/23) 26.07.24 150_2.2_350_3.5
python fs_slipmeas.py 26.07.24 150_2.2_350_3.5 >> _G73_B.log 2>&1
echo   (6/23) 26.07.24 150_2.2_500_5
python fs_slipmeas.py 26.07.24 150_2.2_500_5 >> _G73_B.log 2>&1
echo   (7/23) 26.07.25 100_1.5_250_3
python fs_slipmeas.py 26.07.25 100_1.5_250_3 >> _G73_B.log 2>&1
echo   (8/23) 26.07.25 120_2_250_3
python fs_slipmeas.py 26.07.25 120_2_250_3 >> _G73_B.log 2>&1
echo   (9/23) 26.07.25 150_2.2_250_3
python fs_slipmeas.py 26.07.25 150_2.2_250_3 >> _G73_B.log 2>&1
echo   (10/23) 26.07.25 200_2.5_250_3
python fs_slipmeas.py 26.07.25 200_2.5_250_3 >> _G73_B.log 2>&1
echo   (11/23) 26.07.27 100_1.5_250_3
python fs_slipmeas.py 26.07.27 100_1.5_250_3 >> _G73_B.log 2>&1
echo   (12/23) 26.07.27 120_2_250_3
python fs_slipmeas.py 26.07.27 120_2_250_3 >> _G73_B.log 2>&1
echo   (13/23) 26.07.27 150_2.2_250_3
python fs_slipmeas.py 26.07.27 150_2.2_250_3 >> _G73_B.log 2>&1
echo   (14/23) 26.07.27 200_2.5_250_3
python fs_slipmeas.py 26.07.27 200_2.5_250_3 >> _G73_B.log 2>&1
echo   (15/23) 26.07.27 250_3_250_3
python fs_slipmeas.py 26.07.27 250_3_250_3 >> _G73_B.log 2>&1
echo   (16/23) 26.07.27 60_2_250_3
python fs_slipmeas.py 26.07.27 60_2_250_3 >> _G73_B.log 2>&1
echo   (17/23) 26.07.27 80_2_250_3
python fs_slipmeas.py 26.07.27 80_2_250_3 >> _G73_B.log 2>&1
echo   (18/23) 26.06.02 120_2_120_2
python fs_slipmeas.py 26.06.02 120_2_120_2 >> _G73_B.log 2>&1
echo   (19/23) 26.06.02 150_2.2_250_3
python fs_slipmeas.py 26.06.02 150_2.2_250_3 >> _G73_B.log 2>&1
echo   (20/23) 26.06.02 150_2.2_500_5
python fs_slipmeas.py 26.06.02 150_2.2_500_5 >> _G73_B.log 2>&1
echo   (21/23) 26.06.02 60_0.75_60_2
python fs_slipmeas.py 26.06.02 60_0.75_60_2 >> _G73_B.log 2>&1
echo   (22/23) 26.06.02 60_1.5_60_1.5
python fs_slipmeas.py 26.06.02 60_1.5_60_1.5 >> _G73_B.log 2>&1
echo   (23/23) 26.06.02 90_0.75_90_2
python fs_slipmeas.py 26.06.02 90_0.75_90_2 >> _G73_B.log 2>&1

echo [2/3] proof sheets
python _G72_proof.py >> _G73_B.log 2>&1

echo [3/3] ModeA board : foot radius 0.021 (frozen) vs 0.020 (measured)
set FS_TMAP=canon_cap
set FS_TDCAP=3.8,2.6
set FS_MASS=3.28
set FS_NOSUPP=1
set FS_NOSPR=1
set FS_NOBIAS=1
set FS_NODEEP=1
set FS_PRESLIDE=0.86,0.85,0.02,1.0
echo. >> _G73_B.log
echo ### foot r = 0.021 (frozen best) >> _G73_B.log
set FS_FOOTR=
python _G13_board.py G73_footr_0021 >> _G73_B.log 2>&1
echo. >> _G73_B.log
echo ### foot r = 0.020 (measured 40mm/2) >> _G73_B.log
set FS_FOOTR=0.020
python _G13_board.py G73_footr_0020 >> _G73_B.log 2>&1

echo === done === >> _G73_B.log
echo.
echo FINISHED. See _G73_B.log
pause
