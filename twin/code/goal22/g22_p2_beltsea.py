"""GOAL22 P2 — 벨트 직렬 탄성(SEA) 모델: dq 평활의 물리 후보.

P1 결론(로그 dq=raw, 필터 없음) → 실물 dq2가 sim(정직물리)보다 평활한 것은 물리.
실물 엔코더는 모터측(벨트 앞): 접촉 충격이 벨트 스프링에서 여과되어 모터측 dq가 매끈.
구현: thigh에 rotor 힌지(armature=arm_knee, 모터측 FV/FC) 추가, rotor↔crank fixed
tendon(k_belt, b_belt), 액추에이터/엔코더=rotor. 창 IC는 준정적 신장 보정
(q_crank = q_rotor - tau0/k) + FK base_z 재계산. k→大 극한에서 P13e 재현(sanity).
"""
import sys, json, time, re
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13

_L = {}
OUT = Path(__file__).parent / "p2_beltsea.json"


def winit():
    PH.winit()
    P12 = P13._M["P12"]
    if P12._G["trials"] is None:
        P12.build_trials()
    _L["P12"] = P12
    _L["mj"] = P12._G["mujoco"]
    _L["S"] = P12._G["S"]
    _L["FR"] = P12._G["FR"]
    _L["sv"] = P12._G["sv"]
    import g21_fourbar_flip as FL
    _L["FL"] = FL


def build_sea_xml(x32, k_belt, b_belt):
    S = _L["S"]; FR = _L["FR"]; FL = _L["FL"]
    x32 = np.asarray(x32, float)
    dd = dict(zip(FR.NAMES, x32[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = FL.build_xml_fourbar_flip(dd["arm_knee"], sc)
    xml = P13.apply_linkage_mods(xml, dict(zip(P13.N6, x32[26:32])))
    # ── SEA patch ──
    rotor = (f'<body name="knee_rotor" pos="0 0 0">'
             f'<joint name="rotor" type="hinge" armature="{dd["arm_knee"]:.8f}"'
             f' damping="{dd["fv_knee"]:.6f}" frictionloss="{dd["fc_knee"]:.6f}"/>'
             f'<inertial pos="0 0 0" mass="0.001" diaginertia="1e-07 1e-07 1e-07"/></body>')
    crank_joint = (f'<joint name="knee_motor" type="hinge" armature="0"'
                   f' damping="0.0005" frictionloss="0"'
                   f' stiffness="{dd["stiff_knee"]:.6f}" springref="0.00000"/>')
    xml2 = re.sub(r'<joint name="knee_motor"[^>]*/>', crank_joint, xml, count=1)
    xml2 = xml2.replace('<body name="crank" pos="0 0 0">',
                        rotor + '\n      <body name="crank" pos="0 0 0">', 1)
    tendon = (f'<tendon><fixed name="belt" stiffness="{k_belt:.4f}" damping="{b_belt:.6f}" springlength="0">'
              f'<joint joint="rotor" coef="1"/><joint joint="knee_motor" coef="-1"/>'
              f'</fixed></tendon>')
    xml2 = xml2.replace('<actuator>', tendon + '\n<actuator>', 1)
    xml2 = xml2.replace('<motor name="knee_motor" joint="knee_motor" gear="1"/>',
                        '<motor name="knee_motor" joint="rotor" gear="1"/>', 1)
    assert 'joint="rotor" gear' in xml2 and "belt" in xml2
    return xml2, dd


def jmap(model):
    mj = _L["mj"]
    qa, da = {}, {}
    for n in ["base_z", "hip", "rotor", "knee_motor", "cpin", "knee"]:
        j = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, n)
        qa[n] = model.jnt_qposadr[j]; da[n] = model.jnt_dofadr[j]
    return qa, da


def bz_fk(model, d, q1, q2c):
    """벨트 신장 보정된 calf각으로 foot-FK base 높이."""
    mj = _L["mj"]; S = _L["S"]
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    qa, _ = _L["adr"]
    d.qpos[:] = 0
    d.qpos[qa["base_z"]] = 1.0; d.qpos[qa["hip"]] = q1
    d.qpos[qa["rotor"]] = q2c; d.qpos[qa["knee_motor"]] = q2c
    d.qpos[qa["cpin"]] = -q2c; d.qpos[qa["knee"]] = q2c
    mj.mj_forward(model, d)
    return 1.0 - float(d.geom_xpos[fg][2]) + S.FOOT_RADIUS


def init_state(d, qa, da, pp, i0, k_belt, model, dfk):
    """창 IC: rotor=측정 q2, crank=q2 - tau0/k (준정적), base_z는 보정 FK."""
    q1 = pp["q1m"][i0]; q2 = pp["q2m"][i0]
    dq1 = pp["dq1m"][i0]; dq2 = pp["dq2m"][i0]
    tau0 = float(np.interp(pp["t"][i0], pp["t"], pp["tau_k"]))
    q2c = q2 - tau0 / k_belt
    bz = bz_fk(model, dfk, q1, q2c)
    d.qpos[:] = 0; d.qvel[:] = 0
    d.qpos[qa["base_z"]] = bz; d.qpos[qa["hip"]] = q1
    d.qpos[qa["rotor"]] = q2; d.qpos[qa["knee_motor"]] = q2c
    d.qpos[qa["cpin"]] = -q2c; d.qpos[qa["knee"]] = q2c
    d.qvel[da["base_z"]] = pp["vbz"][i0]; d.qvel[da["hip"]] = dq1
    d.qvel[da["rotor"]] = dq2; d.qvel[da["knee_motor"]] = dq2
    d.qvel[da["cpin"]] = -dq2; d.qvel[da["knee"]] = dq2


def eval_windows_sea(model, pp, k_belt, dfk):
    mj = _L["mj"]; MS = _L["P12"]._G["MS"]
    qa, da = _L["adr"]
    d = mj.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    iq1, iq2 = qa["hip"], qa["rotor"]; iv1, iv2 = da["hip"], da["rotor"]
    sc = 0.0; acc = np.zeros(4); nw = 0
    for i0 in pp["starts"]:
        t1 = min(t[i0] + pp["W"], t[-1])
        init_state(d, qa, da, pp, i0, k_belt, model, dfk)
        mj.mj_forward(model, d)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
        dq1a = np.empty(nst); dq2a = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t[i0] + k * dt
            d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"])]
            try:
                mj.mj_step(model, d)
            except Exception:
                ok = False
                break
            ts[k] = tc + dt
            q1a[k] = d.qpos[iq1]; q2a[k] = d.qpos[iq2]
            dq1a[k] = d.qvel[iv1]; dq2a[k] = d.qvel[iv2]
        nw += 1
        if not ok or not np.isfinite(q2a).all():
            sc += MS.W_Q * 2.0 + MS.W_DQ * 20.0
            acc += [1, 1, 10, 10]
            continue
        mask = (t >= ts[0]) & (t <= ts[-1])
        if mask.sum() < 3:
            nw -= 1
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mask], ts, sim) - real[mask]) ** 2)))
        v = [r(q1a, pp["q1m"]), r(q2a, pp["q2m"]), r(dq1a, pp["dq1m"]), r(dq2a, pp["dq2m"])]
        sc += MS.W_Q * (v[0] + v[1]) + MS.W_DQ * (v[2] + v[3])
        acc += v
    return sc, acc, nw


def fs_metric_sea(model, pp, td, k_belt, dfk):
    mj = _L["mj"]; MS = _L["P12"]._G["MS"]; P12 = _L["P12"]
    qa, da = _L["adr"]
    t = pp["t"]
    rng = P12.stance_range(td, t)
    if rng is None:
        return 0.0, np.nan
    i0, i1 = rng
    if t[i1] - t[i0] < 0.1:
        return 0.0, np.nan
    d = mj.MjData(model)
    init_state(d, qa, da, pp, i0, k_belt, model, dfk)
    mj.mj_forward(model, d)
    dt = model.opt.timestep
    nst = int(round((t[i1] - t[i0]) / dt))
    out = np.empty((nst, 5))
    for k in range(nst):
        tc = t[i0] + k * dt
        d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"])]
        try:
            mj.mj_step(model, d)
        except Exception:
            return MS.W_Q * 2.0 + MS.W_DQ * 20.0, np.nan
        out[k] = [tc + dt, d.qpos[qa["hip"]], d.qpos[qa["rotor"]],
                  d.qvel[da["hip"]], d.qvel[da["rotor"]]]
    if not np.all(np.isfinite(out)):
        return MS.W_Q * 2.0 + MS.W_DQ * 20.0, np.nan
    h_pred = float(d.qpos[qa["base_z"]]) + max(float(d.qvel[da["base_z"]]), 0.0) ** 2 / (2 * 9.81)
    msk = (t >= out[0, 0]) & (t <= out[-1, 0])
    if msk.sum() < 3:
        return 0.0, h_pred
    r = lambda c, real: float(np.sqrt(np.mean((np.interp(t[msk], out[:, 0], out[:, c]) - real[msk]) ** 2)))
    sc = (MS.W_Q * (r(1, pp["q1m"]) + r(2, pp["q2m"]))
          + MS.W_DQ * (r(3, pp["dq1m"]) + r(4, pp["dq2m"])))
    return sc, h_pred


def eval_sea(args):
    """P12 group dict과 동일 키(w_*, fs_*, habs) + m_<ds>=[q1,q2,dq1,dq2] 창 평균."""
    try:
        x32, k_belt, b_belt = args
        if not _L:
            winit()
        mj = _L["mj"]; P12 = _L["P12"]
        xml, dd = build_sea_xml(x32, k_belt, b_belt)
        model = mj.MjModel.from_xml_string(xml)
        _L["adr"] = jmap(model)
        dfk = mj.MjData(model)
        res = {"habs": 0.0}
        cnt = {}
        for tr in P12._G["trials"]:
            ds = tr["ds"]
            k1, k2 = P12.OFFKEY.get(ds, (None, None))
            o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
            ppo = _L["sv"](tr["pp"], o1, o2)
            sc, acc, nw = eval_windows_sea(model, ppo, k_belt, dfk)
            g = P12.GKEY[ds]
            res[g] = res.get(g, 0.0) + sc
            mkey = "m_" + ds
            res[mkey] = np.asarray(res.get(mkey, np.zeros(4))) + acc
            cnt[mkey] = cnt.get(mkey, 0) + nw
            if ds in ("jump_0424", "jump_0602", "jump_0324"):
                fsk = "fs_" + ds.split("_")[-1]
                sc2, h_pred = fs_metric_sea(model, ppo, tr["td"], k_belt, dfk)
                res[fsk] = res.get(fsk, 0.0) + sc2
                if ds != "jump_0324" and np.isfinite(h_pred) and np.isfinite(tr["h_real"]):
                    res["habs"] += abs(h_pred - tr["h_real"])
        for mk, n in cnt.items():
            res[mk] = (np.asarray(res[mk]) / max(n, 1)).tolist()
        return res
    except Exception as e:
        import traceback
        return {"error": f"{e}", "tb": traceback.format_exc()[-600:]}


def main():
    import multiprocessing as mp
    winit()
    P12 = _L["P12"]
    G7 = P12.OBJ_GROUPS
    can = json.load(open(REPO / "code/goal21/fourbar_honest_canonical.json"))
    x32 = np.array(can["x"])
    base = PH.eval32(x32)                 # 공식 P13e 기준 (rigid, 5-dof)
    print("BASE(P13e rigid):", " ".join(f"{k}:{v:.1f}" for k, v in base.items()
                                        if not k.startswith("m_")), flush=True)

    # Stage 0 — sanity: k 매우 큼 → P13e 재현 확인
    r0 = eval_sea((x32, 2.0e4, 0.5))
    if "error" in r0:
        print("SANITY CRASH:", r0["error"], "\n", r0.get("tb", ""), flush=True)
        return
    o0 = sum(r0[g] / base[g] for g in G7)
    print(f"STAGE0 k=2e4 sanity: obj={o0:.4f} (1.0 근처 기대) "
          f"ho={r0['fs_0324']/base['fs_0324']:.3f}", flush=True)
    for ds in ["jump_position_0421", "jump_0424", "jump_0602", "jump_0324"]:
        m = r0.get("m_" + ds)
        if m:
            print(f"   {ds:20s} q1={m[0]:.4f} q2={m[1]:.4f} dq1={m[2]:.3f} dq2={m[3]:.3f}", flush=True)

    # Stage A — (k_belt, b_belt) 그리드 스캔
    KS = [50, 100, 200, 400, 800, 1600, 3200, 6400]
    BS = [0.02, 0.1, 0.5, 2.0]
    grid = [(k, b) for k in KS for b in BS]
    pool = mp.Pool(10, initializer=winit)
    t0 = time.time()
    rs = pool.map(eval_sea, [(x32, k, b) for k, b in grid])
    print(f"\nSTAGE A grid {len(grid)} cells [{(time.time()-t0)/60:.1f}min]", flush=True)
    print(f"{'k':>6} {'b':>5}  {'obj':>7} {'ho':>6} {'habs':>6}   dq2(0421/0424/0602/0324)", flush=True)
    rows = []
    for (k, b), r in zip(grid, rs):
        if r is None or "error" in r:
            print(f"{k:6.0f} {b:5.2f}  CRASH {(r or {}).get('error','')}", flush=True)
            continue
        o = sum(r[g] / base[g] for g in G7)
        ho = r["fs_0324"] / base["fs_0324"]
        dq2s = [r["m_" + ds][3] for ds in
                ["jump_position_0421", "jump_0424", "jump_0602", "jump_0324"]]
        rows.append(dict(k=k, b=b, obj=float(o), ho=float(ho),
                         habs=float(r["habs"] / base["habs"]),
                         dq2=[float(v) for v in dq2s],
                         per={kk: (float(v) if not isinstance(v, list) else v)
                              for kk, v in r.items()}))
        print(f"{k:6.0f} {b:5.2f}  {o:7.4f} {ho:6.3f} {r['habs']/base['habs']:6.3f}   "
              + "/".join(f"{v:.2f}" for v in dq2s), flush=True)
    json.dump(dict(base={k: (float(v) if not isinstance(v, list) else v) for k, v in base.items()},
                   sanity={k: (float(v) if not isinstance(v, list) else v) for k, v in r0.items()},
                   grid=rows), open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
