# -*- coding: utf-8 -*-
"""_F_f2probe — F2 손실 재심 프로브 (escrow ON 고정): η^sign · w2 · seed 스캔.
각 구성 × 4 trial: h, push 6ch RMSE. 출력 _F_f2probe.json + 표.
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
os.environ.update(FS_FIXED="1", FS_FADE="1", FS_TAUOBS="lpf", FS_TC="0.002",
                  FS_KNEE_REL="0.1", FS_KNEE_LOAD="1", FS_TAULIM="20.5",
                  FS_TKOVR="1.0", FS_KDSC="1.0", FS_QDSHIFT="2", FS_PRESLIDE="0.86,0.85")
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import safe
import fs_data as FD, fs_runner as FR, fs_metric as FMET

JH = safe.read_json(HERE / "_D_jumph.json")
TR = [("26.04.24", "120_2.2_150_2.5"), ("26.07.22", "150_2.2_250_3"),
      ("26.07.23", "150_2.2_500_5"), ("26.07.27", "100_1.5_250_3")]


def sh(x, n=2):
    y = np.empty_like(x); y[n:] = x[:-n]; y[:n] = x[0]; return y


def run_one(want, tr):
    ft = FR.fs_twin(); SP = FR._sess_params()
    for s, p, g, cvt, ho in FD.registry():
        if s != want or p.name != tr or cvt or ho:
            continue
        d = FD.load2(p); seg = FD.segment(d)
        i0 = max(0, seg["i_desc"] - 5); t = d["t"][i0:] - d["t"][i0]
        L = FR.rollout_cl_fs(ft, t, sh(d["qd1"][i0:]), sh(d["qd2"][i0:]), sh(d["dqd1"][i0:]), sh(d["dqd2"][i0:]),
                             tuple(g), seg["t_lo"] - d["t"][i0], two_stage=True, bias1=SP[s]["bias1"],
                             knee_deep=SP[s]["knee_deep"], fade=True, taulim=None, vdes_ff=FD.vdes_applied(s))
        if L is None:
            return None
        dtm = float(np.median(np.diff(L["t"])))
        vbz = np.convolve(np.gradient(L["bz"], dtm), np.ones(5) / 5, mode="same")
        h = max(float(vbz.max()), 0.0) ** 2 / (2 * 9.81) * 100
        gi = lambda k: np.interp(t, L["t"], L[k])
        m = seg["push"][i0:][: len(t)]
        r = FMET._rmse6({k: d[k][i0:] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}, m,
                        gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"),
                        np.clip(gi("s1f"), -20.5, 20.5), gi("s2"))
        jh = JH.get(f"{s}/{p.name}", {}).get("h_cm")
        return h, jh, r


CFG = [("기준 fs16 (esc OFF)", {}),
       ("esc만", {"FS_ESCROW": "supp2,hsupp1,spr"})]
for eta in ("0.95", "0.90", "0.85"):
    CFG.append((f"esc+η{eta}", {"FS_ESCROW": "supp2,hsupp1,spr", "FS_ETA": eta}))
for w2 in ("0.005", "0.01", "0.02"):
    CFG.append((f"esc+w2 {w2}", {"FS_ESCROW": "supp2,hsupp1,spr", "FS_W2": w2}))
for sd in ("1", "2", "3"):
    CFG.append((f"esc+seed{sd}J", {"FS_ESCROW": "supp2,hsupp1,spr", "FS_ESCROW_SEED": sd}))

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
            row[f"{want}/{tr}"] = {"h": round(r[0], 1), "h_real": r[1],
                                   "rmse": [round(v, 2) for v in r[2]]}
    OUT[tag] = row
    line = " | ".join(f"{k.split('/')[0][-5:]} h{v['h']:5.1f}/{v['h_real']} q2 {v['rmse'][1]:.2f} τ2 {v['rmse'][5]:.2f}"
                      for k, v in row.items())
    print(f"{tag:<18} {line}", flush=True)
safe.atomic_json_write(HERE / "_F_f2probe.json", OUT)
print("done")
