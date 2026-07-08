# -*- coding: utf-8 -*-
"""P16c — 레일 stick-slip (정지마찰 >> 운동마찰) 시험.

배경: P5 발견 — crouch 정지 시 레일이 hip 토크 ~3Nm급을 대신 부담 (정적 부정정).
P8의 frictionloss 스윕은 '정지=운동' 모델이라 표현 자체가 불가능했고 기각됨.
모델: F_rail = −tanh(v/v_eps)·F_s·exp(−|v|/v_str)  — 정지 근방에서만 크고 운동 시 소멸.
      (v_eps=0.003 m/s 정규화, v_str = 소멸 속도 스케일)
시험: 모델 = P14 고정, 폐루프 재현(라벨 게인)에 base_z 외력으로 주입.
표적: early(홀드) 구간의 hip τ·q1 — P5의 ~3Nm 불일치가 줄어드는가. push/h 부작용 감시.
"""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
import p14_judge as J
from g22_p10_pdlaw import SETS, label_gains
from g22_p10_cl import load_trial_xlsx, SD
from g22_p13_phases import phases

OUT = HERE / "p16c_result.json"
CAND = json.load(open(HERE.parent / "p14_ahat/fourbar_p14_candidate.json"))
X = np.array(CAND["x"]); A = np.array(CAND["A_HAT"])
T_SETTLE, T_AFTER = 0.4, 0.6
V_EPS = 0.003


def rail_force(v, Fs, vstr):
    return -np.tanh(v / V_EPS) * Fs * np.exp(-abs(v) / vstr)


def run_cl_rail(model, dd, ds, d, gains, ffk, dqdes, Fs, vstr):
    mj = J._P["mj"]; S = J._P["S"]
    kp1, kd1, kp2, kd2 = gains
    k1, k2 = J.OFFK.get(ds, (None, None))
    o1 = dd.get(k1, 0.0) if k1 else 0.0; o2 = dd.get(k2, 0.0) if k2 else 0.0
    t = d["t"]
    qd1 = d["qd1"] + o1; qd2 = d["qd2"] + o2
    dqd1 = d["dqd1"] if dqdes else np.zeros_like(t)
    dqd2 = d["dqd2"] if dqdes else np.zeros_like(t)
    md = mj.MjData(model)
    sq1, sq2 = -qd1[0] - np.pi / 2, -qd2[0]
    md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    bz0 = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qpos[:] = [bz0, sq1, sq2, -sq2, sq2]; md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((T_SETTLE + t[-1] + T_AFTER) / dt)
    tl = np.arange(N) * dt - T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz"]}
    for k in range(N):
        tc = tl[k]
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        if tc < 0:
            c1 = S.SETTLE_KP * (qd1[0] - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (qd2[0] - q2c) - S.SETTLE_KD * v2c
        else:
            tm = min(tc, t[-1])
            c1 = kp1 * (np.interp(tm, t, qd1) - q1c) + kd1 * (np.interp(tm, t, dqd1) - v1c)
            c2 = kp2 * (np.interp(tm, t, qd2) - q2c) + kd2 * (np.interp(tm, t, dqd2) - v2c)
            if ffk:
                c2 += np.interp(tm, t, d["tdes2"])
        s1 = float(J.ahat(A, np.array([float(c1)]), np.array([v1c]))[0])
        s2 = float(J.ahat(A, np.array([float(c2)]), np.array([v2c]))[0])
        md.ctrl[:] = [-s1, -s2]
        md.qfrc_applied[0] = rail_force(float(md.qvel[0]), Fs, vstr) if Fs > 0 else 0.0
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        L["q1"][k] = -md.qpos[1] - np.pi / 2; L["q2"][k] = -md.qpos[2]
        L["dq1"][k] = -md.qvel[1]; L["dq2"][k] = -md.qvel[2]
        L["sh1"][k] = s1; L["sh2"][k] = s2; L["bz"][k] = md.qpos[0]
    L["t"] = tl; L["o"] = (o1, o2)
    return L


def seg_rmse(L, d, on, toff):
    t = d["t"]
    g = lambda k: np.interp(t, L["t"], L[k])
    o1, o2 = L["o"]
    tp1 = np.interp(t - SD, t, d["tau1_p14"])
    out = {}
    for sn, sl in [("early", slice(0, on)), ("push", slice(on, min(toff, len(t))))]:
        if sl.stop - sl.start < 5:
            continue
        r = lambda a, b: float(np.sqrt(np.mean((a[sl] - b[sl]) ** 2)))
        out[sn] = dict(tau1=r(g("sh1"), tp1),
                       q1=r(g("q1") - o1, np.asarray(d["q1"])),
                       q2=r(g("q2") - o2, np.asarray(d["q2"])),
                       dq2=r(g("dq2"), np.asarray(d["dq2"])))
    out["h"] = float(L["bz"].max())
    return out


def eval_cfg(args):
    Fs, vstr = args
    if not J._P:
        J.winit()
    model, dd = J.build_model(X[:32])
    per = {}
    for ds, (root, subs) in SETS.items():
        for sub in subs:
            d = load_trial_xlsx(ds, root, sub)
            d["tau1_p14"] = J.ahat(A, d["traw1"], d["dq1"])
            on, toff = phases(d)
            L = run_cl_rail(model, dd, ds, d, label_gains(ds, sub),
                            ds == "jump_0324", ds in ("jump_0424", "jump_0602"), Fs, vstr)
            if L is None:
                continue
            per.setdefault(ds, []).append(seg_rmse(L, d, on, toff))
    agg = {}
    for ds, v in per.items():
        agg[ds] = dict(
            e_tau1=float(np.mean([x["early"]["tau1"] for x in v if "early" in x])) if any("early" in x for x in v) else np.nan,
            e_q1=float(np.mean([x["early"]["q1"] for x in v if "early" in x])) if any("early" in x for x in v) else np.nan,
            p_tau1=float(np.mean([x["push"]["tau1"] for x in v])),
            p_q2=float(np.mean([x["push"]["q2"] for x in v])),
            p_dq2=float(np.mean([x["push"]["dq2"] for x in v])),
            h=float(np.mean([x["h"] for x in v])))
    return dict(Fs=Fs, vstr=vstr, agg=agg)


def main():
    import multiprocessing as mp
    J.winit()
    cfgs = [(0.0, 0.02)] + [(Fs, vstr) for Fs in [3, 6, 12, 20] for vstr in [0.01, 0.04]]
    pool = mp.Pool(9, initializer=J.winit)
    rs = pool.map(eval_cfg, cfgs)
    base = rs[0]["agg"]
    print("=== early 구간 hip τ RMSE (기준 Fs=0 -> 각 설정) / push 부작용 감시 ===", flush=True)
    for r in rs:
        line = f"Fs={r['Fs']:4.0f} vstr={r['vstr']:.2f}  "
        for ds in ["jump_0421" if False else "jump_position_0421", "jump_0424", "jump_0602"]:
            a, b = base.get(ds, {}), r["agg"].get(ds, {})
            if not b:
                continue
            line += f"[{ds.split('_')[-1]}] eτ1 {a['e_tau1']:.2f}->{b['e_tau1']:.2f} " \
                    f"pτ1 {a['p_tau1']:.2f}->{b['p_tau1']:.2f} h {a['h']:.3f}->{b['h']:.3f}  "
        print(line, flush=True)
    json.dump(rs, open(OUT, "w"), indent=1, default=float)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
