export PYTHONIOENCODING=utf-8
export FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
export FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
export FS_PRESLIDE=0.86,0.85
export FS_CMP_OUT=_compare_fs16 FS_STACK_TAG=fs16
echo "=== [1/2] CL + ModeA (전 점프 세션) ==="
python fs_compare_plot.py
echo "=== [2/2] CVT (0429) CL + ModeA ==="
python fs_compare_cvt.py
echo ALLDONE

python _E_cmp_readme.py "$FS_CMP_OUT" "$FS_STACK_TAG"
