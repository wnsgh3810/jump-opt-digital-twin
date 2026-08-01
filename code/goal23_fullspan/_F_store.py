# -*- coding: utf-8 -*-
"""_F_store — F1b 프로브: 하강 흡수 증폭 k 스캔 (CL 4 trial + 0324 MA)."""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
exec(open("_F_f2probe.py", encoding="utf-8").read().split('CFG = ')[0])

def ma0324():
    ft = FR.fs_twin(); SP = FR._sess_params()
    accs = []
    for s, p, g, cvt, ho in FD.registry():
        if s != "26.03.24" or cvt: continue
        d = FD.load2(p); seg = FD.segment(d)
        pw = FD.plot_window(p, d)
        if pw is None: continue
        tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1])
        if m.sum() < 30: continue
        i0 = int(np.argmax(m)); t = tt[m] - tt[i0]
        sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
        L = FR.rollout_ol_fs_b(ft, t, d["raw1"][m], d["raw2"][m],
                               float(d["q1"][i0]), float(d["q2"][i0]),
                               float(d["dq1"][i0]), float(d["dq2"][i0]),
                               float(t[-1] - 0.004), bias1=sp["bias1"], knee_deep=sp["knee_deep"], fade=True)
        if L is None: continue
        gm = lambda k: np.interp(t, L["t"], L[k])
        accs.append([float(np.degrees(np.sqrt(np.mean((d["q1"][m]-gm("thm1"))**2)))),
                     float(np.degrees(np.sqrt(np.mean((d["q2"][m]-gm("q2"))**2))))])
    return np.mean(accs, axis=0) if accs else (np.nan, np.nan)

CFG = [("esc+store2", {"FS_ESCROW": "supp2,hsupp1,spr", "FS_ESC_STORE": "2"}),
       ("esc+store3", {"FS_ESCROW": "supp2,hsupp1,spr", "FS_ESC_STORE": "3"}),
       ("esc+store5", {"FS_ESCROW": "supp2,hsupp1,spr", "FS_ESC_STORE": "5"}),
       ("esc+store3+w2 0.005", {"FS_ESCROW": "supp2,hsupp1,spr", "FS_ESC_STORE": "3", "FS_W2": "0.005"})]
for tag, envs in CFG:
    for k in ("FS_ESCROW", "FS_ESC_STORE", "FS_W2", "FS_ESCROW_SEED"):
        os.environ.pop(k, None)
    os.environ.update(envs)
    FR._CACHE.clear()
    parts = []
    for want, tr in TR:
        r = run_one(want, tr)
        if r: parts.append(f"{want[-5:]} h{r[0]:5.1f}/{r[1]} q2 {r[2][1]:.2f} τ2 {r[2][5]:.2f}")
    ma = ma0324()
    print(f"{tag:<20} " + " | ".join(parts) + f" | 0324MA q1 {ma[0]:.2f} q2 {ma[1]:.2f} (fs16 5.02/14.91)", flush=True)
print("done")
