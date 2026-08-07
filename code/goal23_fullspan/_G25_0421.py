# -*- coding: utf-8 -*-
"""_G25_0421 — **0421 q2 게이트 단독 진단** (마라톤G 최대 단일 병목, 08-08).

배경: G17~G24 의 전 구성에서 게이트 실패의 대부분이 `26.04.21/q2` 하나다.
      이 게이트만 없으면 J_G 가 0.94 → 0.79 대로 내려간다 (−5%p 이상).

핵심 의문: ModeA 는 **측정 토크를 그대로 주입**한다. 제어 모드(위치제어 vs 토크제어)는
  주입값에 영향이 없어야 하는데, 왜 위치제어 세션인 0421 만 유독 민감한가?

진단 축
  A. 0421 의 raw2 분포가 다른 세션과 다른가 (토크맵 민감 구간이 다른가)
  B. q2 오차가 **어느 국면**(하강/유지/푸시)에서 나오는가 → 저raw 문제인가 고raw 문제인가
  C. 0421 의 자세(스쿼트 깊이·무릎각)가 특이한가
CLI: python _G25_0421.py
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

PH = (("desc", "i_desc", "i_bot"), ("prehold", "i_bot", "i_push"), ("push", "i_push", "i_lo"))


def main():
    ft = FR.fs_twin(); SP = FR._sess_params()
    print("=" * 116)
    print("Ⓐ raw2(무릎 명령) 분포 — 세션별. 토크맵의 어느 구간을 쓰는가")
    print(f"{'세션':<12}{'n':>3}{'raw2 중앙':>10}{'p90':>8}{'최대':>8}"
          f"{'|raw2|<5 비율':>13}{'5~11.5':>9}{'>11.5':>8}{'스쿼트깊이[mm]':>14}")
    from _G10_energy import Reduced
    R = Reduced(ft)
    for s in sorted({x[0] for x in FD.registry()}):
        A, dep = [], []
        for ss, p, g, cvt, ho in FD.registry():
            if ss != s or cvt:
                continue
            try:
                d = FD.load2(p); seg = FD.segment(d)
            except Exception:
                continue
            m = seg["score"]
            A.append(np.abs(d["raw2"][m]))
            dep.append(R.MV(d["q1"][seg["i_bot"]], d["q2"][seg["i_bot"]])["zb"] * 1000)
        if not A:
            continue
        a = np.concatenate(A)
        print(f"{s:<12}{len(A):3d}{np.median(a):10.2f}{np.percentile(a,90):8.2f}{a.max():8.2f}"
              f"{100*(a<5).mean():13.1f}{100*((a>=5)&(a<11.5)).mean():9.1f}"
              f"{100*(a>=11.5).mean():8.1f}{np.mean(dep):14.1f}"
              + ("   ← 게이트 세션" if s in ("26.04.21", "26.03.24") else ""))

    print("\n" + "=" * 116)
    print("Ⓑ q2 오차의 국면별 분해 — p24 기준선에서 (어디서 오차가 나는가)")
    print(f"{'세션':<12}{'trial':<20}{'desc':>9}{'prehold':>9}{'push':>9}{'전체':>9}{'최대국면':>10}")
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt or s not in ("26.04.21", "26.03.24", "26.07.27", "26.06.02"):
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d); pw = FD.plot_window(p, d)
            if pw is None:
                continue
            tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1]); i0 = int(np.argmax(m))
            t = tt[m] - tt[i0]
            sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
            L = FR.rollout_ol_fs_b(ft, t, d["raw1"][m], d["raw2"][m],
                                   float(d["q1"][i0]), float(d["q2"][i0]),
                                   float(d["dq1"][i0]), float(d["dq2"][i0]),
                                   float(t[-1] - 0.004), bias1=sp["bias1"],
                                   knee_deep=sp["knee_deep"], fade=True)
            if L is None:
                continue
            q2s = np.interp(t, L["t"], L["q2"])
            err = np.degrees(q2s - d["q2"][m])
            idx = np.flatnonzero(m)
            row = {}
            for lab, a_, b_ in PH:
                sel = (idx >= seg[a_]) & (idx < seg[b_])
                row[lab] = float(np.sqrt(np.mean(err[sel] ** 2))) if sel.sum() > 3 else np.nan
            row["all"] = float(np.sqrt(np.mean(err ** 2)))
            top = max((v, k) for k, v in row.items() if k != "all" and v == v)[1]
            OUT[f"{s}/{p.name}"] = row
            print(f"{s:<12}{p.name[:19]:<20}{row['desc']:9.3f}{row['prehold']:9.3f}"
                  f"{row['push']:9.3f}{row['all']:9.3f}{top:>10}")
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__} {ex}")
    for s in ("26.04.21", "26.03.24", "26.07.27", "26.06.02"):
        sub = [v for k, v in OUT.items() if k.startswith(s)]
        if not sub:
            continue
        print(f"   {s} 평균: desc {np.nanmean([x['desc'] for x in sub]):.3f} · "
              f"prehold {np.nanmean([x['prehold'] for x in sub]):.3f} · "
              f"push {np.nanmean([x['push'] for x in sub]):.3f}")
    json.dump(OUT, io.open(HERE / "_G25_0421.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: _G25_0421.json")


if __name__ == "__main__":
    main()
