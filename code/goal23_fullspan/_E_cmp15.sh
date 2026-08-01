export PYTHONIOENCODING=utf-8
export FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
export FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
unset FS_PRESLIDE
export FS_CMP_OUT=_compare FS_STACK_TAG=fs15
python fs_compare_plot.py
python fs_compare_cvt.py
echo ALLDONE

python _E_cmp_readme.py "$FS_CMP_OUT" "$FS_STACK_TAG"
