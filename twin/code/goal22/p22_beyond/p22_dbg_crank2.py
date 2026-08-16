# -*- coding: utf-8 -*-
"""디버그4: crank I 성분별 FD — δ 스캔 + 개별 성분 set→get 라운드트립."""
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
from p22_base_params import RModel, BODIES, COMP

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
K = 2  # crank

state = (1.0, -1.5, -1.8, 0.7, -1.9, np.array([2., -5., 8., 1., -3.]),
         np.array([100., -300., 200., 50., -150.]))


def tau1():
    bz, q1, qc, qp, qk, v5, a5 = state
    d.qpos[rm.iq] = [bz, q1, qc, qp, qk]
    d.qvel[rm.iv] = v5
    d.qacc[rm.iv] = a5
    mj.mj_inverse(model, d)
    return d.qfrc_inverse[rm.iv].copy()


t0 = tau1()
# 성분별: FD @ δ 스캔 + 라운드트립
for c in range(4, 10):
    name = COMP[c]
    print(f"--- crank.{name} (pi0={rm.pi0[10 * K + c]:.4e}) ---")
    for dj in (1e-8, 1e-7, 1e-6, 1e-5, 1e-4):
        pp = rm.pi0.copy()
        pp[10 * K + c] += dj
        rm.set_pi(pp)
        rt_p = np.max(np.abs(rm.get_pi() - pp))
        tp = tau1()
        pp[10 * K + c] -= 2 * dj
        rm.set_pi(pp)
        rt_m = np.max(np.abs(rm.get_pi() - pp))
        tm = tau1()
        rm.restore()
        col = (tp - tm) / (2 * dj)
        print(f"  δ={dj:.0e}: col={np.array2string(col, precision=4)} "
              f"rt=({rt_p:.1e},{rt_m:.1e})")

# 블록 스케일 기울기 (참값): dof별 dτ/dα → Σ ∂τ/∂I_c·I_c 와 비교
pi = rm.pi0.copy()
h = 0.2
pi[10 * K + 4:10 * K + 10] = rm.pi0[10 * K + 4:10 * K + 10] * (1 + h)
rm.set_pi(pi)
tp = tau1()
pi[10 * K + 4:10 * K + 10] = rm.pi0[10 * K + 4:10 * K + 10] * (1 - h)
rm.set_pi(pi)
tm = tau1()
rm.restore()
slope = (tp - tm) / (2 * h)
print("블록 방향미분 (참):", np.array2string(slope, precision=6))
