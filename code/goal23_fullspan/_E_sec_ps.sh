export PYTHONIOENCODING=utf-8
export FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
export FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
unset FS_MU
export FS_PRESLIDE=0.85
echo "=== ps0.85 secondary ==="
FS_SEC_TAG=_Eps python fs_secondary.py
echo "=== ps0.85 dq2late ==="
python fs_dq2late.py
echo "=== fs15 dq2late (기준) ==="
unset FS_PRESLIDE
python fs_dq2late.py
echo ALLDONE
