# -*- coding: utf-8 -*-
"""fs3_recon — *3 (공중 시작~내려놓기 포함 전사) 전수 정찰 (스프린트 B Phase 0).

trial별로 추출:
  ①정확-0 보고 스팬 (채널 미활성 = 전기 영점 노출 구간) + 활성화 스텝 시각·전후 보고값
  ②공중 창 (GRF ≈ 비행 기준 & 저속 & 초기) — 정지 보고값 (영점+무부하 유지 합)
  ③접지 정지 창 (GRF ≈ 만재 & 저속, 하강 개시 전) — 보고값
  ④Δ(접지 − 공중) = 하중 응답 (상수 오프셋 무관 — 플랜트 검증용)
GRF 절대값 금지 사전 준수: GRF는 비행 기준 상대 스팬 검출에만 사용.
출력: _fs3_recon.json + 세션 요약. 원본 무수정 (deny 훅 등록됨).
CLI: python fs3_recon.py
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")


def load3(fold: Path):
    h = pd.read_excel(fold / "hip3.xlsx")
    k = pd.read_excel(fold / "knee3.xlsx")
    g = pd.read_excel(fold / "GRF3.xlsx")
    n = min(len(h), len(k), len(g))
    h, k, g = h.iloc[:n], k.iloc[:n], g.iloc[:n]
    t = h["Time"].to_numpy(float)
    return dict(t=t - t[0], t_abs=t,
                q1=h["currentAngle"].to_numpy(float), q2=k["currentAngle"].to_numpy(float),
                dq1=h["currentAngleVelocity"].to_numpy(float), dq2=k["currentAngleVelocity"].to_numpy(float),
                raw1=h["currentTorque"].to_numpy(float), raw2=k["currentTorque"].to_numpy(float),
                des1=h["desiredTorque"].to_numpy(float) if "desiredTorque" in h else np.zeros(n),
                grf=g["Current_GRF"].to_numpy(float))


def exact_zero_span(raw, t):
    """선두부터 |raw| == 0 (부동소수 그대로) 연속 스팬 길이 [s]와 끝 인덱스."""
    z = np.abs(raw) < 1e-12
    if not z[0]:
        return 0.0, 0
    i = int(np.argmin(z)) if (~z).any() else len(z) - 1
    return float(t[i] - t[0]), i


def main():
    files = sorted(p.parent for p in ROOT.rglob("hip3.xlsx") if "harness_output" not in str(p))
    OUT = {}
    for fold in files:
        key = str(fold.relative_to(ROOT)).replace("\\", "/")
        try:
            d = load3(fold)
        except Exception as ex:
            OUT[key] = dict(err=type(ex).__name__)
            continue
        t, g, r1, r2 = d["t"], d["grf"], d["raw1"], d["raw2"]
        dqm = np.maximum(np.abs(d["dq1"]), np.abs(d["dq2"]))
        gs = np.convolve(g, np.ones(25) / 25, mode="same")
        g_fl = float(np.quantile(gs, 0.02))            # 비행/무부하 기준 (최저 2%)
        g_full = float(np.quantile(gs, 0.90))          # 만재 기준
        thr_air = g_fl + 0.15 * (g_full - g_fl)
        thr_gnd = g_fl + 0.70 * (g_full - g_fl)
        # ① 정확-0 스팬 (미활성)
        z1, i1 = exact_zero_span(r1, t)
        z2, i2 = exact_zero_span(r2, t)
        # 활성 직후 정지 보고값 (활성 후 0.5~2.5s, 저속)
        def rest_after(idx):
            m = (t >= t[idx] + 0.5) & (t <= t[idx] + 2.5) & (dqm < 0.35)
            return (float(np.median(r1[m])), float(np.median(r2[m])), int(m.sum())) if m.sum() > 50 else None
        # ② 공중 창: GRF<thr_air & 저속, 최초 3s 이상 스팬 (초반 60% 내)
        air = None
        mA = (gs < thr_air) & (dqm < 0.35)
        i = 0
        N = len(t)
        while i < int(N * 0.6):
            if mA[i]:
                j = i
                while j < N and mA[j]:
                    j += 1
                if t[j - 1] - t[i] >= 1.0:
                    air = (i, j)
                    break
                i = j
            else:
                i += 1
        # ③ 접지 정지 창: 공중/시작 이후 GRF>thr_gnd & 저속 & 큰 하강 전 (첫 2s+ 스팬)
        gnd = None
        start = air[1] if air else max(i1, i2)
        mG = (gs > thr_gnd) & (dqm < 0.35)
        i = start
        while i < N:
            if mG[i]:
                j = i
                while j < N and mG[j]:
                    j += 1
                if t[j - 1] - t[i] >= 2.0:
                    gnd = (i, j)
                    break
                i = j
            else:
                i += 1
        e = dict(dur=float(t[-1]), zero_span1=z1, zero_span2=z2,
                 grf_fl=g_fl, grf_full=g_full)
        if max(i1, i2) > 0:
            ra = rest_after(max(i1, i2))
            if ra:
                e["post_enable"] = dict(raw1=ra[0], raw2=ra[1], n=ra[2])
        if air:
            ia, ja = air
            m = np.zeros(N, bool); m[ia:ja] = True; m &= dqm < 0.35
            e["air"] = dict(t0=float(t[ia]), t1=float(t[ja - 1]),
                            raw1=float(np.median(r1[m])), raw2=float(np.median(r2[m])),
                            q1=float(np.degrees(np.median(d["q1"][m]))), q2=float(np.degrees(np.median(d["q2"][m]))),
                            n=int(m.sum()))
        if gnd:
            ig, jg = gnd
            m = np.zeros(N, bool); m[ig:jg] = True; m &= dqm < 0.35
            e["gnd"] = dict(t0=float(t[ig]), t1=float(t[jg - 1]),
                            raw1=float(np.median(r1[m])), raw2=float(np.median(r2[m])),
                            q1=float(np.degrees(np.median(d["q1"][m]))), q2=float(np.degrees(np.median(d["q2"][m]))),
                            n=int(m.sum()))
        OUT[key] = e
        a = e.get("air"); gn = e.get("gnd")
        print(f"{key}: {e['dur']:.0f}s | 미활성 h{z1:.1f}/k{z2:.1f}s | "
              f"공중 {'%.0f~%.0fs raw(%+.2f,%+.2f)@(%.0f°,%.0f°)' % (a['t0'], a['t1'], a['raw1'], a['raw2'], a['q1'], a['q2']) if a else '—'} | "
              f"접지 {'%.0f~%.0fs raw(%+.2f,%+.2f)' % (gn['t0'], gn['t1'], gn['raw1'], gn['raw2']) if gn else '—'}", flush=True)
    json.dump(OUT, open(HERE / "_fs3_recon.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\ndone → _fs3_recon.json ({len(OUT)} trials)")


if __name__ == "__main__":
    main()
