# -*- coding: utf-8 -*-
"""fs_dq2late — 마라톤 E 2급 지표 ②: dq2 push 말기(마지막 1/3) RMSE 세션합.

실기 dq2가 push 고점 직후 꺾이는 구간을 트윈이 따라가는지 정량화 (창=push 마지막 1/3).
구성은 env (baseline_fs3 규약). 출력: 세션별 dq2 말기 RMSE + 합. CLI: python fs_dq2late.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD
import fs_runner as FR


def main():
    ft = FR.fs_twin()
    TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
    SP = FR._sess_params()
    _qs = int(os.environ.get("FS_QDSHIFT", "0") or 0)

    def sh(x):
        if _qs <= 0:
            return x
        y = np.empty_like(x); y[_qs:] = x[:-_qs]; y[:_qs] = x[0]
        return y

    sess = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt or ho or not g:
            continue
        sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
        try:
            d = FD.load2(p); seg = FD.segment(d)
            _tko = os.environ.get("FS_TKOVR"); _kds = os.environ.get("FS_KDSC")
            gm = (g[0], g[1], g[2] * (float(_tko) if _tko else TK.get(g[2], 0.656)),
                  g[3] * (float(_kds) if _kds else 0.20))
            i0 = max(0, seg["i_desc"] - 5)
            t = d["t"][i0:] - d["t"][i0]
            _vff = ((s not in os.environ["FS_VDES0"].split(","))
                    if os.environ.get("FS_VDES0") else FD.vdes_applied(s))
            L = FR.rollout_cl_fs(ft, t, sh(d["qd1"][i0:]), sh(d["qd2"][i0:]), sh(d["dqd1"][i0:]), sh(d["dqd2"][i0:]),
                                 gm, seg["t_lo"] - d["t"][i0], two_stage=True,
                                 bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                                 fade=os.environ.get("FS_FADE") == "1", taulim=None, vdes_ff=_vff)
            if L is None:
                continue
            pm = seg["push"][i0:][: len(t)]
            idx = np.where(pm)[0]
            if len(idx) < 9:
                continue
            late = idx[-len(idx) // 3:]                      # push 마지막 1/3
            dq2s = np.interp(t, L["t"], L["dq2"])
            r = float(np.sqrt(np.mean((d["dq2"][i0:][late] - dq2s[late]) ** 2)))
            sess.setdefault(s, []).append(r)
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__}", flush=True)
    tot = 0.0
    for s in sorted(sess):
        m = float(np.mean(sess[s])); tot += m
        print(f"{s}: dq2말기 {m:.3f} (n={len(sess[s])})")
    print(f"세션합: {tot:.3f}")


if __name__ == "__main__":
    main()
