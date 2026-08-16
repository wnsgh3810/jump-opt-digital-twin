# -*- coding: utf-8 -*-
"""_GHP_sens — 손실-짐 기울기가 방법 선택에 얼마나 흔들리는가 (민감도).

★ 가장 중요한 교란: 짐이 무거우면 **명령 크기도 같이 커진다.** 그런데 환산식은 명령
  크기에 따라 배율이 1.27배(저토크)→0.75배(고토크)로 변한다. 그래서 "짐 비례 손실"과
  "환산식의 고토크 처짐"은 이 데이터에서 **원리상 분리되지 않는다.** 환산식을 바꿔 가며
  기울기가 얼마나 움직이는지 재서 그 폭을 보고한다.
"""
import os, sys, pickle
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
GFS = Path(__file__).parent
sys.path.insert(0, str(GFS)); os.chdir(GFS)
import numpy as np
import mujoco as mj

STACK = dict(FS_TMAP="canon_cap", FS_TDCAP="4.122,2.372", FS_MASS="3.2990",
             FS_FOOTR="0.020", FS_NOSUPP="1", FS_NOSPR="1", FS_NOBIAS="1",
             FS_NODEEP="1", FS_PRESLIDE="0.86,0.85,0.02,1.0",
             FS_CMD_LPF="0.00451,0.00072", FS_IMPRATIO="20",
             FS_KNEEM_FL="0.1177", FS_KNEEM_DAMP="0.2281", FS_HIPM_FL="0.3111",
             FS_HIPM_DAMP="0.0071", FS_KS_HIP="166.34", FS_COMZ="thigh=0.02239",
             FS_RAIL="0.02995")
for _k, _v in STACK.items():
    os.environ.setdefault(_k, _v)
import fs_runner as FR, fs_cvt as FC, fs_data as FD
import _GHP_loadslope as LS

G0 = 9.81
CVTC = ["cvt/no_load", "cvt/load_2.5", "cvt/load_5"]
PAY = {"cvt/no_load": 0.0, "cvt/load_2.5": 2.5, "cvt/load_5": 5.0, "no_cvt/no_load": 0.0}
CLIP = 35.5
R = pickle.load(open(GFS / "_GHP_loadslope.pkl", "rb"))
EN = pickle.load(open(GFS / "_GHP_energy.pkl", "rb"))


def fit3(y):
    x = np.array([0.0, 2.5, 5.0]); A = np.vstack([x, np.ones_like(x)]).T
    sl, ic = np.linalg.lstsq(A, np.asarray(y, float), rcond=None)[0]
    return float(sl), float(ic), float(y[2] - 2 * y[1] + y[0])


def make_tmap(mode, tmodel=None, tdcap=None):
    old = {k: os.environ.get(k) for k in ("FS_TMAP", "FS_TMODEL", "FS_TDCAP")}
    os.environ["FS_TMAP"] = mode
    if tmodel:
        os.environ["FS_TMODEL"] = tmodel
    if tdcap:
        os.environ["FS_TDCAP"] = tdcap
    ft = FR.fs_twin(); A = FR.tq_shape(ft["P"].A_PAPER)
    tm = FR._tmap_init(ft["P"], A)
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return tm


VAR = [("현행 canon_cap (H4)", "canon_cap", None, "4.122,2.372"),
       ("canon 정본곡선 단독", "canon", None, None),
       ("분동 선형 1.24·raw", "model", "lin:1.24", None),
       ("a_hat 논문식", None, None, None)]

print("=" * 112)
print("표8 — 환산식을 바꾸면 '짐 비례 손실 기울기'가 어떻게 움직이나 (에너지 수지, 창 동일)")
print("=" * 112)
print(f"{'환산식':22s} | {'W명령 0kg':>9s} {'2.5kg':>8s} {'5kg':>8s} | {'손실 0kg':>8s} {'2.5kg':>7s} {'5kg':>7s} |"
      f" {'기울기 J/kg':>11s} {'절편 J':>7s} {'/들어올림':>9s}")
dbz = np.mean([EN[c]["dbz"] for c in CVTC])
for nm, mode, tmodel, tdcap in VAR:
    tm = make_tmap(mode, tmodel, tdcap) if mode else None
    ws, ls = [], []
    for c in CVTC:
        r = R[c]; ix = r["ix"]
        r1 = np.clip(r["raw1"], -CLIP, CLIP); r2 = np.clip(r["raw2"], -CLIP, CLIP)
        if tm is None:
            ft = FR.fs_twin(); A = FR.tq_shape(ft["P"].A_PAPER)
            t1 = np.array([float(ft["P"].J.ahat(A, np.array([r1[k]]), np.array([r["dq1"][k]]))[0]) for k in ix])
            t2 = np.array([float(ft["P"].J.ahat(A, np.array([r2[k]]), np.array([r["dq2"][k]]))[0]) for k in ix])
        else:
            t1 = np.array([tm(float(r1[k]), float(r["dq1"][k]), 0) for k in ix])
            t2 = np.array([tm(float(r2[k]), float(r["dq2"][k]), 1) for k in ix])
        w = float(np.sum(t1 * r["dq1"][ix] + t2 * r["dq2"][ix]) * 0.002)
        ws.append(w); ls.append(w - EN[c]["dE"])
    sl, ic, cu = fit3(ls)
    print(f"{nm:22s} | {ws[0]:9.2f} {ws[1]:8.2f} {ws[2]:8.2f} | {ls[0]:8.2f} {ls[1]:7.2f} {ls[2]:7.2f} |"
          f" {sl:11.3f} {ic:7.2f} {sl/(G0*dbz):9.3f}")
print(f"  (들어올림 에너지 = {G0*dbz:.3f} J/kg · 손실이 음수면 '명령이 물리보다 적다' = 환산식이 과소)")

print()
print("=" * 112)
print("표9 — 창·속도·클립 선택의 영향 (현행 환산식)")
print("=" * 112)
for tag, zmin in (("문턱 0.10 (기본)", 0.10), ("문턱 0.15", 0.15), ("문턱 0.20", 0.20), ("문턱 0.25", 0.25)):
    ls = []
    for c in CVTC:
        r = R[c]
        ok = r["bz_an"] > zmin          # analyse() 와 동일 좌표(해석식 몸통높이)로 창을 정한다
        i0 = int(np.argmax(ok)); i1 = int(len(ok) - np.argmax(ok[::-1])); ix = np.arange(i0, i1)
        w = float(np.sum(r["tau_cmd"][ix, 0] * r["dq1"][ix] + r["tau_cmd"][ix, 1] * r["dq2"][ix]) * 0.002)
        rq = float(np.sum(r["tau_req"][ix, 0] * r["dq1"][ix] + r["tau_req"][ix, 1] * r["dq2"][ix]) * 0.002)
        ls.append(w - rq)
    sl, ic, cu = fit3(ls)
    print(f"{tag:16s} 손실 {ls[0]:6.2f}/{ls[1]:6.2f}/{ls[2]:6.2f} J → 기울기 {sl:+.3f} J/kg 절편 {ic:+.2f} 2계차 {cu:+.3f}")
# 속도 출처
ls = []
for c in CVTC:
    r = R[c]; ix = r["ix"]
    v1 = -r["vel"][ix][:, 1]; v2 = -r["vel"][ix][:, 3]
    w = float(np.sum(r["tau_cmd"][ix, 0] * v1 + r["tau_cmd"][ix, 1] * v2) * 0.002)
    rq = float(np.sum(r["tau_req"][ix, 0] * v1 + r["tau_req"][ix, 1] * v2) * 0.002)
    ls.append(w - rq)
sl, ic, cu = fit3(ls)
print(f"{'평활속도 사용':16s} 손실 {ls[0]:6.2f}/{ls[1]:6.2f}/{ls[2]:6.2f} J → 기울기 {sl:+.3f} J/kg 절편 {ic:+.2f} 2계차 {cu:+.3f}")
# 클립 해제
ls = []
for c in CVTC:
    r = R[c]; ix = r["ix"]
    w = float(np.sum(r["tau_cmd_noclip"][ix, 0] * r["dq1"][ix] + r["tau_cmd_noclip"][ix, 1] * r["dq2"][ix]) * 0.002)
    rq = float(np.sum(r["tau_req"][ix, 0] * r["dq1"][ix] + r["tau_req"][ix, 1] * r["dq2"][ix]) * 0.002)
    ls.append(w - rq)
sl, ic, cu = fit3(ls)
print(f"{'명령 클립 해제':16s} 손실 {ls[0]:6.2f}/{ls[1]:6.2f}/{ls[2]:6.2f} J → 기울기 {sl:+.3f} J/kg 절편 {ic:+.2f} 2계차 {cu:+.3f}")
# 정역학만 (관성 무시)
ls = []
for c in CVTC:
    r = R[c]; ix = r["ix"]
    w = float(np.sum(r["tau_cmd"][ix, 0] * r["dq1"][ix] + r["tau_cmd"][ix, 1] * r["dq2"][ix]) * 0.002)
    rq = float(np.sum(r["tau_grav"][ix, 0] * r["dq1"][ix] + r["tau_grav"][ix, 1] * r["dq2"][ix]) * 0.002)
    ls.append(w - rq)
sl, ic, cu = fit3(ls)
print(f"{'정역학만(관성0)':16s} 손실 {ls[0]:6.2f}/{ls[1]:6.2f}/{ls[2]:6.2f} J → 기울기 {sl:+.3f} J/kg 절편 {ic:+.2f} 2계차 {cu:+.3f}")

print()
print("=" * 112)
print("표10 — 환산식이 명령 크기에 따라 배율이 변한다 (교란의 크기)")
print("=" * 112)
tm = make_tmap("canon_cap", None, "4.122,2.372")
print(f"{'명령 raw':>9s} {'무릎 τ':>8s} {'배율':>6s} | {'힙 τ':>8s} {'배율':>6s}   (v>0)")
for raw in (2, 5, 8, 12, 18, 25, 35):
    a = tm(float(raw), 1.0, 1); b = tm(float(raw), 1.0, 0)
    print(f"{raw:9.1f} {a:8.2f} {a/raw:6.3f} | {b:8.2f} {b/raw:6.3f}")
print()
for c in CVTC + ["no_cvt/no_load"]:
    r = R[c]; ix = r["ix"]
    p = np.percentile(np.abs(r["raw2"][ix]), [50, 90, 99])
    print(f"  {c:16s} 무릎 명령 |raw| 중앙 {p[0]:5.2f} · 90% {p[1]:5.2f} · 99% {p[2]:6.2f}"
          f"  → 그 구간 환산배율 {tm(float(p[0]),1.0,1)/p[0]:.3f} / {tm(float(p[1]),1.0,1)/p[1]:.3f} / {tm(float(p[2]),1.0,1)/p[2]:.3f}")
