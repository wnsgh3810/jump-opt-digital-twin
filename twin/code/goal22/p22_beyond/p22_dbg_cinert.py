# -*- coding: utf-8 -*-
"""디버그6: cinert/ximat 추적 — 런타임이 body_iquat 변경을 소비하는가."""
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
import p22_base_params as BP
from p22_base_params import RModel

AD.ensure_init()
import p19_judge as P
import p14_judge as J
import mujoco as mj
import cvt_core as CC

cand = AD.load_candidate(REPO / "code/goal22/p19_jump/fourbar_p19_candidate.json")
x32, v, sp, qoff = AD._p19_args(cand)
BP._R.update(mj=mj, J=J, CC=CC)
rm = RModel(lambda: P.build_flip(x32, float(v[1]), sp), "par")
model, d = rm.model, rm.d
K = 2
b = rm.bid[K]


def fw():
    d.qpos[rm.iq] = [1.0, -1.5, -1.8, 1.8, -1.8]
    d.qvel[:] = 0
    mj.mj_forward(model, d)
    Mf = np.zeros((model.nv, model.nv))
    mj.mj_fullM(model, Mf, d.qM)
    return Mf.copy(), d.cinert[b].copy(), d.ximat[b].copy()


M0, ci0, xi0 = fw()
print("pristine cinert[crank] =", ci0)
print("pristine ximat[crank]  =", xi0)

# 손수 설정: swap-quat + (a, a, b') — set_body_pi가 만든 것과 동일 조합
a_, bp_ = 0.000628, 0.000928
model.body_inertia[b] = [a_, a_, bp_]
q = np.zeros(4)
Rsw = np.array([[-1., 0., 0.], [0., 0., 1.], [0., 1., 0.]])
mj.mju_mat2Quat(q, np.ascontiguousarray(Rsw.flatten()))
model.body_iquat[b] = q
print("hand-set quat:", q)
M1, ci1, xi1 = fw()
print("ΔM max =", np.max(np.abs(M1 - M0)))
print("Δcinert =", ci1 - ci0)
print("Δximat  =", xi1 - xi0)

# 대조: identity quat + (a, b', a) — 직접 yy에 δ
model.body_inertia[b] = [a_, bp_, a_]
model.body_iquat[b] = [1., 0., 0., 0.]
M2, ci2, _ = fw()
print("직접 yy: ΔM max =", np.max(np.abs(M2 - M0)), " Δcinert =", ci2 - ci0)

# 복원
model.body_inertia[b] = [a_, a_, a_]
model.body_iquat[b] = [1., 0., 0., 0.]
