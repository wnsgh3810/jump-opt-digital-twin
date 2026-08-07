# -*- coding: utf-8 -*-
"""_G9_flight — **점프 비행 구간**으로 고속 동적 토크 전달률 검증 (G5-E 이월분, 새 실험 불필요).

왜 비행 구간인가
  이지(발이 땅에서 떨어짐) 후에는 **접촉이 없다**. 남는 것은 (베이스 탄도 + 관절 관성·중력)뿐이라
  동역학이 **측정된 관절각만으로 완전히 결정**된다. 관성은 G6/G8 에서 **토크 센서 없이**
  (무동력 자유진동) 0.057±0.003 kg·m² 로 확정했고, 트윈 M11(0.045~0.056)과 정합한다.
  ⇒ 비행 구간의 **필요 토크를 계산**해 기록 raw 와 대조하면 **점프 속도대(10~30 rad/s)의
    명령→전달 비율**이 나온다. 정적 추(≤0.1 rad/s)·공중 가진(≤3.3 rad/s)이 못 덮던 영역.

비행 중 베이스 처리
  베이스는 수직 레일 위에서 자유낙하하므로 그 일반화력은 **0** 이다. 3자유도
  (z_b, q1, q2) 역동역학에서 z̈_b 를 "베이스 일반화력 = 0" 조건으로 풀고, 그 해에서 관절 토크를 얻는다.
  (동역학이 qacc 에 선형이므로 z̈_b=0,1 두 번 평가로 정확히 해가 나온다.)
  ★ 자유낙하라 유효중력이 거의 0 → **중력 오차(트윈 +22%)에 둔감**하고 관성이 지배한다.

토크 비교는 **G5 정본 곡선**(분동 크기 + 로드셀 모양)으로 raw→Nm 변환해 수행.
CLI: python _G9_flight.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                       # noqa: E402

FS, DT = 500.0, 1.0 / 500.0
SESSIONS = ["26_07_24", "26_07_27", "26_07_25", "26_06_02", "26_04_24",
            "26_03_24/Jump/Jump_No_Tr"]


def lpf(x, fc=25.0, order=4):
    b, a = butter(order, fc / (FS / 2), btype="low")
    return filtfilt(b, a, np.asarray(x, float))


def load2(fold):
    h = pd.read_excel(fold / "hip2.xlsx"); k = pd.read_excel(fold / "knee2.xlsx")
    n = min(len(h), len(k))
    t = np.array(h["Time"].to_numpy(float)[:n], float, copy=True); t -= t[0]
    d = dict(t=t, n=n)
    d["q1"] = h["currentAngle"].to_numpy(float)[:n]
    d["q2"] = k["currentAngle"].to_numpy(float)[:n]
    d["raw1"] = h["currentTorque"].to_numpy(float)[:n]
    d["raw2"] = k["currentTorque"].to_numpy(float)[:n]
    g = fold / "GRF2.xlsx"
    if g.exists():
        s = pd.read_excel(g)
        c = "Current_GRF" if "Current_GRF" in s.columns else s.columns[1]
        d["grf"] = np.interp(t, s["Time"].to_numpy(float) - s["Time"].to_numpy(float)[0],
                             s[c].to_numpy(float))
    else:
        d["grf"] = None
    return d


def flight_window(d):
    """GRF 로 이지·착지 검출 (데이터 사전: GRF 절대값 금지, **상대 타이밍만 허용**)."""
    if d["grf"] is None:
        return None
    g = lpf(d["grf"], 20.0)
    pk = int(np.argmax(g))
    thr = 0.05 * g[pk]
    off = np.flatnonzero(g[pk:] < thr)
    if not len(off):
        return None
    i0 = pk + off[0]
    on = np.flatnonzero(g[i0:] > 3 * thr)
    i1 = i0 + on[0] if len(on) else len(g) - 1
    return i0, i1


def main():
    print("=" * 116)
    print("① 비행 구간 탐색 및 그 구간의 운동 크기 — 이 시험이 유효한 속도대인가")
    print(f"{'세션':<26}{'trial':<20}{'비행[s]':>9}{'길이s':>7}"
          f"{'|dq1|max':>9}{'|dq2|max':>9}{'|q̈1|max':>10}{'|q̈2|max':>10}"
          f"{'|raw1|max':>10}{'|raw2|max':>10}")
    picks = []
    for sess in SESSIONS:
        base = FD.ROOT / sess
        if not base.exists():
            continue
        for f in sorted(base.rglob("hip2.xlsx")):
            d = load2(f.parent)
            w = flight_window(d)
            if w is None or (w[1] - w[0]) < int(0.08 * FS):
                continue
            sl = slice(w[0], w[1])
            q1 = lpf(d["q1"]); q2 = lpf(d["q2"])
            v1 = np.gradient(q1, DT); v2 = np.gradient(q2, DT)
            a1 = lpf(np.gradient(v1, DT), 20.0); a2 = lpf(np.gradient(v2, DT), 20.0)
            picks.append(dict(sess=sess, tr=f.parent.name, i0=w[0], i1=w[1], d=d,
                              q1=q1, q2=q2, v1=v1, v2=v2, a1=a1, a2=a2))
            print(f"{sess:<26}{f.parent.name:<20}{d['t'][w[0]]:9.2f}{(w[1]-w[0])/FS:7.2f}"
                  f"{np.abs(v1[sl]).max():9.2f}{np.abs(v2[sl]).max():9.2f}"
                  f"{np.abs(a1[sl]).max():10.1f}{np.abs(a2[sl]).max():10.1f}"
                  f"{np.abs(d['raw1'][sl]).max():10.2f}{np.abs(d['raw2'][sl]).max():10.2f}")
    print(f"\n  비행 구간 {len(picks)}개 검출")
    print("  ※ 비교 기준: 정적 추 ≤0.1 rad/s · 26_08_02 공중가진 ≤3.3 rad/s")
    json.dump({"n": len(picks)}, io.open(HERE / "_G9_flight_survey.json", "w", encoding="utf-8"))


if __name__ == "__main__":
    main()
