# -*- coding: utf-8 -*-
"""fs_secondary — 마라톤 D 2순위 지표: 점프높이(비행시간법 실측 대비) + 슬립(영상 대비).

h_sim = v_bz(이륙)²/2g (rollout bz 말단 기울기) vs _D_jumph.json (GRF 비행시간 h=g·T²/8)
slip_sim = 하강 창 발 x 순변위 [mm] vs _fs_descslip_all.json drift_deep_px (부호·순위 비교, 스케일 미정)
구성은 env로 (baseline_fs3 규약 — FS_QDSHIFT/FS_TKOVR/FS_KDSC/FS_MU 포함). CLI: python fs_secondary.py
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bench"))
import safe
import fs_data as FD
import fs_runner as FR


def main():
    ft = FR.fs_twin()
    TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
    SP = FR._sess_params()
    JH = safe.read_json(HERE / "_D_jumph.json")
    SL = safe.read_json(HERE / "_fs_descslip_all.json")
    _qs = int(os.environ.get("FS_QDSHIFT", "0") or 0)

    def sh(x):
        if _qs <= 0:
            return x
        y = np.empty_like(x); y[_qs:] = x[:-_qs]; y[:_qs] = x[0]
        return y

    OUT = {}
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
            t_end = seg["t_lo"] - d["t"][i0]
            _vff = ((s not in os.environ["FS_VDES0"].split(","))
                    if os.environ.get("FS_VDES0") else FD.vdes_applied(s))
            L = FR.rollout_cl_fs(ft, t, sh(d["qd1"][i0:]), sh(d["qd2"][i0:]), sh(d["dqd1"][i0:]), sh(d["dqd2"][i0:]),
                                 gm, t_end, two_stage=True, bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                                 fade=os.environ.get("FS_FADE") == "1", taulim=None, vdes_ff=_vff)
            if L is None:
                continue
            dt = float(np.median(np.diff(L["t"])))
            vbz = np.gradient(L["bz"], dt)
            vbz = np.convolve(vbz, np.ones(5) / 5, mode="same")
            v_lo = float(vbz.max())                       # 이륙 속도 강건 추정 (최대 상승 속도)
            h_sim = max(v_lo, 0.0) ** 2 / (2 * 9.81) * 100
            pm = seg["push"][i0:][: len(t)]
            t_p0 = float(t[pm][0]) if pm.sum() else t_end - 0.3
            mdw = L["t"] < t_p0
            slip_sim = (L["fx"][mdw][-1] - L["fx"][mdw][0]) * 1000 if mdw.sum() > 10 else None
            # 마라톤E: 접촉 유지 전창(하강+push) 발 이동 — 판별 지표 D_slip의 원소 (cfz>5N)
            slip_ct = None
            if "cfz" in L:
                ct = L["cfz"] > 5.0
                if ct.sum() > 10:
                    last = int(np.where(ct)[0][-1])
                    slip_ct = (L["fx"][last] - L["fx"][0]) * 1000
            key = f"{s}/{p.name}"
            e = dict(h_sim=round(h_sim, 1))
            jh = JH.get(key)
            if jh:
                e["h_real"] = jh["h_cm"]; e["dh"] = round(h_sim - jh["h_cm"], 1)
            sl = SL.get(key)
            if slip_sim is not None:
                e["slip_sim_mm"] = round(slip_sim, 1)
            if slip_ct is not None:
                e["slip_ct_mm"] = round(slip_ct, 1)
            if sl and sl.get("video"):
                e["slip_video_px"] = sl.get("drift_deep_px")
            OUT[key] = e
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__}", flush=True)
    safe.atomic_json_write(HERE / f"_D_secondary{os.environ.get('FS_SEC_TAG', '')}.json", OUT)
    # 세션 요약
    print(f"{'세션':<10} {'|Δh| 중앙':>9} {'h예 (sim/real)':>16} {'슬립 sim(무슬립일 기준선 대비)':>20}")
    sess = {}
    for k, e in OUT.items():
        sess.setdefault(k.split("/")[0], []).append(e)
    for s in sorted(sess):
        dh = [abs(e["dh"]) for e in sess[s] if "dh" in e]
        ex = [e for e in sess[s] if "dh" in e][:1]
        sl_ = [e.get("slip_sim_mm") for e in sess[s] if e.get("slip_sim_mm") is not None]
        print(f"{s:<10} {np.median(dh) if dh else float('nan'):9.1f} "
              f"{('%s/%s' % (ex[0]['h_sim'], ex[0]['h_real'])) if ex else '—':>16} "
              f"{np.median(sl_) if sl_ else float('nan'):20.1f}")
    print("done → _D_secondary.json", flush=True)


if __name__ == "__main__":
    main()
