@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python p22_nsga.py 60 9 > p22_nsga.log 2>&1
