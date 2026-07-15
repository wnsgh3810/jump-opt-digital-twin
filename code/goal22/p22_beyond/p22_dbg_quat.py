# -*- coding: utf-8 -*-
"""디버그5: iquat 규약 확정 — set_body_pi(Iyy+δ) vs body_inertia 직접 수정."""
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
from p22_base_params import RModel, set_body_pi

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


def M22():
    d.qpos[rm.iq] = [1.0, -1.5, -1.8, 1.8, -1.8]
    d.qvel[:] = 0
    mj.mj_forward(model, d)
    Mf = np.zeros((model.nv, model.nv))
    mj.mj_fullM(model, Mf, d.qM)
    return Mf


M0 = M22()
DL = 3e-4

# (a) 직접: body_inertia yy 성분 += δ (iquat identity 가정 — pristine이 identity)
model.body_inertia[b][1] += DL
mj.mj_setConst(model, rm._scr)
Ma = M22()
model.body_inertia[b][1] -= DL
mj.mj_setConst(model, rm._scr)

# (b) set_body_pi 경유: IO_yy += δ
pi = rm.pi0.copy()
pi[10 * K + 5] += DL
rm.set_pi(pi)
Mb = M22()
print("set 후 crank body_inertia:", model.body_inertia[b], "iquat:", model.body_iquat[b])
rm.restore()

print("직접 수정 ΔM:")
print(Ma - M0)
print("set_body_pi ΔM:")
print(Mb - M0)

# quat 방향 실험: 순수 회전 90° about z 를 iquat로 넣고, diag=(1,2,3) → IC 예상 비교
model2 = model
q = np.zeros(4)
Rz = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])  # 90° about z (col-form)
mj.mju_mat2Quat(q, np.ascontiguousarray(Rz.flatten()))
print("mju_mat2Quat(Rz row-major flatten) =", q, " (기대: 90° about z → [0.707,0,0,0.707])")
R9 = np.zeros(9)
mj.mju_quat2Mat(R9, q)
print("mju_quat2Mat 재변환:\n", R9.reshape(3, 3), "\n(Rz와 같으면 row-major 왕복 일관)")
