# -*- coding: utf-8 -*-
"""_G2_air_close — 재분석 마무리 두 가지 확인.

Ⓐ 마찰 회계: a_hat 변환식이 이미 쿨롱항 (A2 + A3·|Iq|)·sign(v) 를 **빼고** 있다.
   회귀의 fc1 이 음수로 나온 것은 "a_hat 이 실제보다 더 많이 뺐다"는 뜻 —
   ModeA(변환토크 주입)용 트윈이 가져야 할 관절 마찰은 fc1 그 자체(음수→0)이지,
   |fc1| 이 아니다. 1차 분석은 |fc1| 을 트윈 frictionloss 와 직접 비교했다.
Ⓑ Kv(연성 관성) 2배 문제의 소재: 트윈 바디별 질량·CoM 을 나열해 어느 바디가
   m·l1·r2 를 과대하게 만드는지 특정한다.
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np
import mujoco as mjm

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_runner as FR                        # noqa: E402
from _G2_air_fit import A_P, KT, GR, CF       # noqa: E402
from _G2_air_twin import twin, pose, Q1_0     # noqa: E402


def main():
    S = json.load(io.open(HERE / "_G2_air_ident.json", encoding="utf-8"))
    fh = S["fric"]["힙"]; fk = S["fric"]["무릎"]

    print("=" * 100)
    print("Ⓐ 마찰 회계 — a_hat 이 이미 뺀 쿨롱 vs 회귀가 되돌린 양")
    print(f"   a_hat 쿨롱항 = A2 + A3·|Iq| = {A_P[2]:.4f} + {A_P[3]:.4f}·|Iq|   "
          f"(Iq = {CF/(GR*KT):.4f}·raw)")
    print(f"{'raw 토크':>9}{'|Iq|[A]':>9}{'a_hat이 뺀 쿨롱[Nm]':>20}{'회귀 fc1':>10}"
          f"{'실제 잔여 마찰[Nm]':>19}")
    for r in (0.5, 1.0, 2.0, 3.0, 5.0):
        Iq = (CF / (GR * KT)) * r
        sub = A_P[2] + A_P[3] * Iq
        print(f"{r:9.1f}{Iq:9.3f}{sub:20.4f}{fh[0][1]:10.4f}{sub + fh[0][1]:19.4f}")
    print(f"   → 힙: 정지~저부하에서 실제 관절 쿨롱 ≈ {A_P[2]+A_P[3]*(CF/(GR*KT))*0.65+fh[0][1]:.3f} Nm, "
          f"고부하(raw 5)에서 {A_P[2]+A_P[3]*(CF/(GR*KT))*5+fh[0][1]:.3f} Nm")
    print(f"   → **ModeA 트윈(변환토크 주입)이 가져야 할 관절 마찰 = 회귀값 그대로** "
          f"= 점성 {fh[0][0]:+.4f}, 쿨롱 {fh[0][1]:+.4f}")
    print(f"      쿨롱이 음수 = a_hat 과다차감 → 트윈 frictionloss 는 0 이 정답에 가깝다 "
          f"(현행 0.2383).")
    print(f"   → 무릎: 점성 {fk[0][0]:+.4f}, 쿨롱 {fk[0][1]:+.4f} (현행 트윈 0.1496 / 0.2469)")

    print("\n" + "=" * 100)
    print("Ⓑ Kv (연성 관성 = m·l1·r2) 과대의 소재 — 트윈 바디별 질량·무게중심")
    ft = twin()
    m = ft["model"]
    md = pose(ft, Q1_0, np.radians(-85.0))
    jid_k = mjm.mj_name2id(m, mjm.mjtObj.mjOBJ_JOINT, "knee")
    anc_k = md.xanchor[jid_k]
    jid_h = mjm.mj_name2id(m, mjm.mjtObj.mjOBJ_JOINT, "hip_m")
    anc_h = md.xanchor[jid_h]
    print(f"{'바디':<12}{'질량[kg]':>10}{'관성 Iyy':>10}{'힙축 거리[mm]':>14}{'무릎축 거리[mm]':>16}"
          f"{'m·r_knee[kg·m]':>16}")
    tot_first = 0.0
    for nm in ("hip_rotor", "thigh", "crank", "coupler", "calf", "foot"):
        i = mjm.mj_name2id(m, mjm.mjtObj.mjOBJ_BODY, nm)
        if i < 0:
            continue
        d_h = np.linalg.norm((md.xipos[i] - anc_h)[[0, 2]])
        d_k = np.linalg.norm((md.xipos[i] - anc_k)[[0, 2]])
        mass = float(m.body_mass[i])
        below_knee = nm in ("calf", "foot")
        fm = mass * d_k if below_knee else 0.0
        tot_first += fm
        print(f"{nm:<12}{mass:10.4f}{float(m.body_inertia[i][1]):10.5f}{d_h*1000:14.1f}"
              f"{d_k*1000:16.1f}{fm:16.5f}{'  ← 무릎 아래' if below_knee else ''}")
    L1 = 0.25
    print(f"   트윈 Kv = l1 · Σ(m·r_knee) = {L1:.3f} × {tot_first:.5f} = {L1*tot_first:.5f} kg·m²")
    print(f"   실측 Kv = {S['theta'][S['names'].index('Kv')]:.5f} ± "
          f"{S['sd'][S['names'].index('Kv')]:.5f} kg·m²  → 트윈이 "
          f"{L1*tot_first/S['theta'][S['names'].index('Kv')]:.2f} 배")
    print(f"   실측이 요구하는 Σ(m·r_knee) = {S['theta'][S['names'].index('Kv')]/L1:.5f} kg·m "
          f"(예: calf 질량 유지 시 무릎축~CoM 거리 "
          f"{1000*S['theta'][S['names'].index('Kv')]/L1/max(tot_first/max(1e-9,tot_first)*sum(float(m.body_mass[mjm.mj_name2id(m,mjm.mjtObj.mjOBJ_BODY,n)]) for n in ('calf','foot')),1e-9):.1f} mm)")

    print("\n" + "=" * 100)
    print("Ⓒ 무릎쪽 관성 Is2 대조 (무릎축 둘레, 무릎 아래 바디)")
    I2 = 0.0
    for nm in ("calf", "foot"):
        i = mjm.mj_name2id(m, mjm.mjtObj.mjOBJ_BODY, nm)
        if i < 0:
            continue
        d = (md.xipos[i] - anc_k)[[0, 2]]
        I2 += float(m.body_inertia[i][1]) + float(m.body_mass[i]) * float(d @ d)
    j = S["names"].index("Is2")
    print(f"   트윈 Is2 = {I2:.5f} kg·m²   실측 {S['theta'][j]:.5f} ± {S['sd'][j]:.5f} "
          f"→ 트윈이 {I2/S['theta'][j]:+.2f} 배 ({100*(I2/S['theta'][j]-1):+.1f}%)")


if __name__ == "__main__":
    main()
