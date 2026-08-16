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
export FS_ESCROW=supp2,hsupp1,spr
unset FS_ESCROW_SEED FS_W2
run_cfg esc
export FS_ESCROW_SEED=1
run_cfg esc_sd1
export FS_W2=0.005
run_cfg esc_sd1_w2a
export FS_W2=0.01
run_cfg esc_sd1_w2b
export FS_ESCROW_SEED=2 FS_W2=0.01
run_cfg esc_sd2_w2b
echo ALLDONE
