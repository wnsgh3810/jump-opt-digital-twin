export PYTHONIOENCODING=utf-8
export FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
export FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
export FS_PRESLIDE=0.86,0.85
unset FS_ESCROW
echo "===== gate 10,26 ====="
FS_SUPP_VG=10,26 python fs_uboard.py svgp1026 fs16 2>&1 | tail -4
echo "===== gate 12,28 + rc16 ====="
FS_SUPP_VG=12,28 FS_RISE_CAP=16 python fs_uboard.py g1228rc16 fs16 2>&1 | tail -4
echo "===== gate 12,28 + rc12 ====="
FS_SUPP_VG=12,28 FS_RISE_CAP=12 python fs_uboard.py g1228rc12 fs16 2>&1 | tail -4
echo ALLDONE
