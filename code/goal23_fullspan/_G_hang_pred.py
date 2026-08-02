# -*- coding: utf-8 -*-
"""_G_hang_pred — 마라톤G Phase1: **무동력 매달림 평형각 예측** (사용자 제안 실험 08-02).

실험(사용자): 모터를 전부 끄고 로봇을 공중에 매달면 — 무릎은 backdrivability(정지마찰)로
**놓은 각도에 그대로 고정**되고, **힙만 회전해** 다리가 바닥을 향해 떨어져 멈춘다.

왜 강력한가: 멈춘 각도 q1* 는 "힙 축 아래 전체의 **합성 무게중심이 힙 축 바로 밑**"이라는
조건 그 자체다. → **토크 센서·a_hat 변환·오프셋·접촉이 전부 불필요**, 엔코더 각도만으로
질량분포를 읽는다 (공중 토크 실험 G1-F2는 신호 0.34Nm < 잡음 0.4Nm로 실패).

계산: 시뮬레이션(정착) 없이 **순수 기하** — 자세를 놓고 mj_forward 한 뒤 힙 축 아래 바디들의
합성 CoM 수평 offset dx(q1)의 영점을 찾는다. 안정 평형 = CoM이 힙 **아래**(dz<0)인 영점.
CLI: python _G_hang_pred.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np
import mujoco as mjm

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import safe
import fs_runner as FR

BELOW = ("hip_rotor", "thigh", "crank", "coupler", "calf")   # 힙 축 아래에 매달린 전부
Q2_DEG = [-170, -155, -140, -126, -110, -95, -80, -65, -50]
CANDS = [("현행 p24 (com_z −0.1094)", "0.0"),
         ("CAD      (com_z −0.0565)", "0.053")]


def _ctx(ft):
    m = ft["model"]
    ids = [mjm.mj_name2id(m, mjm.mjtObj.mjOBJ_BODY, n) for n in BELOW]
    if min(ids) < 0:
        raise ValueError(f"바디 누락: {list(zip(BELOW, ids))}")
    jid = mjm.mj_name2id(m, mjm.mjtObj.mjOBJ_JOINT, "hip_m")
    return m, np.array(ids), jid, np.array([m.body_mass[i] for i in ids], float)


def com_offset(ft, ctx, q1, q2):
    """자세 (q1,q2)에서 힙 축 기준 합성 CoM의 (수평 dx, 수직 dz) [m]."""
    m, ids, jid, mass = ctx
    iq = ft["iq"]
    md = mjm.MjData(m)
    md.qpos[iq["base_z"]] = 1.0
    md.qpos[iq["hip_m"]] = -q1 - np.pi / 2
    md.qpos[iq["hip"]] = 0.0                  # 무동력 = 힙 직렬스프링 무부하
    md.qpos[iq["knee_motor"]] = -q2
    md.qpos[iq["cpin"]] = q2
    md.qpos[iq["knee"]] = -q2
    mjm.mj_forward(m, md)
    com = (md.xipos[ids] * mass[:, None]).sum(0) / mass.sum()
    anc = md.xanchor[jid]
    return float(com[0] - anc[0]), float(com[2] - anc[2])


def equil(ft, ctx, q2, n=721):
    """dx(q1)=0 이고 CoM이 힙 아래(dz<0)인 **안정 평형** q1 목록 [rad]."""
    qs = np.linspace(-np.pi, np.pi, n)
    dx = np.empty(n); dz = np.empty(n)
    for i, q in enumerate(qs):
        dx[i], dz[i] = com_offset(ft, ctx, float(q), q2)
    out = []
    for i in range(n - 1):
        if dx[i] == 0.0 or dx[i] * dx[i + 1] < 0:
            a, b = qs[i], qs[i + 1]
            for _ in range(40):                     # 이분법 (결정적·빠름)
                mmid = 0.5 * (a + b)
                if com_offset(ft, ctx, float(a), q2)[0] * com_offset(ft, ctx, float(mmid), q2)[0] <= 0:
                    b = mmid
                else:
                    a = mmid
            r = 0.5 * (a + b)
            if com_offset(ft, ctx, float(r), q2)[1] < 0:      # 안정(아래로 매달림)
                out.append(float(r))
    return out


def main():
    print("무동력 매달림 평형각 예측 — thigh 묶음 1.05kg 고정, 힙 아래 전 바디 합성 CoM 기준\n")
    R = {}
    for name, dz in CANDS:
        os.environ["FS_MBODY"] = "thigh=1.05"
        os.environ["FS_COMZ"] = f"thigh={dz}"
        ft = FR.fs_twin()
        ctx = _ctx(ft)
        R[name] = [equil(ft, ctx, np.radians(v)) for v in Q2_DEG]

    print(f"{'무릎 q2[°]':>10} | {'현행 예측 q1*[°]':>18} | {'CAD 예측 q1*[°]':>18} | {'차이[°]':>8}")
    diffs = []
    for k, v in enumerate(Q2_DEG):
        a = R[CANDS[0][0]][k]; b = R[CANDS[1][0]][k]
        sa = ", ".join(f"{np.degrees(x):.1f}" for x in a) or "없음"
        sb = ", ".join(f"{np.degrees(x):.1f}" for x in b) or "없음"
        d = (abs(np.degrees(a[0] - b[0])) if (len(a) == 1 and len(b) == 1) else np.nan)
        diffs.append(d)
        print(f"{v:10.0f} | {sa:>18} | {sb:>18} | {d:8.1f}" if np.isfinite(d)
              else f"{v:10.0f} | {sa:>18} | {sb:>18} |     (다중해)")
    d = np.array(diffs, float)
    if np.isfinite(d).any():
        order = np.argsort(-np.nan_to_num(d, nan=-1))
        print("\n★ 판별력 순위 (예측 차이가 큰 무릎 각도부터):")
        for i in order[:5]:
            if np.isfinite(d[i]) and d[i] > 0.05:
                print(f"   q2 = {Q2_DEG[i]:>5}°  →  힙 평형각 예측 차이 **{d[i]:.1f}°**")


if __name__ == "__main__":
    main()
