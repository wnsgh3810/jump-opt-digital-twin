"""GOAL22 P4 — 노이즈-바닥 (트윈-온-트윈): 달성가능 한계 정량.

P13e 트윈이 만든 full-replay 궤적을 '가상 로봇'의 진실로 삼고, 실측 노이즈
(tau 0.014 Nm, dq 0.053 rad/s, q 9.4e-5 rad ≈ 16bit 양자화)를 주입한 '가상 측정'으로
동일 창 심판을 돌린다. 모델은 완벽(자기 자신)이므로 결과 = 심판의 환원 불가능한 바닥.
실데이터 오차와 비교해 '모델 결손 vs 물리(노이즈+개방루프 발산) 한계'를 분해.
창 길이 W 스윕으로 발산 성장 곡선도 산출.
"""
import sys, json
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13

SIG_TAU, SIG_DQ, SIG_Q = 0.014, 0.053, 9.4e-5
SEEDS = [0, 1, 2]
OUT = Path(__file__).parent / "p4_noisefloor.json"


def winit():
    PH.winit()
    P12 = P13._M["P12"]
    if P12._G["trials"] is None:
        P12.build_trials()
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


def eval_windows5(P12, model, pp, W=None):
    """rigid 5-dof 창 replay → (acc[q1,q2,dq1,dq2], nw). W로 창 길이 덮어쓰기."""
    mj = P12._G["mujoco"]
    d = mj.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    Wv = W if W is not None else pp["W"]
    acc = np.zeros(4); nw = 0
    for i0 in pp["starts"]:
        t1 = min(t[i0] + Wv, t[-1])
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
            d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"])]
            try:
                mj.mj_step(model, d)
            except Exception:
                ok = False
                break
            ts[k] = tc + dt
            q1a[k] = d.qpos[1]; q2a[k] = d.qpos[2]
            dq1a[k] = d.qvel[1]; dq2a[k] = d.qvel[2]
        if not ok:
            acc += [1, 1, 10, 10]; nw += 1
            continue
        mask = (t >= ts[0]) & (t <= ts[-1])
        if mask.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mask], ts, sim) - real[mask]) ** 2)))
        acc += [r(q1a, pp["q1m"]), r(q2a, pp["q2m"]), r(dq1a, pp["dq1m"]), r(dq2a, pp["dq2m"])]
        nw += 1
    return acc, nw


def twin_td(P12, model, td):
    """P13e full replay → 가상 로봇 '진실' 궤적을 500Hz 실측 포맷으로."""
    sys.path.insert(0, str(REPO / "code/goal19/phase11"))
    import mshoot_fourbar as FB
    log = FB.run_jump_sim_fourbar(model, td)
    if log is None:
        return None
    tr = np.asarray(td["t"])
    mk = (log["t"] >= 0) & (log["t"] <= tr[-1] + 1e-9)
    f = lambda a: np.interp(tr, log["t"][mk], a[mk])
    return dict(t=tr,
                q1=f(-log["q1"] - np.pi / 2), q2=f(-log["q2"]),
                dq1=f(-log["dq1"]), dq2=f(-log["dq2"]),
                tau1_real=np.asarray(td["tau1_real"]), tau2_real=np.asarray(td["tau2_real"]),
                grf_z=f(log["grf_z"]), h_real=float(log["base_z"].max()))


def noisy(td2, seed):
    rng = np.random.default_rng(seed)
    o = dict(td2)
    n = len(td2["t"])
    o["q1"] = td2["q1"] + rng.normal(0, SIG_Q, n)
    o["q2"] = td2["q2"] + rng.normal(0, SIG_Q, n)
    o["dq1"] = td2["dq1"] + rng.normal(0, SIG_DQ, n)
    o["dq2"] = td2["dq2"] + rng.normal(0, SIG_DQ, n)
    o["tau1_real"] = td2["tau1_real"] + rng.normal(0, SIG_TAU, n)
    o["tau2_real"] = td2["tau2_real"] + rng.normal(0, SIG_TAU, n)
    return o


def main():
    P12 = winit()
    FR = P12._G["FR"]
    can = json.load(open(REPO / "code/goal21/fourbar_honest_canonical.json"))
    x32 = np.array(can["x"])
    model, dd = build_model(P12, x32)
    pwg = P12._G["pwg"]; sv = P12._G["sv"]
    mj_s, _ = FR.get_serial_models()

    res = {}
    WS = [0.05, 0.10, 0.20]
    for tr_ in P12._G["trials"]:
        ds, sub, td, isj = tr_["ds"], tr_["sub"], tr_["td"], tr_["isj"]
        if not isj:
            continue
        k1, k2 = P12.OFFKEY.get(ds, (None, None))
        o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
        # (a) 실데이터 오차 (P13e, 공식 창)
        ppo = sv(tr_["pp"], o1, o2)
        r = {}
        for W in WS:
            acc, nw = eval_windows5(P12, model, ppo, W=W)
            r[f"real_W{W}"] = (acc / max(nw, 1)).tolist()
        # (b) 트윈-온-트윈 노이즈 바닥
        td2 = twin_td(P12, model, td)
        if td2 is None:
            print("twin crash", ds, sub, flush=True)
            continue
        for W in WS:
            accs = []
            for sd in SEEDS:
                tdn = noisy(td2, hash((ds, str(sub), sd)) % 2**31)
                ppn = pwg(("p4", ds, str(sub), sd), tdn, mj_s)
                acc, nw = eval_windows5(P12, model, ppn, W=W)
                accs.append(acc / max(nw, 1))
            r[f"floor_W{W}"] = np.mean(accs, axis=0).tolist()
        res[f"{ds}/{sub}"] = r
        print("done", ds, sub, flush=True)

    # ── 데이터셋 요약 ──
    print("\n=== P4 노이즈-바닥 vs 실데이터 오차 (창 W=0.10s, 데이터셋 평균) ===")
    print(f"{'dataset':22s}  {'':6s} {'q1':>7} {'q2':>7} {'dq1':>7} {'dq2':>7}")
    summary = {}
    for ds in ["jump_position_0421", "jump_0424", "jump_0602", "jump_0324"]:
        keys = [k for k in res if k.startswith(ds + "/")]
        if not keys:
            continue
        s = {}
        for W in WS:
            fl = np.mean([res[k][f"floor_W{W}"] for k in keys], axis=0)
            re_ = np.mean([res[k][f"real_W{W}"] for k in keys], axis=0)
            s[f"W{W}"] = dict(floor=fl.tolist(), real=re_.tolist(),
                              pct=(100 * fl / np.maximum(re_, 1e-12)).tolist())
        summary[ds] = s
        fl = s["W0.1"]["floor"]; re_ = s["W0.1"]["real"]; pc = s["W0.1"]["pct"]
        print(f"{ds:22s}  floor  {fl[0]:7.4f} {fl[1]:7.4f} {fl[2]:7.3f} {fl[3]:7.3f}")
        print(f"{'':22s}  real   {re_[0]:7.4f} {re_[1]:7.4f} {re_[2]:7.3f} {re_[3]:7.3f}")
        print(f"{'':22s}  pct    {pc[0]:6.1f}% {pc[1]:6.1f}% {pc[2]:6.1f}% {pc[3]:6.1f}%")
    json.dump(dict(sig=dict(tau=SIG_TAU, dq=SIG_DQ, q=SIG_Q), per_trial=res, summary=summary),
              open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)


if __name__ == "__main__":
    main()
