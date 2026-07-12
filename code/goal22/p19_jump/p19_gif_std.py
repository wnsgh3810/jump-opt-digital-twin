# -*- coding: utf-8 -*-
"""P19 결과 GIF 재생성 — render_kit 표준 오버레이 (hip/knee/h_sim/h_real/l_i 포함).

이전 판(마라톤 새벽 인라인 스크립트)은 trial/t/base_z/l_i만 표기 → 표준 위반이라 재생성.
CL은 커맨드층(α) 반영 (마라톤 당시와 동일 — R.cl_run 사용).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p18_cvt"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))
import p19_judge as P
import p19_run as R
import render_kit as RK

P.winit()
import mujoco
from PIL import Image, ImageDraw

sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code")
import make_anim as MA
from cvt_anim import build_anim_model
from cvt_core import closure

W = json.load(open(HERE / "fourbar_p19_candidate.json"))
v = np.array(W["x"])
IDX = dict(stiff=11, fv_hip=14, fc_hip=16, fv_knee=15, fc_knee=17,
           solref=12, imp0=13, arm_knee=9, M_c=4, I_th=5, I_ca=6, dz_th=7, dz_ca=8)
x32 = np.array(P.X37[:32])
for i, n in enumerate(W["names"]):
    if n in IDX:
        x32[IDX[n]] = v[i]
SP = "calf" if v[0] > 1e-3 else "none"
DST = Path(r"C:/Users/junho/Desktop/jump_opt/g22_p19_results/gif")
DST.mkdir(parents=True, exist_ok=True)


def h_real_of(ds, sub):
    for tr in P.J._P["P12"]._G["trials"]:
        if tr["ds"] == ds and str(tr.get("sub", "")) in (sub, str(sub)):
            hr = tr.get("h_real", float("nan"))
            return float(hr) if hr == hr else float("nan")
    return float("nan")


def main():
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    targets = [("jump_0602", "120_2_120_2"), ("jump_0424", "150_2.2_500_4"),
               ("jump_0429", "120_2_120_2")]
    model_f, _ = P.build_flip(x32, v[1], SP)
    model_c = None
    anim = {}
    for ds_w, sub_w in targets:
        for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R.TRIALS:
            if ds != ds_w or sub != sub_w:
                continue
            alphas = R.ALPH.get(ds, [1, 1, 1, 1])
            if is_cvt:
                if model_c is None:
                    model_c, _ = P.build_cvt(x32, v[1], SP, l_i)
                L = R.cl_run(model_c, True, l_i, d, gains, dqon, ffk, P.A_PAPER,
                             v[15], alphas, 0.0, o1=v[16], o2=v[17])
                hr = float(d.get("h_real", float("nan")))
            else:
                dd = dict(zip(P.J._P["FR"].NAMES, x32[:26]))
                k1, k2 = P.J.OFFK.get(ds, (None, None))
                o1 = dd.get(k1, 0.0) if k1 else 0.0
                o2 = dd.get(k2, 0.0) if k2 else 0.0
                L = R.cl_run(model_f, False, l_i, d, gains, dqon, ffk, P.A_PAPER,
                             v[15], alphas, v[2], o1=o1, o2=o2)
                hr = h_real_of(ds, sub)
            if L is None:
                print("skip (crash)", ds_w, sub_w)
                continue
            li_r = round(l_i, 4)
            if li_r not in anim:
                anim[li_r] = build_anim_model(li_r)
            am = anim[li_r]
            t = L["t"]
            mk = (t >= -0.05) & (t <= d["t"][-1] + 0.35)
            tt = t[mk]; q1 = L["q1"][mk]; qc = L["q2"][mk]; bz = L["bz"][mk]
            wrap = lambda x: ((x + np.pi) % (2 * np.pi)) - np.pi
            mj1 = wrap(-q1 - np.pi / 2); mjc = wrap(-qc)
            h_sim = float(bz[tt > 0].max())
            dur = float(tt[-1] - tt[0])
            n = min(MA.N_MAX, max(MA.N_MIN, int(round(dur / MA.PHYS_DT_PER_FRAME))))
            idxs = np.linspace(0, len(tt) - 1, n).astype(int)
            data = mujoco.MjData(am)
            cam = mujoco.MjvCamera()
            cam.azimuth = 135.0; cam.elevation = -15.0; cam.distance = 1.2
            cam.lookat = np.array([0.0, 0.0, 0.3])
            frames = []
            qk_prev = None
            with mujoco.Renderer(am, width=640, height=480) as ren:
                for i in idxs:
                    qk, qp, _ = closure(float(mjc[i]), li_r, qk_prev)
                    qk_prev = qk
                    data.qpos[:] = [float(bz[i]), float(mj1[i]), float(mjc[i]), qp, qk]
                    data.qvel[:] = 0.0
                    mujoco.mj_forward(am, data)
                    ren.update_scene(data, camera=cam)
                    img = Image.fromarray(ren.render())
                    dr = ImageDraw.Draw(img)
                    RK.draw_overlay(dr, MA, f"P19 CL {ds_w}/{sub_w}", tt[i] * 1000,
                                    bz_cm=bz[i] * 100,
                                    hip_deg=float(np.degrees(q1[i])),
                                    knee_deg=float(np.degrees(qc[i])),
                                    h_sim=h_sim, h_real=hr, l_i_mm=li_r * 1000)
                    frames.append(img)
            out = DST / f"{ds_w}_{sub_w}__CL.gif"
            frames[0].save(str(out), save_all=True, append_images=frames[1:],
                           duration=MA.DURATION_MS, loop=0, optimize=False)
            print("gif", out.name, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
