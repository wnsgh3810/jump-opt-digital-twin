# -*- coding: utf-8 -*-
"""_GHP_report — _GHP_posture10.json 을 표와 회귀로 읽는다 (재생 없음, 정리만).

★ 교환비는 **여기서 다시 계산한다** (JSON 안의 r 은 가지 선택 사고가 있던 판이다).
"""
import io, json, os, sys
from pathlib import Path
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["FS_CVT_XML"] = "0"
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "goal22" / "p18_cvt"))
os.chdir(HERE)
import numpy as np
from cvt_core import closure
import _GHP_posture10 as PP

D = json.load(io.open("_GHP_posture10.json", encoding="utf-8"))
R = D["rows"]; F = D["fails"]
CASES = [("cvt/no_load", 0.0), ("cvt/load_2.5", 2.5), ("cvt/load_5", 5.0), ("no_cvt/no_load", 0.0)]
EDG = np.arange(-180, -9, 10.0)
BINS = [(EDG[i], EDG[i + 1]) for i in range(len(EDG) - 1)]
TAB_C = PP.ratio_table(0.025193)     # 변속기 trial 실측 l_i (Clutch.xlsx 중앙값)
TAB_N = PP.ratio_table(0.030)        # 무변속 (평행사변형)

# 모델이 실제로 쓰는 표 (RU.rtab) — 손실항이 이걸로 amp 를 만든다
import fs_cvt as FC
QG, RG = FC.RU.rtab(0.025193)


def r_model(deg):
    return float(np.interp(np.radians(-deg), QG, RG))


def amp_of(r):
    return max(1.0 / max(abs(r), 0.2) - 1.0, 0.0)


for x in R:                       # 가지 고친 교환비로 갱신
    tab = TAB_N if not x["cvt"] else TAB_C
    x["r"], x["drdq"] = PP.r_at(tab, x["crank"])

print("=" * 120)
print("표 1 — 교환비 곡선 (같은 각도축). r = 무릎각속도/크랭크각속도 = 크랭크토크/무릎토크")
print(f"{'크랭크 구간[도]':>15s} {'r(25.19mm)':>11s} {'1/r−1':>8s} {'dr/dθ[1/rad]':>13s} "
      f"{'r(30mm)':>8s} | {'모델표 r':>9s} {'모델 amp':>9s} {'참 amp(캡)':>11s}")
for a, b in BINS:
    c = 0.5 * (a + b)
    r1, d1 = PP.r_at(TAB_C, c)
    r0, _ = PP.r_at(TAB_N, c)
    rm = r_model(c)
    print(f"{f'[{a:.0f},{b:.0f})':>15s} {r1:11.4f} {1/r1-1:8.2f} {d1:13.4f} {r0:8.4f} | "
          f"{rm:9.4f} {amp_of(rm):9.3f} {amp_of(r1):11.3f}")
for nm, tab in (("변속 25.19mm", TAB_C), ("무변속 30.0mm", TAB_N)):
    ang, r, dr = tab
    i = int(np.argmin(np.abs(r)))
    print(f"  {nm}: r 최소 {r[i]:.4f} @ {ang[i]:.1f}도(사점) · r(−175)={np.interp(-175,ang[::-1],r[::-1]):.4f}"
          f" · r(−90)={np.interp(-90,ang[::-1],r[::-1]):.4f} · 최대 {r.max():.4f} @ {ang[int(np.argmax(r))]:.1f}도")

print()
print("=" * 120)
print("표 2 — 모자란 무릎 명령 토크 Δ [명령 N·m] · 크랭크 10도 구간 평균 (0=완벽, +=모델이 덜 민다)")
hdr = f"{'구간[도]':>13s} {'r':>6s} {'1/r−1':>7s}"
for nm, _ in CASES:
    hdr += f" | {nm:>14s}"
print(hdr)
print("-" * 120)
for a, b in BINS:
    c = 0.5 * (a + b)
    r1, _ = PP.r_at(TAB_C, c)
    line = f"{f'[{a:.0f},{b:.0f})':>13s} {r1:6.3f} {1/r1-1:7.2f}"
    for nm, _p in CASES:
        v = [x["delta"] for x in R if x["sub"] == nm and a <= x["crank"] < b]
        line += f" | {np.mean(v):+8.2f}({len(v):3d})" if v else f" | {'':>14s}"
    print(line)
print("-" * 120)
print("괄호 = 창 개수 (0.15초 창을 0.02초 간격으로 밀어 이웃끼리 87% 겹친다 → 독립 표본은 대략 /7).")

print()
print("표 2b — 같은 구간: 축토크 환산 Δ_axis [축 N·m] / 크랭크속도 dq2 [rad/s] / 명령 raw2 [N·m]")
print(f"{'구간 좌단[도]':>16s}" + "".join(f"{a:7.0f}" for a, b in BINS))
for nm, _p in CASES:
    for key, lab in (("delta_axis", "Δ_axis"), ("dq2", "dq2"), ("raw2", "raw2")):
        s = f"{nm if key=='delta_axis' else '':>9s} {lab:>6s}"
        for a, b in BINS:
            z = [x[key] for x in R if x["sub"] == nm and a <= x["crank"] < b]
            s += f"{np.mean(z):+7.2f}" if z else "       "
        print(s)

print()
print("표 3 — 되찾기 실패(±8 명령 N·m 안에서 부호 안 바뀜) = 결손이 8 N·m 를 넘는 자리")
for nm, _p in CASES:
    s = [x for x in F if x["sub"] == nm]
    if not s:
        print(f"  {nm:16s} 실패 0"); continue
    cr = np.array([x["crank"] for x in s])
    print(f"  {nm:16s} {len(s):3d}창 · 크랭크 {cr.min():7.1f}~{cr.max():7.1f}도 · "
          f"Δ=−8 잔여 {np.mean([x['err_lo'] for x in s]):+7.2f}도 / Δ=+8 잔여 {np.mean([x['err_hi'] for x in s]):+7.2f}도")


def r2_origin(y, x):
    k = float(np.sum(x * y) / np.sum(x * x)) if np.sum(x * x) > 0 else np.nan
    return k, 1 - float(np.sum((y - k * x) ** 2)) / float(np.sum(y ** 2))


def corr(y, x):
    return np.nan if (len(y) < 3 or np.std(x) < 1e-12) else float(np.corrcoef(x, y)[0, 1])


print()
print("=" * 120)
print("표 4 — Δ 의 모양 가르기: 후보 설명변수와의 상관 r_p (부호 포함)")
print("  amp=1/r−1 (모델의 변속기 손실 모양) · r · dr/dθ · θ(크랭크각) · |raw2|(명령크기) · dq2(속도)")
print(f"{'경우':>14s} {'n':>4s} {'amp':>7s} {'r':>7s} {'dr/dθ':>7s} {'θ':>7s} {'|raw2|':>7s} {'dq2':>7s}"
      f" | {'k(Δ=k·amp)':>11s} {'R²(원점)':>9s}")
for nm, _p in CASES:
    s = [x for x in R if x["sub"] == nm]
    y = np.array([x["delta"] for x in s])
    amp = np.array([1 / x["r"] - 1 for x in s]); rr = np.array([x["r"] for x in s])
    dd = np.array([x["drdq"] for x in s]); th = np.array([x["crank"] for x in s])
    ra = np.array([abs(x["raw2"]) for x in s]); vv = np.array([x["dq2"] for x in s])
    k, r2 = r2_origin(y, amp)
    print(f"{nm:>14s} {len(s):4d} {corr(y,amp):+7.2f} {corr(y,rr):+7.2f} {corr(y,dd):+7.2f} "
          f"{corr(y,th):+7.2f} {corr(y,ra):+7.2f} {corr(y,vv):+7.2f} | {k:+11.3f} {r2:9.3f}")

print()
print("표 4b — 무변속은 amp 가 상수(=0)라 위 표에서 amp/r 열이 뜻이 없다. 확인용:")
s = [x for x in R if x["sub"] == "no_cvt/no_load"]
print(f"  no_cvt r 범위 {min(x['r'] for x in s):.4f}~{max(x['r'] for x in s):.4f} · "
      f"dr/dθ 범위 {min(x['drdq'] for x in s):.2e}~{max(x['drdq'] for x in s):.2e}")

print()
print("표 5 — 부호가 뒤집히는가: 깊은 가지(θ<−90) vs 편 가지(θ>−90)")
print(f"{'경우':>14s} | {'깊은 Δ':>8s} {'n':>4s} {'깊은 1/r−1':>10s} | {'편 Δ':>8s} {'n':>4s} {'편 1/r−1':>10s}")
for nm, _p in CASES:
    s = [x for x in R if x["sub"] == nm]
    dp = [x for x in s if x["crank"] < -90]; sh = [x for x in s if x["crank"] >= -90]
    f = lambda z: f"{np.mean([x['delta'] for x in z]):+8.2f}" if z else f"{'-':>8s}"
    g = lambda z: f"{np.mean([1/x['r']-1 for x in z]):10.2f}" if z else f"{'-':>10s}"
    print(f"{nm:>14s} | {f(dp)} {len(dp):4d} {g(dp)} | {f(sh)} {len(sh):4d} {g(sh)}")

print()
print("표 6 — 짐 의존 (변속기 3경우) : Δ = c0 + c1·짐[kg]")
print(f"{'구간[도]':>13s} {'0kg':>8s} {'2.5kg':>8s} {'5kg':>8s} {'c1[N·m/kg]':>12s} {'R²':>6s}")
for a, b in BINS:
    vs, ps = [], []
    for nm, p in CASES[:3]:
        v = [x["delta"] for x in R if x["sub"] == nm and a <= x["crank"] < b]
        vs.append(np.mean(v) if v else np.nan); ps.append(p)
    if np.sum(np.isfinite(vs)) < 3:
        continue
    A = np.column_stack([np.ones(3), ps]); vs = np.array(vs)
    co, *_ = np.linalg.lstsq(A, vs, rcond=None)
    r2 = 1 - np.sum((vs - A @ co) ** 2) / max(np.sum((vs - vs.mean()) ** 2), 1e-12)
    print(f"{f'[{a:.0f},{b:.0f})':>13s} {vs[0]:+8.2f} {vs[1]:+8.2f} {vs[2]:+8.2f} {co[1]:+12.3f} {r2:6.3f}")

print()
print("표 7 — ④ 무변속에도 자세 의존이 남는가 (겹치는 구간 −140~−40도만, 같은 자로)")
for nm, _p in CASES:
    s = [x for x in R if x["sub"] == nm and -140 <= x["crank"] < -40]
    if len(s) < 5:
        print(f"  {nm:16s} 표본 부족 (n={len(s)})"); continue
    y = np.array([x["delta"] for x in s]); th = np.array([x["crank"] for x in s])
    A = np.column_stack([np.ones(len(th)), th])
    co, *_ = np.linalg.lstsq(A, y, rcond=None)
    r2 = 1 - np.sum((y - A @ co) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-12)
    print(f"  {nm:16s} n={len(s):3d}  Δ = {co[0]:+6.2f} {co[1]:+.4f}·θ  "
          f"(100도당 {100*co[1]:+.2f} N·m) R²={r2:.2f} · Δ 범위 {y.min():+.2f}~{y.max():+.2f} 평균 {y.mean():+.2f}")

print()
print("표 8 — 같은 자로 두 경우의 폭 (−140~−40도): 자세에 따라 Δ 가 얼마나 움직이나")
for nm, _p in CASES:
    s = [x for x in R if x["sub"] == nm and -140 <= x["crank"] < -40]
    if len(s) < 5:
        continue
    y = np.array([x["delta"] for x in s])
    print(f"  {nm:16s} 최대−최소 {y.max()-y.min():5.2f} N·m · 표준편차 {y.std():4.2f}")
