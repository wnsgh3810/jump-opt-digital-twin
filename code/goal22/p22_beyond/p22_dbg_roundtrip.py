# -*- coding: utf-8 -*-
"""디버그: get_pi/set_pi 라운드트립이 pristine 모델을 정확히 재현하는가."""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "code" / "bench"))
import safe
safe.utf8_console()
import p19_adapter as AD
sys.path.insert(0, str(HERE))
from p22_base_params import RModel, body_pi, set_body_pi, BODIES, JOINTS
import p22_base_params as BP

AD.ensure_init()
import p19_judge as P
import p14_judge as J
import mujoco as mj
import cvt_core as CC

cand = AD.load_candidate(REPO / "code/goal22/p19_jump/fourbar_p19_candidate.json")
x32, v, sp, qoff = AD._p19_args(cand)
ref = float(v[1])
BP._R.update(mj=mj, J=J, CC=CC)

rm = RModel(lambda: P.build_flip(x32, ref, sp), "par")
model, d = rm.model, rm.d

# pristine 필드 스냅샷
snap = {f: getattr(model, f).copy() for f in
        ["body_mass", "body_ipos", "body_iquat", "body_inertia"]}

rng = np.random.default_rng(1)
states = [(rng.uniform(0.5, 1.5), rng.uniform(-3.2, -0.5), rng.uniform(-2.7, -0.15),
           rng.uniform(-np.pi, np.pi), rng.uniform(-2.7, -0.15),
           rng.uniform(-20, 20, 5), rng.uniform(-500, 500, 5)) for _ in range(20)]


def tau_all():
    out = np.empty((20, 5))
    for i, (bz, q1, qc, qp, qk, v5, a5) in enumerate(states):
        d.qpos[rm.iq] = [bz, q1, qc, qp, qk]
        d.qvel[rm.iv] = v5
        d.qacc[rm.iv] = a5
        mj.mj_inverse(model, d)
        out[i] = d.qfrc_inverse[rm.iv]
    return out


tau_pris = tau_all()
print("bodies:", BODIES)
for k, b in enumerate(rm.bid):
    name = BODIES[k]
    pi_b = body_pi(model, b, mj)
    # 이 body만 라운드트립
    set_body_pi(model, b, pi_b, mj)
    mj.mj_setConst(model, rm._scr)
    t2 = tau_all()
    err = np.max(np.abs(t2 - tau_pris)) / max(np.max(np.abs(tau_pris)), 1e-12)
    print(f"[{name}] roundtrip rel err = {err:.2e}")
    print(f"   mass {snap['body_mass'][b]:.6f} -> {model.body_mass[b]:.6f}")
    print(f"   ipos {snap['body_ipos'][b]} -> {model.body_ipos[b]}")
    print(f"   iner {snap['body_inertia'][b]} -> {model.body_inertia[b]}")
    print(f"   iqua {snap['body_iquat'][b]} -> {model.body_iquat[b]}")
    # 복원
    for f in snap:
        getattr(model, f)[:] = snap[f]
    mj.mj_setConst(model, rm._scr)
t3 = tau_all()
print("복원 후 rel err =", np.max(np.abs(t3 - tau_pris)) / np.max(np.abs(tau_pris)))
