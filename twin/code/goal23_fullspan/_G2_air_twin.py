# -*- coding: utf-8 -*-
"""_G2_air_twin — 26_08_02 실측 동정값 vs 디지털 트윈 (마라톤G 재분석 결론부).

입력: `_G2_air_ident.json` (위상자 기반, DC 오프셋 축퇴 없음, 부트스트랩 신뢰구간)
대상: 힙축 관성 M11(q2) · 중력 레버 gA/gB · 관절 마찰.

★ 1차 분석의 계산 오류 정정
   회귀 파라미터 Is1 은 표준 2링크 표기의 (Is1 + Is2) 를 흡수한다
   (τ1 의 q̈1 계수 = M11 = Is1_std + Is2_std + 2·Kv·cos q2 인데 회귀에선 Is1_reg + 2Kv·cos q2).
   1차 분석(_G_sysid_air.main)은 `Is1 + Is2 + 2Kv cos q2` 로 계산해 **Is2 를 이중계상**했다.
   여기서는 M11 = Is1r + 2·Kv·cos q2 (정본).

CLI: python _G2_air_twin.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np
import mujoco as mjm

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import safe                                   # noqa: E402
import fs_runner as FR                        # noqa: E402
from _G_hang_pred import _ctx, BELOW          # noqa: E402

Q2S = (-110.0, -85.0, -62.0)                  # 실험의 세 무릎 자세
Q1_0 = np.radians(-45.2)


def twin(comz=None, mthigh=None, reset=True):
    if reset:
        for k in ("FS_MBODY", "FS_COMZ", "FS_IBODY"):
            os.environ.pop(k, None)
    if mthigh is not None:
        os.environ["FS_MBODY"] = f"thigh={mthigh}"
    if comz is not None:
        os.environ["FS_COMZ"] = f"thigh={comz}"
    return FR.fs_twin()


def pose(ft, q1, q2):
    m = ft["model"]; iq = ft["iq"]
    md = mjm.MjData(m)
    md.qpos[iq["base_z"]] = 1.0
    md.qpos[iq["hip_m"]] = -q1 - np.pi / 2
    md.qpos[iq["hip"]] = 0.0
    md.qpos[iq["knee_motor"]] = -q2
    md.qpos[iq["cpin"]] = q2
    md.qpos[iq["knee"]] = -q2
    mjm.mj_forward(m, md)
    return md


def M11(ft, ctx, q2):
    """힙 축 둘레 총관성 (평행축 정리, 힙 아래 전 바디)."""
    m, ids, jid, mass = ctx
    md = pose(ft, Q1_0, q2)
    anc = md.xanchor[jid]
    I = 0.0
    for i in ids:
        d = md.xipos[i] - anc
        I += float(m.body_inertia[i][1]) + float(m.body_mass[i]) * (d[0] ** 2 + d[2] ** 2)
    return I


def grav(ft):
    """트윈의 중력토크를 gA·cos q1 + gB·cos(q1+q2) 로 회귀 (qvel=0 → qfrc_bias = 순수 중력)."""
    dofh = ft["dof"]["hip_m"]
    X, y = [], []
    for a in np.radians(np.linspace(-60, -30, 13)):
        for b in np.radians(np.linspace(-125, -60, 14)):
            md = pose(ft, a, b)
            y.append(-float(md.qfrc_bias[dofh]))
            X.append([np.cos(a), np.cos(a + b)])
    g, *_ = np.linalg.lstsq(np.array(X), np.array(y), rcond=None)
    return float(g[0]), float(g[1])


def mass_report(ft, ctx):
    m, ids, jid, mass = ctx
    md = pose(ft, Q1_0, np.radians(-85.0))
    anc = md.xanchor[jid]
    com = (md.xipos[ids] * mass[:, None]).sum(0) / mass.sum()
    return mass.sum(), float(np.linalg.norm(com - anc)), float(m.body_mass.sum())


def main():
    S = json.load(io.open(HERE / "_G2_air_ident.json", encoding="utf-8"))
    th = dict(zip(S["names"], S["theta"]))
    Mm = {int(k): v for k, v in S["M11"].items()}
    print("=" * 104)
    print("① 힙축 관성 M11(q2) — 실측(위상자, 오프셋 무관) vs 트윈")
    print("   ※ 1차 분석은 M11 = Is1+Is2+2Kv·cos q2 로 Is2를 이중계상했다 → 여기서는 Is1r+2Kv·cos q2")
    CAND = [("현행 p24 (트윈 기본)", dict()),
            ("+thigh 질량 1.05", dict(mthigh=1.05)),
            ("+CoM CAD (comz +0.053)", dict(mthigh=1.05, comz=0.053)),
            ("+CoM 1차분석 채택(+0.073)", dict(mthigh=1.05, comz=0.073))]
    print(f"{'후보':<28}" + "".join(f"{f'M11(q2={q:+.0f}°)':>17}" for q in Q2S)
          + f"{'평균 오차%':>11}")
    rows = {}
    for lab, kw in CAND:
        ft = twin(**kw); ctx = _ctx(ft)
        v = [M11(ft, ctx, np.radians(q)) for q in Q2S]
        e = [100 * (v[i] / Mm[int(Q2S[i])][0] - 1) for i in range(3)]
        rows[lab] = (v, e, grav(ft), mass_report(ft, ctx))
        print(f"{lab:<28}" + "".join(f"{v[i]:11.5f}({e[i]:+5.1f}%)" for i in range(3))
              + f"{np.mean(np.abs(e)):11.1f}")
    print(f"{'실측 (95% 신뢰구간)':<28}" + "".join(
        f"{Mm[int(q)][0]:11.5f}(±{100*Mm[int(q)][1]/Mm[int(q)][0]:4.1f}%)" for q in Q2S))

    print("\n" + "=" * 104)
    print("② 중력 레버 gA·gB — 실측 신뢰구간과 트윈")
    i_gA, i_gB = S["names"].index("gA"), S["names"].index("gB")
    print(f"   실측 gA = {th['gA']:.4f} Nm  95%[{S['ci_lo'][i_gA]:.4f}, {S['ci_hi'][i_gA]:.4f}]  "
          f"({S['verdict']['gA']})")
    print(f"   실측 gB = {th['gB']:.4f} Nm  95%[{S['ci_lo'][i_gB]:.4f}, {S['ci_hi'][i_gB]:.4f}]  "
          f"({S['verdict']['gB']})")
    print(f"{'후보':<28}{'트윈 gA':>10}{'실측대비':>10}{'구간내?':>8}{'트윈 gB':>10}{'실측대비':>10}{'구간내?':>8}")
    for lab, _ in CAND:
        gA, gB = rows[lab][2]
        inA = "예" if S["ci_lo"][i_gA] <= gA <= S["ci_hi"][i_gA] else "아니오"
        inB = "예" if S["ci_lo"][i_gB] <= gB <= S["ci_hi"][i_gB] else "아니오"
        print(f"{lab:<28}{gA:10.4f}{100*(gA/th['gA']-1):+9.1f}%{inA:>8}"
              f"{gB:10.4f}{100*(gB/th['gB']-1):+9.1f}%{inB:>8}")

    print("\n" + "=" * 104)
    print("③ comz 스캔 — 실측 gA·M11 을 동시에 만족하는 무게중심이 있는가")
    print(f"{'comz[m]':>9}{'thigh CoM(힙기준)':>18}{'트윈 gA':>10}{'gA 오차%':>10}"
          + "".join(f"{f'M11({q:+.0f})오차%':>15}" for q in Q2S))
    best = None
    for cz in np.arange(0.00, 0.121, 0.010):
        ft = twin(mthigh=1.05, comz=float(cz)); ctx = _ctx(ft)
        gA, gB = grav(ft)
        v = [M11(ft, ctx, np.radians(q)) for q in Q2S]
        e = [100 * (v[i] / Mm[int(Q2S[i])][0] - 1) for i in range(3)]
        eg = 100 * (gA / th["gA"] - 1)
        sc = abs(eg) + np.mean(np.abs(e))
        if best is None or sc < best[0]:
            best = (sc, cz, gA, e, eg)
        m = ft["model"]
        bi = mjm.mj_name2id(m, mjm.mjtObj.mjOBJ_BODY, "thigh")
        print(f"{cz:9.3f}{float(m.body_ipos[bi][2]):18.4f}{gA:10.4f}{eg:+10.1f}"
              + "".join(f"{e[i]:+15.1f}" for i in range(3)))
    print(f"   → 동시 최적 comz = {best[1]:.3f} m (gA 오차 {best[4]:+.1f}%, "
          f"M11 평균 오차 {np.mean(np.abs(best[3])):.1f}%)")

    print("\n" + "=" * 104)
    print("④ 관절 마찰 — 실측 vs 트윈 현행값")
    fh, fk = S["fric"]["힙"], S["fric"]["무릎"]
    ft = twin(); m = ft["model"]
    for nm, meas in (("hip_m", fh), ("knee_motor", fk)):
        j = safe.dofadr(m, nm, mjm)
        print(f"   {nm:<12} 트윈 damping {float(m.dof_damping[j]):.4f} / frictionloss "
              f"{float(m.dof_frictionloss[j]):.4f}   ←→   실측 점성 {meas[0][0]:.4f}±{meas[1][0]:.4f} / "
              f"쿨롱 {abs(meas[0][1]):.4f}±{meas[1][1]:.4f}")
    print("   ※ 무릎 점성은 (ω,A) 조합이 2개뿐이라 조건수 43.9 — 쿨롱만 신뢰, 점성은 미확정")

    print("\n" + "=" * 104)
    print("⑤ 질량 대장 확인")
    for lab, _ in CAND:
        tm, com, tot = rows[lab][3]
        print(f"   {lab:<28} 힙 아래 질량 {tm:.3f} kg · 힙축~합성CoM {com*1000:6.1f} mm · 총질량 {tot:.3f} kg")


if __name__ == "__main__":
    main()
