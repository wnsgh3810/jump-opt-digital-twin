# -*- coding: utf-8 -*-
"""canonical MuJoCo 렌더 — 전 게인 × {FF+PD, 순수 PD} 배치 (사용자 지시 07-18).

t0_mjc_render의 검증된 배선(render/qpos_flip/xml)을 import해 재사용 — 렌더러는 정본 그대로.
산출: sims/canonical/<방법>/{ffpd,pd_only}/gain_<게인>.gif (5계획 × 8게인 × 2모드 = 80)
      + 요약 sims/canonical/mjc_render_all_summary.json
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import numpy as np
import t0_mjc_render as R          # env·canonical 로드 포함 (main은 실행 안 됨)
import p25_d_deploy as D
import p25_d_ff as FF
import mujoco
import safe

MDIR = {"t0nc_ol": "OL-CMA", "t0nc_cl": "CL-CMA", "t0nc_nlp": "NLP",
        "t0nc_ppo": "PPO", "t0nc_ppo_long": "PPO_long"}
MODES = (("FF+PD", "ffpd", lambda p, g: FF.deploy_ff(p, g, return_log=True)),
         ("PD", "pd_only", lambda p, g: D.deploy(p, g, return_log=True)))


def main():
    only = sys.argv[1:] or None
    D.setup()
    mf = D.model_flip()
    xml_flip = R.SCR / "twin_flip.xml"
    mujoco.mj_saveLastXML(str(xml_flip), mf)
    rows = {}
    for stem, mdir in MDIR.items():
        if not (HERE / f"{stem}.npz").exists() or (only and stem not in only):
            continue
        for mname, sub, fn in MODES:
            for gk in D.GAINS:
                r = fn(HERE / f"{stem}.npz", gk)
                if r.get("crash"):
                    print(f"[{stem}|{mname}|{gk}] CRASH — skip", flush=True)
                    continue
                L = r["log"]
                out_dir = HERE / "sims" / "canonical" / mdir / sub
                out_dir.mkdir(parents=True, exist_ok=True)
                R.OUT = out_dir                      # render()가 쓰는 출력 폴더 재지정
                row = R.render(f"gain_{gk}", L["t"],
                               R.qpos_flip(L["bz"], L["q1"], L["q2"]), L["grf"],
                               xml_flip, f"task0 {mdir} {mname} {gk}",
                               float(r["h_PD"]), "h_PD(regen)", float(r["h_plan"]))
                row.update(F_tau=round(float(r["F_tau"]), 4), mode=mname, gain=gk)
                rows[f"{stem}|{sub}|{gk}"] = row
    safe.atomic_json_write(HERE / "sims" / "canonical" / "mjc_render_all_summary.json", rows)
    print(f"DONE — {len(rows)} gifs", flush=True)


if __name__ == "__main__":
    main()
