# -*- coding: utf-8 -*-
"""_G11_ablate — "a_hat + 포화인데 왜 sim 이 0.88m 나오나" (사용자 질문 08-07).

소재: ModeA 재생의 주입 토크는 **측정 a_hat 이 전부가 아니다**.
  `fs_runner.rollout_ol_fs_b` → `md.ctrl[:] = [-(s1 + hip_supp), -(s2 + supp)]`
    s1,s2 = 측정 raw → 클립(35.5) → a_hat
    **supp  = RU.supp_scalar(s2, dq2, law) (+ rise_term)** = 무릎 인공 지지층
    **hip_supp = RU.hip_supp_scalar(s1, s2, dq1)**         = 힙 인공 지지층
  둘 다 **명령 비례 형태**(부하 대리 |s2|)라 토크가 클수록 더 얹힌다.

측정: ①층별 주입 에너지(푸시 창 적분) ②**인공층 OFF 절제(ablation)** 시 점프높이 붕괴량.
CLI: python _G11_ablate.py
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
RU = FR.RU
from _G10_energy import real_h, G, M_REAL                     # noqa: E402


def run(ft, SP, s, p, d):
    pw = FD.plot_window(p, d)
    if pw is None:
        return None
    tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1]); i0 = int(np.argmax(m))
    t_end = min(tt[m][-1] + 0.6, tt[-1]); m2 = (tt >= tt[i0]) & (tt <= t_end)
    t = tt[m2] - tt[i0]
    sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
    return FR.rollout_ol_fs_b(ft, t, d["raw1"][m2], d["raw2"][m2],
                              float(d["q1"][i0]), float(d["q2"][i0]),
                              float(d["dq1"][i0]), float(d["dq2"][i0]),
                              float(t[-1] - 0.004), bias1=sp["bias1"],
                              knee_deep=sp["knee_deep"], fade=True), t


def main():
    ft = FR.fs_twin(); SP = FR._sess_params()
    law_a, law_b, law_v0 = ft["law"]; kr = ft["kr"]
    HIP = dict(RU.HIP)
    print("=" * 126)
    print(f"⓪ 인공 지지층 파라미터 (p24 후보)")
    print(f"   무릎 supp:  a={law_a:.4f} Nm(상수) · b={law_b} (부하비례) · v0={law_v0} · rise k={kr}")
    print(f"   힙  hsupp:  a1={HIP['a1']:.4f} · b1={HIP['b1']} · v01={HIP['v01']} · k1={HIP['k1']}"
          f" · src={HIP['src']} · cap={HIP['cap']}")

    print("\n" + "=" * 126)
    print("① 층별 주입 에너지 [J] (푸시 창 = sim 최저→최고) 와 ② 인공층 OFF 절제")
    print(f"{'세션':<11}{'trial':<19}{'h_실측':>7}{'h_sim':>7}{'배율':>6}"
          f"{'W_a_hat':>9}{'W_supp':>8}{'W_hsupp':>8}{'인공%':>7}"
          f" | {'h_OFF':>7}{'배율':>6}{'Δh[cm]':>8}")
    R = []
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        hr = real_h(p)
        if hr is None:
            continue
        try:
            d = FD.load2(p)
            out = run(ft, SP, s, p, d)
            if out is None or out[0] is None:
                continue
            L, t = out
            bz = np.asarray(L["bz"], float); hs = float(bz.max())
            # ★ L 은 입력 t(2ms)가 아니라 **내부 스텝(0.5ms) 격자**에 기록된다 (len 1656 vs 415).
            #   median(diff(t)) 를 쓰면 창과 dt 가 동시에 어긋나 일 적분이 무의미해진다 (08-07 자체발견).
            dt = (t[-1] - t[0]) / (len(bz) - 1)
            vb = np.gradient(bz, dt); ab = np.gradient(vb, dt)
            k1 = int(np.argmax(bz)); k0 = int(np.argmin(bz[:k1])) if k1 > 5 else 0
            _c = [k for k in range(k0, k1) if ab[k] < -8.0]
            k1 = _c[0] if _c else k1                    # 일 적분은 **이지까지만** (비행 중 주입 제외)
            s1 = np.asarray(L["s1"], float); s2 = np.asarray(L["s2"], float)
            v1 = np.asarray(L["dq1"], float); v2 = np.asarray(L["dq2"], float)
            sp_ = np.array([RU.supp_scalar(s2[i], v2[i], law_a, law_b, law_v0)
                            + (float(RU.rise_term(v2[i], kr, law_v0)) if kr else 0.0)
                            for i in range(k0, k1 + 1)])
            hp_ = np.array([RU.hip_supp_scalar(s1[i], s2[i], v1[i]) for i in range(k0, k1 + 1)])
            sl = slice(k0, k1 + 1)
            Wm = float(np.trapezoid(s1[sl] * v1[sl] + s2[sl] * v2[sl], dx=dt))
            Ws = float(np.trapezoid(sp_ * v2[sl], dx=dt))
            Wh = float(np.trapezoid(hp_ * v1[sl], dx=dt))
            # ── 절제: 인공층 전부 0 ──
            ft2 = dict(ft); ft2["law"] = (0.0, 0.0, law_v0); ft2["kr"] = 0.0
            for k_ in ("a1", "b1", "k1"):
                RU.HIP[k_] = 0.0
            out2 = run(ft2, SP, s, p, d)
            for k_ in ("a1", "b1", "k1"):
                RU.HIP[k_] = HIP[k_]
            h2 = float(np.asarray(out2[0]["bz"], float).max()) if out2 and out2[0] else np.nan
            art = 100 * (Ws + Wh) / max(Wm + Ws + Wh, 1e-9)
            R.append((hr, hs, h2, Wm, Ws, Wh, art))
            print(f"{s:<11}{p.name[:18]:<19}{hr:7.3f}{hs:7.3f}{hs/hr:6.3f}"
                  f"{Wm:9.2f}{Ws:8.2f}{Wh:8.2f}{art:7.1f}"
                  f" | {h2:7.3f}{h2/hr:6.3f}{(h2-hs)*100:8.1f}")
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__} {ex}")
    a = np.array(R)
    f = lambda x: f"{np.median(x):.3f} [{np.percentile(x,10):.3f}, {np.percentile(x,90):.3f}]"
    print("\n" + "=" * 126)
    print(f"  h_sim / 실측  (현행)        {f(a[:,1]/a[:,0])}")
    print(f"  h_sim / 실측  (인공층 OFF)  {f(a[:,2]/a[:,0])}")
    print(f"  인공층 제거 시 높이 변화    {np.median(a[:,2]-a[:,1])*100:+.1f} cm "
          f"[{np.percentile(a[:,2]-a[:,1],10)*100:+.1f}, {np.percentile(a[:,2]-a[:,1],90)*100:+.1f}]")
    print(f"  W(a_hat 주입) [J]           {f(a[:,3])}")
    print(f"  W(무릎 supp) [J]            {f(a[:,4])}")
    print(f"  W(힙 hsupp) [J]             {f(a[:,5])}")
    print(f"  ★ 인공층 몫                 {np.median(a[:,6]):.1f}% "
          f"[{np.percentile(a[:,6],10):.1f}, {np.percentile(a[:,6],90):.1f}]")
    json.dump(dict(hr=list(a[:, 0]), hs=list(a[:, 1]), hoff=list(a[:, 2]),
                   Wm=list(a[:, 3]), Ws=list(a[:, 4]), Wh=list(a[:, 5])),
              io.open(HERE / "_G11_ablate.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장: _G11_ablate.json")


if __name__ == "__main__":
    main()
