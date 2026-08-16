# -*- coding: utf-8 -*-
"""_G6_zerogain — 26_08_07/no_current2: **게인 0 (모터 통전·토크 명령 0)** 실험 분석.

설계 의도: 전원을 켜되 토크를 0으로 명령하면 **센서는 살아있는데 실제 토크는 0**이다.
  → 채널이 읽는 값 = **오프셋 그 자체**.
  → 그리고 다리를 아무리 빨리 흔들어도 실제 토크는 계속 0이므로,
    **속도에 따라 값이 변하면 그건 전부 판독 아티팩트**다 (동적 결손의 '판독 성분' 직접 측정).
  ※ 감속기 효율 저하는 실제로 토크를 먹는 것이라 이 시험으로는 안 잡힌다 (비행 구간 분석 몫).

구간(사용자 수행): 0~20s 정지 · 20~50s 저속 왕복 · 50~80s 고속/자유진동 ·
                   80~110s 여러 자세 정지 · 110~164s 재정지
CLI: python _G6_zerogain.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                       # noqa: E402

SESS = FD.ROOT / "26_08_07" / "no_current2"
FS = 500.0


def load():
    h = pd.read_excel(SESS / "hip.xlsx"); k = pd.read_excel(SESS / "knee.xlsx")
    n = min(len(h), len(k))
    t = np.array(h["Time"].to_numpy(float)[:n], float, copy=True); t -= t[0]
    d = dict(t=t, n=n)
    for tag, s in (("1", h), ("2", k)):
        d["q" + tag] = s["currentAngle"].to_numpy(float)[:n]
        d["qd" + tag] = s["desiredAngle"].to_numpy(float)[:n]
        d["dq" + tag] = s["currentAngleVelocity"].to_numpy(float)[:n]
        d["raw" + tag] = s["currentTorque"].to_numpy(float)[:n]
        d["tdes" + tag] = s["desiredTorque"].to_numpy(float)[:n] if "desiredTorque" in s else None
    return d


def main():
    d = load()
    print("=" * 108)
    print(f"① 기본 확인 — 게인 0 이 실제로 걸렸나 (토크가 0 근처여야 한다)")
    print(f"   표본 {d['n']}  길이 {d['t'][-1]:.1f}s")
    for tag, nm in (("1", "힙"), ("2", "무릎")):
        r = d["raw" + tag]
        print(f"   {nm:<4} raw: 평균 {r.mean():+.4f}  중앙 {np.median(r):+.4f}  "
              f"표준편차 {r.std():.4f}  범위 [{r.min():+.3f}, {r.max():+.3f}]  고유값 {len(np.unique(r))}개")
        print(f"        각도 [{np.degrees(d['q'+tag]).min():+.1f}, {np.degrees(d['q'+tag]).max():+.1f}]°  "
              f"|dq|max {np.abs(d['dq'+tag]).max():.2f} rad/s")
    print(f"   (참고: 무동력 동결값은 힙 +0.7077 / 무릎 −0.0308, 잡음 정확히 0 이었다)")

    # ── ② 시간 구간별 ──
    print("\n" + "=" * 108)
    print("② 구간별 — 정지 오프셋 · 속도 의존 · 자세 의존 · 드리프트")
    SEG = [(0, 20, "정지 ①"), (20, 50, "저속 왕복"), (50, 80, "고속/자유진동"),
           (80, 110, "자세별 정지"), (110, 1e9, "정지 ②")]
    print(f"{'구간':<14}{'t[s]':>11}{'표본':>7} | {'힙 raw 평균':>11}{'±std':>8}{'|dq1|max':>9}"
          f" | {'무릎 raw 평균':>12}{'±std':>8}{'|dq2|max':>9}")
    for a, b, nm in SEG:
        m = (d["t"] >= a) & (d["t"] < b)
        if m.sum() < 100:
            continue
        print(f"{nm:<14}{f'{a:.0f}~{min(b,d[chr(116)][-1]):.0f}':>11}{int(m.sum()):7d} | "
              f"{d['raw1'][m].mean():+11.4f}{d['raw1'][m].std():8.4f}{np.abs(d['dq1'][m]).max():9.2f} | "
              f"{d['raw2'][m].mean():+12.4f}{d['raw2'][m].std():8.4f}{np.abs(d['dq2'][m]).max():9.2f}")

    # ── ③ ★ 속도 의존 (핵심) ──
    print("\n" + "=" * 108)
    print("③ ★ 속도 의존 — 실제 토크는 항상 0 이므로 속도에 따라 변하면 **전부 판독 아티팩트**")
    for tag, nm in (("1", "힙"), ("2", "무릎")):
        v = d["dq" + tag]; r = d["raw" + tag]
        print(f"\n   [{nm}]")
        print(f"{'속도 구간[rad/s]':>20}{'표본':>8}{'raw 평균':>10}{'±std':>8}{'정지대비':>10}")
        base = None
        edges = [-99, -3, -1.5, -0.6, -0.2, -0.03, 0.03, 0.2, 0.6, 1.5, 3, 99]
        rows = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (v >= lo) & (v < hi)
            if m.sum() < 50:
                continue
            mu = r[m].mean()
            if lo == -0.03:
                base = mu
            rows.append((lo, hi, int(m.sum()), mu, r[m].std()))
        for lo, hi, n, mu, sd in rows:
            print(f"{f'{lo:+6.2f} ~ {hi:+6.2f}':>20}{n:8d}{mu:+10.4f}{sd:8.4f}"
                  f"{(mu-base):+10.4f}" if base is not None else "")
        # 부호 대칭성: |v| 같은 크기에서 +방향 vs −방향
        print(f"      {'|속도|':>9}{'+방향 평균':>11}{'−방향 평균':>11}{'차이(부호항)':>13}{'평균(속도항)':>13}")
        for lo, hi in ((0.05, 0.3), (0.3, 1.0), (1.0, 2.5), (2.5, 6.0)):
            mp = (v >= lo) & (v < hi); mn = (v <= -lo) & (v > -hi)
            if mp.sum() < 50 or mn.sum() < 50:
                continue
            a1, a2 = r[mp].mean(), r[mn].mean()
            print(f"      {f'{lo:.2f}~{hi:.2f}':>9}{a1:+11.4f}{a2:+11.4f}{(a1-a2)/2:+13.4f}{(a1+a2)/2:+13.4f}")

    # ── ④ 자세 의존 ──
    print("\n" + "=" * 108)
    print("④ 자세 의존 — 정지 표본만 각도별로 (실제 토크 0 이므로 각도와 무관해야 한다)")
    still = (np.abs(d["dq1"]) < 0.05) & (np.abs(d["dq2"]) < 0.05)
    q1d = np.degrees(d["q1"])
    print(f"{'q1 구간[°]':>16}{'표본':>8}{'힙 raw':>10}{'±std':>8}{'무릎 raw':>10}{'±std':>8}")
    for lo in range(-180, -10, 20):
        m = still & (q1d >= lo) & (q1d < lo + 20)
        if m.sum() < 100:
            continue
        print(f"{f'{lo} ~ {lo+20}':>16}{int(m.sum()):8d}{d['raw1'][m].mean():+10.4f}"
              f"{d['raw1'][m].std():8.4f}{d['raw2'][m].mean():+10.4f}{d['raw2'][m].std():8.4f}")

    # ── ⑤ 드리프트 ──
    print("\n" + "=" * 108)
    print("⑤ 시간 드리프트 — 정지 표본만 10초 단위")
    print(f"{'t[s]':>10}{'표본':>8}{'힙 raw':>10}{'무릎 raw':>10}")
    for a in range(0, int(d["t"][-1]), 10):
        m = still & (d["t"] >= a) & (d["t"] < a + 10)
        if m.sum() < 100:
            continue
        print(f"{f'{a}~{a+10}':>10}{int(m.sum()):8d}{d['raw1'][m].mean():+10.4f}{d['raw2'][m].mean():+10.4f}")

    # ── ⑥ 자유진동 주기 재확인 (모터 ON 상태) ──
    print("\n" + "=" * 108)
    print("⑥ 모터 ON(토크 0) 상태의 자유진동 주기 — 무동력(모터 OFF) 측정과 비교")
    m = (d["t"] >= 40) & (d["t"] <= 115)
    tt, qq, vv = d["t"][m], d["q1"][m], d["dq1"][m]
    s = np.sign(vv); s[np.abs(vv) < 0.30] = 0
    turns, last = [], 0
    for i in range(len(s)):
        if s[i] != 0:
            if last != 0 and s[i] != last:
                turns.append(i)
            last = s[i]
    hp = []
    for i in range(len(turns) - 1):
        dur = tt[turns[i + 1]] - tt[turns[i]]
        if 0.2 < dur < 1.6:
            th0 = np.radians(abs(np.degrees(qq[turns[i + 1]]) - np.degrees(qq[turns[i]]))) / 2
            hp.append((th0, 2 * dur, 2 * dur / (1 + th0 ** 2 / 16 + 11 * th0 ** 4 / 3072)))
    if hp:
        T0 = np.mean([x[2] for x in hp])
        print(f"   반스윙 {len(hp)}개 · 대진폭 보정 T₀ = {T0:.4f} ± {np.std([x[2] for x in hp]):.4f} s")
        print(f"   (무동력 측정: T₀ = 1.2330 ± 0.0911 s → I = 0.051~0.055 kg·m²)")
        gA = 1.4286
        print(f"   → I = {gA/(2*np.pi/T0)**2:.5f} kg·m²  (gA=1.4286 Nm 기준)")
    else:
        print("   자유진동 구간 미검출")


if __name__ == "__main__":
    main()
