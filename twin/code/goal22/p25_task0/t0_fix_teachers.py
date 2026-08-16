# -*- coding: utf-8 -*-
"""t0_fix_teachers — 고정-l_i 스윕용 BC 교사 npz 생성 + 재생 검증 (코디 지시 07-18 밤).

교사 출처: t0wc_li_sweep.json의 고정-l_i CMA 재최적화 knots (이웃 warm-start 스윕
— 코디 지시의 '단축 CMA'와 동일 산출물이 이미 존재하므로 재실행 대신 그 knots를
t0wc_cma.rollout_cl로 재롤아웃해 npz화). 생성: t0wc_cl_li{24,26,28,30}.npz
(스키마 = t0wc_cma.save_all cl판 — collect_teacher가 쓰는 t/qd/dqd/gains/h_plan 포함).

검증: t0_train_long.collect_teacher(폐루프 PD + 배리어)로 2ms 재생 apex 확인.
프로브용: liopt(26.25)를 1ms/0.5ms 주기로 재생 검증.
"""
import numpy as np
from pathlib import Path
from scipy.interpolate import CubicSpline

import t0wc_cma as W
import t0_spec as T0
import safe

HERE = Path(__file__).parent


def gen_teacher(li_mm):
    W.setup()
    sw = safe.read_json(HERE / "t0wc_li_sweep.json")["rows"]
    r = sw[f"{li_mm:g}"]
    x1 = np.asarray(r["knots_qd1"], float)
    x2 = np.asarray(r["knots_qd2"], float)
    l_i = round(li_mm / 1000.0, 6)
    model, _, _ = W.model_cvt(l_i)
    dt = float(model.opt.timestep)
    TG = np.arange(0.0, W.T_END + dt, dt)
    s1 = CubicSpline(W.KT_CL, x1, bc_type="natural")
    s2 = CubicSpline(W.KT_CL, x2, bc_type="natural")
    g1, g2, dg1, dg2 = s1(TG), s2(TG), s1(TG, 1), s2(TG, 1)
    Lg = W.rollout_cl(l_i, TG, g1, g2, dg1, dg2, W.GAINS, alphas=(1, 1, 1, 1),
                      record=True)
    assert Lg is not None, f"rollout_cl 발산 (li={li_mm})"
    aud = T0.audit(Lg, t_end=W.T_END, cvt=True)
    h = W.apex_of(Lg)
    tl = Lg["t"]
    qd_l = [np.interp(np.clip(tl, 0.0, W.T_END), TG, g) for g in (g1, g2)]
    dqd_l = [np.where((tl >= 0) & (tl <= W.T_END),
                      np.interp(np.clip(tl, 0.0, W.T_END), TG, dg), 0.0)
             for dg in (dg1, dg2)]
    name = f"t0wc_cl_li{f'{li_mm:g}'.replace('.', '')}.npz"
    np.savez(HERE / name,
             t=tl, q1=Lg["q1"], q2=Lg["q2"], dq1=Lg["dq1"], dq2=Lg["dq2"],
             raw1=Lg["raw1"], raw2=Lg["raw2"], tau1_nm=Lg["sh1"], tau2_nm=Lg["sh2"],
             bz=Lg["bz"], grf=Lg["grf"], h_plan=h, qm=Lg["q2"], l_i=li_mm,
             extrapolated=float(li_mm < 25.08),
             qd1=qd_l[0], qd2=qd_l[1], dqd1=dqd_l[0], dqd2=dqd_l[1],
             knot_t=W.KT_CL, knots_qd1=x1, knots_qd2=x2,
             gains=np.array(W.GAINS))
    print(f"[gen] {name}: h={h:.4f} (sweep {r['h_plan']:.4f}) audit={aud['pass']}",
          flush=True)
    return name, h


def main():
    safe.utf8_console()
    for li in (24.0, 26.0, 28.0, 30.0):
        gen_teacher(li)


if __name__ == "__main__":
    main()
