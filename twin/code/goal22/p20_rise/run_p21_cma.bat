@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python p21_cma.py 8000 > p21_cma.log 2>&1
