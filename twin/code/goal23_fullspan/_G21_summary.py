# -*- coding: utf-8 -*-
"""_G21_summary — G21 공적합 스윕 결과 요약표 (게이트 통과분만 랭킹)."""
import os, io, json, glob
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
HERE = Path(__file__).parent
R = []
for f in sorted(glob.glob(str(HERE / "_G13_board_*.json"))):
    try:
        d = json.load(io.open(f, encoding="utf-8"))
    except Exception:
        continue
    if "J" not in d:
        continue
    R.append((d.get("tag", Path(f).stem), d["J"], d.get("ema"), d.get("eh_n"),
              d.get("es_n"), len(d.get("gate_fail", [])) == 0, d.get("gate_fail", [])))
R.sort(key=lambda x: x[1])
print(f"{'tag':<22}{'J_G':>9}{'Ê_MA':>9}{'Ê_h':>9}{'Ê_slip':>9}  게이트")
for t, J, a, h, s, ok, bad in R:
    f = lambda x: f"{x:9.4f}" if isinstance(x, (int, float)) else f"{'—':>9}"
    print(f"{t[:21]:<22}{J:9.4f}{f(a)}{f(h)}{f(s)}  " +
          ("PASS" if ok else "FAIL " + " · ".join(bad)[:60]))
print(f"\n총 {len(R)}건 · 게이트 통과 {sum(1 for r in R if r[5])}건 · p24 = 1.0000")
ok = [r for r in R if r[5]]
if ok:
    print(f"★ 최고(게이트 통과): {ok[0][0]}  J_G = {ok[0][1]:.4f}  (p24 대비 {100*(ok[0][1]-1):+.2f}%)")
