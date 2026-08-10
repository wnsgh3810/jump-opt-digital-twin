# -*- coding: utf-8 -*-
"""_GB3_cmdlaw — 실로봇 PD 가 **실제로 무슨 식을 썼는지** 데이터만으로 동정한다 (마라톤G, 08-11).

왜
  08-11 자기검증에서 "실측 각도로 재구성한 명령"이 기록된 명령(raw)을 20% 나 못 맞췄다.
  같은 날 sim 무릎 토크가 실측보다 10~34ms **이르다**는 것도 나왔다. 둘 다 **시간축**
  냄새가 난다. 시뮬레이션을 끌어들이기 전에 **데이터만으로** 커맨드 법칙을 확정한다.
  (개루프 최적 ≠ 폐루프 최적 — 커맨드층은 물리와 분리해 먼저 못 박아야 한다.)

동정 대상
      raw[i] ≈ clip( kp·(qd[i−A] − q[i−B]) + kd·(dqd[i−A] − dq[i−B]) )
  A = 목표 신호를 뒤로 미는 양, B = 상태 신호를 뒤로 미는 양 [샘플, 1샘플=2ms].
  · 데이터 사전은 A−B = 2 (qd 가 2샘플 선행 기록)라고 말한다 → **검증 대상**.
  · B > 0 이면 컨트롤러가 **묵은 상태**로 계산했다는 뜻 = 실제 지연.
  kp·kd 는 (A,B) 마다 최소자승으로 구한다. 폴더 라벨과 비교해 라벨이 맞는지도 본다.

먼저 확인
  `desiredTorque` 열은 전 세션 0 — 피드포워드 항이 없다 (08-11 확인). 그래서
  raw 는 순수 PD 출력이다. 이 식 말고 다른 항을 가정할 이유가 없다.

CLI: python _GB3_cmdlaw.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                                             # noqa: E402
import safe                                                      # noqa: E402

OUT = HERE / "_compare_G50" / "_cmdlaw.json"
AMAX = 7          # 스캔 범위 [샘플]
NO_VDES = ("26.04.21",)


def lag(x, k):
    if k <= 0:
        return np.asarray(x, float)
    y = np.empty_like(np.asarray(x, float)); y[k:] = x[:-k]; y[:k] = x[0]
    return y


def fit_one(d, m, ch, g, sess):
    """(A,B) 격자에서 kp·kd 최소자승. 반환: 최적 (A,B,kp,kd,잔차) + 라벨게인 잔차."""
    qd = d["qd1"] if ch == 0 else d["qd2"]
    q = d["q1"] if ch == 0 else d["q2"]
    dqd = d["dqd1"] if ch == 0 else d["dqd2"]
    dq = d["dq1"] if ch == 0 else d["dq2"]
    raw = (d["raw1"] if ch == 0 else d["raw2"])[m]
    if sess in NO_VDES:
        dqd = np.zeros_like(dqd)
    kpL, kdL = (g[0], g[1]) if ch == 0 else (g[2], g[3])
    best = None
    for A in range(AMAX):
        for B in range(AMAX):
            e = (lag(qd, A) - lag(q, B))[m]
            de = (lag(dqd, A) - lag(dq, B))[m]
            M = np.stack([e, de], 1)
            c, *_ = np.linalg.lstsq(M, raw, rcond=None)
            r = float(np.sqrt(np.mean((M @ c - raw) ** 2)))
            rl = float(np.sqrt(np.mean((kpL * e + kdL * de - raw) ** 2)))
            if best is None or r < best["r"]:
                best = dict(A=A, B=B, kp=float(c[0]), kd=float(c[1]), r=r, rl=rl)
    # 라벨 게인 기준 최적 (A,B) 도 따로 (게인은 라벨을 믿고 시간만 찾는 판)
    bl = None
    for A in range(AMAX):
        for B in range(AMAX):
            e = (lag(qd, A) - lag(q, B))[m]
            de = (lag(dqd, A) - lag(dq, B))[m]
            rl = float(np.sqrt(np.mean((kpL * e + kdL * de - raw) ** 2)))
            if bl is None or rl < bl["r"]:
                bl = dict(A=A, B=B, r=rl)
    return best, bl, float(np.sqrt(np.mean(raw ** 2))), (kpL, kdL)


def main():
    rows = []
    sat = []
    for s, p, g, cvt, ho in FD.registry():
        if cvt or not g:
            continue
        try:
            d = FD.load2(p)
            pw = FD.plot_window(p, d)
            if pw is None:
                continue
            m = (d["t"] >= pw[0]) & (d["t"] <= pw[1])
            if m.sum() < 40:
                continue
        except Exception as ex:
            print(f"  ✗ {s}/{p.name}: {type(ex).__name__}", flush=True); continue
        for ch, nm in ((0, "힙"), (1, "무릎")):
            b, bl, rms, lab = fit_one(d, m, ch, g, s)
            rows.append(dict(sess=s, trial=p.name, ch=ch, joint=nm, rms=rms,
                             lab_kp=lab[0], lab_kd=lab[1], **b,
                             labA=bl["A"], labB=bl["B"], labr=bl["r"]))
        rr = np.abs(d["raw2"][m])
        sat.append(float(np.mean(rr > 35.5)))
        print(f"  {s}/{p.name}: OK", flush=True)
    safe.atomic_json_write(OUT, rows)

    print("\n" + "=" * 78)
    print(f"명령 클립(35.5) 초과 비율: 중앙 {100*np.median(sat):.2f}% · 최대 {100*np.max(sat):.2f}%")
    print("\n① 시간축 — 라벨 게인을 믿고 **시간만** 맞췄을 때 (1샘플 = 2ms)")
    print(f"{'세션':10s} {'관절':5s} {'A(목표)':>7s} {'B(상태)':>7s} {'A−B':>5s}  {'잔차':>6s} {'명령크기':>7s}")
    import collections
    G = collections.defaultdict(list)
    for r in rows:
        G[(r["sess"], r["joint"])].append(r)
    for k in sorted(G):
        A = G[k]
        a = np.median([x["labA"] for x in A]); b = np.median([x["labB"] for x in A])
        print(f"{k[0]:10s} {k[1]:5s} {a:7.0f} {b:7.0f} {a-b:5.0f}  "
              f"{np.mean([x['labr'] for x in A]):6.2f} {np.mean([x['rms'] for x in A]):7.1f}")

    print("\n② 게인까지 자유롭게 맞췄을 때 — 라벨이 맞는가")
    print(f"{'세션':10s} {'관절':5s} {'라벨 kp,kd':>14s} {'맞춘 kp,kd':>14s} {'비율':>6s}  "
          f"{'잔차 라벨→자유':>15s}")
    for k in sorted(G):
        A = G[k]
        lkp = np.median([x["lab_kp"] for x in A]); lkd = np.median([x["lab_kd"] for x in A])
        fkp = np.median([x["kp"] for x in A]); fkd = np.median([x["kd"] for x in A])
        print(f"{k[0]:10s} {k[1]:5s} {lkp:8.0f},{lkd:5.2f} {fkp:8.1f},{fkd:5.2f} "
              f"{fkp/lkp:6.2f}  {np.mean([x['labr'] for x in A]):6.2f} → "
              f"{np.mean([x['r'] for x in A]):6.2f}")
    print(f"\n저장 → {OUT}")


if __name__ == "__main__":
    main()
