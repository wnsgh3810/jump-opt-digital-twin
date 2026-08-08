@echo off
REM ==========================================================================
REM  G72 : slip/rolling over ALL trials (video + encoder fusion)
REM    slip = dx_video(roller center) - r*dtheta_encoder,  r = 20.0 mm
REM    ruler = foot metal disc 30.0 mm, re-measured PER VIDEO
REM  fps/resolution are read PER VIDEO (24 / 30 / 59.35 ; 720p..4K mixed).
REM  4K trials take ~4 min each (24 of them) -> total roughly 2 hours.
REM  Old results are deleted first: fps handling changed 2026-08-08.
REM  NOTE: this file MUST be CRLF. LF-only breaks cmd.exe.
REM  Run: double-click.  Output -> _G72_slipall.log / _G72_slipall.json
REM ==========================================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set P25_CLIP_RAW=35.5
if exist _G72_slipall.json del _G72_slipall.json
echo === G72 slip/rolling ALL === > _G72_slipall.log
python fs_slipmeas.py --all >> _G72_slipall.log 2>&1
echo --- proof sheets --- >> _G72_slipall.log
python _G72_proof.py >> _G72_slipall.log 2>&1
echo.
echo FINISHED. See _G72_slipall.log / _G72_slipall.json / graphs\G72_proof
pause
