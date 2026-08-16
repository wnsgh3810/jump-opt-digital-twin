# -*- coding: utf-8 -*-
"""_F_f2combo — F2 조합 프로브: esc + seed(저장 크레딧) × w2/η. _F_f2probe와 동일 계측."""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
exec(open("_F_f2probe.py", encoding="utf-8").read().split('CFG = ')[0])  # run_one/TR 재사용

CFG = []
for sd in ("1", "2"):
    for w2 in ("0.005", "0.01", "0.02"):
        CFG.append((f"esc+sd{sd}+w2 {w2}", {"FS_ESCROW": "supp2,hsupp1,spr", "FS_ESCROW_SEED": sd, "FS_W2": w2}))
CFG.append(("esc+sd1+η0.95", {"FS_ESCROW": "supp2,hsupp1,spr", "FS_ESCROW_SEED": "1", "FS_ETA": "0.95"}))
CFG.append(("esc+sd1+η0.95+w2 0.01", {"FS_ESCROW": "supp2,hsupp1,spr", "FS_ESCROW_SEED": "1", "FS_ETA": "0.95", "FS_W2": "0.01"}))

OUT = {}
for tag, envs in CFG:
    for k in ("FS_ESCROW", "FS_ETA", "FS_W2", "FS_ESCROW_SEED"):
        os.environ.pop(k, None)
    os.environ.update(envs)
    FR._CACHE.clear()
    row = {}
    for want, tr in TR:
        r = run_one(want, tr)
        if r:
            row[f"{want}/{tr}"] = {"h": round(r[0], 1), "h_real": r[1], "rmse": [round(v, 2) for v in r[2]]}
    OUT[tag] = row
    line = " | ".join(f"{k.split('/')[0][-5:]} h{v['h']:5.1f}/{v['h_real']} q2 {v['rmse'][1]:.2f} τ2 {v['rmse'][5]:.2f}"
                      for k, v in row.items())
    print(f"{tag:<22} {line}", flush=True)
safe.atomic_json_write(HERE / "_F_f2combo.json", OUT)
print("done")
