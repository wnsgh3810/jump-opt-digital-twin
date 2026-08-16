export PYTHONIOENCODING=utf-8
export FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
export FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
export FS_PRESLIDE=0.86,0.85
echo "########## fs16 (질량 3.201) ##########"
python _F_majump.py
echo "########## 질량 3.26 (실측) ##########"
FS_MASS=3.26 python _F_majump.py
echo "########## 질량 3.26 + 속도게이트 ##########"
FS_MASS=3.26 FS_SUPP_VG=12,28 python _F_majump.py
echo ALLDONE
