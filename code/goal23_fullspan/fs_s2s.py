# -*- coding: utf-8 -*-
"""fs_s2s — 0604 페이로드 s2s 참관 (Day1 #5): off-stop 창 선별 재현.

F18 잔여: 페이로드 5/7.5kg에서 q2 75~103° 발산 = H14 '3중 접촉 퍼즐' (착좌 중 다리
무부하 → sim 무릎 자유낙하). SEA의 정직한 회피 = off-stop 창 선별: 실측 자세 FK 기준
base가 엔드스톱(0.169) 위 = 다리가 실제 하중을 받는 창만 채점 (착좌 창은 물리 부재로 제외).
h14b 문자 미러 (0.4s 창/0.3 stride/시간창/페이로드 질량 패치) + fs 러너(rollout_ol_fs_b,
엔드스톱 XML) + 실측 FK off-stop 판정 (창 시작/중간/끝 3점 min > 0.171).
데이터: 0604 s2s는 *2 미제공 (참관 전용) → raw_unwrap 원본 사용 (fs_data 금지목록은 점프 *2 규약).
CLI: python fs_s2s.py
"""
import os, sys, json, copy
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import fs_data as FD                     # noqa: E402
import fs_model as FM                    # noqa: E402
import fs_runner as FR                   # noqa: E402
import safe                              # noqa: E402
import mujoco as mjm                     # noqa: E402

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data/26.06.04")
TRIALS = [("0kg", ROOT / "no_cvt/no_load/raw_unwrap", 0.0, (47.8, 53.2)),
          ("5kg", ROOT / "no_cvt/load_5/raw_unwrap", 5.0, (47.0, 53.0)),
          ("7.5kg", ROOT / "no_cvt/load_7.5/raw_unwrap", 7.5, (52.9, 58.5))]
WLEN, STRIDE = 0.4, 0.3
Z_STOP, Z_MARGIN = 0.169, 0.002


def ft_payload(PL):
    ft0 = FR.fs_twin()
    base_xml = FR._CACHE["base"][0]
    model, xml = FM.build_fs(base_xml=base_xml, endstop=True)
    if PL > 0:
        b = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_BODY, "base")
        model.body_mass[b] += PL
        model.body_inertia[b] *= (1 + PL / 1.39 * 0.5)
    ft = dict(ft0)
    ft["model"] = model
    ft["iq"] = {n: safe.qadr(model, n, mjm) for n in ("base_z", "hip_m", "hip", "knee_motor", "cpin", "knee")}
    ft["dof"] = {n: safe.dofadr(model, n, mjm) for n in ft["iq"]}
    return ft


def bz_fk(ft, md, q1, q2):
    """실측 자세의 발접지 base_z (다리 하중 판정용)."""
    S = ft["P"].J._P["S"]
    iq = ft["iq"]
    md.qpos[:] = 0
    md.qvel[:] = 0
    md.qpos[iq["base_z"]] = 1.0
    md.qpos[iq["hip_m"]] = -q1 - np.pi / 2
    md.qpos[iq["knee_motor"]] = -q2
    md.qpos[iq["cpin"]] = q2
    md.qpos[iq["knee"]] = -q2
    mjm.mj_forward(ft["model"], md)
    fg = mjm.mj_name2id(ft["model"], mjm.mjtObj.mjOBJ_GEOM, "foot")
    return 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS


def main():
    OUT = {}
    for lab, fold, PL, (t0, t1) in TRIALS:
        hip = pd.read_excel(fold / "hip.xlsx"); knee = pd.read_excel(fold / "knee.xlsx")
        n = min(len(hip), len(knee)); hip, knee = hip.iloc[:n], knee.iloc[:n]
        t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
        q1m = hip["currentAngle"].to_numpy(float); q2m = knee["currentAngle"].to_numpy(float)
        dq1m = hip["currentAngleVelocity"].to_numpy(float); dq2m = knee["currentAngleVelocity"].to_numpy(float)
        raw1 = hip["currentTorque"].to_numpy(float); raw2 = knee["currentTorque"].to_numpy(float)
        ft = ft_payload(PL)
        md_fk = mjm.MjData(ft["model"])
        rows_on, rows_off = [], []
        w0 = t0
        while w0 + WLEN <= t1:
            seg = (t >= w0) & (t <= w0 + WLEN)
            if seg.sum() < 50:
                w0 += STRIDE
                continue
            tg = t[seg] - w0
            i0 = int(np.argmax(seg))
            imid = i0 + seg.sum() // 2
            iend = i0 + seg.sum() - 1
            bzs = [bz_fk(ft, md_fk, float(q1m[i]), float(q2m[i])) for i in (i0, imid, iend)]
            off = min(bzs) > Z_STOP + Z_MARGIN
            L = FR.rollout_ol_fs_b(ft, tg, raw1[seg], raw2[seg],
                                   float(q1m[i0]), float(q2m[i0]), float(dq1m[i0]), float(dq2m[i0]),
                                   float(tg[-1] - 0.005), bias1=0.0, knee_deep=None, fade=True,
                                   bz_floor=Z_STOP, knee_rel=0.1)
            if L is None:
                w0 += STRIDE
                continue
            msk = (tg >= 0.02) & (tg <= tg[-1] - 0.02)
            q1s = np.interp(tg[msk], L["t"], L["q1"]); q2s = np.interp(tg[msk], L["t"], L["q2"])
            r = (float(np.degrees(np.sqrt(np.mean((q1m[seg][msk] - q1s) ** 2)))),
                 float(np.degrees(np.sqrt(np.mean((q2m[seg][msk] - q2s) ** 2)))))
            (rows_off if off else rows_on).append(r)
            w0 += STRIDE
        res = {}
        for tag, rows in (("off_stop", rows_off), ("on_stop", rows_on)):
            if rows:
                a = np.array(rows)
                res[tag] = dict(n=len(rows), q1=round(float(a[:, 0].mean()), 2), q2=round(float(a[:, 1].mean()), 2))
        OUT[lab] = res
        po = res.get("off_stop", {}); pn = res.get("on_stop", {})
        print(f"{lab}: off-stop 창 {po.get('n', 0)}개 q1 {po.get('q1', '—')} q2 {po.get('q2', '—')} || "
              f"on-stop(착좌) 창 {pn.get('n', 0)}개 q1 {pn.get('q1', '—')} q2 {pn.get('q2', '—')}", flush=True)
    safe.atomic_json_write(HERE / "_fs_s2s.json", OUT)
    print("done → _fs_s2s.json")


if __name__ == "__main__":
    main()
