# -*- coding: utf-8 -*-
"""일회성 조사: 현행 스택에서 모델에 실제로 박혀 있는 값 + 꺼져 있는 층의 값 출력. (읽기 전용)"""
import os, sys
os.environ["PYTHONIOENCODING"] = "utf-8"
STACK = dict(
    FS_TMAP="canon_cap", FS_TDCAP="4.122,2.372", FS_MASS="3.2990", FS_FOOTR="0.020",
    FS_NOSUPP="1", FS_NOSPR="1", FS_NOBIAS="1", FS_NODEEP="1",
    FS_PRESLIDE="0.86,0.85,0.02,1.0", FS_CMD_LPF="0.00451,0.00072", FS_IMPRATIO="20",
    FS_KNEEM_FL="0.1177", FS_KNEEM_DAMP="0.2281", FS_HIPM_FL="0.3111", FS_HIPM_DAMP="0.0071",
    FS_KS_HIP="166.34", FS_COMZ="thigh=0.02239", FS_RAIL="0.02995")
os.environ.update(STACK)
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import numpy as np
import fs_runner as FR
import mujoco as mjm
import safe

ft = FR.fs_twin()
m = ft["model"]
print("=== 조인트 ===")
for i in range(m.njnt):
    n = mjm.mj_id2name(m, mjm.mjtObj.mjOBJ_JOINT, i)
    a = m.jnt_dofadr[i]
    print(f"{n:12s} type={m.jnt_type[i]} stiff={m.jnt_stiffness[i]:.4f} "
          f"damp={m.dof_damping[a]:.5f} fric={m.dof_frictionloss[a]:.5f} arm={m.dof_armature[a]:.7f} "
          f"limited={m.jnt_limited[i]} range={m.jnt_range[i]}")
print("\n=== 바디 ===")
for i in range(m.nbody):
    n = mjm.mj_id2name(m, mjm.mjtObj.mjOBJ_BODY, i)
    print(f"{n:12s} mass={m.body_mass[i]:.5f} ipos={m.body_ipos[i]} inertia={m.body_inertia[i]}")
print(f"총질량 {m.body_mass.sum():.4f} kg | nq={m.nq} nv={m.nv}")
print("\n=== 접촉/솔버 ===")
print("impratio", m.opt.impratio, "timestep", m.opt.timestep, "integrator", m.opt.integrator, "cone", m.opt.cone)
for gn in ("foot", "floor"):
    gi = mjm.mj_name2id(m, mjm.mjtObj.mjOBJ_GEOM, gn)
    print(f"{gn}: size={m.geom_size[gi]} fric={m.geom_friction[gi]} solref={m.geom_solref[gi]} "
          f"solimp={m.geom_solimp[gi]} pos={m.geom_pos[gi]} margin={m.geom_margin[gi]} condim={m.geom_condim[gi]}")
print("\n=== equality ===")
for i in range(m.neq):
    print("eq", i, "type", m.eq_type[i], "solref", m.eq_solref[i], "active", m.eq_active0[i], "data", m.eq_data[i][:4])
print("\n=== 인공층 (지금 꺼짐) 값 ===")
print("law (a,b,v0) =", ft["law"], " k_rise =", ft["kr"], " sprm(ks,kref,T) =", ft["sprm"])
import p23_v6_runners as RU
print("HIP dict =", RU.HIP)
print("SUPP_CAP =", RU.SUPP_CAP, " LAW_C =", RU.LAW_C)
print("A_PAPER =", ft["P"].A_PAPER, " SD =", ft["P"].SD)
S = ft["P"].J._P["S"]
print("FOOT_RADIUS(상수) =", S.FOOT_RADIUS, " SETTLE_KP/KD =", S.SETTLE_KP, S.SETTLE_KD,
      " T_SETTLE =", ft["P"].J.T_SETTLE)
print("CLIP =", __import__("p25_a_twin").R19.CLIP)
print("\n=== 세션 상수 (지금 꺼짐) ===")
sp = FR._sess_params()
for k in sp if isinstance(sp, dict) else []:
    print(" ", k, sp[k])
print("\n=== CVT 손실 계수 ===")
import safe as _s
cand = _s.read_json(__import__("p25_a_twin").CAND_PATH)
nm = dict(zip(cand["names"], np.asarray(cand["x"], float)))
for k in ("C_CVT", "o1_429", "o2_429"):
    if k in nm:
        print(" ", k, nm[k])
