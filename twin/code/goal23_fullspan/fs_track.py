# -*- coding: utf-8 -*-
"""fs_track — 마라톤 C 주 분석기: 깊은 목표 추종 결손 e의 다중 판별.

T1 e(kp) LSQ 분해 (전 세션·양 채널): e = θ0 + c/kp — θ0=좌표 오프셋[°], τf=c·π/180=토크 요구[raw]
   (PD 정지 평형: kp·e = τ_req 그 자체 — B12. 게인 스윕이 자연 실험장:
    hip 25/27/22/0602 · knee 22/23/24/0424/0602)
T2 trial별 deep kp·e ↔ 하강 슬립 실측(_fs_descslip_all.json drift_deep_px) 상관 — 정역학 변화 판별
T3 접근 방향 히스테리시스: 같은 깊이 유지창을 하강 접근 vs 상승 접근으로 분류해 e 비교
   (마찰이면 부호/크기 접근 의존, 정역학이면 무관)
부산물: 깊이별 kp·e 프로파일 (τ_req(q2) — 구 '깊이 램프'의 물리 단위 재계측)
출력: _fs_track.json. 데이터 전용 (mujoco 불필요). CLI: python fs_track.py
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bench"))
import safe
import fs_data as FD
from fs3_recon import ROOT

DEEP = (-135.0, -100.0)          # 1급 창 [°]
BINS = np.arange(-140, -64.9, 5.0)


def load_full(fold: Path):
    h = pd.read_excel(fold / "hip3.xlsx")
    k = pd.read_excel(fold / "knee3.xlsx")
    g = pd.read_excel(fold / "GRF3.xlsx")
    n = min(len(h), len(k), len(g))
    h, k, g = h.iloc[:n], k.iloc[:n], g.iloc[:n]
    t = h["Time"].to_numpy(float)
    return dict(t=t - t[0],
                q1=h["currentAngle"].to_numpy(float), q2=k["currentAngle"].to_numpy(float),
                qd1=h["desiredAngle"].to_numpy(float), qd2=k["desiredAngle"].to_numpy(float),
                dq1=h["currentAngleVelocity"].to_numpy(float), dq2=k["currentAngleVelocity"].to_numpy(float),
                raw1=h["currentTorque"].to_numpy(float), raw2=k["currentTorque"].to_numpy(float),
                grf=g["Current_GRF"].to_numpy(float))


def masks(d, en):
    t = d["t"]
    gs = np.convolve(d["grf"], np.ones(25) / 25, mode="same")
    g_fl = float(np.quantile(gs, 0.02))
    g_full = float(np.quantile(gs, 0.90))
    gnd = gs > g_fl + 0.6 * (g_full - g_fl)
    slow = np.maximum(np.abs(d["dq1"]), np.abs(d["dq2"])) < 0.4
    return (t > en + 1) & gnd & slow


def rolling_const(x, w):
    """이동 창 내 최대-최소 < 1e-4 rad → 목표 상수 판정 (부울)."""
    n = len(x)
    out = np.zeros(n, bool)
    if n < w:
        return out
    from numpy.lib.stride_tricks import sliding_window_view
    sw = sliding_window_view(x, w)
    c = (sw.max(axis=1) - sw.min(axis=1)) < 1e-4
    for off in range(w):                       # 창에 속한 전 표본에 마킹
        out[off:off + len(c)][c] = True
    return out


def holds(d, base, fs=500):
    """T3: 목표 상수 유지창 탐지 + 접근 방향 분류 → (dir, q2d, e1°, e2°, dur)."""
    t = d["t"]
    cst = rolling_const(d["qd1"], fs // 2) & rolling_const(d["qd2"], fs // 2)
    q2d = np.degrees(d["q2"])
    ok = cst & base & (q2d < -95)
    res = []
    i, N = 0, len(t)
    while i < N:
        if not ok[i]:
            i += 1
            continue
        j = i
        while j < N and ok[j]:
            j += 1
        if t[j - 1] - t[i] >= 1.2:
            i_pre = np.searchsorted(t, t[i] - 0.8)
            dqd2 = d["qd2"][i] - d["qd2"][i_pre]
            dqd1 = d["qd1"][i] - d["qd1"][i_pre]
            drv = dqd2 if abs(dqd2) > abs(dqd1) else dqd1
            if abs(drv) > np.radians(0.3):
                dirn = "desc" if drv < 0 else "asc"       # q 깊을수록 음수
                i_m = i + (j - i) // 2                     # 후반부 (정착 후)
                e1 = float(np.degrees(np.median(d["qd1"][i_m:j] - d["q1"][i_m:j])))
                e2 = float(np.degrees(np.median(d["qd2"][i_m:j] - d["q2"][i_m:j])))
                res.append(dict(dir=dirn, q2d=float(np.median(q2d[i_m:j])),
                                e1=e1, e2=e2, dur=float(t[j - 1] - t[i])))
        i = j
    return res


def main():
    state = json.load(open(HERE / "_fs3_state.json", encoding="utf-8"))
    try:
        slip = json.load(open(HERE / "_fs_descslip_all.json", encoding="utf-8"))
    except Exception:
        slip = {}
    TR = {}
    for key in sorted(state):
        fold = ROOT / key
        g = FD.gains_of(fold.name)
        if not g or not (fold / "hip3.xlsx").exists():
            continue
        try:
            d = load_full(fold)
        except Exception as ex:
            print(f"{key}: LOAD FAIL {type(ex).__name__}", flush=True)
            continue
        en = max(state[key]["h"]["t_enable"] or 0, state[key]["k"]["t_enable"] or 0)
        base = masks(d, en)
        q2d = np.degrees(d["q2"])
        e = dict(kp1=g[0], kp2=g[2])
        m = base & (q2d > DEEP[0]) & (q2d < DEEP[1])
        if m.sum() >= 150:
            e1 = float(np.median(d["qd1"][m] - d["q1"][m]))
            e2 = float(np.median(d["qd2"][m] - d["q2"][m]))
            e["deep"] = dict(e1=np.degrees(e1), e2=np.degrees(e2),
                             kpe1=g[0] * e1, kpe2=g[2] * e2, n=int(m.sum()))
        prof = {}
        for b0 in BINS:
            mb = base & (q2d >= b0) & (q2d < b0 + 5)
            if mb.sum() >= 100:
                prof[f"{b0:.0f}"] = [round(g[0] * float(np.median(d["qd1"][mb] - d["q1"][mb])), 2),
                                     round(g[2] * float(np.median(d["qd2"][mb] - d["q2"][mb])), 2)]
        e["prof"] = prof
        e["holds"] = holds(d, base)
        sl = slip.get(key)
        if sl and sl.get("video"):
            e["slip_px"] = sl.get("drift_px")
            e["slip_deep_px"] = sl.get("drift_deep_px")
        TR[key] = e
        print(f"{key}: deep {'e1 %+.2f° e2 %+.2f° kpe(%+.1f,%+.1f)' % (e['deep']['e1'], e['deep']['e2'], e['deep']['kpe1'], e['deep']['kpe2']) if 'deep' in e else '—'}"
              f" | holds {len(e['holds'])}", flush=True)

    # ---- T1: 세션·채널 LSQ ----
    print("\n=== T1 e(kp) 분해 (e = θ0 + τf/kp) ===", flush=True)
    fits = {}
    sess_of = lambda k: k.split("/")[0]
    for s in sorted({sess_of(k) for k in TR}):
        for ch, kk, ee in (("hip", "kp1", "e1"), ("knee", "kp2", "e2")):
            pts = [(TR[k][kk], TR[k]["deep"][ee]) for k in TR
                   if sess_of(k) == s and "deep" in TR[k]]
            kps = sorted({p[0] for p in pts})
            if len(pts) < 3 or len(kps) < 3 or kps[-1] / kps[0] < 1.8:
                continue
            A = np.array([[1.0, 1.0 / p[0]] for p in pts])
            y = np.array([p[1] for p in pts])
            p_, *_ = np.linalg.lstsq(A, y, rcond=None)
            yh = A @ p_
            r2 = 1 - np.sum((y - yh) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-12)
            fits[f"{s}/{ch}"] = dict(theta0=round(float(p_[0]), 2),
                                     tauf_raw=round(float(p_[1]) * np.pi / 180, 2),
                                     r2=round(float(r2), 3), n=len(pts), kps=kps)
            print(f"{s} {ch:<5}: θ0 {p_[0]:+.2f}° · τf {p_[1] * np.pi / 180:+.2f} raw | R² {r2:.3f} | kp {kps}", flush=True)

    # ---- T2: 슬립 상관 ----
    print("\n=== T2 deep kp·e ↔ 슬립 ===", flush=True)
    corr = {}
    for tag, fld in (("deep", "slip_deep_px"), ("full", "slip_px")):
        xs, ys, lab = [], [], []
        for k, e in TR.items():
            if "deep" in e and e.get(fld) is not None:
                xs.append(abs(e[fld])); ys.append(e["deep"]["kpe1"]); lab.append(k)
        if len(xs) >= 5:
            r = float(np.corrcoef(xs, ys)[0, 1])
            sl_, ic = np.polyfit(xs, ys, 1)
            corr[tag] = dict(r=round(r, 3), slope=round(float(sl_), 3), n=len(xs))
            print(f"kpe1 vs |{fld}|: r {r:+.3f} · 기울기 {sl_:+.3f} raw/px · n {len(xs)}", flush=True)
    # knee도
    xs, ys = [], []
    for k, e in TR.items():
        if "deep" in e and e.get("slip_deep_px") is not None:
            xs.append(abs(e["slip_deep_px"])); ys.append(e["deep"]["kpe2"])
    if len(xs) >= 5:
        r = float(np.corrcoef(xs, ys)[0, 1])
        corr["knee_deep"] = dict(r=round(r, 3), n=len(xs))
        print(f"kpe2 vs |deep_px|: r {r:+.3f} · n {len(xs)}", flush=True)

    # ---- T3: 히스테리시스 ----
    print("\n=== T3 접근 방향별 e (유지창) ===", flush=True)
    hyst = {}
    for s in sorted({sess_of(k) for k in TR}):
        for dirn in ("desc", "asc"):
            hh = [h for k in TR if sess_of(k) == s for h in TR[k]["holds"] if h["dir"] == dirn]
            if hh:
                hyst[f"{s}/{dirn}"] = dict(n=len(hh),
                                           e1=round(float(np.median([h["e1"] for h in hh])), 2),
                                           e2=round(float(np.median([h["e2"] for h in hh])), 2))
        a, b = hyst.get(f"{s}/desc"), hyst.get(f"{s}/asc")
        if a and b:
            print(f"{s}: desc n{a['n']} e1 {a['e1']:+.2f}° e2 {a['e2']:+.2f}° || asc n{b['n']} e1 {b['e1']:+.2f}° e2 {b['e2']:+.2f}°", flush=True)

    safe.atomic_json_write(HERE / "_fs_track.json",
                           dict(trials={k: {kk: vv for kk, vv in v.items() if kk != "holds"} for k, v in TR.items()},
                                holds={k: v["holds"] for k, v in TR.items() if v["holds"]},
                                fits=fits, slip_corr=corr, hyst=hyst))
    print("\ndone → _fs_track.json", flush=True)


if __name__ == "__main__":
    main()
