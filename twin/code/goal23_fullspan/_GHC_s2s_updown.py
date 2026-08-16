# -*- coding: utf-8 -*-
"""**마찰인가, 하중이 지나가는 길인가** — 올라갈 때와 내려갈 때를 갈라 잰다 (08-14 신설).

■ 왜 이 시험이 가르나
  마찰은 **움직임을 방해**하므로 방향이 바뀌면 **부호가 뒤집힌다**.
  중력이 지렛대를 타고 크랭크로 전해지는 몫은 **방향과 무관**하다 (자세만의 함수).
  그래서 같은 자세를 **일어설 때**와 **앉을 때** 각각 재서 비교하면 둘을 가를 수 있다.
  이 저장소가 무게추 실험에서 쓴 "상행−하행" 분해와 같은 원리인데, 여기서는 실제 동작에 쓴다.

■ 재는 값
  짧은 창(0.15초)을 매번 실측 상태로 새로 시작해 재생하되, 무릎(크랭크) 명령에 일정한
  여분 Δ 를 더해 창 끝의 어긋남을 0 으로 만드는 Δ 를 되찾는다 [명령 N·m]. **0 이 완벽**.

■ 읽는 법
  · Δ(올라갈 때) ≈ Δ(내려갈 때)  → 방향 무관 = **하중이 지나가는 길**(기하·중력 반영) 문제
  · Δ(올라갈 때) ≈ −Δ(내려갈 때) → 방향 반대 = **마찰**
  · 절반합 = 방향 무관 성분 · 절반차 = 마찰 성분  (두 성분을 수치로 분리해 낸다)

사용법: python _GHC_s2s_updown.py
"""
from __future__ import annotations

import collections
import os
import sys
from pathlib import Path

os.environ.setdefault("FS_SWEEP_AIR", "0")
os.environ.setdefault("FS_SWEEP_S2S", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
HERE = str(Path(__file__).parent)
sys.path.insert(0, HERE)
os.chdir(HERE)

import numpy as np                       # noqa: E402
import fs_data as FD                     # noqa: E402
import fs_runner as FR                   # noqa: E402
import fs_cvt as FC                      # noqa: E402
import _GHB_sweep as S                   # noqa: E402
from _GHC_s2s_missing import solve_delta  # noqa: E402  (같은 되찾기 방법을 쓴다)

WIN, STEP = 0.15, 0.05
BINS = [(-180, -155), (-155, -120), (-120, -80), (-80, 0)]
VMIN = 0.35        # 이보다 느린 창은 방향이 애매해 버린다 [rad/s]
S2S_DIR = FD.S2S_DIR


def load_full(sub):
    """**전 구간** 기록을 읽는다 (앉는 구간이 여기에만 있다).

    ☠ 함정: 폴더 이름과 반대로, 위쪽 파일이 토크를 **푼 것**이고 `raw_unwrap/` 이 ±18 에서
      **감긴 원본**이다 (08-14 원자료 감사에서 확인). 다만 실제로 감긴 것은 한 경우의
      무릎뿐이고 나머지는 이미 멀쩡하다.
    ☠ 08-14 에 한 번 틀렸다: "이웃 표본 차이가 36 근처면 감긴 것" 이라고 거칠게 판정했더니
      **멀쩡하던 3 경우까지 망가뜨렸다** (정본 창과 최대 6~15 N·m 어긋남). 그래서 지금은
      **푼 것과 안 푼 것 두 후보를 만들어, 정본 창과 더 잘 맞는 쪽을 데이터가 고르게** 한다.
    ★ 그리고 고른 뒤에도 정본 창과 일치하는지 다시 확인하고, 안 맞으면 그 경우는 버린다.
    """
    import pandas as pd
    fold = S2S_DIR / sub / "raw_unwrap"
    if not (fold / "knee.xlsx").exists():
        return None
    out = {}
    for ch, nm in ((1, "hip"), (2, "knee")):
        df = pd.read_excel(fold / f"{nm}.xlsx")
        c = {k.lower().replace(" ", ""): k for k in df.columns}
        g = lambda k: np.asarray(df[c[k]], float)          # noqa: E731
        t = g("time")
        out[f"tau_raw{ch}"] = g("currenttorque").copy()
        out[f"tau_unw{ch}"] = np.unwrap(g("currenttorque"), period=36.0)
        out[f"t{ch}"] = t
        out[f"q{ch}"] = g("currentangle")
        out[f"dq{ch}"] = g("currentanglevelocity")
    return out


def win_abs_t(sub):
    """정본 창 파일의 **절대 시간** [s].

    ☠ 08-14 함정: 창을 읽는 코드는 시간을 0 부터로 다시 매긴다(0→1.92초). 전 구간 기록은
      절대 시간(44.91→46.83초)이다. 이걸 모르고 겹쳐 보면 엉뚱한 순간끼리 비교해
      "토크가 6~38 N·m 어긋난다"는 가짜 경고가 난다 (실제로 한 번 그렇게 읽었다).
      절대 시간으로 맞추면 두 기록은 **완전히 같다** (최대 차이 0.0, 어긋난 표본 0개).
    """
    import pandas as pd
    df = pd.read_excel(S2S_DIR / sub / "knee.xlsx")
    col = [c for c in df.columns if "time" in c.lower()][0]
    return np.asarray(df[col], float)


def pick_tau(sub, out, dwin):
    """푼 것 / 안 푼 것 중 **정본 창과 더 잘 맞는 쪽**을 데이터가 고르게 한다."""
    tw = win_abs_t(sub)
    n = min(len(tw), len(dwin["t"]))
    dwin = dict(dwin, t=tw[:n], raw1=np.asarray(dwin["raw1"])[:n], raw2=np.asarray(dwin["raw2"])[:n])
    t0, t1 = float(dwin["t"][0]), float(dwin["t"][-1])
    chosen = {}
    for ch in (1, 2):
        t = out[f"t{ch}"]
        m = (t >= t0) & (t <= t1)
        if m.sum() < 50:
            return None, None
        best, bname, berr = None, None, np.inf
        for nm, v in (("그대로", out[f"tau_raw{ch}"]), ("풀어서", out[f"tau_unw{ch}"])):
            e = float(np.max(np.abs(np.interp(dwin["t"], t[m], v[m]) - dwin[f"raw{ch}"])))
            if e < berr:
                best, bname, berr = v, nm, e
        chosen[ch] = (best, bname, berr)
    t = out["t2"]
    d = dict(t=t, q2=out["q2"], dq2=out["dq2"], raw2=chosen[2][0],
             q1=np.interp(t, out["t1"], out["q1"]),
             dq1=np.interp(t, out["t1"], out["dq1"]),
             raw1=np.interp(t, out["t1"], chosen[1][0]))
    info = f"힙 {chosen[1][1]}(차 {chosen[1][2]:.3f}) · 무릎 {chosen[2][1]}(차 {chosen[2][2]:.3f})"
    return d, (info, max(chosen[1][2], chosen[2][2]))


def check_full(sub, dfull, dwin):
    """전 구간 기록의 토크가 창 파일(정본)과 겹치는 구간에서 같은지 확인한다."""
    t0, t1 = float(dwin["t"][0]), float(dwin["t"][-1])
    m = (dfull["t"] >= t0) & (dfull["t"] <= t1)
    if m.sum() < 50:
        return None
    e2 = np.max(np.abs(np.interp(dwin["t"], dfull["t"][m], dfull["raw2"][m]) - dwin["raw2"]))
    e1 = np.max(np.abs(np.interp(dwin["t"], dfull["t"][m], dfull["raw1"][m]) - dwin["raw1"]))
    return float(e1), float(e2)


def scan(ft, d, sign):
    """sign=+1 이면 펴는 방향(일어서기), −1 이면 접는 방향(앉기) 창만 모은다."""
    t = d["t"]
    dq = FD._smooth(np.nan_to_num(d["dq2"]), 11) if hasattr(FD, "_smooth") else np.nan_to_num(d["dq2"])
    acc = collections.defaultdict(list)
    a = float(t[0])
    while a + WIN <= float(t[-1]):
        mm = (t >= a) & (t <= a + WIN)
        if mm.sum() >= 20:
            v = float(np.mean(dq[mm]))
            if abs(v) >= VMIN and np.sign(v) == sign:
                dl = solve_delta(ft, d, mm)
                if dl is not None:
                    cr = float(np.degrees(np.mean(d["q2"][mm])))
                    for b in BINS:
                        if b[0] <= cr < b[1]:
                            acc[b].append(dl); break
        a += STEP
    return acc


def main():
    S._apply(S.env_of("canon_cap", np.asarray(S.DEPLOY, float)))
    m0 = float(os.environ.get("FS_MASS", "3.30"))
    print("모자란 무릎 명령 토크 Δ [N·m] — 0 이 완벽 · 방향별로 갈라 잰다")
    print("  절반합 = (올라갈때+내려갈때)/2 = **방향 무관 성분** (하중이 지나가는 길)")
    print("  절반차 = (올라갈때−내려갈때)/2 = **마찰 성분** (움직임을 방해하는 것)")
    hdr = " ".join(f"{a}~{b}".rjust(22) for a, b in BINS)
    print(f"\n{'경우':16s} {hdr}")
    print("-" * (17 + 23 * len(BINS)))
    for sub, pay, cvt in FD.S2S_CASES:
        dw = FD.load_s2s(sub)
        if dw is None:
            continue
        raw = load_full(sub)
        if raw is None:
            print(f"{sub}: 전 구간 기록 없음 — 건너뜀"); continue
        d, pick = pick_tau(sub, raw, dw)
        if d is None or pick[1] > 0.5:
            print(f"{sub}: ⚠ 전 구간 기록이 정본 창과 안 맞는다 "
                  f"({'—' if pick is None else pick[0]}) — 건너뜀")
            continue
        print(f"{sub}: 전 구간 토크 선택 = {pick[0]}  ✔ 정본 창과 일치")
        d["l_i"] = dw["l_i"]
        os.environ["FS_MASS"] = f"{m0 + pay:.4f}"
        FR._CACHE.clear(); S._CVT_STAMPED.clear()
        ft = FC.cvt_ft(float(d["l_i"]), ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
        up, dn = scan(ft, d, +1), scan(ft, d, -1)
        for lab, get in (("올라갈때", lambda b: up.get(b)), ("내려갈때", lambda b: dn.get(b)),
                         ("절반합", None), ("절반차", None)):
            row = []
            for b in BINS:
                u, w = up.get(b), dn.get(b)
                if lab == "올라갈때":
                    row.append(f"{np.mean(u):+9.2f}({len(u):2d})" if u else " " * 13)
                elif lab == "내려갈때":
                    row.append(f"{np.mean(w):+9.2f}({len(w):2d})" if w else " " * 13)
                elif u and w:
                    x = (np.mean(u) + np.mean(w)) / 2 if lab == "절반합" else (np.mean(u) - np.mean(w)) / 2
                    row.append(f"{x:+9.2f}     ")
                else:
                    row.append(" " * 13)
            name = f"{sub} {lab}" if lab in ("올라갈때",) else f"{'':16s}{lab}"
            print(f"{name:16s} " + " ".join(f"{c:>22s}" for c in row))
        print()
    print("변속기 지렛대 비율: −176° 0.014(사점) · −170° 0.19 · −140° 0.70 · −90° 0.84 · −20° 0.50")


if __name__ == "__main__":
    main()
