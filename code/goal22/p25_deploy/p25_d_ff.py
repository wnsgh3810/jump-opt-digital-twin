# -*- coding: utf-8 -*-
"""P25-D 확장 2 — FF+PD 배포 (실기 FF 세션 구조의 재현): tdes = τ*_raw 직접 주입 + PD 보조.

실기(0422/0319tau/0324)가 실제로 쓰는 배포 채널: desiredTorque(FF) + PD.
cl_run23의 ffk/ff_hip 경로 그대로 (tdes는 raw-도메인 — 명령 합산 후 클립 ±35.5 → a_hat).
기대: 개루프 계획(NLP 포함)도 τ-fidelity 배포 가능 (성형이 실패한 천장 라이딩 계획의 구제).
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("P23_SPRING_GATED", "1")
os.environ.setdefault("P23_RISE_GATED", "1")
os.environ.setdefault("P24_HIP_LAW", "1")
os.environ.setdefault("P24_REFIT", "1")

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p23_veins"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import safe
import p25_d_deploy as D
import p23_v6_runners as RU


def deploy_ff(npz_path, gains_key):
    D.setup()
    g4 = D.GAINS[gains_key]
    plan = D.load_plan(npz_path)
    z = np.load(npz_path, allow_pickle=True)
    # τ*_raw: pair 또는 matrix 스키마
    if "raw1" in z.files:
        r1, r2 = np.asarray(z["raw1"], float), np.asarray(z["raw2"], float)
        t_src = np.asarray(z["t"], float)
    else:
        a = np.asarray(z["tau_cmd_raw"], float)
        a = a if a.ndim == 2 and a.shape[1] == 2 else a.T
        r1, r2 = a[:, 0], a[:, 1]
        t_src = np.asarray(z["t"], float)
    m = t_src >= 0
    t0 = t_src[m] - t_src[m][0]
    # 계획 시간축(load_plan 크롭)에 맞춰 보간
    t = plan["t"]
    tdes1 = np.interp(t, t0, r1[m])
    tdes2 = np.interp(t, t0, r2[m])
    d = dict(t=t, qd1=plan["qd"][:, 0], qd2=plan["qd"][:, 1],
             dqd1=plan["dqd"][:, 0], dqd2=plan["dqd"][:, 1],
             tdes1=tdes1, tdes2=tdes2)
    L = RU.cl_run23_log(D.model_flip(), False, 0.030, d, g4, True, True,
                        D.G["A"], D.G["TM"], [1, 1, 1, 1], D.G["LAW"], c_cvt=0.0,
                        o1=0.0, o2=0.0, ff_hip=True, spr=D.G["SPR"],
                        k_rise=D.G["KR"])
    if L is None:
        return dict(crash=True, plan=str(npz_path), gains=gains_key)
    out = D.metrics_of(L, plan)
    out.update(plan=Path(npz_path).name, gains=gains_key, mode="FF+PD")
    return out


def main():
    T18 = bool(os.environ.get("P25_T18"))
    suf = "_t18" if T18 else ""
    plans = [p for p in sorted(set(HERE.glob("p25_[abc]_*.npz")) | set(HERE.glob("p25_a4_*.npz")))
             if all(s not in p.name for s in ("shaped", "plan", "golden", "fixedpoint"))
             and p.stem.endswith("_t18") == T18]
    rows = {}
    print(f"{'계획(FF+PD)':28s} {'게인':5s} {'h_plan':>7s} {'h_PD':>7s} {'F_τ':>7s} {'hip':>7s} {'knee':>7s}")
    for src in plans:
        for gname in D.GAINS:
            r = deploy_ff(src, gname)
            if r.get("crash"):
                print(f"{src.stem:28s} {gname:5s}  CRASH", flush=True)
                continue
            rows[f"{src.name}|{gname}"] = {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                                           for k, v in r.items() if not isinstance(v, (list, np.ndarray))}
            print(f"{src.stem:28s} {gname:5s} {r.get('h_plan', float('nan')):7.3f} "
                  f"{r['h_PD']:7.3f} {100*r['F_tau']:6.1f}% {100*r['F_tau_hip']:6.1f}% "
                  f"{100*r['F_tau_knee']:6.1f}%", flush=True)
    safe.atomic_json_write(HERE / f"p25_d_ff_results{suf}.json", rows)
    print(f"saved p25_d_ff_results{suf}.json", flush=True)


if __name__ == "__main__":
    main()
