# -*- coding: utf-8 -*-
"""_F_vceil — F-H7 프로브: 전압 포락선 천장 (w0,w1) 스캔. dq2 말기 꺾임 + h + push RMSE."""
import os, sys
import fs_data as FD
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
exec(open("_F_f2probe.py", encoding="utf-8").read().split('CFG = ')[0])  # run_one/TR 재사용

def run_dq2late(want, tr):
    ft = FR.fs_twin(); SP = FR._sess_params()
    for s, p, g, cvt, ho in FD.registry():
        if s != want or p.name != tr or cvt or ho: continue
        d = FD.load2(p); seg = FD.segment(d)
        i0 = max(0, seg["i_desc"] - 5); t = d["t"][i0:] - d["t"][i0]
        L = FR.rollout_cl_fs(ft, t, sh(d["qd1"][i0:]), sh(d["qd2"][i0:]), sh(d["dqd1"][i0:]), sh(d["dqd2"][i0:]),
                             tuple(g), seg["t_lo"] - d["t"][i0], two_stage=True, bias1=SP[s]["bias1"],
                             knee_deep=SP[s]["knee_deep"], fade=True, taulim=None, vdes_ff=FD.vdes_applied(s))
        if L is None: return None
        pm = seg["push"][i0:][:len(t)]; idx = np.where(pm)[0]
        late = idx[-len(idx)//3:]
        dq2s = np.interp(t, L["t"], L["dq2"])
        return float(np.sqrt(np.mean((d["dq2"][i0:][late] - dq2s[late])**2)))

CFG = [("esc만 (기준)", {"FS_ESCROW": "supp2,hsupp1,spr"})]
for w in ("22,32", "22,38", "25,40", "20,30"):
    CFG.append((f"esc+vceil {w}", {"FS_ESCROW": "supp2,hsupp1,spr", "FS_VCEIL": w}))
CFG.append(("esc+sd1+vceil 22,32", {"FS_ESCROW": "supp2,hsupp1,spr", "FS_ESCROW_SEED": "1", "FS_VCEIL": "22,32"}))
CFG.append(("esc+sd2+vceil 22,32", {"FS_ESCROW": "supp2,hsupp1,spr", "FS_ESCROW_SEED": "2", "FS_VCEIL": "22,32"}))

for tag, envs in CFG:
    for k in ("FS_ESCROW", "FS_ETA", "FS_W2", "FS_ESCROW_SEED", "FS_VCEIL"):
        os.environ.pop(k, None)
    os.environ.update(envs)
    FR._CACHE.clear()
    parts = []
    for want, tr in TR:
        r = run_one(want, tr)
        dl = run_dq2late(want, tr)
        if r:
            parts.append(f"{want[-5:]} h{r[0]:5.1f}/{r[1]} q2 {r[2][1]:.2f} τ2 {r[2][5]:.2f} dq2말기 {dl:.2f}")
    print(f"{tag:<22} " + " | ".join(parts), flush=True)
print("done")
