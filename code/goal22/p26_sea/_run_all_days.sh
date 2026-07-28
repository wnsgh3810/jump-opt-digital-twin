cd /c/Users/junho/Documents/jump-opt-digital-twin/code/goal22/p26_sea
for d in 26.07.22 26.07.24 26.07.25 26.04.24 26.04.21 26.04.22 26.04.29 26.06.02/position 26.03.24/Jump/Jump_No_Tr; do
  echo "=== $d ==="
  PYTHONIOENCODING=utf-8 python video_slip_alldays.py "$d" 2>&1 | grep -viE "warning|frame size"
done
echo ALLDONE
