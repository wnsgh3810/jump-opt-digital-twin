# -*- coding: utf-8 -*-
"""_GHP_loadslope — 짐 무게에 대한 **부족한 토크**의 기울기 재유도 (26.06.04, 08-15).

무엇을 하나
  ① 실측 관절 궤적(q1 힙, q2 무릎 크랭크)을 **그대로 따라가는 데 필요한 축 토크**를
     역동역학으로 구한다 (강체 관성 + 중력 + 코리올리; 관절 마찰·감쇠는 뺀 '물리 바닥').
  ② 실측 명령 토크에 **현행 환산식**(H4_260813: canon_cap, cap 4.122/2.372, clip ±35.5)을
     먹여 축 토크로 바꾼다.
  ③ 차이 Δτ = τ_필요 − τ_명령 = **부족한 토크** 를 짐 무게(0/2.5/5kg)에 회귀한다.

역동역학의 형식 (contact 솔버·GRF 를 쓰지 않는 축약 좌표 방식)
  발이 바닥에 붙어 있는 동안 모델의 6 좌표 x=(base_z, hip_m, hip처짐, crank, cpin, knee)는
  독립 좌표 u=(q1,q2) 두 개로 전부 정해진다 (4절 폐쇄 + 발끝 높이=반지름).
      x = X(u),  G = ∂X/∂u  (6x2)
  전체 운동방정식  M x'' + c = S τ + J_c^T f_접촉 + J_eq^T λ  에 G^T 를 곱하면
    · 폐쇄 구속력 λ 항은 0 (G 가 그 구속의 접평면)
    · 접촉 **수직** 성분은 0 (발끝 높이가 u 에 무관 → ∂z_foot/∂u = 0)  ⇒ **GRF 불필요**
    · 접촉 **접선** 성분만 남는데 이건 가정으로 0 (아래 '가정' 참조)
    · G^T S = -I  이고 액추에이터 ctrl = -(축토크) 이므로  **τ_축 = G^T (M x'' + c)**
  M x'' + c 는 mj_rne(flg_acc=1) + armature·x'' 로 계산 (구속 솔버 미사용 → 빠르고 결정적).

가정 (전부 결과에 명시)
  A1. 발 접선력 f_x = 0 (자유 구름). 근거: 발이 롤러이고 준정적. 검증 못 함.
  A2. 힙 직렬탄성 처짐 = 0 (강체 힙). 처짐은 τ/ks ≈ τ/166 rad.
  A3. 관절 마찰/감쇠는 τ_필요에 **안** 넣는다 (그게 지금 재려는 '부족분'의 후보이므로).
      참고로 현행 모델 마찰분도 같이 출력한다.

CLI: python _GHP_loadslope.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path

GFS = Path(__file__).parent
sys.path.insert(0, str(GFS))
os.chdir(GFS)

# 현행 런타임 스택 H4_260813 (CURRENT_STACK.md)
STACK = dict(FS_TMAP="canon_cap", FS_TDCAP="4.122,2.372", FS_MASS="3.2990",
             FS_FOOTR="0.020", FS_NOSUPP="1", FS_NOSPR="1", FS_NOBIAS="1",
             FS_NODEEP="1", FS_PRESLIDE="0.86,0.85,0.02,1.0",
             FS_CMD_LPF="0.00451,0.00072", FS_IMPRATIO="20",
             FS_KNEEM_FL="0.1177", FS_KNEEM_DAMP="0.2281", FS_HIPM_FL="0.3111",
             FS_HIPM_DAMP="0.0071", FS_KS_HIP="166.34", FS_COMZ="thigh=0.02239",
             FS_RAIL="0.02995")
for _k, _v in STACK.items():
    os.environ.setdefault(_k, _v)

import numpy as np
import mujoco as mj
from scipy.signal import savgol_filter
import fs_data as FD, fs_runner as FR, fs_cvt as FC

G0 = 9.81
Z_MIN = 0.10          # 몸통이 이 높이[m] 위로 떠 있는 구간만 (아래는 받침에 얹힘)
CLIP = 35.5           # 명령 천장 (TW.R19.CLIP)
SG_WIN, SG_ORD = 51, 3        # 102ms / 3차 — 각도 2계 미분용 평활
EPS = 1e-5


def base_h(q1, q2, L=0.25):
    return -L * (np.sin(q1) + np.sin(q1 + q2))


def make_map(ft, cvt, l_i):
    """u=(q1,q2) → 모델 6-qpos.  base_z 는 발끝이 바닥에 닿도록 정한다."""
    m = ft["model"]
    iq = ft["iq"]
    d = mj.MjData(m)
    fg = mj.mj_name2id(m, mj.mjtObj.mjOBJ_GEOM, "foot")
    r = float(m.geom_size[fg][0])
    cinit = ft.get("cvt_init")

    def X(q1, q2):
        """→ (6-qpos, 발 geom 의 수평 위치 x[m])"""
        q = np.zeros(m.nq)
        if cvt:
            q5 = np.asarray(cinit(q1, q2), float)
            q[iq["hip_m"]] = q5[1]
            q[iq["hip"]] = 0.0
            q[iq["knee_motor"]] = q5[2]
            q[iq["cpin"]] = q5[3]
            q[iq["knee"]] = q5[4]
        else:
            q[iq["hip_m"]] = -q1 - np.pi / 2
            q[iq["hip"]] = 0.0
            q[iq["knee_motor"]] = -q2
            q[iq["cpin"]] = q2
            q[iq["knee"]] = -q2
        q[iq["base_z"]] = 1.0
        d.qpos[:] = q
        mj.mj_kinematics(m, d)
        q[iq["base_z"]] = 1.0 - float(d.geom_xpos[fg][2]) + r
        return q, float(d.geom_xpos[fg][0])

    return X


def analyse(sub, payload, cvt, verbose=False):
    d = FD.load_s2s(sub)
    t = d["t"]
    q1, q2 = d["q1"], d["q2"]
    ok = base_h(q1, q2) > Z_MIN
    i0 = int(np.argmax(ok)); i1 = int(len(ok) - np.argmax(ok[::-1]))
    ix = np.arange(i0, i1)

    # 모델: 짐은 base 에 통째로 (사용자 확인 08-12)
    os.environ["FS_MASS"] = f"{float(STACK['FS_MASS']) + payload:.4f}"
    FR._CACHE.clear() if hasattr(FR, "_CACHE") else None
    ft0 = FR.fs_twin()
    if cvt:
        FC._MC.clear(); FC._RT.clear()
        ft = FC.cvt_ft(float(d["l_i"]), ft_base=ft0)
    else:
        ft = ft0
    m = ft["model"]
    md = mj.MjData(m)
    X = make_map(ft, cvt, float(d["l_i"]))

    n = len(t)
    xs = np.zeros((n, m.nq))
    Gs = np.zeros((n, m.nq, 2))
    Jfx = np.zeros((n, 2))       # ∂(발 수평위치)/∂u  [m/rad]
    for k in range(n):
        x0, xf0 = X(q1[k], q2[k])
        xa, xfa = X(q1[k] + EPS, q2[k])
        xb, xfb = X(q1[k], q2[k] + EPS)
        xs[k] = x0
        Gs[k, :, 0] = (xa - x0) / EPS
        Gs[k, :, 1] = (xb - x0) / EPS
        Jfx[k, 0] = (xfa - xf0) / EPS
        Jfx[k, 1] = (xfb - xf0) / EPS

    dt = float(np.median(np.diff(t)))
    v = savgol_filter(xs, SG_WIN, SG_ORD, deriv=1, delta=dt, axis=0, mode="interp")
    a = savgol_filter(xs, SG_WIN, SG_ORD, deriv=2, delta=dt, axis=0, mode="interp")

    tau_req = np.zeros((n, 2))       # 동역학 (관성+중력+코리올리)
    tau_grav = np.zeros((n, 2))      # 정역학만 (v=a=0)
    tau_pass = np.zeros((n, 2))      # 현행 모델 관절 마찰·감쇠·스프링분
    res = np.zeros(m.nv)
    for k in range(n):
        md.qpos[:] = xs[k]; md.qvel[:] = v[k]; md.qacc[:] = a[k]
        mj.mj_kinematics(m, md); mj.mj_comPos(m, md); mj.mj_comVel(m, md)
        mj.mj_rne(m, md, 1, res)
        f = res + m.dof_armature * a[k]
        tau_req[k] = Gs[k].T @ f
        md.qvel[:] = 0; md.qacc[:] = 0
        mj.mj_kinematics(m, md); mj.mj_comPos(m, md); mj.mj_comVel(m, md)
        mj.mj_rne(m, md, 1, res)
        tau_grav[k] = Gs[k].T @ (res + 0.0)
        # 수동력(마찰/감쇠/스프링): 관절을 그 속도로 돌리려면 더 필요한 몫
        fp = (m.dof_damping * v[k]
              + m.dof_frictionloss * np.tanh(v[k] / 0.02)
              + np.array([m.jnt_stiffness[m.dof_jntid[j]] * (xs[k][m.jnt_qposadr[m.dof_jntid[j]]]
                          - m.qpos_spring[m.jnt_qposadr[m.dof_jntid[j]]]) for j in range(m.nv)]))
        tau_pass[k] = Gs[k].T @ fp

    # 명령 → 축 토크 (현행 환산식)
    A = FR.tq_shape(ft["P"].A_PAPER)
    tmap = FR._tmap_init(ft["P"], A)
    r1 = np.clip(d["raw1"], -CLIP, CLIP)
    r2 = np.clip(d["raw2"], -CLIP, CLIP)
    tau_cmd = np.zeros((n, 2))
    tau_cmd_noclip = np.zeros((n, 2))
    for k in range(n):
        tau_cmd[k, 0] = tmap(float(r1[k]), float(d["dq1"][k]), 0)
        tau_cmd[k, 1] = tmap(float(r2[k]), float(d["dq2"][k]), 1)
        tau_cmd_noclip[k, 0] = tmap(float(d["raw1"][k]), float(d["dq1"][k]), 0)
        tau_cmd_noclip[k, 1] = tmap(float(d["raw2"][k]), float(d["dq2"][k]), 1)

    # 짐 1kg 이 각 축에 만드는 정적 토크 [N·m/kg] = g · ∂base_z/∂q_j
    lever = Gs[:, ft["iq"]["base_z"], :] * G0

    return dict(sub=sub, payload=payload, cvt=cvt, l_i=float(d["l_i"]),
                t=t, ix=ix, q1=q1, q2=q2, bz=xs[:, ft["iq"]["base_z"]],
                bz_an=base_h(q1, q2),
                tau_req=tau_req, tau_grav=tau_grav, tau_pass=tau_pass,
                tau_cmd=tau_cmd, tau_cmd_noclip=tau_cmd_noclip, lever=lever,
                Jfx=Jfx, mass=float(STACK["FS_MASS"]) + payload,
                raw1=d["raw1"], raw2=d["raw2"], dq1=d["dq1"], dq2=d["dq2"],
                nsat=int((np.abs(d["raw2"]) > CLIP).sum()),
                vel=v, acc=a, iq=ft["iq"])


if __name__ == "__main__":
    import json, safe
    R = {}
    for sub, pay, cvt in FD.S2S_CASES:
        r = analyse(sub, pay, cvt)
        R[sub] = r
        ix = r["ix"]
        print(f"\n=== {sub}  짐={pay}kg  변속={cvt}  l_i={r['l_i']*1000:.2f}mm "
              f"창={len(ix)}샘플({len(ix)*0.002:.2f}s) 명령포화={r['nsat']}샘플")
        for j, nm in ((0, "힙 "), (1, "무릎")):
            rq = r["tau_req"][ix, j]; cm = r["tau_cmd"][ix, j]; dd = rq - cm
            print(f"  {nm} τ필요 {rq.mean():7.3f} ({rq.min():7.3f}..{rq.max():7.3f}) | "
                  f"τ명령 {cm.mean():7.3f} ({cm.min():7.3f}..{cm.max():7.3f}) | "
                  f"Δ평균 {dd.mean():7.3f}  Δ|평균| {np.abs(dd).mean():7.3f}  "
                  f"레버 {r['lever'][ix, j].mean():6.3f} Nm/kg")
    # 검산: 무변속(평행사변형)에서 모델 base_z 기울기 = 해석식 −0.25(cos q1+cos(q1+q2))
    r = R["no_cvt/no_load"]; ix = r["ix"]
    an1 = -0.25 * (np.cos(r["q1"]) + np.cos(r["q1"] + r["q2"]))
    an2 = -0.25 * np.cos(r["q1"] + r["q2"])
    md1 = r["lever"][:, 0] / G0; md2 = r["lever"][:, 1] / G0
    print(f"\n[검산] 무변속 ∂bz/∂q1 모델 vs 해석 최대차 {np.abs(md1[ix]-an1[ix]).max():.2e} m/rad"
          f" · ∂bz/∂q2 {np.abs(md2[ix]-an2[ix]).max():.2e}"
          f" · bz 자체 최대차 {np.abs(r['bz'][ix]-r['bz_an'][ix]-(r['bz'][ix]-r['bz_an'][ix]).mean()).max():.2e} m")
    import pickle
    with open(GFS / "_GHP_loadslope.pkl", "wb") as f:
        pickle.dump(R, f)
    print("\n저장 -> _GHP_loadslope.pkl")
