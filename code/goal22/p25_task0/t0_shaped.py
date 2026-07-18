# -*- coding: utf-8 -*-
"""성형 순수 PD 배포 — 사용자 최종 목적(순수 PD로 측정 τ ≈ 계획 τ*) 구현.

성형: q_des = q_plan + raw*/Kp (게인별로 다름!), dq_des = dq_plan — FF 채널 불사용.
전 계획 × 실 세션 게인 8종. 산출: t0_shaped_results.json +
graphs/<방법>/pd_shaped/gain_<게인>.png (기준양식).
"""
import os
import sys
from pathlib import Path

for k in ("P23_SPRING_GATED", "P23_RISE_GATED", "P24_HIP_LAW", "P24_REFIT"):
    os.environ.setdefault(k, "1")
os.environ["P25_CLIP_RAW"] = "35.5"
os.environ["P25_GAINS_FULL"] = "1"

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p25_deploy"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p25_d_deploy as D
import safe
from t0_figs import _chan, _log_chan
from t0_ours import fig_std, MDIR


def shaped_npz(z, kp1, kp2, dst):
    """쌍·행렬(Phase B) 스키마 겸용 — 채널은 _chan, raw는 스키마별 추출."""
    ch = _chan(z)
    t = np.asarray(z["t"], float)
    m = t >= 0
    if "raw1" in z.files:
        r1 = np.asarray(z["raw1"], float)[m]
        r2 = np.asarray(z["raw2"], float)[m]
    else:
        a2 = np.asarray(z["tau_cmd_raw"], float)
        a2 = a2 if a2.ndim == 2 and a2.shape[1] == 2 else a2.T
        r1, r2 = a2[m, 0], a2[m, 1]
    out = dict(t=ch["t"], q1=ch["q1"], q2=ch["q2"], dq1=ch["dq1"], dq2=ch["dq2"],
               raw1=r1, raw2=r2, tau1_nm=ch["tau1"], tau2_nm=ch["tau2"],
               bz=ch["bz"], grf=ch["grf"])
    out["qd1"] = out["q1"] + out["raw1"] / kp1
    out["qd2"] = out["q2"] + out["raw2"] / kp2
    out["dqd1"] = out["dq1"]
    out["dqd2"] = out["dq2"]
    out["h_plan"] = float(z["h_plan"])
    np.savez(dst, **out)


def main():
    rows = {}
    for stem, mdir in MDIR.items():
        f = HERE / f"{stem}.npz"
        if not f.exists():
            continue
        z = np.load(f)
        P = _chan(z)
        for gk, (kp1, kd1, kp2, kd2) in D.GAINS.items():
            tmp = HERE / f"_shape_{stem}_{gk}.npz"
            shaped_npz(z, kp1, kp2, tmp)
            r = D.deploy(tmp, (kp1, kd1, kp2, kd2), return_log=True)
            tmp.unlink()
            if r.get("crash"):
                print(f"[{stem}|성형PD|{gk}] CRASH", flush=True)
                continue
            rows[f"{stem}|shaped|{gk}"] = dict(
                h_plan=float(r["h_plan"]), h_PD=float(r["h_PD"]), F_tau=float(r["F_tau"]),
                F_tau_hip=float(r["F_tau_hip"]), F_tau_knee=float(r["F_tau_knee"]))
            Dc = _log_chan(r["log"])
            tlo = r.get("t_liftoff", float("nan"))
            ttl = (f"{stem}/{gk} [성형 순수PD p24a — q_des=q+raw*/Kp, FF 없음] — "
                   f"h_PD {r['h_PD']:.2f} / h_plan {r['h_plan']:.2f} m  (F_τ {100*r['F_tau']:.1f}%)")
            out = HERE / "graphs" / mdir / "pd_shaped" / f"gain_{gk}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            fig_std(P, Dc, out, ttl, tlo)
            print(f"[{stem}|성형PD|{gk}] h_PD {r['h_PD']:.3f} F_τ {100*r['F_tau']:.1f}%", flush=True)
    safe.atomic_json_write(HERE / "t0_shaped_results.json", rows)
    print("SHAPED DONE", flush=True)


if __name__ == "__main__":
    main()
