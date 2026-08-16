# -*- coding: utf-8 -*-
"""_GHQ_fricv2 — 08.07 무게추 왕복에서 **마찰의 속도 모양**을 뽑는다 (모델 없음).

_GHQ_fricv 의 개선판:
  ① 칸 안에서 중력이 자세에 따라 기울어지는 것을 **국소 선형회귀로 제거**한 뒤 상행/하행을 뺀다
     (중앙값만 쓰면 상행·하행 표본이 칸 안 다른 자리에 몰릴 때 중력 기울기가 마찰로 샌다 —
      2kg/4kg 힙에서 실제로 그렇게 퍼졌다).
  ② 저속 칸을 더 잘게 (0.005부터).
  ③ **같은 자세칸 안에서** 기준속도(0.06~0.16) 대비 비를 내어 자세 효과를 없앤 뒤,
     그 정규화된 모양을 여러 모형과 맞춰 본다: 쿨롱(일정) · tanh(v/v0) · 쿨롱+점성 · Stribeck.

CLI: python _GHQ_fricv2.py
"""
# --- 실험 데이터 경로: 단일 출처 (code/bench/datapaths.py) ---
import os as _o, sys as _s
_d = _o.path.dirname(_o.path.abspath(__file__))
while _d != _o.path.dirname(_d) and not _o.path.isdir(_o.path.join(_d, 'code', 'bench')):
    _d = _o.path.dirname(_d)
if _o.path.join(_d, 'code', 'bench') not in _s.path:
    _s.path.append(_o.path.join(_d, 'code', 'bench'))
from datapaths import DATA_ROOT, CVT_ROOT  # noqa: E402
# ---------------------------------------------------------------
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench")); os.chdir(HERE)
DATA = Path(DATA_ROOT)
OUT = HERE / "_GHQ_fricv2.json"

FILES = [("0kg", "0kg/probe_sweep_v1"), ("0kg#2", "0kg/probe_sweep_v1 - 2"),
         ("2kg", "2kg/probe_sweep_v1"), ("4kg", "4kg/probe_sweep_v1")]
VED = np.array([0.005, 0.010, 0.018, 0.030, 0.050, 0.080, 0.120, 0.180, 0.280, 0.450, 0.700])
NPOS = 14
MINS = 15
VREF = (0.06, 0.16)          # 정규화 기준 속도대


def rd(p):
    df = pd.read_excel(p)
    c = {k.lower().replace(" ", ""): k for k in df.columns}
    g = lambda k: np.asarray(df[c[k]], float)
    return dict(t=g("time"), q=g("currentangle"), tau=g("currenttorque"))


def vel(t, q, w=25):
    dt = float(np.median(np.diff(t)))
    return np.convolve(np.gradient(q, dt), np.ones(w) / w, mode="same")


def rev_mask(v, dt, hold):
    s = np.sign(v); s[s == 0] = 1
    ch = np.nonzero(np.diff(s) != 0)[0] + 1
    bad = np.zeros(len(v), bool); n = int(round(hold / dt))
    for i in ch:
        bad[max(0, i - n):i + n] = True
    return bad


def at_center(q, tau, qc):
    """중력 기울기를 없애고 칸 중심에서의 명령값을 낸다 (1차 회귀)."""
    A = np.stack([np.ones_like(q), q - qc], 1)
    b, *_ = np.linalg.lstsq(A, tau, rcond=None)
    return float(b[0]), float(b[1])


def cells(q, v, tau, dt, hold=0.0):
    sp = np.abs(v)
    ok = sp >= VED[0]
    if hold > 0:
        ok &= ~rev_mask(v, dt, hold)
    lo, hi = np.percentile(q[ok], [2, 98])
    ped = np.linspace(lo, hi, NPOS + 1)
    out = []
    for i in range(NPOS):
        qc = (ped[i] + ped[i + 1]) / 2
        mp = ok & (q >= ped[i]) & (q < ped[i + 1])
        for j in range(len(VED) - 1):
            m = mp & (sp >= VED[j]) & (sp < VED[j + 1])
            up, dn = m & (v > 0), m & (v < 0)
            if up.sum() < MINS or dn.sum() < MINS:
                continue
            u, _ = at_center(q[up], tau[up], qc)
            d, _ = at_center(q[dn], tau[dn], qc)
            out.append(dict(pos=float(np.degrees(qc)), ipos=i, vbin=j,
                            v=float(np.median(sp[m])), fric=(u - d) / 2, grav=(u + d) / 2,
                            nu=int(up.sum()), nd=int(dn.sum())))
    return out


def fit_shapes(v, f):
    """정규화된 (속도, 마찰비) 점들에 모형을 맞춘다 — 잔차 RMS 로 비교."""
    v = np.asarray(v); f = np.asarray(f)
    res = {}
    res["쿨롱(일정=1)"] = (float(np.sqrt(np.mean((f - 1) ** 2))), "—")
    # tanh(v/v0) 정규화: 기준속도 vr 에서 1 이 되도록
    vr = float(np.median(v[(v >= VREF[0]) & (v <= VREF[1])])) if ((v >= VREF[0]) & (v <= VREF[1])).any() else 0.1
    best = (np.inf, None)
    for v0 in np.geomspace(0.002, 3.0, 200):
        pred = np.tanh(v / v0) / np.tanh(vr / v0)
        r = float(np.sqrt(np.mean((f - pred) ** 2)))
        if r < best[0]:
            best = (r, v0)
    res[f"tanh(v/v0), v0 자유"] = (best[0], f"v0={best[1]:.3f}")
    res["tanh(v/0.30) — 지금 모델"] = (float(np.sqrt(np.mean((f - np.tanh(v / 0.3) / np.tanh(vr / 0.3)) ** 2))), "고정")
    # 쿨롱+점성: f = (1 + b(v-vr)) 형태로 (기준에서 1)
    A = np.stack([np.ones_like(v), v - vr], 1)
    b, *_ = np.linalg.lstsq(A, f, rcond=None)
    res["쿨롱+점성 (1+b·(v−vr))"] = (float(np.sqrt(np.mean((f - A @ b) ** 2))),
                                  f"b={b[1]:+.3f}/(rad/s), 절편{b[0]:.3f}")
    # Stribeck: f = fc + (fs-fc)exp(-(v/vs)^2), 기준에서 1 로 정규화
    best2 = (np.inf, None)
    for fs in np.linspace(1.0, 4.0, 31):
        for vs in np.geomspace(0.005, 0.5, 40):
            g = lambda x: 1.0 + (fs - 1.0) * np.exp(-(x / vs) ** 2)
            pred = g(v) / g(vr)
            r = float(np.sqrt(np.mean((f - pred) ** 2)))
            if r < best2[0]:
                best2 = (r, (fs, vs))
    res["Stribeck (저속에서 솟음)"] = (best2[0], f"fs/fc={best2[1][0]:.2f}, vs={best2[1][1]:.3f}")
    return res, vr


def main():
    ALL = {}
    pool = {"hip": [], "knee": []}
    for lab, rel in FILES:
        p = DATA / "26_08_07" / rel
        for ch in ("hip", "knee"):
            x = rd(p / f"{ch}.xlsx")
            dt = float(np.median(np.diff(x["t"])))
            v = vel(x["t"], x["q"])
            cs = cells(x["q"], v, x["tau"], dt)
            ALL[f"{lab}/{ch}"] = cs
            print(f"\n── {lab} {ch}: 칸 {len(cs)}개")
            print(f"   {'속도칸':>14s} {'v중앙':>7s} {'마찰[명령]':>11s} {'사분위':>15s} {'칸수':>4s}")
            for j in range(len(VED) - 1):
                g = [c for c in cs if c["vbin"] == j]
                if len(g) < 2:
                    continue
                f = np.array([c["fric"] for c in g])
                print(f"   {VED[j]:.3f}~{VED[j+1]:.3f}".rjust(17)
                      + f" {np.median([c['v'] for c in g]):7.3f} {np.median(f):11.3f}"
                      + f"  {np.percentile(f,25):6.3f}~{np.percentile(f,75):6.3f} {len(g):4d}")
            # 자세칸 안 정규화
            byp = {}
            for c in cs:
                byp.setdefault(c["ipos"], []).append(c)
            for ip, g in byp.items():
                ref = [c for c in g if VREF[0] <= c["v"] <= VREF[1]]
                if not ref:
                    continue
                r0 = float(np.mean([c["fric"] for c in ref]))
                if abs(r0) < 0.05:            # 기준이 너무 작으면 비가 폭발한다
                    continue
                for c in g:
                    pool[ch].append((c["v"], c["fric"] / r0, lab, c["pos"]))
    print("\n" + "=" * 96)
    print("■ 자세를 고정하고 정규화한 **마찰의 속도 모양** (기준 = 그 자세칸의 0.06~0.16 rad/s 값 = 1.00)")
    print("=" * 96)
    for ch in ("hip", "knee"):
        P = pool[ch]
        if not P:
            continue
        v = np.array([p[0] for p in P]); f = np.array([p[1] for p in P])
        print(f"\n── {ch}  (점 {len(P)}개)")
        print(f"   {'속도칸':>14s} {'v중앙':>7s} {'실측 마찰비':>11s} {'사분위':>15s} {'점수':>4s} "
              f"{'tanh(v/0.3)':>12s}")
        vr_all = None
        for j in range(len(VED) - 1):
            m = (v >= VED[j]) & (v < VED[j + 1])
            if m.sum() < 3:
                continue
            vm = float(np.median(v[m]))
            if VREF[0] <= vm <= VREF[1] and vr_all is None:
                vr_all = vm
            print(f"   {VED[j]:.3f}~{VED[j+1]:.3f}".rjust(17)
                  + f" {vm:7.3f} {np.median(f[m]):11.2f}"
                  + f"  {np.percentile(f[m],25):6.2f}~{np.percentile(f[m],75):6.2f} {m.sum():4d}", end="")
            print(f" {np.tanh(vm/0.3)/np.tanh(0.10/0.3):12.2f}")
        R, vr = fit_shapes(v, f)
        print(f"   모형 맞춤 (기준속도 {vr:.3f} rad/s):")
        for k, (r, note) in sorted(R.items(), key=lambda x: x[1][0]):
            print(f"      {k:28s} 잔차RMS {r:.3f}   {note}")
    import safe
    safe.atomic_json_write(OUT, dict(cells={k: v for k, v in ALL.items()},
                                     pool={k: [[a, b, c, d] for a, b, c, d in v] for k, v in pool.items()}))
    print(f"\n저장 → {OUT}")


if __name__ == "__main__":
    main()
