"""P15 시험지 — Mode A로만 학습한 (모델 + a_hat5)를 미학습 폐루프 PD 재현에 투입.
비교 기준: P13h+paper의 v5 label 런 (p10_cl.json). 상태(q/dq/h)는 직접 비교,
τ는 참조 변환이 달라 참고용. s2s 상충 해소 여부는 fit 로그의 w_s2s 비로 확인."""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
import p14_judge as J
from p15_fit import ahat5

SD = J.SD
T_SETTLE, T_AFTER = 0.4, 0.6


def run_cl5(model, dd, tr, A):
    mj = J._P["mj"]; S = J._P["S"]
    d = tr["d"]; t = d["t"]
    kp1, kd1, kp2, kd2 = tr["gains"]
    k1, k2 = J.OFFK.get(tr["ds"], (None, None))
    o1 = dd.get(k1, 0.0) if k1 else 0.0; o2 = dd.get(k2, 0.0) if k2 else 0.0
    qd1 = d["qd1"] + o1; qd2 = d["qd2"] + o2
    dqd1 = d["dqd1"] if tr["dqdes"] else np.zeros_like(t)
    dqd2 = d["dqd2"] if tr["dqdes"] else np.zeros_like(t)
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
            if tr["ffk"]:
                c2 += np.interp(tm, t, d["tdes2"])
        s1 = float(ahat5(A, np.array([float(c1)]), np.array([v1c]))[0])
        s2 = float(ahat5(A, np.array([float(c2)]), np.array([v2c]))[0])
        md.ctrl[:] = [-s1, -s2]
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


def main():
    J.winit()
    cand = json.load(open(HERE / "fourbar_p15_candidate.json"))
    x = np.array(cand["x"])
    A = x[32:37]
    model, dd = J.build_model(x[:32])
    old = json.load(open(HERE.parent / "p10_cl.json"))
    print("=== 미학습 시험지: 폐루프 PD 재현 (P13h+paper -> P15+A5) ===", flush=True)
    print(f"{'dataset':22s} {'q2':>13s} {'dq2':>13s} {'dq1':>13s} {'h_sim':>13s} {'h_real':>7s}",
          flush=True)
    agg = {}
    for tr in J._P["cl"]:
        L = run_cl5(model, dd, tr, A)
        if L is None:
            print(tr["ds"], tr["sub"], "CRASH", flush=True)
            continue
        d = tr["d"]; t = d["t"]
        g = lambda k: np.interp(t, L["t"], L[k])
        o1, o2 = L["o"]
        r = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
        o = old[f"{tr['ds']}/{tr['sub']}"]["label"]
        agg.setdefault(tr["ds"], []).append(
            (r(g("q2") - o2, d["q2"]), o["q2"],
             r(g("dq2"), d["dq2"]), o["dq2"],
             r(g("dq1"), d["dq1"]), o["dq1"],
             float(L["bz"].max()), o["h"], o.get("h_real", np.nan)))
    res = {}
    for ds, v in agg.items():
        v = np.array(v, float)
        m = v.mean(axis=0)
        res[ds] = m.tolist()
        print(f"{ds:22s} {m[1]:.3f}->{m[0]:.3f}  {m[3]:.2f}->{m[2]:.2f}  "
              f"{m[5]:.2f}->{m[4]:.2f}  {m[7]:.3f}->{m[6]:.3f}  {np.nanmean(v[:,8]):.3f}",
              flush=True)
    json.dump(res, open(HERE / "p15_test.json", "w"), indent=1)
    print("saved p15_test.json  (각 칸: paper기준 -> P15)", flush=True)


if __name__ == "__main__":
    main()
