@echo off
rem ===============================================================
rem  CVT -> D drive backup  (incremental; only changed files copy)
rem  Written 2026-08-17.  See twin\docs\context\BACKUP.md
rem
rem  /E    include subfolders (also empty ones)
rem  /MT:4 4 threads only - a parameter sweep may be running, stay gentle
rem  /R:1 /W:1  retry once, wait 1s  (do not hang on a locked file)
rem  NOTE: /E does NOT delete anything on the destination.
rem ===============================================================
setlocal
set "SRC=C:\Users\junho\CVT"
set "DST=D:\CVT_backup_260816"
set "LOG=%~dp0_backup_to_D.log"

echo ================================================================
echo  SOURCE : %SRC%
echo  DEST   : %DST%
echo  START  : %DATE% %TIME%
echo ================================================================

robocopy "%SRC%" "%DST%" /E /MT:4 /R:1 /W:1 /NFL /NDL /NP /LOG+:"%LOG%" /TEE
set RC=%ERRORLEVEL%

echo.
echo ================================================================
echo  END    : %DATE% %TIME%
echo  ROBOCOPY EXIT CODE = %RC%
echo    0     nothing needed copying (already identical)
echo    1     files were copied  (this is success)
echo    2,3   copied + extra files exist on destination (fine)
echo    8+    ERROR - check %LOG%
echo ================================================================
endlocal
exit /b %RC%
