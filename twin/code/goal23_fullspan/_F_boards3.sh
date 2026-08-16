export PYTHONIOENCODING=utf-8
export FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
export FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
export FS_PRESLIDE=0.86,0.85
unset FS_ESCROW FS_ESC_STORE FS_ESCROW_SEED FS_W2
for VG in "12,28" "15,30" "18,35"; do
  TAG=svgp$(echo $VG | tr -d ',')
  echo "===== $TAG ($VG) ====="
  FS_SUPP_VG=$VG python fs_uboard.py $TAG fs16
done
echo ALLDONE
