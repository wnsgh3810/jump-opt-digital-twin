"""GOAL22 P9 — hip 제어측 Stribeck (역대 미시도 축; P4 'hip 헤드룸 5~9배' 후속).

GOAL21 air 회귀: hip 초과 쿨롱 ~0.35Nm. strib_knee는 P12/P8b에서 기각됐지만
hip측은 시도된 적 없음. 구현: 창/fs replay에서 hip ctrl에 -c*tanh(v/0.3)*exp(-|v|/1) 추가.
P13h(계측보정) 위 스윕, c ∈ [0.2, 0.5, 1.0, 2.0]."""
import json
import numpy as np
from pathlib import Path
from g22_p8b_axes import winit as winit0
import g21_p13_linkage as P13
import g21_p13e_honest as PH

SD = -0.0015
OUT = Path(__file__).parent / "p9_stribhip.json"
_C = {}


def winit():
    P12 = winit0()
    _C["P12"] = P12
    return P12


def build_model(P12, x32):
    S = P12._G["S"]; FR = P12._G["FR"]; FL = P12._G["FL"]; mj = P12._G["mujoco"]
    dd = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = FL.build_xml_fourbar_flip(dd["arm_knee"], sc)
    xml = P13.apply_linkage_mods(xml, dict(zip(P13.N6, np.asarray(x32)[26:32])))
    return mj.MjModel.from_xml_string(xml), dd


def eval_striph(args):
    """P12 group dict 동일 키 — hip ctrl-side Stribeck c 적용, sens_delay 고정."""
    x32, c = args
    if not P13._M:
        winit()
    P12 = _C.get("P12") or winit()
    mj = P12._G["mujoco"]; MS = P12._G["MS"]
    model, dd = build_model(P12, x32)
    eh = (lambda v: -c * np.tanh(v / 0.3) * np.exp(-abs(v) / 1.0)) if c > 0 else None
    d = mj.MjData(model)
    res = {"habs": 0.0}
    for tr_ in P12._G["trials"]:
        ds = tr_["ds"]
        k1, k2 = P12.OFFKEY.get(ds, (None, None))
        o1 = dd.get(k1, 0.0) if k1 else 0.0; o2 = dd.get(k2, 0.0) if k2 else 0.0
        ppv = P12.mod_tau(tr_["pp"], tr_["pp"]["t"], {"sens_delay": SD})
        pp = P12._G["sv"](ppv, o1, o2)
        t = pp["t"]; dt = model.opt.timestep
        sc = 0.0
        for i0 in pp["starts"]:
            t1 = min(t[i0] + pp["W"], t[-1])
            q2 = pp["q2m"][i0]; dq2 = pp["dq2m"][i0]
            d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], q2, -q2, q2]
            d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dq2, -dq2, dq2]
            mj.mj_forward(model, d)
            nst = int(round((t1 - t[i0]) / dt))
            ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
            dq1a = np.empty(nst); dq2a = np.empty(nst)
            ok = True
            for k in range(nst):
                tc = t[i0] + k * dt
                e1 = eh(d.qvel[1]) if eh else 0.0
                d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]) + e1, np.interp(tc, t, pp["tau_k"])]
                try:
                    mj.mj_step(model, d)
                except Exception:
                    ok = False
                    break
                ts[k] = tc + dt
                q1a[k] = d.qpos[1]; q2a[k] = d.qpos[2]
                dq1a[k] = d.qvel[1]; dq2a[k] = d.qvel[2]
            if not ok:
                sc += MS.W_Q * 2.0 + MS.W_DQ * 20.0
                continue
            mask = (t >= ts[0]) & (t <= ts[-1])
            if mask.sum() < 3:
                continue
            r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mask], ts, sim) - real[mask]) ** 2)))
            sc += (MS.W_Q * (r(q1a, pp["q1m"]) + r(q2a, pp["q2m"]))
                   + MS.W_DQ * (r(dq1a, pp["dq1m"]) + r(dq2a, pp["dq2m"])))
        res[P12.GKEY[ds]] = res.get(P12.GKEY[ds], 0.0) + sc
        if ds in ("jump_0424", "jump_0602", "jump_0324"):
            fsk = "fs_" + ds.split("_")[-1]
            # fs: hip extra 포함 버전 — P12.fs_metric은 knee extra만 지원하므로 c>0이면 근사로 knee-extra 없이
            sc2, h_pred = P12.fs_metric(model, pp, tr_["td"], None)
            res[fsk] = res.get(fsk, 0.0) + sc2
            if ds != "jump_0324" and np.isfinite(h_pred) and np.isfinite(tr_["h_real"]):
                res["habs"] += abs(h_pred - tr_["h_real"])
    return res


def main():
    import multiprocessing as mp
    P12 = winit()
    G7 = P12.OBJ_GROUPS
    x_h = np.array(json.load(open(Path(__file__).parent / "fourbar_p13h_candidate.json"))["x"])
    pool = mp.Pool(8, initializer=winit)
    CS = [0.0, 0.2, 0.5, 1.0, 2.0]
    rs = pool.map(eval_striph, [(x_h, c) for c in CS])
    base = rs[0]
    rows = []
    for c, r in zip(CS, rs):
        o = sum(r[g] / base[g] for g in G7)
        ho = r["fs_0324"] / base["fs_0324"]
        rows.append(dict(c=c, obj=float(o), ho=float(ho), habs=float(r["habs"] / base["habs"])))
        print(f"strib_hip c={c}: obj={o:.4f} ho={ho:.3f} habs={r['habs']/base['habs']:.3f}", flush=True)
    json.dump(rows, open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
