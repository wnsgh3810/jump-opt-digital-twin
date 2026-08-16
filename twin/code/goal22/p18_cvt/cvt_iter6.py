# -*- coding: utf-8 -*-
"""P18b iter6 — 정적 유지 토크 감사: 평행사변형 세션 시작 정지 구간에서
측정 무릎 토크 vs 모델 hold (spring crank/calf/none). 스프링 실재의 데이터 판별."""
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
A = np.array(C16["x"][32:36])
REF = float(X37[36])


def settle_hold(model, q1_0, q2_0):
    """settle PD 0.5s 후 유지 명령토크 (crank). 반환 (hold1, hold2)."""
    mj = J._P["mj"]; S = J._P["S"]
    d = mj.MjData(model)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    d.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, d)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    bz0 = 1.0 - float(d.geom_xpos[fg][2]) + S.FOOT_RADIUS
    d.qpos[:] = [bz0, sq1, sq2, -sq2, sq2]; d.qvel[:] = 0
    mj.mj_forward(model, d)
    dt = model.opt.timestep
    h1 = h2 = 0.0
    for k in range(int(0.5 / dt)):
        q1c = -d.qpos[1] - np.pi / 2; q2c = -d.qpos[2]
        v1c = -d.qvel[1]; v2c = -d.qvel[2]
        c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
        c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
        h1 = float(J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        h2 = float(J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        d.ctrl[:] = [-h1, -h2]
        mj.mj_step(model, d)
    return h1, h2


def main():
    J.winit()
    P12 = J._P["P12"]
    models = {sp: build_flip_variant(X37[:32], REF, sp)[0]
              for sp in ("crank", "calf", "none")}
    print(f"{'trial':26s} {'q2_0':>6} {'meas':>6} {'crank':>7} {'calf':>7} {'none':>7}")
    rows = []
    for tr in P12._G["trials"]:
        td = tr["td"]; ds = tr["ds"]
        q1_0 = float(np.mean(np.asarray(td["q1"])[:25]))
        q2_0 = float(np.mean(np.asarray(td["q2"])[:25]))
        dq2_0 = float(np.mean(np.abs(np.asarray(td["dq2"])[:25])))
        if dq2_0 > 0.15:      # 시작이 정지가 아닌 trial 제외
            continue
        meas = float(np.mean(J.ahat(A, tr["raw2"][:25], tr["v2"][:25])))
        hs = {}
        for sp in ("crank", "calf", "none"):
            hs[sp] = settle_hold(models[sp], q1_0, q2_0)[1]
        nm = f"{ds}/{tr.get('sub', tr.get('name', '?'))}"
        print(f"{nm:26s} {q2_0:6.2f} {meas:+6.2f} {hs['crank']:+7.2f} "
              f"{hs['calf']:+7.2f} {hs['none']:+7.2f}", flush=True)
        rows.append(dict(nm=nm, ds=ds, q2_0=q2_0, meas=meas, **hs))
    # 세션별 |오차| 평균
    print()
    for ds in sorted(set(r["ds"] for r in rows)):
        rs = [r for r in rows if r["ds"] == ds]
        e = lambda sp: np.mean([abs(r[sp] - r["meas"]) for r in rs])
        print(f"[{ds:12s}] n={len(rs)} |err| crank {e('crank'):.2f} "
              f"calf {e('calf'):.2f} none {e('none'):.2f}", flush=True)
    json.dump(rows, open(HERE / "p18b_iter6_static.json", "w"), indent=1)
    print("saved p18b_iter6_static.json", flush=True)


if __name__ == "__main__":
    main()
