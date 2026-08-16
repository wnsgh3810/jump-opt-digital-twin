@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python p23_fit_nsga.py 60 9 36 > p23_fit_nsga.log 2>&1
