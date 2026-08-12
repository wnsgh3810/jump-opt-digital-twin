# -*- coding: utf-8 -*-
"""_GHL_taumeter — 토크를 **최종 목적에 맞는 자**로 다시 잰다 (08-12).

왜
  이 연구의 합격 기준은 "최적화 궤적으로 실로봇을 PD 제어했을 때 **측정 토크 ≈ 계획 토크**" 다.
  직전 마라톤(G66)이 자를 셋 비교하고 **"명령 대 명령이 옳다"** 고 판정했다:

  | 자 | 무엇을 비교하나 | 문제 |
  |---|---|---|
  | ① 옛 변환식으로 바꾼 실측 vs 시뮬 토크 | — | **약한 변환식을 쓰는 모델을 구조적으로 우대**한다 |
  | ② **명령 대 명령** | 트윈의 PD 가 만든 명령 vs 실로봇이 보낸 명령 | 변환식과 **무관** ← 옳은 자 |
  | ③ 각자 자기 변환식으로 | — | 변환식의 국소 이득만큼 오차가 눌린다 |

  **그런데 현행 채점판은 ③ 을 쓴다.** 판정된 지 나흘이 지났는데 반영이 안 됐다.
  ②가 옳은 이유: "트윈의 PD 가 실로봇과 **같은 명령**을 만드는가" 가 곧 합격 기준이다.

무엇을 하나
  두 자로 **동시에** 재서 나란히 놓는다. ③ 을 없애지 않는다 — 두 자가 다른 답을 주면
  그 자체가 정보이고, 승격 기준을 바꾸는 것은 별도 결정 사항이다.

CLI: python _GHL_taumeter.py
"""
import os, sys, collections
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GHL_taumeter.json"

STACK = dict(FS_TMAP="canon_cap", FS_TDCAP="3.733,2.309", FS_MASS="3.2988",
             FS_FOOTR="0.020", FS_NOSUPP="1", FS_NOSPR="1", FS_NOBIAS="1",
             FS_NODEEP="1", FS_PRESLIDE="0.86,0.85,0.02,1.0",
             FS_CMD_LPF="0.00317,0.00292", FS_IMPRATIO="20",
             FS_KNEEM_FL="0.2880", FS_KNEEM_DAMP="0.1617", FS_HIPM_FL="0.3026",
             FS_HIPM_DAMP="0.0964", FS_KS_HIP="138.53", FS_COMZ="thigh=-0.00189")
for _k, _v in STACK.items():
    os.environ.setdefault(_k, _v)


def main():
    import safe
    import fs_data as FD, fs_compare_plot as CP, fs_runner as FR
    import fs_cvt as FC
    ft0 = FR.fs_twin()
    R = collections.defaultdict(lambda: collections.defaultdict(list))
    for s, p, g, cvt, ho in FD.registry():
        if not g:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d); pw = FD.plot_window(p, d)
            if pw is None:
                continue
            tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1])
            if m.sum() < 30:
                continue
            i0 = int(np.argmax(m)); t = tt[m] - tt[i0]
            init = (float(d["q1"][i0]), float(d["q2"][i0]), float(d["dq1"][i0]),
                    float(d["dq2"][i0]), float(d["raw1"][i0]), float(d["raw2"][i0]))
            qd = (CP.sh(d["qd1"][m]), CP.sh(d["qd2"][m]),
                  CP.sh(d["dqd1"][m]), CP.sh(d["dqd2"][m]))
            ft = FC.cvt_ft(d["l_i"], ft_base=ft0) if cvt else ft0
            sp = CP.sess_params(s)
            L = FR.rollout_cl_fs(ft, t, *qd, tuple(g), float(t[-1]), two_stage=True,
                                 bias1=sp["bias1"], knee_deep=sp["knee_deep"], fade=True,
                                 taulim=None, vdes_ff=(s != "26.04.21"), init_meas=init)
            if L is None:
                continue
            gi = lambda k: np.interp(t, L["t"], L[k])
            # ② 명령 대 명령 — 트윈의 PD 가 만든 명령(맵 통과 전) vs 실로봇이 보낸 명령
            for i, (ck, rk) in enumerate((("c1", "raw1"), ("c2", "raw2"))):
                real = np.asarray(d[rk])[m]; sim = gi(ck)
                R[s][f"cmd{i+1}"].append(float(np.sqrt(np.mean((real - sim) ** 2))))
                R[s][f"cmdband{i+1}"].append(float(np.std(real)))
            # ③ 각자 자기 변환식으로 (현행 채점판이 쓰는 자)
            for i, (sk, rk, dk, ch) in enumerate((("s1f", "raw1", "dq1", 0),
                                                  ("s2", "raw2", "dq2", 1))):
                ref = CP.tau_ref(np.asarray(d[rk])[m], np.asarray(d[dk])[m], ch, old=False)
                sim = gi(sk)
                if sk == "s1f":
                    sim = np.clip(sim, -20.5, 20.5)
                R[s][f"nm{i+1}"].append(float(np.sqrt(np.mean((np.asarray(ref) - sim) ** 2))))
                R[s][f"nmband{i+1}"].append(float(np.std(np.asarray(ref))))
        except Exception:
            continue
    print("토크를 두 자로 나란히 잰다 (폐루프, 점프 창)\n")
    print("  ② 명령 대 명령 = 트윈의 PD 가 만든 명령 vs 실로봇이 보낸 명령 (변환식 무관)")
    print("     → **이 연구의 합격 기준에 가장 가까운 자** (직전 마라톤 판정)")
    print("  ③ 각자 자기 변환식 = 현행 채점판이 쓰는 자\n")
    print(f"  {'세션':11s} | {'힙 ② 명령':>16s} {'힙 ③ 현행':>16s} | "
          f"{'무릎 ② 명령':>17s} {'무릎 ③ 현행':>17s}")
    print("  " + "-" * 78)
    acc = collections.defaultdict(list)
    for s in sorted(R):
        r = R[s]
        cells = []
        for i in (1, 2):
            for tag in ("cmd", "nm"):
                v = np.mean(r[f"{tag}{i}"]); b = np.mean(r[f"{tag}band{i}"])
                cells.append(f"{v:6.2f}({100*v/b:4.0f}%)")
                acc[f"{tag}{i}"].append(100 * v / b)
        print(f"  {s:11s} | {cells[0]:>16s} {cells[1]:>16s} | "
              f"{cells[2]:>17s} {cells[3]:>17s}")
    print("  " + "-" * 78)
    print(f"  {'평균':11s} | " + " ".join(
        f"{np.mean(acc[k]):15.0f}%" for k in ("cmd1", "nm1", "cmd2", "nm2")))
    print("\n  ※ 괄호 = 그 신호가 실제로 움직인 폭 대비 몇 % (0% 가 완벽). 단위는 N·m.")
    print("     두 자가 다른 답을 주면, 지금 승격 판정이 최종 목적과 어긋나 있다는 뜻이다.")
    safe.atomic_json_write(OUT, {s: {k: list(map(float, v)) for k, v in r.items()}
                                 for s, r in R.items()})
    print(f"\n저장 → {OUT}")


if __name__ == "__main__":
    main()
