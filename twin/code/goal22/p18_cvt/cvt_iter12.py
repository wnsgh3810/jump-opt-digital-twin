# -*- coding: utf-8 -*-
"""P18b iter12 — 해석 판별: 데이터 오프셋(H* 센서) vs 플랜트 편향 토크(H_load 프리로드).
Mode A는 두 해석이 동일; CL만 구분. 플랜트 편향판: sim 무릎에 상수 토크 β 추가
(명령 로그는 PD만), 기준 토크는 무편(원본 a_hat)."""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
sys.path.insert(0, str(HERE.parent / "p16_structure"))
import p14_judge as J
from cvt_iter5 import build_flip_variant

C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X37 = np.array(C16["x"])
SD = -0.0015
W = json.load(open(HERE / "p18b_iter11.json"))["x"]
STIFF, REF = W[0], W[1]
BT2 = {"jump_0602": W[2], "jump_position_0421": W[3], "s2s": W[4],
       "jump_0424": W[5], "jump_0324": W[6]}
BT1 = {"s2s": W[7], "jump_position_0421": W[8]}


def ofor(ds, table):
    for k, v in table.items():
        if ds.startswith(k):
            return v
    return 0.0


def run_cl_bias(model, dd, tr, A, b1, b2):
    """p14_judge.run_cl 복제 + 플랜트 편향 토크 (로그는 PD 명령만)."""
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
    N = int((J.T_SETTLE + t[-1] + J.T_AFTER) / dt)
    tl = np.arange(N) * dt - J.T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2"]}
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
        s1 = float(J.ahat(A, np.array([float(c1)]), np.array([v1c]))[0])
        s2 = float(J.ahat(A, np.array([float(c2)]), np.array([v2c]))[0])
        md.ctrl[:] = [-(s1 - b1), -(s2 - b2)]     # 플랜트 결핍 = sim에서 빼기
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        L["q1"][k] = -md.qpos[1] - np.pi / 2; L["q2"][k] = -md.qpos[2]
        L["dq1"][k] = -md.qvel[1]; L["dq2"][k] = -md.qvel[2]
        L["sh1"][k] = s1; L["sh2"][k] = s2
    L["t"] = tl; L["o"] = (o1, o2)
    return L


def eval_cl_bias(x32, ref, sp, sign):
    A = np.array(X37[32:36])
    model, _ = build_flip_variant(x32, ref, sp)
    dd = dict(zip(J._P["FR"].NAMES, np.asarray(x32)[:26]))
    fit_s, ho_s = [], []
    for tr in J._P["cl"]:
        b1 = sign * ofor(tr["ds"], BT1); b2 = sign * ofor(tr["ds"], BT2)
        L = run_cl_bias(model, dd, tr, A, b1, b2)
        if L is None:
            return 99.0, 99.0
        s = J.cl_trial_score(L, tr, A)   # 기준 무편 (원본)
        (ho_s if tr["heldout"] else fit_s).append(s)
    return float(np.mean(fit_s)), float(np.mean(ho_s))


def main():
    J.winit()
    x32 = np.array(X37[:32]); x32[11] = max(STIFF, 1e-6)
    c0, cg0 = 0.8943, 1.0271
    for nm, sign in [("plant-bias(-)", +1), ("plant-bias(+)", -1)]:
        c, cg = eval_cl_bias(x32, REF, "calf", sign)
        print(f"[CL {nm}] C={c:.4f}({c/c0:.2f}) Cg={cg:.4f}({cg/cg0:.2f})", flush=True)
    # 참고: 편향 없는 W-모델 CL (스프링만 약화된 모델, 기준 무편)
    c, cg = eval_cl_bias(x32, REF, "calf", 0)
    print(f"[CL no-bias]   C={c:.4f}({c/c0:.2f}) Cg={cg:.4f}({cg/cg0:.2f})", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
