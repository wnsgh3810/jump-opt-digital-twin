@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python p20_cma.py 400 > p20_cma.log 2>&1
