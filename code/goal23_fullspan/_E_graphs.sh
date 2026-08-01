export PYTHONIOENCODING=utf-8
export FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
export FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
export FS_PRESLIDE=0.85
echo "=== fs16 비교 그래프 (CL+MA) ==="
python fs_compare_plot.py
echo "=== fs16 CVT 비교 그래프 ==="
python fs_compare_cvt.py
echo ALLDONE
