# -*- coding: utf-8 -*-
"""_G66_taufair — **CL τ 열세에서 '기준선 편향'과 '진짜 오차'를 분리** (마라톤G, 08-08).

문제
  통일 보드의 CL τ 채점은 `sim 인가 토크[Nm]` vs `d["a1"]/d["a2"]` 인데,
  `fs_data.py:115` 에서 **`a1 = ahat_np(raw1, v1)`** — **기준선 자체가 a_hat 변환값**이다.
  ⇒ 다른 토크맵(canon_cap)을 쓰는 스택은 **구조적으로 불리**하다 (G53 에서 ModeA 판으로 확인).
  TK 표 통일 후에도 CL τ1 +48.6% · τ2 +40.3% 가 남아 승격의 마지막 관문이 되어 있다.

해법 — 세 가지 자로 동시에 잰다
  ① **Nm 대 a_hat 기준선** (현행 보드 방식) — 편향 포함
  ② **명령 대 명령** (`Lg["c1"]` vs `d["raw1"]`) — **맵 무관**. PD 가 만든 명령이
     실로봇이 실제로 보낸 명령과 같은가? **이것이 τ-fidelity 의 정의 그 자체.**
  ③ **Nm 대 각 모델 자기 맵으로 변환한 실측** — 맵을 공정하게 맞춘 판

  ①과 ②의 차이가 '기준선 편향분', ②가 '진짜 τ-fidelity'.

CLI:  <스택 env> python _G66_taufair.py <tag>
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

QS = 2                                   # qd 스큐 보정 [샘플] (4ms@500Hz) — uboard 와 동일


def sh(x, n=QS):
    y = np.empty_like(np.asarray(x, float)); y[n:] = np.asarray(x, float)[:-n]; y[:n] = x[0]
    return y


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "x"
    ft = FR.fs_twin(); P = ft["P"]; A = P.A_PAPER
    tm = FR._tmap_init(P, A)             # None 이면 a_hat 경로
    use_tk = os.environ.get("FS_TKMODE") == "table"
    OUT = {}
    print("=" * 108)
    print(f"[{tag}]  토크맵 = {'a_hat (맵 없음)' if tm is None else os.environ.get('FS_TMAP')}"
          f" · α = {'TK 표' if use_tk else os.environ.get('FS_TKOVR', '1.0')}")
    print(f"{'세션':<12}{'①Nm vs a_hat':>16}{'②명령 vs 명령':>16}{'③Nm vs 자기맵':>16}"
          f"{'  (τ1 / τ2)':<10}")
    for s, p, g, cvt, ho in FD.registry():
        if s in FD.FF_SESS or not g:
            continue
        try:
            d = FD.load2(p); pw = FD.plot_window(p, d)
            if pw is None:
                continue
            t = d["t"]; m = (t >= pw[0]) & (t <= pw[1])
            if m.sum() < 30:
                continue
            i0 = int(np.argmax(m)); tg = t[m] - t[i0]
            sp = FR.sess_params(s)
            al = FR.alpha_of(g[2]) if use_tk else float(os.environ.get("FS_TKOVR", "1.0"))
            kd = 0.20 if use_tk else float(os.environ.get("FS_KDSC", "1.0"))
            gcl = (g[0], g[1], g[2] * al, g[3] * kd)
            init = tuple(float(d[k][i0]) for k in ("q1", "q2", "dq1", "dq2", "raw1", "raw2"))
            L = FR.rollout_cl_fs(ft, tg, sh(d["qd1"][m]), sh(d["qd2"][m]),
                                 sh(d["dqd1"][m]), sh(d["dqd2"][m]), gcl, float(tg[-1]),
                                 two_stage=True, bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                                 fade=True, taulim=None,
                                 vdes_ff=FD.vdes_applied(s), init_meas=init)
            if L is None:
                continue
            gi = lambda k: np.interp(tg, L["t"], L[k])
            row = {}
            for ch, ck, sk, rk, ak in ((1, "c1", "s1", "raw1", "a1"), (2, "c2", "s2", "raw2", "a2")):
                sim_nm = gi(sk); sim_cmd = gi(ck)
                meas_cmd = np.asarray(d[rk][m], float)
                meas_ahat = np.asarray(d[ak][m], float)
                v = np.asarray(d["dq1" if ch == 1 else "dq2"][m], float)
                vs = np.where(np.abs(v) > 1e-6, v, 1.0)
                # ③ 실측 명령을 **이 스택 자기 맵**으로 변환
                if tm is None:
                    meas_own = meas_ahat
                else:
                    meas_own = np.array([tm(float(x), float(w), 0 if ch == 1 else 1)
                                         for x, w in zip(meas_cmd, vs)])
                f = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
                row[f"t{ch}_a"] = f(sim_nm, meas_ahat)      # ①
                row[f"t{ch}_c"] = f(sim_cmd, meas_cmd)      # ②
                row[f"t{ch}_o"] = f(sim_nm, meas_own)       # ③
            OUT.setdefault(s, []).append(row)
        except Exception as ex:
            print(f"  {s}/{p.name}: ERR {type(ex).__name__} {str(ex)[:40]}", flush=True)
    K = ("t1_a", "t2_a", "t1_c", "t2_c", "t1_o", "t2_o")
    AGG = {}
    for s in sorted(OUT):
        a = {k: float(np.mean([r[k] for r in OUT[s]])) for k in K}
        AGG[s] = a
        print(f"{s:<12}{a['t1_a']:7.2f}/{a['t2_a']:<8.2f}{a['t1_c']:7.2f}/{a['t2_c']:<8.2f}"
              f"{a['t1_o']:7.2f}/{a['t2_o']:<8.2f}")
    tot = {k: float(np.mean([AGG[s][k] for s in AGG])) for k in K}
    print(f"{'평균':<12}{tot['t1_a']:7.2f}/{tot['t2_a']:<8.2f}{tot['t1_c']:7.2f}/{tot['t2_c']:<8.2f}"
          f"{tot['t1_o']:7.2f}/{tot['t2_o']:<8.2f}")
    json.dump(dict(per=AGG, tot=tot), io.open(HERE / f"_G66_taufair_{tag}.json", "w",
              encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n저장: _G66_taufair_{tag}.json")


if __name__ == "__main__":
    main()
