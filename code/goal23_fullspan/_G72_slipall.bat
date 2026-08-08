@echo off
REM ==========================================================================
REM  G72 : slip/rolling measurement over ALL trials (video + encoder fusion)
REM    slip = dx_video(roller center) - r*dtheta_encoder,  r = 20.0 mm
REM    ruler = foot metal disc 30.0 mm, re-measured PER VIDEO
REM  Takes ~30-60 min (55 trials x ~110 frames x circle fit).
REM  NOTE: this file MUST be CRLF. LF-only breaks cmd.exe.
REM  Run: double-click.  Output -> _G72_slipall.log / _G72_slipall.json
REM ==========================================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set P25_CLIP_RAW=35.5
echo === G72 slip/rolling ALL === > _G72_slipall.log
python fs_slipmeas.py --all >> _G72_slipall.log 2>&1
echo.
echo FINISHED. See _G72_slipall.log  /  _G72_slipall.json
pause
