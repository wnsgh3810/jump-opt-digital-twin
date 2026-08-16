# -*- coding: utf-8 -*-
"""디버그3: crank I 비선형의 정체 — α-스캔 + set→get 라운드트립 + 필드 검사."""
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
from p22_base_params import RModel, BODIES, body_pi

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
print("tau(pi0) =", t0)
print("crank pi0 I-block:", rm.pi0[10 * K + 4:10 * K + 10])
alphas = np.linspace(0.5, 1.5, 11)
taus = []
for a in alphas:
    pi = rm.pi0.copy()
    pi[10 * K + 4:10 * K + 10] *= a
    rm.set_pi(pi)
    # set→get 라운드트립
    pi_back = rm.get_pi()
    rt = np.max(np.abs(pi_back - pi))
    taus.append(tau1())
    if a in (0.5, 0.7, 1.0, 1.5):
        b = rm.bid[K]
        print(f"a={a:.1f} roundtrip |Δπ|max={rt:.2e}  body_inertia={model.body_inertia[b]}"
              f"  iquat={model.body_iquat[b]}")
    rm.restore()
taus = np.array(taus)
# 선형이면 taus[:, j]는 alpha에 대해 직선 — 2차 계수 추정
for j in range(5):
    c2 = np.polyfit(alphas, taus[:, j], 2)[0]
    c1 = np.polyfit(alphas, taus[:, j], 1)[0]
    print(f"dof{j}: quad coeff={c2:.3e}  lin coeff={c1:.3e}")

# α=0.7에서 실제 τ vs 선형 보간 (α=0.5,1.5 기준)
lin = 0.5 * (taus[0] + taus[-1])
print("mid(α=1.0) τ =", taus[5])
print("lin pred     =", lin)
print("차            =", taus[5] - lin)

# setConst 없이 set만 하면? (mj_setConst 우회 실험)
pi = rm.pi0.copy()
pi[10 * K + 4:10 * K + 10] *= 0.7
for k, b in enumerate(rm.bid):
    from p22_base_params import set_body_pi
    set_body_pi(model, b, pi[10 * k:10 * k + 10], mj)
# mj_setConst 호출 안 함
t_nosc = tau1()
mj.mj_setConst(model, rm._scr)
t_sc = tau1()
rm.restore()
print("setConst 유무 차:", np.max(np.abs(t_nosc - t_sc)))
