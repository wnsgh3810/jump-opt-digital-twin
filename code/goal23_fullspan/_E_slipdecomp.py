# -*- coding: utf-8 -*-
"""_E_slipdecomp — 발 이동을 **구름 vs 진짜 미끄럼**으로 분해 (마라톤E P12).

발 geom 중심 이동 = 구름(기구학) + 미끄럼(접촉 물질점 접선속도 적분).
영상(_fs_descslip_all.json drift_deep_px)이 잰 구간은 하강(deep)이므로 창을 맞춰 비교한다.
CLI: FS_PRESLIDE=... python _E_slipdecomp.py <태그>
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
os.environ["FS_SLIPLOG"] = "1"
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bench"))
import safe
import fs_data as FD
import fs_runner as FR

VID = safe.read_json(HERE / "_fs_descslip_all.json")
_qs = int(os.environ.get("FS_QDSHIFT", "0") or 0)


def sh(x):
    if _qs <= 0:
        return x
    y = np.empty_like(x); y[_qs:] = x[:-_qs]; y[:_qs] = x[0]; return y


def main():
    ft = FR.fs_twin(); SP = FR._sess_params()
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt or ho or not g:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            i0 = max(0, seg["i_desc"] - 5)
            t = d["t"][i0:] - d["t"][i0]
            sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
            L = FR.rollout_cl_fs(ft, t, sh(d["qd1"][i0:]), sh(d["qd2"][i0:]), sh(d["dqd1"][i0:]),
                                 sh(d["dqd2"][i0:]), tuple(g), seg["t_lo"] - d["t"][i0],
                                 two_stage=True, bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                                 fade=True, taulim=None, vdes_ff=(s != "26.04.21"))
            if L is None:
                continue
            dt = float(np.median(np.diff(L["t"])))
            pm = seg["push"][i0:][: len(t)]
            t_p0 = float(t[pm][0]) if pm.sum() else float(t[-1])
            ct = L["cfz"] > 5.0
            e = {}
            for nm, w in (("desc", ct & (L["t"] < t_p0)), ("push", ct & (L["t"] >= t_p0)), ("all", ct)):
                if w.sum() < 5:
                    continue
                i, j = int(np.where(w)[0][0]), int(np.where(w)[0][-1])
                mv = (L["fx"][j] - L["fx"][i]) * 1000
                sl = float(np.sum(L["slipv"][w]) * dt) * 1000
                e[nm] = dict(move_mm=round(mv, 2), slide_mm=round(sl, 2),
                             roll_mm=round(mv - sl, 2),
                             slide_path_mm=round(float(np.sum(np.abs(L["slipv"][w])) * dt) * 1000, 2))
            v = VID.get(f"{s}/{p.name}", {})
            if v.get("video"):
                e["video_deep_px"] = v.get("drift_deep_px")
            OUT[f"{s}/{p.name}"] = e
            print(f"{s}/{p.name}: OK", flush=True)
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__} {ex}", flush=True)
    tag = sys.argv[1] if len(sys.argv) > 1 else "x"
    safe.atomic_json_write(HERE / f"_E_slipdecomp_{tag}.json", OUT)
    print("done", flush=True)


if __name__ == "__main__":
    main()
