# -*- coding: utf-8 -*-
"""일회성 검증: ①발 초기화 간극 ②힙 2단 스프링 실효 강성 ③짐 부착 위치의 영향(=0?) ④레일마찰 입력"""
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
import fs_runner as FR
import numpy as np, mujoco as mjm

ft = FR.fs_twin(); m = ft["model"]; iq, dof = ft["iq"], ft["dof"]
S = ft["P"].J._P["S"]
md = mjm.MjData(m)
q1_0, q2_0 = -0.785, -2.2
md.qpos[iq["base_z"]] = 1.0
md.qpos[iq["hip_m"]] = -q1_0 - np.pi/2
md.qpos[iq["knee_motor"]] = -q2_0
md.qpos[iq["cpin"]] = q2_0
md.qpos[iq["knee"]] = -q2_0
mjm.mj_forward(m, md)
fg = mjm.mj_name2id(m, mjm.mjtObj.mjOBJ_GEOM, "foot")
md.qpos[iq["base_z"]] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
mjm.mj_forward(m, md)
r_geom = float(m.geom_size[fg][0])
zc = float(md.geom_xpos[fg][2])
print(f"[1] 초기화 후 발 중심 z = {zc*1000:.3f} mm · geom 반경 = {r_geom*1000:.3f} mm "
      f"→ 바닥과의 간극 {(zc-r_geom)*1000:+.3f} mm (margin {m.geom_margin[fg]*1000:.1f} mm)")
print(f"    S.FOOT_RADIUS 상수 = {S.FOOT_RADIUS*1000:.1f} mm (FS_FOOTR 과 무관하게 고정)")

print("\n[2] 힙 직렬 스프링 실효 토크 (플랜트 스프링 + 러너 qfrc 보정)")
import fs_model as FM
print(f"    FM.KS_HIP(모듈 상수) = {FM.KS_HIP} · env FS_KS_HIP = {os.environ['FS_KS_HIP']}"
      f" · 실제 모델 jnt_stiffness = {m.jnt_stiffness[mjm.mj_name2id(m,mjm.mjtObj.mjOBJ_JOINT,'hip')]:.2f}")
print(f"    2단 스프링 상수 _s2s() = {FR._s2s()}  (k_lo, k_hi, tau0) — FS_HSPR 미설정 시 고정")
ks_env = float(os.environ["FS_KS_HIP"])
for dg in (0.5, 1.0, 2.0, 5.0, 5.37, 8.0, 12.0):
    d = np.radians(dg)
    passive = -ks_env * d
    corr = FM.KS_HIP * d - FR._tau2s(d)
    tot = passive + corr
    print(f"    처짐 {dg:5.2f}° → 스프링 {-passive:6.3f} + 보정 {corr:+7.3f} = 실효 {-tot:6.3f} N·m"
          f"  (실효강성 {-tot/d:7.2f} N·m/rad)")

print("\n[3] 짐 부착 위치의 영향 — base 무게중심 ipos 를 흔들어 본다")
bi = mjm.mj_name2id(m, mjm.mjtObj.mjOBJ_BODY, "base")
mjm.mj_forward(m, md)
M0 = np.zeros((m.nv, m.nv)); mjm.mj_fullM(m, M0, md.qM)
b0 = np.array(md.qfrc_bias)
old = np.array(m.body_ipos[bi])
for off in ([0.10, 0, 0], [0, 0, -0.10]):
    m.body_ipos[bi] = old + np.array(off)
    md2 = mjm.MjData(m); md2.qpos[:] = md.qpos; md2.qvel[:] = md.qvel
    mjm.mj_forward(m, md2)
    M1 = np.zeros((m.nv, m.nv)); mjm.mj_fullM(m, M1, md2.qM)
    print(f"    base 무게중심 {off} m 이동 → |ΔM|max {np.abs(M1-M0).max():.3e} · "
          f"|Δ중력·코리올리|max {np.abs(np.array(md2.qfrc_bias)-b0).max():.3e} N·m")
m.body_ipos[bi] = old
print(f"    base 관성 diag = {m.body_inertia[bi]} · base 의 자유도 = base_z(slide z) 1 개")
print(f"    전체 자유도 이름 = {[mjm.mj_id2name(m, mjm.mjtObj.mjOBJ_JOINT, i) for i in range(m.njnt)]}")

print("\n[4] 레일 마찰 입력 = 발 접촉의 **수평력** (수직 하중 아님)")
print("    코드: md.qfrc_applied[base_z] = -FS_RAIL * |Fx| * tanh(v_bz/0.05)  (fs_runner 1139~1153 / 1693~1707)")
print(f"    FS_RAIL = {os.environ['FS_RAIL']} [무차원 마찰계수] · 짐 무게는 이 식에 안 들어간다")
