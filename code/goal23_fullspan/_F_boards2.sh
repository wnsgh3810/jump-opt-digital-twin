export PYTHONIOENCODING=utf-8
export FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
export FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
export FS_PRESLIDE=0.86,0.85
run_cfg () {
  TAG=$1
  echo "===== $TAG ====="
  python fs_runner.py fs3
  cp _fs3_cl.json _F_board_${TAG}_cl.json
  cp _fs3_ma.json _F_board_${TAG}_ma.json
  FS_SEC_TAG=_F_${TAG} python fs_secondary.py
  python fs_uboard.py ${TAG} fs16
}
unset FS_ESCROW FS_ESC_STORE FS_ESCROW_SEED FS_W2
export FS_SUPP_VG=15
run_cfg svg15
export FS_SUPP_VG=20
run_cfg svg20
export FS_SUPP_VG=25
run_cfg svg25
echo ALLDONE
