# -*- coding: utf-8 -*-
"""P25-D 확장 — 기준 성형(reference shaping) 배포: q_des = q_plan + raw*/kp.

개루프 계획(NLP/토크 CMA)을 PD로 배포하면 F_τ ~100% (계획 토크와 무관한 토크가 나옴).
처방: PD 법칙 τ_raw = kp(q_des−q)+kd(dq_des−dq)에서, 로봇이 계획 상태를 따를 때
정확히 raw*가 나오도록 기준각을 성형: q_des = q_plan + raw*/kp, dq_des = dq_plan.
(1차 근사 — 피드포워드를 기준각에 인코딩. G20 배포 CSV 사상의 정식화.)
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

GAINS = D.GAINS                     # env P25_GAINS_FULL=1 → 8종
T18 = bool(os.environ.get("P25_T18"))
SUF = "_t18" if T18 else ""


def shape_npz(src, kp1, kp2):
    """계획 npz → 성형된 임시 npz 경로 (q_des = q + raw*/kp)."""
    z = np.load(src, allow_pickle=True)
    files = z.files
    def get(k1, k2=None):
        if k1 in files:
            return np.asarray(z[k1], float)
        return np.asarray(z[k2], float) if k2 and k2 in files else None
    t = get("t")
    m = t >= 0                    # settle 제외
    q1, q2 = get("q1"), get("q2")
    dq1, dq2 = get("dq1"), get("dq2")
    r1, r2 = get("raw1"), get("raw2")
    if q1 is None:                # 행렬 스키마 (B: q/dq/tau_cmd_raw, (N,2) 또는 (2,N))
        def col(name, j):
            a = get(name)
            if a is None:
                return None
            a = np.asarray(a, float)
            return a[:, j] if a.ndim == 2 and a.shape[1] == 2 else a[j]
        q1, q2 = col("q", 0), col("q", 1)
        dq1, dq2 = col("dq", 0), col("dq", 1)
        r1, r2 = col("tau_cmd_raw", 0), col("tau_cmd_raw", 1)
    out = dict(t=t[m] - t[m][0],
               q1=q1[m], q2=q2[m], dq1=dq1[m], dq2=dq2[m],
               raw1=r1[m], raw2=r2[m])
    if "tau1_nm" in files:
        out["tau1_nm"] = get("tau1_nm")[m]; out["tau2_nm"] = get("tau2_nm")[m]
    if "bz" in files:
        out["bz"] = get("bz")[m]
    if "h_plan" in files:
        out["h_plan"] = float(z["h_plan"])
    # ── 성형 ──
    out["qd1"] = out["q1"] + out["raw1"] / kp1
    out["qd2"] = out["q2"] + out["raw2"] / kp2
    out["dqd1"] = out["dq1"]
    out["dqd2"] = out["dq2"]
    dst = src.parent / (src.stem + f"_shaped_kp{int(kp1)}_{int(kp2)}.npz")
    np.savez(dst, **out)
    return dst


def main():
    plans = [p for p in sorted(set(HERE.glob("p25_[abc]_*.npz")) | set(HERE.glob("p25_a4_*.npz")))
             if "shaped" not in p.name and "plan" not in p.name
             and "golden" not in p.name and "fixedpoint" not in p.name
             and p.stem.endswith("_t18") == T18]
    rows = {}
    print(f"{'계획(성형)':28s} {'게인':5s} {'h_plan':>7s} {'h_PD':>7s} {'F_τ':>7s} {'hip':>7s} {'knee':>7s}")
    for src in plans:
        for gname, (kp1, kd1, kp2, kd2) in GAINS.items():
            dst = shape_npz(src, kp1, kp2)
            r = D.deploy(str(dst), (kp1, kd1, kp2, kd2))
            key = f"{src.name}|{gname}"
            rows[key] = {k: v for k, v in r.items() if not isinstance(v, (list, np.ndarray))}
            print(f"{src.stem:28s} {gname:5s} {r.get('h_plan', float('nan')):7.3f} "
                  f"{r['h_PD']:7.3f} {100*r['F_tau']:6.1f}% {100*r['F_tau_hip']:6.1f}% "
                  f"{100*r['F_tau_knee']:6.1f}%", flush=True)
            dst.unlink()          # 임시 성형본 정리
    safe.atomic_json_write(HERE / f"p25_d_shaped_results{SUF}.json", rows)
    print(f"saved p25_d_shaped_results{SUF}.json", flush=True)


if __name__ == "__main__":
    main()
