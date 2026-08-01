export PYTHONIOENCODING=utf-8
export FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
export FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
unset FS_MU FS_RAILX
echo "=== fs15 secondary ==="
FS_SEC_TAG=_Efs15 python fs_secondary.py
echo "=== E1 secondary (μ0.85+railx) ==="
FS_MU=0.85 FS_RAILX=200000,600 FS_SEC_TAG=_Ee1 python fs_secondary.py
echo ALLDONE
