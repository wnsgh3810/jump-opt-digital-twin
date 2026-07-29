# -*- coding: utf-8 -*-
"""fs_s2s_air — 0324 s2s 공중(매달림) 세션 참관 (설계상 참관 대상 중 마지막 미관찰).

의의: 무부하 앵커 (사용자 확인: 공중, knee â rms 0.25Nm) — 접촉·지지법칙 없이 순수
모터+직렬 스프링+중력 사슬만 검증. fs11의 하중 비례 간섭은 N=0에서 자연 소멸 (설계 정합:
0324는 3월 = 클러치 장착 전 = 실기에도 간섭 없음 — 모델·실기가 0에서 일치해야 함).
방법: base_z를 XML range로 핀 고정 (0.999~1.001) → 다리 자유 스윙, MA mshoot 0.4s 창
(측정 상태 초기화 + 측정 raw 주입 + 2단 스프링 qfrc + 세션 바이어스 fade). 채점 thm1 기준.
구식 xlsx: deg 가능성 → rad 변환 가드. CLI: python fs_s2s_air.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import fs_runner as FR
import fs_model as FM
import safe
import mujoco as mjm

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data/26.03.24/sit2stand")
WLEN, STRIDE = 0.4, 0.3


def ft_air():
    FR.fs_twin()
    base_xml = FR._CACHE["base"][0]
    model, xml = FM.build_fs(base_xml=base_xml)
    xml2 = safe.xml_patch(xml, '<joint name="base_z" type="slide" axis="0 0 1"/>',
                          '<joint name="base_z" type="slide" axis="0 0 1" limited="true" range="0.999 1.001" solreflimit="0.002 1"/>', count=1)
    model2 = mjm.MjModel.from_xml_string(xml2)
    ft0 = FR.fs_twin()
    ft = dict(ft0)
    ft["model"] = model2
    ft["iq"] = {n: safe.qadr(model2, n, mjm) for n in ("base_z", "hip_m", "hip", "knee_motor", "cpin", "knee")}
    ft["dof"] = {n: safe.dofadr(model2, n, mjm) for n in ft["iq"]}
    return ft


def load_old(fold):
    hip = pd.read_excel(fold / "hip.xlsx"); knee = pd.read_excel(fold / "knee.xlsx")
    n = min(len(hip), len(knee)); hip, knee = hip.iloc[:n], knee.iloc[:n]
    t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
    q1 = hip["currentAngle"].to_numpy(float); q2 = knee["currentAngle"].to_numpy(float)
    if np.nanmax(np.abs(q2)) > 7:
        q1, q2 = np.radians(q1), np.radians(q2)
    dq1 = hip["currentAngleVelocity"].to_numpy(float); dq2 = knee["currentAngleVelocity"].to_numpy(float)
    if np.nanmax(np.abs(dq2)) > 25:
        dq1, dq2 = np.radians(dq1), np.radians(dq2)
    return dict(t=t, q1=q1, q2=q2, dq1=dq1, dq2=dq2,
                raw1=hip["currentTorque"].to_numpy(float), raw2=knee["currentTorque"].to_numpy(float))


def run_trial(ft, d, bias1):
    model = ft["model"]; P = ft["P"]
    law_a, law_b, law_v0 = ft["law"]; kr = ft["kr"]; sprm = ft["sprm"]
    iq, dof = ft["iq"], ft["dof"]
    A = P.A_PAPER
    RU = FR.RU
    t = d["t"]
    rows = []
    w0 = t[0] + 0.5
    while w0 + WLEN <= t[-1] - 0.1:
        seg = (t >= w0) & (t <= w0 + WLEN)
        if seg.sum() < 50:
            w0 += STRIDE
            continue
        tg = t[seg] - w0
        i0 = int(np.argmax(seg))
        md = mjm.MjData(model)
        s1_0 = float(P.J.ahat(A, np.array([d["raw1"][i0]]), np.array([d["dq1"][i0]]))[0])
        defl0 = float(np.clip(np.sign(s1_0) * (abs(s1_0) / 96.0 if abs(s1_0) <= 9 else 9 / 96.0 + (abs(s1_0) - 9) / 323.0), -0.3, 0.3))
        md.qpos[iq["base_z"]] = 1.0
        md.qpos[iq["hip_m"]] = -float(d["q1"][i0]) - np.pi / 2 - defl0
        md.qpos[iq["hip"]] = defl0
        md.qpos[iq["knee_motor"]] = -float(d["q2"][i0])
        md.qpos[iq["cpin"]] = float(d["q2"][i0])
        md.qpos[iq["knee"]] = -float(d["q2"][i0])
        md.qvel[:] = 0
        md.qvel[dof["hip_m"]] = -float(d["dq1"][i0])
        md.qvel[dof["knee_motor"]] = -float(d["dq2"][i0])
        md.qvel[dof["cpin"]] = float(d["dq2"][i0])
        md.qvel[dof["knee"]] = -float(d["dq2"][i0])
        mjm.mj_forward(model, md)
        dt = model.opt.timestep
        N = int(round((tg[-1] - 0.004) / dt))
        L = {k: np.zeros(N) for k in ("t", "thm1", "q2")}
        bad = False
        for k in range(N):
            tc = k * dt
            v1c = -md.qvel[dof["hip_m"]]
            v2c = -md.qvel[dof["knee_motor"]]
            r1 = float(np.clip(np.interp(tc, tg, d["raw1"][seg]), -FR.TW.R19.CLIP, FR.TW.R19.CLIP))
            r2 = float(np.clip(np.interp(tc, tg, d["raw2"][seg]), -FR.TW.R19.CLIP, FR.TW.R19.CLIP))
            s1 = float(P.J.ahat(A, np.array([r1]), np.array([v1c]))[0])
            s2 = float(P.J.ahat(A, np.array([r2]), np.array([v2c]))[0])
            supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
            if kr:
                supp += float(RU.rise_term(v2c, kr, law_v0))
            tql = RU.spr_tau(float(md.qpos[iq["knee"]]), abs(s2), sprm) if sprm is not None else 0.0
            hs = 0.0 if PLAIN else RU.hip_supp_scalar(s1, s2, v1c)
            md.ctrl[:] = [-(s1 + hs), -(s2 + supp)]
            md.qfrc_applied[dof["knee"]] = tql
            dq_s = float(md.qpos[iq["hip"]])
            b_eff = bias1
            if abs(v1c) > 1.0:
                b_eff = bias1 * max(0.0, 1.0 - (abs(v1c) - 1.0) / 2.0)
            md.qfrc_applied[dof["hip"]] = (FM.KS_HIP * dq_s - FR._tau2s(dq_s)) + b_eff
            mjm.mj_step(model, md)
            if not np.isfinite(md.qpos).all():
                bad = True
                break
            L["t"][k] = tc
            L["thm1"][k] = -md.qpos[iq["hip_m"]] - np.pi / 2
            L["q2"][k] = -md.qpos[iq["knee_motor"]]
        if bad:
            w0 += STRIDE
            continue
        msk = (tg >= 0.02) & (tg <= tg[-1] - 0.02)
        q1s = np.interp(tg[msk], L["t"], L["thm1"])
        q2s = np.interp(tg[msk], L["t"], L["q2"])
        rows.append((float(np.degrees(np.sqrt(np.mean((d["q1"][seg][msk] - q1s) ** 2)))),
                     float(np.degrees(np.sqrt(np.mean((d["q2"][seg][msk] - q2s) ** 2))))))
        w0 += STRIDE
    return rows


PLAIN = False


def main():
    global PLAIN
    PLAIN = len(sys.argv) > 1 and sys.argv[1] == "plain"
    ft = ft_air()
    SP = FR._sess_params()
    b = 0.0 if PLAIN else SP.get("26.03.24", {}).get("bias1", 0.0)
    print(f"0324 s2s 공중 참관 (bias1={b:+.2f}, hip지지 {'OFF' if PLAIN else 'ON'})", flush=True)
    for fold in sorted(ROOT.iterdir()):
        if not fold.is_dir() or not (fold / "hip.xlsx").exists():
            continue
        try:
            d = load_old(fold)
            rows = run_trial(ft, d, b)
        except Exception as ex:
            print(f"{fold.name}: FAIL {type(ex).__name__} {ex}", flush=True)
            continue
        if rows:
            a = np.array(rows)
            print(f"{fold.name}: 창 {len(rows)}개 | q1 {a[:, 0].mean():.2f}° | q2 {a[:, 1].mean():.2f}°", flush=True)
        else:
            print(f"{fold.name}: 창 없음", flush=True)


if __name__ == "__main__":
    main()
