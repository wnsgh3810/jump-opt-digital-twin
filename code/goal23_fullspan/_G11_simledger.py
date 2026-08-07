# -*- coding: utf-8 -*-
"""_G11_simledger — "a_hat + 15Nm 포화인데 왜 sim 이 0.88m 나오나" (사용자 질문 08-07).

답의 소재: ModeA 재생의 주입 토크는 **측정 a_hat 이 전부가 아니다**.
  `fs_runner.rollout_ol_fs_b` → `md.ctrl[:] = [-(s1 + hip_supp), -(s2 + supp)]`
  s1,s2 = 측정 raw → 클립(35.5) → a_hat  ·  **supp / hip_supp = 인공 지지층 (추가 주입)**
`FS_ELEDGER=1` 이 층별 순간 파워를 남기므로, 푸시 창에서 적분하면 **층별 에너지 기여**가 나온다.
CLI: python _G11_simledger.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
os.environ["FS_ELEDGER"] = "1"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                                          # noqa: E402
import fs_runner as FR                                        # noqa: E402
from _G10_energy import real_h, G, M_REAL                     # noqa: E402

KEYS = ("motor1", "motor2", "supp2", "hsupp1", "spr_tql", "kdeep2", "bias_h")


def main():
    ft = FR.fs_twin(); SP = FR._sess_params()
    print("=" * 132)
    print("ModeA 재생의 **층별 에너지 기여** [J] — 푸시 창(딥 바닥→sim 최고점 직전) 적분")
    print("  motor1/2 = 측정 a_hat 주입 · supp2/hsupp1 = **인공 지지층** · spr_tql = 무릎스프링/CVT · kdeep2 = 깊은굽힘 보정")
    print(f"{'세션':<11}{'trial':<19}{'h_sim':>7}{'h_실측':>7}{'배율':>6}"
          f"{'motor1':>8}{'motor2':>8}{'supp2':>8}{'hsupp1':>8}{'spr':>7}{'kdeep':>7}{'bias':>7}"
          f"{'합계':>7}{'인공층%':>8}")
    R = []
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        hr = real_h(p)
        if hr is None:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d); pw = FD.plot_window(p, d)
            if pw is None:
                continue
            tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1])
            i0 = int(np.argmax(m))
            t_end = min(tt[m][-1] + 0.6, tt[-1])
            m2 = (tt >= tt[i0]) & (tt <= t_end)
            t = tt[m2] - tt[i0]
            sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
            L = FR.rollout_ol_fs_b(ft, t, d["raw1"][m2], d["raw2"][m2],
                                   float(d["q1"][i0]), float(d["q2"][i0]),
                                   float(d["dq1"][i0]), float(d["dq2"][i0]),
                                   float(t[-1] - 0.004), bias1=sp["bias1"],
                                   knee_deep=sp["knee_deep"], fade=True)
            if L is None or "eledger" not in L:
                continue
            bz = np.asarray(L["bz"], float); hs = float(bz.max())
            dt = float(np.median(np.diff(t)))
            k1 = int(np.argmax(bz))                      # sim 최고점
            k0 = int(np.argmin(bz[:k1])) if k1 > 5 else 0   # 그 직전 최저(딥 바닥)
            E = {}
            for kk in KEYS:
                v = np.asarray(L["eledger"][kk], float)[:len(bz)]
                E[kk] = float(np.trapezoid(v[k0:k1 + 1], dx=dt))
            tot = sum(E.values())
            art = E["supp2"] + E["hsupp1"]
            R.append(dict(s=s, name=p.name, hs=hs, hr=hr, E=E, tot=tot, art=art))
            print(f"{s:<11}{p.name[:18]:<19}{hs:7.3f}{hr:7.3f}{hs/hr:6.3f}"
                  f"{E['motor1']:8.2f}{E['motor2']:8.2f}{E['supp2']:8.2f}{E['hsupp1']:8.2f}"
                  f"{E['spr_tql']:7.2f}{E['kdeep2']:7.2f}{E['bias_h']:7.2f}{tot:7.2f}"
                  f"{100*art/max(tot,1e-9):8.1f}")
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__} {ex}")
    if not R:
        return
    a = lambda k: np.array([r["E"][k] for r in R])
    f = lambda x: f"{np.median(x):7.2f} [{np.percentile(x,10):6.2f}, {np.percentile(x,90):6.2f}]"
    print("\n" + "=" * 132)
    print("층별 중앙값 [J] (10~90%)")
    for k in KEYS:
        print(f"   {k:<10}{f(a(k))}")
    tot = np.array([r["tot"] for r in R]); art = np.array([r["art"] for r in R])
    mot = a("motor1") + a("motor2")
    print(f"   {'모터 계':<10}{f(mot)}")
    print(f"   {'인공층 계':<10}{f(art)}   ← supp2 + hsupp1")
    print(f"   {'총 주입':<10}{f(tot)}")
    print(f"\n   ★ 인공층이 총 주입의 {100*np.median(art/tot):.1f}% 를 담당")
    print(f"   ★ 인공층 없으면 주입 에너지 {np.median(mot):.2f} J "
          f"→ 있으면 {np.median(mot+art):.2f} J (×{np.median((mot+art)/mot):.2f})")
    hs = np.array([r["hs"] for r in R]); hr = np.array([r["hr"] for r in R])
    print(f"   sim/실측 높이 배율 {np.median(hs/hr):.3f} [{np.percentile(hs/hr,10):.3f}, "
          f"{np.percentile(hs/hr,90):.3f}]  (sim 중앙 {np.median(hs):.3f} m)")
    json.dump([{k: r[k] for k in ("s", "name", "hs", "hr", "tot", "art")} | r["E"] for r in R],
              io.open(HERE / "_G11_simledger.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장: _G11_simledger.json")


if __name__ == "__main__":
    main()
