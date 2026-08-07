@echo off
REM ==========================================================================
REM  Marathon G / G21 joint sweep  (ASCII only - cmd cp949 safe)
REM  FIXED : canon_cap torque map, supp OFF, knee-spring OFF, bias1 OFF, knee_deep OFF
REM  FREE  : knee cap x hip cap x thigh CoM   (27 combos, ~3 min each = 80-90 min)
REM  Current best: knee 3.3 / hip 2.8 / comz 0  ->  J_G 0.7725 (gate PASS)
REM ==========================================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set P25_CLIP_RAW=35.5
set FS_TMAP=canon_cap
set FS_NOSUPP=1
set FS_NOSPR=1
set FS_NOBIAS=1
set FS_NODEEP=1
set LOG=_G21_sweep.log
echo G21 joint sweep start > %LOG%
echo ==========================================
echo  G21 joint sweep : 27 combos, 80-90 min
echo  detail log -^> %LOG%
echo ==========================================
echo.
python -c "import sys;print('python OK',sys.version.split()[0])" || (echo PYTHON NOT FOUND & pause & exit /b)

echo [1/27] knee 3.1 / hip 2.6 / comz 0.0
echo [1/27] knee 3.1 / hip 2.6 / comz 0.0 >> %LOG%
set FS_TDCAP=3.1,2.6
set FS_COMZ=
python _G13_board.py Q_k3p1_h2p6_c0p0 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p1_h2p6_c0p0.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [2/27] knee 3.1 / hip 2.6 / comz 0.015
echo [2/27] knee 3.1 / hip 2.6 / comz 0.015 >> %LOG%
set FS_TDCAP=3.1,2.6
set FS_COMZ=thigh=0.015
python _G13_board.py Q_k3p1_h2p6_c0p015 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p1_h2p6_c0p015.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [3/27] knee 3.1 / hip 2.6 / comz 0.027
echo [3/27] knee 3.1 / hip 2.6 / comz 0.027 >> %LOG%
set FS_TDCAP=3.1,2.6
set FS_COMZ=thigh=0.027
python _G13_board.py Q_k3p1_h2p6_c0p027 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p1_h2p6_c0p027.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [4/27] knee 3.1 / hip 2.8 / comz 0.0
echo [4/27] knee 3.1 / hip 2.8 / comz 0.0 >> %LOG%
set FS_TDCAP=3.1,2.8
set FS_COMZ=
python _G13_board.py Q_k3p1_h2p8_c0p0 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p1_h2p8_c0p0.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [5/27] knee 3.1 / hip 2.8 / comz 0.015
echo [5/27] knee 3.1 / hip 2.8 / comz 0.015 >> %LOG%
set FS_TDCAP=3.1,2.8
set FS_COMZ=thigh=0.015
python _G13_board.py Q_k3p1_h2p8_c0p015 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p1_h2p8_c0p015.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [6/27] knee 3.1 / hip 2.8 / comz 0.027
echo [6/27] knee 3.1 / hip 2.8 / comz 0.027 >> %LOG%
set FS_TDCAP=3.1,2.8
set FS_COMZ=thigh=0.027
python _G13_board.py Q_k3p1_h2p8_c0p027 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p1_h2p8_c0p027.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [7/27] knee 3.1 / hip 3.0 / comz 0.0
echo [7/27] knee 3.1 / hip 3.0 / comz 0.0 >> %LOG%
set FS_TDCAP=3.1,3.0
set FS_COMZ=
python _G13_board.py Q_k3p1_h3p0_c0p0 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p1_h3p0_c0p0.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [8/27] knee 3.1 / hip 3.0 / comz 0.015
echo [8/27] knee 3.1 / hip 3.0 / comz 0.015 >> %LOG%
set FS_TDCAP=3.1,3.0
set FS_COMZ=thigh=0.015
python _G13_board.py Q_k3p1_h3p0_c0p015 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p1_h3p0_c0p015.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [9/27] knee 3.1 / hip 3.0 / comz 0.027
echo [9/27] knee 3.1 / hip 3.0 / comz 0.027 >> %LOG%
set FS_TDCAP=3.1,3.0
set FS_COMZ=thigh=0.027
python _G13_board.py Q_k3p1_h3p0_c0p027 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p1_h3p0_c0p027.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [10/27] knee 3.3 / hip 2.6 / comz 0.0
echo [10/27] knee 3.3 / hip 2.6 / comz 0.0 >> %LOG%
set FS_TDCAP=3.3,2.6
set FS_COMZ=
python _G13_board.py Q_k3p3_h2p6_c0p0 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p3_h2p6_c0p0.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [11/27] knee 3.3 / hip 2.6 / comz 0.015
echo [11/27] knee 3.3 / hip 2.6 / comz 0.015 >> %LOG%
set FS_TDCAP=3.3,2.6
set FS_COMZ=thigh=0.015
python _G13_board.py Q_k3p3_h2p6_c0p015 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p3_h2p6_c0p015.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [12/27] knee 3.3 / hip 2.6 / comz 0.027
echo [12/27] knee 3.3 / hip 2.6 / comz 0.027 >> %LOG%
set FS_TDCAP=3.3,2.6
set FS_COMZ=thigh=0.027
python _G13_board.py Q_k3p3_h2p6_c0p027 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p3_h2p6_c0p027.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [13/27] knee 3.3 / hip 2.8 / comz 0.0
echo [13/27] knee 3.3 / hip 2.8 / comz 0.0 >> %LOG%
set FS_TDCAP=3.3,2.8
set FS_COMZ=
python _G13_board.py Q_k3p3_h2p8_c0p0 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p3_h2p8_c0p0.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [14/27] knee 3.3 / hip 2.8 / comz 0.015
echo [14/27] knee 3.3 / hip 2.8 / comz 0.015 >> %LOG%
set FS_TDCAP=3.3,2.8
set FS_COMZ=thigh=0.015
python _G13_board.py Q_k3p3_h2p8_c0p015 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p3_h2p8_c0p015.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [15/27] knee 3.3 / hip 2.8 / comz 0.027
echo [15/27] knee 3.3 / hip 2.8 / comz 0.027 >> %LOG%
set FS_TDCAP=3.3,2.8
set FS_COMZ=thigh=0.027
python _G13_board.py Q_k3p3_h2p8_c0p027 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p3_h2p8_c0p027.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [16/27] knee 3.3 / hip 3.0 / comz 0.0
echo [16/27] knee 3.3 / hip 3.0 / comz 0.0 >> %LOG%
set FS_TDCAP=3.3,3.0
set FS_COMZ=
python _G13_board.py Q_k3p3_h3p0_c0p0 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p3_h3p0_c0p0.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [17/27] knee 3.3 / hip 3.0 / comz 0.015
echo [17/27] knee 3.3 / hip 3.0 / comz 0.015 >> %LOG%
set FS_TDCAP=3.3,3.0
set FS_COMZ=thigh=0.015
python _G13_board.py Q_k3p3_h3p0_c0p015 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p3_h3p0_c0p015.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [18/27] knee 3.3 / hip 3.0 / comz 0.027
echo [18/27] knee 3.3 / hip 3.0 / comz 0.027 >> %LOG%
set FS_TDCAP=3.3,3.0
set FS_COMZ=thigh=0.027
python _G13_board.py Q_k3p3_h3p0_c0p027 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p3_h3p0_c0p027.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [19/27] knee 3.5 / hip 2.6 / comz 0.0
echo [19/27] knee 3.5 / hip 2.6 / comz 0.0 >> %LOG%
set FS_TDCAP=3.5,2.6
set FS_COMZ=
python _G13_board.py Q_k3p5_h2p6_c0p0 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p5_h2p6_c0p0.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [20/27] knee 3.5 / hip 2.6 / comz 0.015
echo [20/27] knee 3.5 / hip 2.6 / comz 0.015 >> %LOG%
set FS_TDCAP=3.5,2.6
set FS_COMZ=thigh=0.015
python _G13_board.py Q_k3p5_h2p6_c0p015 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p5_h2p6_c0p015.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [21/27] knee 3.5 / hip 2.6 / comz 0.027
echo [21/27] knee 3.5 / hip 2.6 / comz 0.027 >> %LOG%
set FS_TDCAP=3.5,2.6
set FS_COMZ=thigh=0.027
python _G13_board.py Q_k3p5_h2p6_c0p027 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p5_h2p6_c0p027.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [22/27] knee 3.5 / hip 2.8 / comz 0.0
echo [22/27] knee 3.5 / hip 2.8 / comz 0.0 >> %LOG%
set FS_TDCAP=3.5,2.8
set FS_COMZ=
python _G13_board.py Q_k3p5_h2p8_c0p0 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p5_h2p8_c0p0.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [23/27] knee 3.5 / hip 2.8 / comz 0.015
echo [23/27] knee 3.5 / hip 2.8 / comz 0.015 >> %LOG%
set FS_TDCAP=3.5,2.8
set FS_COMZ=thigh=0.015
python _G13_board.py Q_k3p5_h2p8_c0p015 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p5_h2p8_c0p015.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [24/27] knee 3.5 / hip 2.8 / comz 0.027
echo [24/27] knee 3.5 / hip 2.8 / comz 0.027 >> %LOG%
set FS_TDCAP=3.5,2.8
set FS_COMZ=thigh=0.027
python _G13_board.py Q_k3p5_h2p8_c0p027 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p5_h2p8_c0p027.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [25/27] knee 3.5 / hip 3.0 / comz 0.0
echo [25/27] knee 3.5 / hip 3.0 / comz 0.0 >> %LOG%
set FS_TDCAP=3.5,3.0
set FS_COMZ=
python _G13_board.py Q_k3p5_h3p0_c0p0 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p5_h3p0_c0p0.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [26/27] knee 3.5 / hip 3.0 / comz 0.015
echo [26/27] knee 3.5 / hip 3.0 / comz 0.015 >> %LOG%
set FS_TDCAP=3.5,3.0
set FS_COMZ=thigh=0.015
python _G13_board.py Q_k3p5_h3p0_c0p015 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p5_h3p0_c0p015.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo [27/27] knee 3.5 / hip 3.0 / comz 0.027
echo [27/27] knee 3.5 / hip 3.0 / comz 0.027 >> %LOG%
set FS_TDCAP=3.5,3.0
set FS_COMZ=thigh=0.027
python _G13_board.py Q_k3p5_h3p0_c0p027 >> %LOG% 2>&1
python -c "import io,json;d=json.load(io.open('_G13_board_Q_k3p5_h3p0_c0p027.json',encoding='utf-8'));print('    J_G %.4f   gate %s'%(d['J'],'PASS' if not d['gate_fail'] else 'FAIL'))"

echo.
echo ==========================================
echo  DONE. summary:
echo ==========================================
python _G21_summary.py
echo.
pause