export PYTHONIOENCODING=utf-8
export FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
export FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
export FS_PRESLIDE=0.86,0.85
unset FS_SUPP_VG FS_ESCROW FS_RISE_CAP
for W in 0.003 0.006 0.012; do
  echo "===== w2 $W ====="
  FS_W2=$W python fs_uboard.py w2_${W} fs16 2>&1 | tail -4
done
echo "===== gate12,28 + w2 0.006 ====="
FS_SUPP_VG=12,28 FS_W2=0.006 python fs_uboard.py g1228w2 fs16 2>&1 | tail -4
echo ALLDONE
