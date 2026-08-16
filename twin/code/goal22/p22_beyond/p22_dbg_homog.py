# -*- coding: utf-8 -*-
"""디버그2: τ(π)가 π에 선형-동차인가? τ(απ0) = α·τ(π0)? 잔차 구조는?"""
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
from p22_base_params import RModel, BODIES

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


t0 = tau_all()
for a in (0.5, 2.0):
    rm.set_pi(rm.pi0 * a)
    ta = tau_all()
    rm.restore()
    err = np.max(np.abs(ta - a * t0)) / np.max(np.abs(t0))
    print(f"동차성 τ({a}·π0) vs {a}·τ(π0): rel err = {err:.2e}")

# 부분 재선형성: body별 π를 0으로 낮추긴 불가(m>0), 대신 superposition:
# τ(π0) − τ(π0 with thigh π×0.5) == 0.5·(τ(π0) − τ(π0 with thigh π×0)) ~ m>0 필요.
# 대신 h만 스케일 (m 유지):
pi = rm.pi0.copy()
for k, b in enumerate(BODIES):
    pih = rm.pi0.copy()
    pih[10 * k + 1:10 * k + 4] *= 0.7          # h만 0.7배
    rm.set_pi(pih)
    th = tau_all()
    rm.restore()
    # h에 선형이면 τ(0.7h) = τ(h) − 0.3·(∂τ/∂h·h) — FD로 좌우 확인
    dj = 1e-6
    grad = np.zeros((20, 5))
    for c in range(1, 4):
        pp = rm.pi0.copy()
        pp[10 * k + c] += dj
        rm.set_pi(pp)
        tp = tau_all()
        pp[10 * k + c] -= 2 * dj
        rm.set_pi(pp)
        tm = tau_all()
        rm.restore()
        grad += (tp - tm) / (2 * dj) * rm.pi0[10 * k + c]
    lin_pred = t0 - 0.3 * grad
    err = np.max(np.abs(th - lin_pred)) / np.max(np.abs(t0))
    print(f"[{BODIES[k]}] h-선형성: rel err = {err:.2e}")

# I 열 선형성 (Ixx 등): 같은 방식으로 Iyy만 0.7배
for k, b in enumerate(BODIES):
    pih = rm.pi0.copy()
    pih[10 * k + 4:10 * k + 10] *= 0.7
    rm.set_pi(pih)
    th = tau_all()
    rm.restore()
    dj = 1e-7
    grad = np.zeros((20, 5))
    for c in range(4, 10):
        if abs(rm.pi0[10 * k + c]) < 1e-15:
            continue
        pp = rm.pi0.copy()
        pp[10 * k + c] += dj
        rm.set_pi(pp)
        tp = tau_all()
        pp[10 * k + c] -= 2 * dj
        rm.set_pi(pp)
        tm = tau_all()
        rm.restore()
        grad += (tp - tm) / (2 * dj) * rm.pi0[10 * k + c]
    lin_pred = t0 - 0.3 * grad
    err = np.max(np.abs(th - lin_pred)) / np.max(np.abs(t0))
    print(f"[{BODIES[k]}] I-선형성: rel err = {err:.2e}")

# m 열 선형성
for k, b in enumerate(BODIES):
    pih = rm.pi0.copy()
    pih[10 * k] *= 1.3
    rm.set_pi(pih)
    th = tau_all()
    rm.restore()
    dj = 1e-6
    pp = rm.pi0.copy()
    pp[10 * k] += dj
    rm.set_pi(pp)
    tp = tau_all()
    pp[10 * k] -= 2 * dj
    rm.set_pi(pp)
    tm = tau_all()
    rm.restore()
    grad = (tp - tm) / (2 * dj) * rm.pi0[10 * k]
    lin_pred = t0 + 0.3 * grad
    err = np.max(np.abs(th - lin_pred)) / np.max(np.abs(t0))
    print(f"[{BODIES[k]}] m-선형성 (×1.3): rel err = {err:.2e}")
