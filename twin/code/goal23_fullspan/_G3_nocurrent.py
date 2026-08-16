# -*- coding: utf-8 -*-
"""_G3_nocurrent — 26_08_07 **무동력 평형각** 분석 (토크 센서를 전혀 쓰지 않는 측정).

실험(사용자 08-07): 모터 전원 OFF → 무릎을 세 각도에 두고, 각 각도마다 힙을 들었다 놓기를
**4회** = 정지점 총 12개. 무릎은 backdrivability 정지마찰로 그 자리에 머문다.

왜 강력한가: 정지점은 "힙축 아래 합성 무게중심이 힙축 바로 밑"이라는 **순수 기하 조건**이다.
  gA·cos q1* + gB·cos(q1*+q2) = ±τ_c   (τ_c = 무동력 힙 정지마찰, 밴드 폭)
  → 양변을 gA로 나누면 **ρ = gB/gA 와 τ_c/gA 만 남는다**.
  즉 토크 센서·a_hat 변환·오프셋·척도가 **원리적으로 개입하지 않는다**.
  ρ는 H1(토크 척도 오차)/H2(질량 분포 오차) 어느 쪽이든 **불변**이므로,
  트윈의 ρ와 비교하면 **질량 분포의 '모양'만** 골라 판정할 수 있다.

정지점 판정: |dq1|,|dq2| < 0.05 rad/s 가 0.4s 이상 지속 + **직전 1s 안에 |dq1| > 1.0** (실제 스윙 후)
             → 손으로 붙잡고 있던 구간과 구분된다.
CLI: python _G3_nocurrent.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                   # noqa: E402

SESS = FD.ROOT / "26_08_07" / "no_current"
FS = 500.0
# 정지 판정은 **각도 기반**. 기록 dq는 1샘플 차분이라 양자화 계단이 0.0122 rad/s 로 굵어
# 속도 문턱(0.05)으로는 정지를 못 가른다. 엔코더 각도 분해능은 0.0219° 로 훨씬 곱다.
W_STILL = 150          # 0.3 s 창
R_STILL = 0.15         # 창 내 각도 변화폭 한계 [deg]
T_STILL = 0.4          # 최소 지속 [s]
V_SWING = 1.0          # 직전 1s 최대 |dq1| — 이보다 크면 '스윙 후 정착'


def load():
    h = pd.read_excel(SESS / "hip.xlsx"); k = pd.read_excel(SESS / "knee.xlsx")
    n = min(len(h), len(k))
    t = np.array(h["Time"].to_numpy(float)[:n], float, copy=True); t -= t[0]
    return dict(t=t, q1=h["currentAngle"].to_numpy(float)[:n],
                q2=k["currentAngle"].to_numpy(float)[:n],
                dq1=h["currentAngleVelocity"].to_numpy(float)[:n],
                dq2=k["currentAngleVelocity"].to_numpy(float)[:n], n=n)


def rests(d):
    from numpy.lib.stride_tricks import sliding_window_view
    q1d, q2d = np.degrees(d["q1"]), np.degrees(d["q2"])
    W1 = sliding_window_view(q1d, W_STILL); W2 = sliding_window_view(q2d, W_STILL)
    still = ((W1.max(1) - W1.min(1)) < R_STILL) & ((W2.max(1) - W2.min(1)) < R_STILL)
    idx = np.flatnonzero(np.diff(still.astype(int)))
    edges = np.concatenate([[0], idx + 1, [len(still)]])
    out = []
    nmin = int(T_STILL * FS)
    for a, b in zip(edges[:-1], edges[1:]):
        if not still[a] or (b - a) < nmin:
            continue
        pre = slice(max(0, a - int(1.0 * FS)), max(1, a))
        vmax = float(np.abs(d["dq1"][pre]).max()) if a > 0 else 0.0
        sl = slice(a + (b - a) // 2, b + W_STILL - 1)     # 뒷절반 (완전 정착)
        out.append(dict(i0=a, i1=b, t0=d["t"][a], dur=(b - a) / FS, vpre=vmax,
                        q1=float(np.median(d["q1"][sl])), q2=float(np.median(d["q2"][sl])),
                        settled=vmax > V_SWING))
    return out


def G(q1, q2, rho):
    return np.cos(q1) + rho * np.cos(q1 + q2)


def main():
    d = load()
    R = rests(d)
    print("=" * 104)
    print("① 정지 구간 전수 (■ = 스윙 후 정착 = 평형점 후보 · □ = 손으로 잡고 있던 구간)")
    print(f"{'':2}{'t0[s]':>7}{'지속s':>7}{'직전|dq1|max':>12}{'q1[°]':>9}{'q2[°]':>9}")
    for r in R:
        print(f"{'■' if r['settled'] else '□':2}{r['t0']:7.1f}{r['dur']:7.2f}{r['vpre']:12.2f}"
              f"{np.degrees(r['q1']):9.2f}{np.degrees(r['q2']):9.2f}")

    S = [r for r in R if r["settled"]]
    print(f"\n정착 정지점 {len(S)}개 (사용자 보고 12개)")

    # 무릎 각도로 그룹핑 (3° 이내 동일 그룹)
    groups = []
    for r in sorted(S, key=lambda x: x["q2"]):
        if groups and abs(np.degrees(r["q2"] - groups[-1][0]["q2"])) < 3.0:
            groups[-1].append(r)
        else:
            groups.append([r])
    print("\n" + "=" * 104)
    print("② 무릎 각도별 정지점 — 폭이 곧 정지마찰 밴드")
    print(f"{'q2 평균[°]':>11}{'개수':>5}{'정지 q1 목록[°]':>44}{'최소':>9}{'최대':>9}{'중앙':>9}{'폭':>7}")
    for g in groups:
        q1s = sorted(np.degrees([r["q1"] for r in g]))
        print(f"{np.degrees(np.mean([r['q2'] for r in g])):11.2f}{len(g):5d}"
              f"{'  '.join(f'{v:+7.2f}' for v in q1s):>44}"
              f"{min(q1s):9.2f}{max(q1s):9.2f}{np.mean([min(q1s),max(q1s)]):9.2f}"
              f"{max(q1s)-min(q1s):7.2f}")

    # ── ③ ρ = gB/gA 와 τ_c/gA 적합 ──
    # 각 정지점은 |G(q1*,q2,ρ)| ≤ τ_c/gA 를 만족해야 한다.
    # 밴드 중심을 0으로 만드는 ρ를 찾는다: 그룹별 (max G + min G)/2 = 0 이 되도록.
    print("\n" + "=" * 104)
    print("③ ρ = gB/gA 적합 — 그룹별 밴드 중심이 0이 되는 값 (토크 센서 불개입)")
    rho_grid = np.linspace(-0.2, 1.2, 28001)
    cost = np.zeros_like(rho_grid)
    for gi, g in enumerate(groups):
        vals = np.array([[G(r["q1"], r["q2"], rho) for r in g] for rho in rho_grid])
        cost += ((vals.max(1) + vals.min(1)) / 2.0) ** 2
    rho = float(rho_grid[np.argmin(cost)])
    band = []
    for g in groups:
        v = np.array([G(r["q1"], r["q2"], rho) for r in g])
        band.append((v.min(), v.max()))
    tc_over_gA = float(np.mean([0.5 * (b[1] - b[0]) for b in band]))
    print(f"   ρ = gB/gA = **{rho:.4f}**")
    print(f"{'q2[°]':>9}{'밴드 하한 G':>13}{'밴드 상한 G':>13}{'중심':>10}{'반폭 = τ_c/gA':>15}")
    for g, b in zip(groups, band):
        print(f"{np.degrees(np.mean([r['q2'] for r in g])):9.2f}{b[0]:13.4f}{b[1]:13.4f}"
              f"{0.5*(b[0]+b[1]):10.4f}{0.5*(b[1]-b[0]):15.4f}")
    print(f"   평균 τ_c/gA = {tc_over_gA:.4f}  → gA=1.053 Nm 가정 시 무동력 힙 정지마찰 "
          f"τ_c ≈ {tc_over_gA*1.053:.3f} Nm")

    # ── ④ 트윈·기존 동정과 대조 ──
    print("\n" + "=" * 104)
    print("④ ρ 대조 — 이 값은 토크 척도(H1)와 무관하므로 **질량 분포의 모양만** 판정한다")
    import mujoco as mjm
    from _G2_air_twin import twin, grav
    S2 = json.load(io.open(HERE / "_G2_air_ident.json", encoding="utf-8"))
    th = dict(zip(S2["names"], S2["theta"]))
    lo = dict(zip(S2["names"], S2["ci_lo"])); hi = dict(zip(S2["names"], S2["ci_hi"]))
    print(f"{'출처':<34}{'gA':>9}{'gB':>9}{'ρ=gB/gA':>10}{'무동력 ρ 대비':>14}")
    print(f"{'무동력 평형 (본 분석)':<34}{'-':>9}{'-':>9}{rho:10.4f}{'기준':>14}")
    print(f"{'26_08_02 위상자 동정':<34}{th['gA']:9.4f}{th['gB']:9.4f}"
          f"{th['gB']/th['gA']:10.4f}{100*((th['gB']/th['gA'])/rho-1):+13.1f}%")
    print(f"{'   └ gB 95% 구간으로 본 ρ 범위':<34}{'':>9}{'':>9}"
          f"{f'{lo[chr(103)+chr(66)]/th[chr(103)+chr(65)]:.3f}~{hi[chr(103)+chr(66)]/th[chr(103)+chr(65)]:.3f}':>10}{'':>14}")
    for lab, kw in (("트윈 현행 p24", dict()),
                    ("트윈 +CoM 0.073", dict(mthigh=1.05, comz=0.073)),
                    ("트윈 +CoM 0.080", dict(mthigh=1.05, comz=0.080))):
        ft = twin(**kw); gA, gB = grav(ft)
        print(f"{lab:<34}{gA:9.4f}{gB:9.4f}{gB/gA:10.4f}{100*((gB/gA)/rho-1):+13.1f}%")

    # ── ⑤ 예측 정지각 대조 ──
    print("\n" + "=" * 104)
    print("⑤ 무릎 각도별 **예측 정지각** (마찰 없는 평형) — 실측 밴드 중심과 직접 비교")
    print(f"{'q2[°]':>9}{'실측 밴드중심':>13}{'실측 폭':>9} | {'ρ적합':>9}{'위상자ρ':>10}"
          f"{'트윈 p24':>10}{'트윈 .073':>11}")

    def eqang(q2, rho_):
        # cos q1 + rho cos(q1+q2) = 0  →  tan q1 = −(1+rho cos q2)/(rho sin q2)
        num = 1.0 + rho_ * np.cos(q2)
        den = rho_ * np.sin(q2)
        return np.degrees(np.arctan2(-num, den)) if den != 0 else np.nan

    ft24 = twin(); gA24, gB24 = grav(ft24)
    ft73 = twin(mthigh=1.05, comz=0.073); gA73, gB73 = grav(ft73)
    for g in groups:
        q2m = float(np.mean([r["q2"] for r in g]))
        q1s = np.degrees([r["q1"] for r in g])
        c = 0.5 * (q1s.min() + q1s.max())
        row = [eqang(q2m, rho), eqang(q2m, th["gB"] / th["gA"]),
               eqang(q2m, gB24 / gA24), eqang(q2m, gB73 / gA73)]
        row = [v + 180 if v > 0 else v for v in row]     # 안정 평형 가지 선택
        print(f"{np.degrees(q2m):9.2f}{c:13.2f}{q1s.max()-q1s.min():9.2f} | "
              + "".join(f"{v:10.2f}" for v in row[:1]) + f"{row[1]:10.2f}{row[2]:10.2f}{row[3]:11.2f}")

    json.dump(dict(rho=rho, tc_over_gA=tc_over_gA, n_settled=len(S),
                   groups=[[{"q1": r["q1"], "q2": r["q2"], "t0": r["t0"]} for r in g] for g in groups]),
              io.open(HERE / "_G3_nocurrent.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장: _G3_nocurrent.json")


if __name__ == "__main__":
    main()
