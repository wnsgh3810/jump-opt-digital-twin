export PYTHONIOENCODING=utf-8
export FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
export FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
export FS_PRESLIDE=0.86,0.85
python fs_runner.py fs3
cp _fs3_cl.json _E_board_ps2_cl.json
cp _fs3_ma.json _E_board_ps2_ma.json
FS_SEC_TAG=_Eps2 python fs_secondary.py
python fs_dq2late.py
echo ALLDONE
