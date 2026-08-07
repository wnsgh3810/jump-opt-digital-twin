# -*- coding: utf-8 -*-
"""_G40_postureloss — **전달 손실 25% 가 자세에 따라 변하는가** (마라톤G, 08-08).

왜 이걸 보나
  G37 에서 접착제(`canon_cap`)의 정체가 **전달 토크의 25% 소산 = 효율 75% 전동계**로 규명됐다.
  그런데 G39 에서 **0725 만 유일하게 dq2 가 악화**(+47%)했고, 캡 스캔에서 **0725 만 캡이
  높을수록 좋아진다**(1.62 → 1.38). 0725 는 **스쿼트가 가장 깊은**(287mm) 세션이다.

가설 (고등학생 눈높이)
  4절링크는 **자세마다 지렛대 길이가 달라진다.** 문 손잡이를 문틀 가까이서 밀면 안 열리고
  멀리서 밀면 쉽게 열리는 것과 같다. 지렛대가 나쁜 자세에서는 같은 힘을 전달하려고
  **부품끼리 더 세게 눌린다** → 마찰이 더 커진다.
  ⇒ **손실률은 상수 25% 가 아니라 자세(q2)의 함수여야 한다.**

방법
  canon_cap 의 실효 출력을 목표로 두고, **q2 구간별로** 손실 계수 fc1 을 따로 적합한다.
      y = canon_cap(raw,v),  ŷ = 정본(raw) − (fc0 + fc1·|raw|)·tanh(v/0.5)
  fc1(q2) 가 유의하게 변하면 자세 의존이 실재한다. 변하지 않으면 상수 25% 가 맞다.
  ※ 이건 J_G 최적화가 아니라 **기존 최적해의 구조를 읽는 작업**이다 (과적합 위험 없음).

CLI: python _G40_postureloss.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                                          # noqa: E402
import fs_runner as FR                                        # noqa: E402

CAP = {1: 2.4, 2: 3.5}          # 기록 구성 (G39)
K_CANON = 1.24                  # 분동 저토크 이득 [Nm/raw]


def collect():
    """세션 전체에서 (raw1,raw2,dq1,dq2,q2) 를 점프창으로 모은다."""
    out = {1: [], 2: []}
    meta = []
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
        except Exception:
            continue
        m = seg["score"]
        q2 = np.degrees(d["q2"][m])
        for ch, rk, vk in ((2, "raw2", "dq2"), (1, "raw1", "dq1")):
            r = np.asarray(d[rk][m], float); v = np.asarray(d[vk][m], float)
            out[ch].append(np.column_stack([r, v, q2, np.full(len(r), len(meta))]))
        meta.append(s)
    return {c: np.vstack(v) for c, v in out.items()}, meta


def target(ch, r, v):
    """canon_cap 실효 출력 y 와 순수 정본 c (벡터화)."""
    ft = FR.fs_twin(); P = ft["P"]; A = P.A_PAPER
    os.environ["FS_TMAP"] = "canon"; FR._TM = None
    canon = FR._tmap_init(P, A)
    vs = np.where(np.abs(v) > 1e-6, v, 1.0)
    a = P.J.ahat(A, r, vs)                                  # 벡터 호출 (핵심: 루프 금지)
    c = np.array([canon(float(x), float(w), ch) for x, w in zip(r, vs)])
    y = a + np.clip(c - a, -CAP[ch], CAP[ch])
    return y, c, vs


def fit(r, vs, y, c):
    """ŷ = c − (fc0 + fc1|r|)·tanh(vs/0.5) 최소자승 → (fc0, fc1, R²)."""
    T = np.tanh(vs / 0.5)
    M = np.column_stack([-T, -np.abs(r) * T])
    co, *_ = np.linalg.lstsq(M, y - c, rcond=None)
    res = y - c - M @ co
    r2 = 1 - np.var(res) / max(np.var(y), 1e-12)
    return float(co[0]), float(co[1]), float(r2), float(np.sqrt(np.mean(res ** 2)))


def main():
    D, meta = collect()
    print("=" * 112)
    print("① 전체 적합 (기준) — 손실 계수 fc1 과 손실률 fc1/1.24")
    BASE = {}
    for ch, nm in ((2, "무릎"), (1, "힙")):
        X = D[ch][::5]
        r, v, q2 = X[:, 0], X[:, 1], X[:, 2]
        y, c, vs = target(ch, r, v)
        fc0, fc1, r2, rms = fit(r, vs, y, c)
        BASE[ch] = (fc0, fc1)
        print(f"   {nm}: n={len(r):6d}  fc0 {fc0:+7.3f}  **fc1 {fc1:.4f}**  "
              f"손실률 **{100*fc1/K_CANON:.1f}%**   R² {r2:.4f}  잔차 {rms:.3f} Nm")

    print("\n" + "=" * 112)
    print("② ★ 자세(q2) 구간별 손실률 — 4절 지렛대 가설 검정")
    print("   가설이 맞으면 fc1 이 깊은 자세(q2 음수 큼)에서 **커야** 한다")
    EDGES = [-180, -110, -95, -80, -65, -50, -35, 0]
    OUT = {}
    for ch, nm in ((2, "무릎"), (1, "힙")):
        X = D[ch][::5]
        r, v, q2 = X[:, 0], X[:, 1], X[:, 2]
        y, c, vs = target(ch, r, v)
        print(f"\n   [{nm}]{'q2 구간[°]':>18}{'n':>8}{'fc0':>9}{'fc1':>9}{'손실률':>9}"
              f"{'R²':>8}{'|raw| 중앙':>11}")
        rows = []
        for lo, hi in zip(EDGES[:-1], EDGES[1:]):
            m = (q2 >= lo) & (q2 < hi)
            if m.sum() < 400:
                continue
            fc0, fc1, r2, rms = fit(r[m], vs[m], y[m], c[m])
            rows.append((0.5 * (lo + hi), fc1, int(m.sum())))
            print(f"        {f'[{lo},{hi})':>18}{m.sum():8d}{fc0:+9.3f}{fc1:9.4f}"
                  f"{100*fc1/K_CANON:8.1f}%{r2:8.4f}{np.median(np.abs(r[m])):11.2f}")
        OUT[nm] = rows
        if len(rows) >= 3:
            a = np.array(rows)
            sl = np.polyfit(a[:, 0], a[:, 1], 1)[0]
            print(f"        ⇒ 기울기 d(fc1)/d(q2) = {sl:+.5f} /°   "
                  f"(양수 = 얕을수록 손실 큼 · 음수 = **깊을수록 손실 큼** = 가설 지지)")
            print(f"        ⇒ 손실률 범위 {100*a[:,1].min()/K_CANON:.1f}% ~ "
                  f"{100*a[:,1].max()/K_CANON:.1f}%  (전체 상수값 "
                  f"{100*BASE[ch][1]/K_CANON:.1f}%)")

    print("\n" + "=" * 112)
    print("③ ★ 세션별 손실률 — 0725 가 정말 다른가")
    print(f"   {'세션':<12}{'n':>8}{'fc1':>9}{'손실률':>9}{'R²':>8}{'|raw2| 중앙':>12}{'q2 중앙[°]':>12}")
    SESS = {}
    X = D[2][::5]
    r, v, q2, si = X[:, 0], X[:, 1], X[:, 2], X[:, 3].astype(int)
    y, c, vs = target(2, r, v)
    for i, s in enumerate(meta):
        m = si == i
        if m.sum() < 400:
            continue
        fc0, fc1, r2, rms = fit(r[m], vs[m], y[m], c[m])
        SESS[s] = fc1
        print(f"   {s:<12}{m.sum():8d}{fc1:9.4f}{100*fc1/K_CANON:8.1f}%{r2:8.4f}"
              f"{np.median(np.abs(r[m])):12.2f}{np.median(q2[m]):12.1f}"
              + ("   ← 유일 악화 세션" if s == "26.07.25" else ""))
    json.dump(dict(base={str(k): v for k, v in BASE.items()}, bins=OUT, sess=SESS),
              io.open(HERE / "_G40_postureloss.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: _G40_postureloss.json")


if __name__ == "__main__":
    main()
