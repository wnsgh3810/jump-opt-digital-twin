@echo off
REM ==========================================================================
REM  G74 : slip/rolling, 2-pass with SESSION-FIXED ruler
REM    pass1: measure foot metal-disc diameter over the session's trials,
REM           take the MEDIAN as the session ruler (camera is fixed per session)
REM    pass2: force that ruler on every trial and re-measure
REM    -> trials whose own diameter disagrees by >12%% get a QC flag
REM       (this is what catches tracking failures that used to pass silently)
REM  NOTE: this file MUST be CRLF. LF-only breaks cmd.exe.
REM  Run: double-click.  Output -> _G74.log
REM ==========================================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set P25_CLIP_RAW=35.5
echo === G74 slip 2-pass (session-fixed ruler) === > _G74.log
echo [1/5] 26.07.23
echo. >> _G74.log
echo ### 26.07.23 >> _G74.log
python fs_slipmeas.py 26.07.23 * >> _G74.log 2>&1
echo [2/5] 26.06.02
echo. >> _G74.log
echo ### 26.06.02 >> _G74.log
python fs_slipmeas.py 26.06.02 * >> _G74.log 2>&1
echo [3/5] 26.07.24
echo. >> _G74.log
echo ### 26.07.24 >> _G74.log
python fs_slipmeas.py 26.07.24 * >> _G74.log 2>&1
echo [4/5] 26.07.25
echo. >> _G74.log
echo ### 26.07.25 >> _G74.log
python fs_slipmeas.py 26.07.25 * >> _G74.log 2>&1
echo [5/5] 26.07.27
echo. >> _G74.log
echo ### 26.07.27 >> _G74.log
python fs_slipmeas.py 26.07.27 * >> _G74.log 2>&1

echo [proof] verification sheets
python _G72_proof.py >> _G74.log 2>&1
echo === done === >> _G74.log
echo.
echo FINISHED. See _G74.log  /  graphs\G72_proof
pause
