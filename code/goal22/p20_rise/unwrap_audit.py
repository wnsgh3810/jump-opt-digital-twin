# -*- coding: utf-8 -*-
"""P20 실험 2 — 토크 언랩 감사 (전 trial).

비교: <trial>/knee.xlsx·hip.xlsx (MATLAB 언랩본, 파이프라인 사용본)
  vs <trial>/raw_unwrap/*.xlsx (무언랩, batch_export_no_unwrap.m 산출).

원리: 기록계는 토크를 ±18Nm(스팬 36)로 접어서 저장 → 언랩본 = raw + 36·k(t).
검사 항목 (currentTorque):
  n_shift   : branch k(t)가 바뀐 횟수 (랩 통과 횟수 — 많을수록 언랩이 일한 것)
  frac_bad  : (언랩−raw)/36 이 정수가 아닌 샘플 수 (정렬/알고리즘 이상)
  leftover  : 언랩본에 남은 |Δ|>14 점프 수 (언랩이 못 편 곳 or 실제 충격)
  sus_des   : desiredTorque 기준으로 다른 branch가 더 그럴듯한 샘플 수
              (|cur−des|>20 이면서 ±36 이동 시 |·|<10 이 되는 곳)
출력: 세션별 표 + 의심 trial 겹침 그림 (raw/언랩/desired) → g22_p20_results/unwrap_audit/
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
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

DATA = Path(DATA_ROOT)
DST = Path(r"C:/Users/junho/Desktop/jump_opt/g22_p20_results/unwrap_audit")
DST.mkdir(parents=True, exist_ok=True)
SPAN = 36.0


def load_cols(p):
    df = pd.read_excel(p)
    return {c: df[c].values.astype(float) for c in df.columns}


def audit_one(orig_p, raw_p, joint):
    o = load_cols(orig_p)
    r = load_cols(raw_p)
    # Time 정렬 (언랩본은 범위 크롭 가능 → 교집합, 1e-6 라운딩)
    to = np.round(o["Time"], 6)
    tr_ = np.round(r["Time"], 6)
    common, io_, ir_ = np.intersect1d(to, tr_, return_indices=True)
    if len(common) < 50:
        return dict(err=f"time overlap {len(common)}")
    cu = o["currentTorque"][io_]
    cr = r["currentTorque"][ir_]
    de = o.get("desiredTorque")
    de = de[io_] if de is not None else None
    m = np.isfinite(cu) & np.isfinite(cr)
    cu, cr = cu[m], cr[m]
    t = common[m]
    de = de[m] if de is not None else None
    k = (cu - cr) / SPAN
    kr = np.round(k)
    frac_bad = int(np.sum(np.abs(k - kr) > 0.01))
    n_shift = int(np.sum(np.diff(kr) != 0))
    dj = np.abs(np.diff(cu))
    leftover = int(np.sum(dj > 14))
    sus_des = 0
    sus_t = []
    if de is not None and np.isfinite(de).any():
        dd = np.where(np.isfinite(de), de, 0.0)
        err0 = np.abs(cu - dd)
        errp = np.abs(cu + SPAN - dd)
        errm = np.abs(cu - SPAN - dd)
        sus = (err0 > 20) & (np.minimum(errp, errm) < 10) & np.isfinite(de)
        sus_des = int(np.sum(sus))
        sus_t = t[sus].tolist()[:5]
    return dict(joint=joint, n=len(cu), max_abs=float(np.max(np.abs(cu))),
                n_shift=n_shift, frac_bad=frac_bad, leftover=leftover,
                sus_des=sus_des, sus_t=sus_t,
                t=t, cu=cu, cr=cr, de=de)


def fig_trial(name, a, out):
    fig, ax = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    ax[0].plot(a["t"], a["cu"], lw=1.1, label="언랩본 (파이프라인 사용)")
    ax[0].plot(a["t"], a["cr"], lw=0.9, alpha=0.7, label="raw (기록 그대로, 접힘)")
    if a["de"] is not None:
        ax[0].plot(a["t"], a["de"], lw=0.9, ls="--", alpha=0.7, label="desired (명령)")
    for yy in (18, -18):
        ax[0].axhline(yy, ls=":", lw=0.8)
    ax[0].set_ylabel("knee raw 토크 [모터 단위 Nm]")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    k = np.round((a["cu"] - a["cr"]) / SPAN)
    ax[1].step(a["t"], k, where="post", lw=1.2)
    ax[1].set_ylabel("branch k (언랩이 더한 36의 배수)")
    ax[1].set_xlabel("t [s]"); ax[1].grid(alpha=0.3)
    fig.suptitle(f"{name} — 언랩 감사 (shift {a['n_shift']} · 잔존점프 {a['leftover']} · "
                 f"desired 의심 {a['sus_des']})")
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def main():
    rows = []
    for raw_p in sorted(DATA.rglob("raw_unwrap/knee.xlsx")) + sorted(DATA.rglob("raw_unwrap/hip.xlsx")):
        trial_dir = raw_p.parent.parent
        joint = raw_p.stem
        orig_p = trial_dir / f"{joint}.xlsx"
        if not orig_p.exists():
            continue
        rel = str(trial_dir.relative_to(DATA))
        try:
            a = audit_one(orig_p, raw_p, joint)
        except Exception as e:
            print(f"ERR {rel}/{joint}: {e}", flush=True)
            continue
        if "err" in a:
            print(f"SKIP {rel}/{joint}: {a['err']}", flush=True)
            continue
        rows.append(dict(trial=rel, **{k: v for k, v in a.items()
                                       if k not in ("t", "cu", "cr", "de")}))
        flag = (a["frac_bad"] > 0) or (a["sus_des"] > 0) or \
               (joint == "knee" and a["leftover"] > 0 and a["max_abs"] > 17)
        if flag:
            fig_trial(f"{rel}/{joint}", a,
                      DST / (rel.replace("\\", "_").replace("/", "_") + f"__{joint}.png"))
        print(f"{rel}/{joint:5s} max|τ| {a['max_abs']:5.1f} shift {a['n_shift']:3d} "
              f"frac_bad {a['frac_bad']:3d} 잔존점프 {a['leftover']:2d} 의심 {a['sus_des']:3d}"
              + ("  ← FLAG" if flag else ""), flush=True)
    json.dump(rows, open(DST / "audit_rows.json", "w"), indent=1, default=float)
    # 세션 요약
    print("\n=== 세션 요약 (knee) ===", flush=True)
    ses = {}
    for r in rows:
        if r["joint"] != "knee":
            continue
        s = r["trial"].split("\\")[0].split("/")[0]
        d = ses.setdefault(s, dict(n=0, shift=0, frac=0, left=0, sus=0))
        d["n"] += 1; d["shift"] += r["n_shift"]; d["frac"] += r["frac_bad"]
        d["left"] += r["leftover"]; d["sus"] += r["sus_des"]
    for s, d in sorted(ses.items()):
        print(f"{s:10s} trial {d['n']:3d} | branch shift 합 {d['shift']:4d} | "
              f"비정수 {d['frac']:3d} | 잔존점프 {d['left']:3d} | desired 의심 {d['sus']:4d}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
