@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python p20_cma2.py 2500 > p20_cma2.log 2>&1
