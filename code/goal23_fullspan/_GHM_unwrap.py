# -*- coding: utf-8 -*-
"""_GHM_unwrap — **토크 언랩 전수 감사** (08-12, 사용자 지시).

배경
  모터는 토크 명령을 12비트로 보내는데 전송 범위가 ±18 N·m 다. 그 범위를 넘으면 값이
  위아래로 **감긴다**. 엑셀의 토크는 그 감긴 것을 **편(unwrap) 값**이라 |값|>18 이 나온다.

  ★ 사용자 확정 (08-12): **원본 `hip.xlsx`/`knee.xlsx` 의 언랩이 항상 맞다.**
    확장판 `hip2/knee2.xlsx` 는 다르게 펴진 곳이 있다.

발단 (사용자 적발)
  변속기 폐루프 그림에서 무릎 토크가 이륙 직후 44 N·m 까지 튀었다. 원본에는 그런 값이 없다.
  대조해 보니 **정확히 +36.00**(=2×18) 만큼 어긋나 있었다 — 감긴 횟수를 한 칸 잘못 센 것이다.
  판별 증거: 그 구간은 **목표 토크가 0** 이다(이륙해서 제어가 끊김). 그러면 실제 토크도 0 을
  향해야 하는데, 원본은 0 을 지나 음으로 가고 확장판만 위로 44 까지 올라간다.

무엇을 검사하나 (두 가지 잣대)
  ① **원본과 대조** — 겹치는 구간에서 값이 다른 곳. 원본이 정답이므로 이게 1급 판정이다.
  ② **인접 점프** — 이웃한 두 점(2ms) 사이가 **36 근처로 뛰는 곳**. 모터 최대가 18 이므로
     2ms 만에 36 이 변하는 것은 물리적으로 불가능하다 = 언랩 서명. 원본이 없는 구간
     (앉기·착지)까지 볼 수 있는 유일한 방법이다.

  ※ ②는 참고용이다 — 진짜 급변(이륙 순간의 부하 해제)도 20 이상 뛸 수 있어 오탐이 있다.
    그래서 **30~42 구간**만 세고, 판정은 ①로 한다.

CLI: python _GHM_unwrap.py [fix]     ("fix" 면 교정 결과를 JSON 으로 저장)
"""
import os, sys, collections
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GHM_unwrap.json"

WRAP = 36.0        # 통신 범위 폭 [N·m] = 2 x 18
TOL = 1.0          # 원본과 이만큼 넘게 다르면 어긋난 것 [N·m]
JLO, JHI = 30.0, 42.0   # 인접 점프가 이 사이면 언랩 서명으로 센다


def audit_pair(t_ext, q_ext, orig_path, t0_abs, window=None):
    """확장판 한 채널을 원본과 대조 + 인접 점프 검사.

    반환 dict: n_diff(원본과 다른 점) · n_win(그중 채점 창 안) · med(어긋난 크기 중앙값)
               · k(36 의 배수인가) · n_jump(인접 점프 서명) · t0,t1(어긋난 구간)
    """
    r = dict(n_diff=0, n_win=0, med=np.nan, k=np.nan, n_jump=0, t0=np.nan, t1=np.nan,
             n_ov=0, exact=0)
    # ② 인접 점프 (원본 유무와 무관)
    dq = np.abs(np.diff(q_ext))
    r["n_jump"] = int(((dq >= JLO) & (dq <= JHI)).sum())
    if orig_path is None or not orig_path.exists():
        return r
    o = pd.read_excel(orig_path)
    t1 = o["Time"].to_numpy(float) - t0_abs
    q1 = o["currentTorque"].to_numpy(float)
    ov = (t_ext >= t1[0]) & (t_ext <= t1[-1])
    r["n_ov"] = int(ov.sum())
    if not ov.any():
        return r
    q1i = np.interp(t_ext, t1, q1)
    dif = q_ext - q1i
    bad = ov & (np.abs(dif) > TOL)
    r["n_diff"] = int(bad.sum())
    if not bad.any():
        return r
    i = np.where(bad)[0]
    r["med"] = float(np.median(dif[i]))
    r["k"] = float(r["med"] / WRAP)
    # 어긋난 값이 **정확히** 36 의 배수인가 (반올림 오차 0.01 안)
    r["exact"] = int(np.sum(np.abs(dif[i] - np.round(dif[i] / WRAP) * WRAP) < 0.01))
    r["t0"], r["t1"] = float(t_ext[i[0]]), float(t_ext[i[-1]])
    if window is not None:
        r["n_win"] = int(((t_ext[i] >= window[0]) & (t_ext[i] <= window[1])).sum())
    return r


def main():
    import fs_data as FD
    import safe
    print("토크 언랩 전수 감사 — 원본(hip/knee.xlsx)이 정답, 확장판(*2·*3)을 대조한다")
    print()
    print(f"  판정 ① 원본과 {TOL:.0f} N·m 넘게 다른 점  (원본이 있는 구간만)")
    print(f"  판정 ② 이웃한 두 점이 {JLO:.0f}~{JHI:.0f} N·m 뛰는 곳 = 언랩 서명 (참고용)")
    print()
    print(f"  {'세션/trial':32s} {'판':3s} {'채널':4s} {'대조점':>6s} {'다름':>5s} {'창안':>5s} "
          f"{'어긋난크기':>10s} {'36배수':>7s} {'점프':>5s}")
    print("  " + "-" * 96)
    R = {}
    tot = collections.Counter()
    # ★ 08-12 감사 중에는 교정을 끈다 — 교정된 값을 감사하면 항상 "이상 없음"이 나온다.
    os.environ["FS_NO_UNWRAP_FIX"] = "1"
    for s, p, g, cvt, ho in FD.registry():
        for tagn, loader in (("*2", FD.load2), ("*3", FD.load3)):
            try:
                d = loader(p)
                if d is None:
                    continue
                pw = FD.plot_window(p, d) if tagn == "*2" else None
                for ch, orig, col in (("힙", p / "hip.xlsx", "raw1"),
                                      ("무릎", p / "knee.xlsx", "raw2")):
                    a = audit_pair(d["t"], np.asarray(d[col]), orig, d["t_abs"][0], pw)
                    R[f"{s}/{p.name}/{tagn}/{ch}"] = a
                    tot["ov"] += a["n_ov"]; tot["diff"] += a["n_diff"]
                    tot["win"] += a["n_win"]; tot["jump"] += a["n_jump"]
                    tot["exact"] += a["exact"]
                    if a["n_diff"] or a["n_jump"]:
                        mk = "  <<< 채점 창 안" if a["n_win"] else ""
                        kk = f"{a['k']:+7.2f}" if np.isfinite(a["k"]) else "      -"
                        md = f"{a['med']:+10.2f}" if np.isfinite(a["med"]) else "         -"
                        print(f"  {s + '/' + p.name:32s} {tagn:3s} {ch:4s} {a['n_ov']:6d} "
                              f"{a['n_diff']:5d} {a['n_win']:5d} {md} {kk} {a['n_jump']:5d}{mk}")
            except Exception as ex:
                print(f"  {s}/{p.name} {tagn}: ERR {type(ex).__name__} {ex}")
    os.environ.pop("FS_NO_UNWRAP_FIX", None)
    print("  " + "-" * 96)
    print(f"  합계 — 원본과 대조한 점 {tot['ov']} · **다른 점 {tot['diff']}** "
          f"(그중 채점 창 안 {tot['win']}) · 그중 36 의 정확한 배수 {tot['exact']}")
    print(f"        인접 점프 서명 {tot['jump']} 곳 (참고 — 진짜 급변도 섞인다)")
    print()
    if tot["diff"]:
        print("  ⇒ 원본이 정답이므로, 데이터를 읽는 코드가 **원본이 있는 구간은 원본 값으로**")
        print("     덮어쓴다 (fs_data._fix_unwrap). 원본 파일은 규약대로 건드리지 않는다.")
        print("     ※ 이 감사는 교정을 끄고 돌린 결과다 (교정본을 감사하면 늘 '이상 없음'이 된다).")
    else:
        print("  ⇒ 확장판과 원본이 겹치는 구간에서 완전히 일치한다.")
    safe.atomic_json_write(OUT, R)
    print(f"\n저장 -> {OUT}")


if __name__ == "__main__":
    main()
