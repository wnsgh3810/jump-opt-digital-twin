"""P11a — cross-validate the USER's analytic 4-bar equations (Notion
'수정된 4-bar linkage dynamics') against the FLIPPED MuJoCo model, at pure CAD.

User frame: link dir (cos th, sin th), z up, hip x=0.
  thigh th1 (abs) / shin th1+th2 / crank th12+pi / coupler th1 (parallel thigh).
Mapping to mujoco: th1 = q1m - pi/2, th2 = q2m.

User params -> CAD: m_t=M1, r_t=R1, I_t=I1 (knee motor incl in thigh: CAD does
include the hip-mounted knee motor in M1);  m_c=M_C, r_c=RC, I_c=IC;
m_p=M_P, r_p=RP, I_p=IP;  m_s=M2, r_s=R2, I_s=I2;  l_t=l_p=0.25, l_c=0.03.

MuJoCo flipped model is 5-DoF (z,q1,crank,cpin,knee) + connect. Project onto
the parallelogram manifold with T: (dz,dq1,dq2) -> (dz,dq1,dq2,-dq2,dq2):
  M3 = T' M5 T ,  bias3 = T' bias5.
Compare with user's M(q), C(q,dq)qd + G(q). PASS if max err < 1e-9.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_fourbar_flip as FL
FL.winit()
mujoco = FL._G["mujoco"]; S = FL._G["S"]; B = FL._G["B"]

G = 9.81
lt = B.L1_VAL; lc = B.LC_VAL
mt, rt, It = B.M1_CAD, B.R1_VAL, B.I1_VAL
mc, rc, Ic = B.M_C_CAD, B.RC_VAL, B.IC_VAL
mp, rp, Ip = B.M_P_CAD, B.RP_VAL, B.IP_VAL
ms, rs, Is = B.M2_CAD, B.R2_VAL, B.I2_VAL

# user's coefficients at CAD
Mb = S._base_mass()
Mtot = Mb + mt + mc + mp + ms
A = mt * rt + mp * rp + ms * lt
Bc = ms * rs - mc * rc - mp * lc
K = ms * lt * rs - mp * lc * rp
IS1 = (It + mt * rt**2) + (Ic + mc * rc**2) + (Ip + mp * rp**2 + mp * lc**2) + (Is + ms * rs**2 + ms * lt**2)
IS2 = (Is + ms * rs**2) + (Ic + mc * rc**2) + mp * lc**2
print(f"user coeffs @CAD:  A={A:.6f}  B={Bc:.6f}  K={K:.6f}  IS1={IS1:.6f}  IS2={IS2:.6f}  Mtot={Mtot:.4f}")
print(f"  (비교: serial 시절 무릎측 질량모멘트 k2 ≈ +0.175 — 4-bar 진짜 B는 {Bc:+.4f}, 부호 반대·48배 작음)")


def M_user(q1m, q2m):
    t1 = q1m - np.pi / 2; t2 = q2m
    c1, c12, c2 = np.cos(t1), np.cos(t1 + t2), np.cos(t2)
    return np.array([
        [Mtot, A * c1 + Bc * c12, Bc * c12],
        [A * c1 + Bc * c12, IS1 + 2 * K * c2, IS2 + K * c2],
        [Bc * c12, IS2 + K * c2, IS2]])


def bias_user(q1m, q2m, dz, d1, d2):
    t1 = q1m - np.pi / 2; t2 = q2m
    s1, s12, s2 = np.sin(t1), np.sin(t1 + t2), np.sin(t2)
    c1, c12 = np.cos(t1), np.cos(t1 + t2)
    d12 = d1 + d2
    C = np.array([-A * s1 * d1**2 - Bc * s12 * d12**2,
                  -K * s2 * (2 * d1 * d2 + d2**2),
                  K * s2 * d1**2])
    Gv = np.array([Mtot * G, G * (A * c1 + Bc * c12), G * Bc * c12])
    return C + Gv


# flipped mujoco @ pure CAD (scales=1, no friction/flex/armature/foot)
S.FV_HIP = 0.0; S.FV_KNEE = 0.0; S.FC_HIP = 0.0; S.FC_KNEE = 0.0
S.STIFF_HIP = 0.0; S.STIFF_KNEE = 0.0; S.SPRINGREF_KNEE = 0.0
S.SOLREF_TC_LOCK = 0.006; S.IMP0_LOCK = 0.3
xml = FL.build_xml_fourbar_flip(0.0, {})           # all scales default 1, m_foot 0
m = mujoco.MjModel.from_xml_string(xml)
d = mujoco.MjData(m)
T = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 0, -1], [0, 0, 1]], dtype=float)

rng = np.random.default_rng(7)
errM = errB = 0.0
for _ in range(300):
    z = rng.uniform(0.8, 1.5)                       # airborne: no contact
    q1, q2 = rng.uniform(-2.5, 2.5, 2)
    v = rng.uniform(-12, 12, 3)
    d.qpos[:] = [z, q1, q2, -q2, q2]
    d.qvel[:] = T @ v
    mujoco.mj_forward(m, d)
    M5 = np.zeros((m.nv, m.nv)); mujoco.mj_fullM(m, M5, d.qM)
    M3 = T.T @ M5 @ T
    b3 = T.T @ d.qfrc_bias
    errM = max(errM, float(np.max(np.abs(M3 - M_user(q1, q2)))))
    errB = max(errB, float(np.max(np.abs(b3 - bias_user(q1, q2, *v)))))
print(f"[CROSS-CHECK] |M_mujoco - M_user|max = {errM:.3e}   |bias diff|max = {errB:.3e}")
print("VERDICT:", "PASS — 사용자 해석식과 뒤집힌 MuJoCo 모델이 동일한 물리" if max(errM, errB) < 1e-9
      else ("NEAR (수치 잔차 확인 필요)" if max(errM, errB) < 1e-5 else "FAIL — 불일치, 원인 추적 필요"))

# 참고: 원위상(canonical pre-flip) 모델은 어긋나는지도 정량화
import mshoot_fourbar as FB0
xml0 = FB0.build_xml_fourbar_jump.__wrapped__ if hasattr(FB0.build_xml_fourbar_jump, "__wrapped__") else None
# FL.winit monkeypatched FB.build_xml... rebuild original from source module copy:
import importlib, mshoot_fourbar
importlib.reload(mshoot_fourbar)
xml_orig = mshoot_fourbar.build_xml_fourbar_jump(0.0, {})
m0 = mujoco.MjModel.from_xml_string(xml_orig)
d0 = mujoco.MjData(m0)
errM0 = 0.0
for _ in range(100):
    q1, q2 = rng.uniform(-2.5, 2.5, 2)
    d0.qpos[:] = [1.2, q1, q2, -q2, q2]; d0.qvel[:] = 0
    mujoco.mj_forward(m0, d0)
    M5 = np.zeros((m0.nv, m0.nv)); mujoco.mj_fullM(m0, M5, d0.qM)
    M3 = T.T @ M5 @ T
    errM0 = max(errM0, float(np.max(np.abs(M3 - M_user(q1, q2)))))
print(f"[참고] 원위상(정정 전) 모델 vs 사용자 식: |dM|max = {errM0:.3e}  (뒤집힌 모델 {errM:.3e}와 대조)")
