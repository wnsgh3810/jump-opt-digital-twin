# -*- coding: utf-8 -*-
"""_GHP_agg — _GHP_loadslope.pkl 집계: 자세별로 맞춰 놓고 짐 무게에 회귀."""
import os, sys, pickle
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
GFS = Path(__file__).parent
sys.path.insert(0, str(GFS)); os.chdir(GFS)
import numpy as np

R = pickle.load(open(GFS / "_GHP_loadslope.pkl", "rb"))
G0 = 9.81
CASES = ["cvt/no_load", "cvt/load_2.5", "cvt/load_5", "no_cvt/no_load"]
CVTC = CASES[:3]
PAY = {"cvt/no_load": 0.0, "cvt/load_2.5": 2.5, "cvt/load_5": 5.0, "no_cvt/no_load": 0.0}
EDGES = np.arange(0.10, 0.50001, 0.05)
NB = len(EDGES) - 1


def binstats(sub):
    r = R[sub]; ix = r["ix"]
    bz = r["bz"][ix]
    out = {}
    for k in range(NB):
        m = (bz >= EDGES[k]) & (bz < EDGES[k + 1])
        if m.sum() < 5:
            out[k] = None; continue
        s = lambda a: float(np.mean(np.asarray(a)[ix][m]))
        out[k] = dict(n=int(m.sum()),
                      q1=np.degrees(s(r["q1"])), q2=np.degrees(s(r["q2"])),
                      dq1=s(r["dq1"]), dq2=s(r["dq2"]),
                      rq_h=s(r["tau_req"][:, 0]), rq_k=s(r["tau_req"][:, 1]),
                      gv_h=s(r["tau_grav"][:, 0]), gv_k=s(r["tau_grav"][:, 1]),
                      cm_h=s(r["tau_cmd"][:, 0]), cm_k=s(r["tau_cmd"][:, 1]),
                      ps_h=s(r["tau_pass"][:, 0]), ps_k=s(r["tau_pass"][:, 1]),
                      lv_h=s(r["lever"][:, 0]), lv_k=s(r["lever"][:, 1]),
                      jx_h=s(r["Jfx"][:, 0]), jx_k=s(r["Jfx"][:, 1]),
                      raw2=s(r["raw2"]), raw1=s(r["raw1"]))
    return out


B = {c: binstats(c) for c in CASES}


def fit3(y, x=(0.0, 2.5, 5.0)):
    x = np.asarray(x, float); y = np.asarray(y, float)
    A = np.vstack([x, np.ones_like(x)]).T
    sl, ic = np.linalg.lstsq(A, y, rcond=None)[0]
    pred = sl * x + ic
    curv = y[2] - 2 * y[1] + y[0]           # 2계 차분 (>0 볼록 = 위로 휨)
    return float(sl), float(ic), float(np.abs(y - pred).max()), float(curv)


print("=" * 118)
print("표1 — 자세(몸통 높이)별  τ필요(역동역학, 강체) · τ명령(현행 환산식) · Δ=필요−명령  [N·m]   (변속 3경우)")
print("=" * 118)
hdr = f"{'bz[m]':>10s} {'q1°':>6s} {'q2°':>7s} |"
for lbl in ("0kg", "2.5kg", "5kg"):
    hdr += f" {lbl+' 필요':>11s} {lbl+' 명령':>11s} {'Δ':>7s} |"
print("무릎(크랭크축)")
print(hdr)
for k in range(NB):
    if any(B[c][k] is None for c in CVTC):
        continue
    b0 = B[CVTC[0]][k]
    row = f"{EDGES[k]:.2f}-{EDGES[k+1]:.2f} {b0['q1']:6.1f} {b0['q2']:7.1f} |"
    for c in CVTC:
        b = B[c][k]
        row += f" {b['rq_k']:11.2f} {b['cm_k']:11.2f} {b['rq_k']-b['cm_k']:7.2f} |"
    print(row)
print()
print("힙")
print(hdr)
for k in range(NB):
    if any(B[c][k] is None for c in CVTC):
        continue
    b0 = B[CVTC[0]][k]
    row = f"{EDGES[k]:.2f}-{EDGES[k+1]:.2f} {b0['q1']:6.1f} {b0['q2']:7.1f} |"
    for c in CVTC:
        b = B[c][k]
        row += f" {b['rq_h']:11.2f} {b['cm_h']:11.2f} {b['rq_h']-b['cm_h']:7.2f} |"
    print(row)

print()
print("=" * 118)
print("표2 — Δτ(=필요−명령)의 짐무게 회귀  [기울기 N·m/kg · 절편 N·m] · 정적 레버 g·∂bz/∂q [N·m/kg]")
print("=" * 118)
print(f"{'bz[m]':>10s} | {'무릎 기울기':>10s} {'절편':>7s} {'휨(2계차)':>9s} {'최대잔차':>8s} {'레버_무릎':>9s} {'기울기/레버':>10s} |"
      f" {'힙 기울기':>9s} {'절편':>7s} {'휨':>7s} {'레버_힙':>8s} {'기울기/레버':>10s}")
agg = {}
for k in range(NB):
    if any(B[c][k] is None for c in CVTC):
        continue
    dk = [B[c][k]["rq_k"] - B[c][k]["cm_k"] for c in CVTC]
    dh = [B[c][k]["rq_h"] - B[c][k]["cm_h"] for c in CVTC]
    sk, ik, rk, ck = fit3(dk)
    sh, ih, rh, ch = fit3(dh)
    lvk = np.mean([B[c][k]["lv_k"] for c in CVTC])
    lvh = np.mean([B[c][k]["lv_h"] for c in CVTC])
    agg[k] = (sk, ik, ck, lvk, sh, ih, ch, lvh, dk, dh)
    print(f"{EDGES[k]:.2f}-{EDGES[k+1]:.2f} | {sk:10.3f} {ik:7.2f} {ck:9.3f} {rk:8.3f} {lvk:9.3f} {sk/lvk:10.3f} |"
          f" {sh:9.3f} {ih:7.2f} {ch:7.3f} {lvh:8.3f} {sh/lvh if abs(lvh)>1e-3 else float('nan'):10.3f}")

ks = sorted(agg)
print("-" * 118)
print(f"{'자세평균':>10s} | {np.mean([agg[k][0] for k in ks]):10.3f} {np.mean([agg[k][1] for k in ks]):7.2f} "
      f"{np.mean([agg[k][2] for k in ks]):9.3f} {'':8s} {np.mean([agg[k][3] for k in ks]):9.3f} "
      f"{np.mean([agg[k][0] for k in ks])/np.mean([agg[k][3] for k in ks]):10.3f} |"
      f" {np.mean([agg[k][4] for k in ks]):9.3f} {np.mean([agg[k][5] for k in ks]):7.2f} "
      f"{np.mean([agg[k][6] for k in ks]):7.3f} {np.mean([agg[k][7] for k in ks]):8.3f}")

print()
print("=" * 118)
print("표3 — 전체 자세를 하나로 (자세 8구간 평균 = 시간이 아니라 자세로 맞춘 평균)  [N·m]")
print("=" * 118)
print(f"{'경우':16s} {'짐kg':>5s} | {'무릎 필요':>9s} {'무릎 명령':>9s} {'무릎Δ':>7s} | {'힙 필요':>8s} {'힙 명령':>8s} {'힙Δ':>7s} |"
      f" {'무릎 모델마찰':>12s} {'힙 모델마찰':>11s}")
pool = {}
for c in CASES:
    kk = [k for k in range(NB) if B[c][k] is not None and all(B[cc][k] is not None for cc in CVTC)]
    f = lambda key: np.mean([B[c][k][key] for k in kk])
    pool[c] = dict(rq_k=f("rq_k"), cm_k=f("cm_k"), rq_h=f("rq_h"), cm_h=f("cm_h"),
                   ps_k=f("ps_k"), ps_h=f("ps_h"), lv_k=f("lv_k"), lv_h=f("lv_h"))
    p = pool[c]
    print(f"{c:16s} {PAY[c]:5.1f} | {p['rq_k']:9.2f} {p['cm_k']:9.2f} {p['rq_k']-p['cm_k']:7.2f} |"
          f" {p['rq_h']:8.2f} {p['cm_h']:8.2f} {p['rq_h']-p['cm_h']:7.2f} | {p['ps_k']:12.2f} {p['ps_h']:11.2f}")
sk, ik, rk, ck = fit3([pool[c]["rq_k"] - pool[c]["cm_k"] for c in CVTC])
sh, ih, rh, ch = fit3([pool[c]["rq_h"] - pool[c]["cm_h"] for c in CVTC])
skr, ikr, _, _ = fit3([pool[c]["rq_k"] for c in CVTC])
skc, ikc, _, _ = fit3([pool[c]["cm_k"] for c in CVTC])
shr, ihr, _, _ = fit3([pool[c]["rq_h"] for c in CVTC])
shc, ihc, _, _ = fit3([pool[c]["cm_h"] for c in CVTC])
print()
print(f"  무릎 Δ 기울기 {sk:+.4f} N·m/kg · 절편 {ik:+.4f} N·m · 2계차 {ck:+.4f} · 최대잔차 {rk:.4f}")
print(f"       (τ필요 기울기 {skr:+.4f} · τ명령 기울기 {skc:+.4f}) · 레버 {pool[CVTC[0]]['lv_k']:.4f} N·m/kg")
print(f"  힙   Δ 기울기 {sh:+.4f} N·m/kg · 절편 {ih:+.4f} N·m · 2계차 {ch:+.4f} · 최대잔차 {rh:.4f}")
print(f"       (τ필요 기울기 {shr:+.4f} · τ명령 기울기 {shc:+.4f}) · 레버 {pool[CVTC[0]]['lv_h']:.4f} N·m/kg")

print()
print("=" * 118)
print("표4 — 발 접선력 f_x 가정의 영향: '힙은 손실 0' 이라 두고 f_x 를 역산 → 무릎 잔차 재계산")
print("=" * 118)
print(f"{'bz[m]':>10s} | {'f_x 0kg':>8s} {'2.5kg':>8s} {'5kg':>8s} | {'무릎Δ보정 0kg':>13s} {'2.5kg':>9s} {'5kg':>9s} | {'기울기':>8s}")
fxall = {}
for k in ks:
    fx = []; dkc = []
    for c in CVTC:
        b = B[c][k]
        f = (b["rq_h"] - b["cm_h"]) / b["jx_h"] if abs(b["jx_h"]) > 1e-6 else np.nan
        fx.append(f)
        dkc.append(b["rq_k"] - b["jx_k"] * f - b["cm_k"])
    s2, i2, r2, c2 = fit3(dkc)
    fxall[k] = (fx, dkc, s2, i2)
    print(f"{EDGES[k]:.2f}-{EDGES[k+1]:.2f} | {fx[0]:8.2f} {fx[1]:8.2f} {fx[2]:8.2f} |"
          f" {dkc[0]:13.2f} {dkc[1]:9.2f} {dkc[2]:9.2f} | {s2:8.3f}")
pk = [np.mean([fxall[k][1][i] for k in ks]) for i in range(3)]
pf = [np.mean([fxall[k][0][i] for k in ks]) for i in range(3)]
s3, i3, r3, c3 = fit3(pk)
print("-" * 118)
print(f"{'자세평균':>10s} | {pf[0]:8.2f} {pf[1]:8.2f} {pf[2]:8.2f} | {pk[0]:13.2f} {pk[1]:9.2f} {pk[2]:9.2f} | {s3:8.3f}"
      f"   (절편 {i3:+.3f} · 2계차 {c3:+.3f})")
print(f"   총 수직하중 N=Mg: 0kg {(3.299)*G0:.1f} N · 2.5kg {(3.299+2.5)*G0:.1f} N · 5kg {(3.299+5)*G0:.1f} N")
print(f"   역산 f_x/N = {pf[0]/(3.299*G0):.3f} · {pf[1]/((3.299+2.5)*G0):.3f} · {pf[2]/((3.299+5)*G0):.3f}")

print()
print("=" * 118)
print("표5 — 무변속 0kg 대조 (변속 0kg 과 같은 자세대)")
print("=" * 118)
print(f"{'bz[m]':>10s} | {'무변속 무릎필요':>14s} {'명령':>8s} {'Δ':>7s} {'레버':>7s} | {'변속 무릎필요':>13s} {'명령':>8s} {'Δ':>7s} {'레버':>7s}")
for k in range(NB):
    if B["no_cvt/no_load"][k] is None or B["cvt/no_load"][k] is None:
        continue
    a = B["no_cvt/no_load"][k]; b = B["cvt/no_load"][k]
    print(f"{EDGES[k]:.2f}-{EDGES[k+1]:.2f} | {a['rq_k']:14.2f} {a['cm_k']:8.2f} {a['rq_k']-a['cm_k']:7.2f} {a['lv_k']:7.3f} |"
          f" {b['rq_k']:13.2f} {b['cm_k']:8.2f} {b['rq_k']-b['cm_k']:7.2f} {b['lv_k']:7.3f}")

print()
print("=" * 118)
print("표6 — 관성분 확인 (정역학만 vs 동역학) · 궤적 정합 · 포화")
print("=" * 118)
for c in CASES:
    r = R[c]; ix = r["ix"]
    di_k = np.abs(r["tau_req"][ix, 1] - r["tau_grav"][ix, 1])
    di_h = np.abs(r["tau_req"][ix, 0] - r["tau_grav"][ix, 0])
    print(f"{c:16s} 관성분 |동−정| 평균 무릎 {di_k.mean():6.3f} 최대 {di_k.max():6.3f} · "
          f"힙 {di_h.mean():6.3f} 최대 {di_h.max():6.3f} N·m | 명령>35.5 샘플 {r['nsat']:4d} | "
          f"|dq2|평균 {np.abs(r['dq2'][ix]).mean():5.2f} rad/s")
print()
print("자세 정합 확인 — 같은 bz 구간에서 세 경우의 q1·q2 차 [도]")
for k in ks:
    q1s = [B[c][k]["q1"] for c in CVTC]; q2s = [B[c][k]["q2"] for c in CVTC]
    print(f"  bz {EDGES[k]:.2f}-{EDGES[k+1]:.2f}: q1 {q1s[0]:7.2f}/{q1s[1]:7.2f}/{q1s[2]:7.2f} (폭 {max(q1s)-min(q1s):.2f}) "
          f" q2 {q2s[0]:8.2f}/{q2s[1]:8.2f}/{q2s[2]:8.2f} (폭 {max(q2s)-min(q2s):.2f})")
