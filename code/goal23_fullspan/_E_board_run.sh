export PYTHONIOENCODING=utf-8
export FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
export FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
unset FS_MU FS_RAILX
echo "=== [1/2] fs15 기준 보드 ==="
python fs_runner.py fs3
cp _fs3_cl.json _E_board_fs15_cl.json
cp _fs3_ma.json _E_board_fs15_ma.json
echo "=== [2/2] E1 보드 (μ0.85 + railx 2e5,600) ==="
export FS_MU=0.85 FS_RAILX=200000,600
python fs_runner.py fs3
cp _fs3_cl.json _E_board_e1_cl.json
cp _fs3_ma.json _E_board_e1_ma.json
echo ALLDONE
