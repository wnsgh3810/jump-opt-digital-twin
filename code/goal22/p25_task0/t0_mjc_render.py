# -*- coding: utf-8 -*-
"""t0 MuJoCo 정식 렌더 — goal18 canonical jump 렌더러로 P25-task0 GIF 9종 재렌더.

사용자 정정 (07-18): 디지털 트윈 실험의 시뮬 렌더링은 canonical 파이프라인이 정본
(AVT 스틱피겨 GIF는 보조). 렌더러는 import만 — 절대 수정 금지 (헌법 철칙 2).

정본 렌더러: Desktop/jump_opt/goal18_v9/_make_anim_universal_colored.py
  :: make_anim_universal_colored(npz, xml, gif, trial_label, h_real_m)
  (640x480 / 60 frames / 40ms / iso 카메라 az135 el-15 d1.2 / 팔레트 강제 /
   오버레이 trial/t/base_z/GRF/h_sim/h_real — jump 정본 규격)
  아카이브 사본(fallback): code/goal19/canonical_render/_make_anim_universal_colored.py
드라이버 규약 = code/goal19/phase11/make_anim_v3_canonical.py (xml 임시 저장 + npz 생성만)
  + g22_p10_anim.py (4-bar qpos 재구성 [bz, mj1, mj2, -mj2, mj2], 크롭 t>=-0.05).

npz 입력 계약 (렌더러): t / q [N, nq=5 mj-frame qpos] / grf_z.
좌표 변환 (측정→mj): mj1 = wrap(-q1 - pi/2), mj2 = wrap(-q2) — cl_run23_log 역변환.
CVT(l_i=25.08mm): qpos = cvt_core.qpos_from_crank(bz, mj1, -qm, l_i) (폐쇄 솔버 체인).
물리/모델 = p24a 후보 그대로 (RU.build_flip23 / RU.build_cvt23) — XML은
mj_saveLastXML로 임시 저장만 (컴파일 직후 즉시 저장; 시각 전용).

배포 롤아웃 재생성: p25_d_ff.deploy_ff(npz, "60_1.5_60_1.5", return_log=True)
  (t0_deploy_results.json FF+PD 최저 F_τ 게인 = 전 계획 60_1.5_60_1.5,
   env: P23_*=1 + P25_CLIP_RAW=25.5810 + P25_GAINS_FULL=1 — t0_deploy.py 동일 배선).

산출: p25_task0/mjc_gifs/mjc_{ol,cl,nlp,ppo}_{plan,deploy}.gif + mjc_wc_cl_li2508_plan.gif
  + mjc_render_summary.json (렌더 h vs npz h 대조표).
"""
import os
import sys
import importlib.util
import json
from pathlib import Path

for _k in ("P23_SPRING_GATED", "P23_RISE_GATED", "P24_HIP_LAW", "P24_REFIT"):
    os.environ.setdefault(_k, "1")
os.environ["P25_CLIP_RAW"] = "25.5810"
os.environ["P25_GAINS_FULL"] = "1"

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "p25_deploy"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p25_d_deploy as D
import p25_d_ff as FF
import p23_v6_runners as RU
import safe
import mujoco

# ── canonical 렌더러 로드 (원본 우선, 아카이브 사본 fallback) — import만 ──
_CANON = Path("C:/Users/junho/Desktop/jump_opt/goal18_v9/_make_anim_universal_colored.py")
if not _CANON.exists():
    _CANON = HERE.parent.parent / "goal19/canonical_render/_make_anim_universal_colored.py"
_spec = importlib.util.spec_from_file_location("_mauc", str(_CANON))
_mauc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mauc)

SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research"
           r"-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4"
           r"/scratchpad") / "mjc_render"
SCR.mkdir(parents=True, exist_ok=True)
OUT = HERE / "mjc_gifs"
OUT.mkdir(exist_ok=True)

GAIN = "60_1.5_60_1.5"   # t0_deploy_results.json FF+PD 최저 F_τ (전 계획 공통)
T_CROP = -0.05           # g22_p10_anim 크롭 규약
LI_M = 0.02508           # with_cvt l_i [m]


def wrap(x):
    return ((x + np.pi) % (2 * np.pi)) - np.pi


def qpos_flip(bz, q1, q2):
    """측정 (q1,q2) → flip(평행사변형) qpos [bz, hip, knee_motor, cpin, knee]."""
    mj1 = wrap(-np.asarray(q1, float) - np.pi / 2)
    mj2 = wrap(-np.asarray(q2, float))
    return np.column_stack([np.asarray(bz, float), mj1, mj2, -mj2, mj2])


def qpos_cvt(bz, q1, qm, l_i):
    """측정 (q1, qm=크랭크) → CVT qpos (폐쇄 솔버, qk 체인 연속)."""
    from cvt_core import qpos_from_crank
    mj1 = wrap(-np.asarray(q1, float) - np.pi / 2)
    mjc = wrap(-np.asarray(qm, float))
    rows = np.empty((len(mj1), 5))
    qk_prev = None
    for i in range(len(mj1)):
        qp, qk_prev, _ = qpos_from_crank(float(np.asarray(bz, float)[i]),
                                         float(mj1[i]), float(mjc[i]), l_i, qk_prev)
        rows[i] = qp
    return rows


def render(tag, t, qpos, grf, xml_path, label, h_ref, h_ref_name, h_overlay):
    """크롭 → npz 저장 → canonical 렌더 호출 → h 대조 dict 반환."""
    t = np.asarray(t, float)
    m = t >= T_CROP
    t, qpos, grf = t[m], qpos[m], np.asarray(grf, float)[m]
    npz = SCR / f"{tag}.npz"
    np.savez(npz, t=t, q=qpos, grf_z=grf)
    gif = OUT / f"{tag}.gif"
    _mauc.make_anim_universal_colored(str(npz), str(xml_path), str(gif),
                                      trial_label=label, h_real_m=h_overlay)
    post = t >= 0.0
    h_render = float(qpos[post, 0].max() if post.any() else qpos[:, 0].max())
    row = dict(gif=gif.name, label=label, h_render=round(h_render, 4),
               h_ref=round(float(h_ref), 4), h_ref_name=h_ref_name,
               dh_mm=round(1000.0 * (h_render - float(h_ref)), 3),
               n_samples=int(len(t)), size_kb=round(gif.stat().st_size / 1024.0, 1))
    print(f"[{tag}] h_render={h_render:.4f} vs {h_ref_name}={h_ref:.4f} "
          f"(d={row['dh_mm']:+.1f}mm) {row['size_kb']:.0f}KB", flush=True)
    return row


def main():
    D.setup()
    # 트윈 XML 임시 저장 (컴파일 직후 즉시 — mj_saveLastXML 전역성 주의)
    mf = D.model_flip()
    xml_flip = SCR / "twin_flip.xml"
    mujoco.mj_saveLastXML(str(xml_flip), mf)
    mc = RU.build_cvt23(D.G["X32"], D.G["REF"], D.G["SP"], LI_M, D.G["D_DQ"])
    xml_cvt = SCR / "twin_cvt2508.xml"
    mujoco.mj_saveLastXML(str(xml_cvt), mc)

    dep_ref = json.load(open(HERE / "t0_deploy_results.json", encoding="utf-8"))
    rows = {}

    plans = [("ol", "t0nc_ol.npz", "OL-CMA"), ("cl", "t0nc_cl.npz", "CL-CMA"),
             ("nlp", "t0nc_nlp.npz", "NLP"), ("ppo", "t0nc_ppo.npz", "PPO")]

    # ── 계획 롤아웃 (개루프 재생 — npz 저장분 그대로) ──
    for key, fn, lab in plans:
        z = np.load(HERE / fn)
        h_plan = float(z["h_plan"])
        if key == "nlp":   # NLP: 트윈 재생 채널 (*_twin) = 개루프 재생
            t, q, bz, grf = (np.asarray(z[k], float) for k in
                             ("t_twin", "q_twin", "bz_twin", "grf_twin"))
            q1, q2 = q[:, 0], q[:, 1]
            h_ref, h_ref_name = float(z["h_twin"]), "h_twin(npz)"
        else:
            t, q1, q2, bz, grf = (np.asarray(z[k], float) for k in
                                  ("t", "q1", "q2", "bz", "grf"))
            h_ref, h_ref_name = h_plan, "h_plan(npz)"
        rows[f"{key}_plan"] = render(
            f"mjc_{key}_plan", t, qpos_flip(bz, q1, q2), grf, xml_flip,
            f"task0 {lab} plan", h_ref, h_ref_name, h_plan)

    # ── 배포 롤아웃 (FF+PD 최적게인 — deploy_ff 재생성) ──
    for key, fn, lab in plans:
        r = FF.deploy_ff(HERE / fn, GAIN, return_log=True)
        assert not r.get("crash"), f"deploy crash: {fn}"
        L = r["log"]
        ref = dep_ref[f"{fn}|FF+PD|{GAIN}"]
        row = render(f"mjc_{key}_deploy", L["t"],
                     qpos_flip(L["bz"], L["q1"], L["q2"]), L["grf"], xml_flip,
                     f"task0 {lab} FF+PD {GAIN}", float(ref["h_PD"]),
                     "h_PD(json)", float(ref["h_plan"]))
        row.update(F_tau=round(float(r["F_tau"]), 4),
                   F_tau_json=round(float(ref["F_tau"]), 4),
                   h_PD_regen=round(float(r["h_PD"]), 4))
        rows[f"{key}_deploy"] = row

    # ── CVT 25.08 CL 계획 ──
    w = np.load(HERE / "t0wc_cl_li2508.npz")
    t, q1, qm, bz, grf = (np.asarray(w[k], float) for k in
                          ("t", "q1", "qm", "bz", "grf"))
    h_plan = float(w["h_plan"])
    rows["wc_cl_li2508_plan"] = render(
        "mjc_wc_cl_li2508_plan", t, qpos_cvt(bz, q1, qm, LI_M), grf, xml_cvt,
        "task0 CVT li=25.08 CL plan", h_plan, "h_plan(npz)", h_plan)

    safe.atomic_json_write(OUT / "mjc_render_summary.json", rows)
    print(f"DONE — {len([k for k in rows])} gifs -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
