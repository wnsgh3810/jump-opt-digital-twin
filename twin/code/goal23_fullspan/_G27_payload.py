# -*- coding: utf-8 -*-
"""_G27_payload — **페이로드 s2s = 로봇 전체로 하는 분동 실험** (고raw 구간 교정, 08-08).

왜 이게 필요한가
  raw→토크 정본곡선은 **raw ≤ 11.5 만 분동(2/4kg 발끝)으로 검증**됐고, 그 위는 **절대값 불신
  로드셀의 외삽**이다 (데이터 사전 등재). 마라톤 G 의 남은 최대 불확실이 바로 이 구간이다.
  그런데 `26.06.04/no_cvt` 에 **0 / 5 / 7.5 kg 페이로드 sit-to-stand** 가 있고,
  **준정적**(|dq2| 중앙 0.061 rad/s)이며 **raw2 가 18 까지** 간다. 분동 실험의 상위 호환이다.

원리 (분동 실험과 동일 — 척도가 약분된다)
  페이로드는 **베이스**에 얹힌다. 베이스는 수직 레일 위라 회전이 없으므로 페이로드의 효과는
  **순수 수직 하중**이다. 두 하중 조건의 차이는:
        Δτ_i = Δm · g · (∂z_base/∂q_i)          ← **정확히 계산 가능** (질량이 알려짐)
  같은 자세에서 측정된 Δraw_i 와 나누면 그 토크 대역의 **Nm/raw 가 나온다**.
  오프셋·중력·자체마찰은 **차분으로 소거**된다.

마찰 처리: G3 과 동일하게 **방향평균** (상행·하행 통과의 평균 → 쿨롱이 부호 반전해 소거).
CLI: python _G27_payload.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                                          # noqa: E402
import fs_runner as FR                                        # noqa: E402
from _G10_energy import Reduced                               # noqa: E402

G = 9.80665
ROOT = FD.ROOT / "26_06_04" / "no_cvt"
CONDS = [("no_load", 0.0), ("load_5", 5.0), ("load_7.5", 7.5)]


def load(c):
    f = ROOT / c
    if not (f / "hip.xlsx").exists():
        f = f / "raw_unwrap"
    h = pd.read_excel(f / "hip.xlsx"); k = pd.read_excel(f / "knee.xlsx")
    n = min(len(h), len(k))
    t = np.array(h["Time"].to_numpy(float)[:n], float, copy=True); t -= t[0]
    return dict(t=t, q1=h["currentAngle"].to_numpy(float)[:n],
                q2=k["currentAngle"].to_numpy(float)[:n],
                r1=h["currentTorque"].to_numpy(float)[:n],
                r2=k["currentTorque"].to_numpy(float)[:n],
                v1=h["currentAngleVelocity"].to_numpy(float)[:n],
                v2=k["currentAngleVelocity"].to_numpy(float)[:n])


def diravg(d, grid, key, on="q2", vth=0.02):
    """방향평균: q2 격자에서 상행/하행 각각 평균낸 뒤 두 방향의 평균 (쿨롱 소거)."""
    q = d[on]; y = d[key]; v = d["v2" if on == "q2" else "v1"]
    out = []
    for mask in (v > vth, v < -vth):
        if mask.sum() < 200:
            return None
        qq, yy = q[mask], y[mask]
        o = np.argsort(qq); qq, yy = qq[o], yy[o]
        uq, inv = np.unique(np.round(qq, 4), return_inverse=True)
        out.append(np.interp(grid, uq, np.bincount(inv, yy) / np.bincount(inv),
                             left=np.nan, right=np.nan))
    return 0.5 * (out[0] + out[1])


def main():
    R = Reduced(FR.fs_twin())
    D = {c: load(c) for c, m in CONDS}
    print("=" * 118)
    print("① 무결성 — 세 하중 조건이 같은 궤적·같은 준정적 조건인가")
    print(f"{'조건':<10}{'kg':>5}{'표본':>7}{'길이s':>7}{'|dq2|중앙':>10}{'|dq2|p95':>10}"
          f"{'q2 범위[°]':>18}{'|raw2|max':>10}")
    for c, m in CONDS:
        d = D[c]
        print(f"{c:<10}{m:5.1f}{len(d['t']):7d}{d['t'][-1]:7.1f}"
              f"{np.median(np.abs(d['v2'])):10.3f}{np.percentile(np.abs(d['v2']),95):10.3f}"
              f"[{np.degrees(d['q2']).min():+8.1f},{np.degrees(d['q2']).max():+7.1f}]"
              f"{np.abs(d['r2']).max():10.2f}")
    print("   ※ no_load 는 1.7s 단발이라 방향평균 불가 → **5kg ↔ 7.5kg 차등(Δm=2.5kg)** 이 주경로.")

    # ── ② 5kg ↔ 7.5kg 차등 (Δm = 2.5 kg) ──
    lo = max(np.degrees(D[c]["q2"]).min() for c in ("load_5", "load_7.5"))
    hi = min(np.degrees(D[c]["q2"]).max() for c in ("load_5", "load_7.5"))
    grid = np.radians(np.linspace(lo + 2, hi - 2, 60))
    print("\n" + "=" * 118)
    print(f"② ★ 차등 교정 (Δm = 2.5 kg) — 공통 q2 [{lo+2:.1f}, {hi-2:.1f}]°")
    Y = {}
    for c in ("load_5", "load_7.5"):
        Y[c] = {k: diravg(D[c], grid, k) for k in ("r1", "r2", "q1")}
        if Y[c]["r2"] is None:
            print(f"   {c}: 방향평균 불가 (한 방향 표본 부족)")
            return
    q1g = 0.5 * (Y["load_5"]["q1"] + Y["load_7.5"]["q1"])
    print(f"{'q2[°]':>8}{'q1[°]':>8}{'∂z/∂q1':>9}{'∂z/∂q2':>9}"
          f"{'Δτ1 계산':>10}{'Δraw1':>9}{'Nm/raw1':>10}"
          f"{'Δτ2 계산':>10}{'Δraw2':>9}{'Nm/raw2':>10}{'raw2 수준':>10}")
    ROWS = []
    for i in range(0, len(grid), 5):
        if not np.isfinite(q1g[i]):
            continue
        s = R.MV(q1g[i], grid[i])
        dz1, dz2 = s["dzb"]
        dt1 = 2.5 * G * dz1; dt2 = 2.5 * G * dz2
        dr1 = Y["load_7.5"]["r1"][i] - Y["load_5"]["r1"][i]
        dr2 = Y["load_7.5"]["r2"][i] - Y["load_5"]["r2"][i]
        if not (np.isfinite(dr1) and np.isfinite(dr2)):
            continue
        lvl = 0.5 * (abs(Y["load_7.5"]["r2"][i]) + abs(Y["load_5"]["r2"][i]))
        ROWS.append(dict(q2=np.degrees(grid[i]), q1=np.degrees(q1g[i]), dz1=dz1, dz2=dz2,
                         dt1=dt1, dt2=dt2, dr1=dr1, dr2=dr2, lvl=lvl))
        print(f"{np.degrees(grid[i]):8.1f}{np.degrees(q1g[i]):8.1f}{dz1:9.4f}{dz2:9.4f}"
              f"{dt1:10.3f}{dr1:9.3f}{dt1/dr1 if abs(dr1)>0.3 else np.nan:10.3f}"
              f"{dt2:10.3f}{dr2:9.3f}{dt2/dr2 if abs(dr2)>0.3 else np.nan:10.3f}{lvl:10.2f}")

    if not ROWS:
        print("   유효 격자점 없음")
        return
    print("\n" + "=" * 118)
    print("③ ★★ 전역 회귀 (원점 통과: Δτ = s · Δraw) — 고raw 대역의 Nm/raw")
    for ch, kt, kr in ((1, "dt1", "dr1"), (2, "dt2", "dr2")):
        A = np.array([[r[kr], r[kt]] for r in ROWS if abs(r[kr]) > 0.2])
        if len(A) < 4:
            print(f"   ch{ch}: 유효 표본 부족 ({len(A)})")
            continue
        s = float(A[:, 0] @ A[:, 1] / (A[:, 0] @ A[:, 0]))
        res = A[:, 1] - s * A[:, 0]
        r2 = 1 - np.var(res) / max(np.var(A[:, 1]), 1e-12)
        lv = np.median([r["lvl"] for r in ROWS])
        print(f"   {'힙' if ch==1 else '무릎'}: **{s:.4f} Nm/raw**  (n={len(A)}, R²={r2:.4f}, "
              f"잔차 RMS {np.sqrt(np.mean(res**2)):.3f} Nm)  · raw 대역 중앙 {lv:.1f}")
    print("\n   비교 기준")
    print(f"   {'':<22}{'Nm/raw':>10}")
    print(f"   {'분동 실측 (raw≤11.5)':<22}{1.24:10.3f}")
    print(f"   {'a_hat (선형 이득)':<22}{0.682:10.3f}")
    for raw in (12, 15, 18, 20):
        os.environ["FS_TMAP"] = "canon"
        f = FR._tmap_init(FR.fs_twin()["P"], FR.fs_twin()["P"].A_PAPER)
        print(f"   {f'정본곡선 국소기울기@raw{raw}':<22}{(f(raw+0.5,1.,1)-f(raw-0.5,1.,1)):10.3f}")
        break
    json.dump([{k: float(v) for k, v in r.items()} for r in ROWS],
              io.open(HERE / "_G27_payload.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: _G27_payload.json")


if __name__ == "__main__":
    main()
