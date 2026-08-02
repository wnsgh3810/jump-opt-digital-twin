export PYTHONIOENCODING=utf-8
export FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
export FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
export FS_PRESLIDE=0.86,0.85
for M in 3.26 3.30; do
  echo "===== 질량 $M kg ====="
  FS_MASS=$M python fs_runner.py fs3 2>&1 | tail -2
  cp _fs3_cl.json _F_board_m${M}_cl.json
  FS_MASS=$M FS_SEC_TAG=_F_m${M} python fs_secondary.py 2>&1 | tail -9
  FS_MASS=$M python fs_uboard.py m${M} fs16 2>&1 | tail -3
done
echo ALLDONE
