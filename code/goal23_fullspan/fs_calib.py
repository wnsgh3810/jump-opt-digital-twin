# -*- coding: utf-8 -*-
"""fs_calib — 준정적 하강 창 정적 감사 + 세션 상수 캘리브 (GOAL23 Day0 밤 → Day1).

원리: 하강(천천히 deep squat) 창은 연속 정적 자세 스윕. 각 표본 자세 (q1m, q2m)에서
트윈의 정적 유지 토크 (settle 평형의 축토크 s1,s2 — p25 settle_state 루프 문자 미러,
지지법칙/스프링층 전부 활성)를 구해 실측 â1,â2와 비교 → 잔차 r1(q), r2(q).
잔차 해석(회귀는 후속 틱): 상수항=오프셋/중력, â1 비례항=관측 처짐(k_s), 자세 의존=발 접촉점/CoM.
주의: 자세는 인코더각(모터측) 기준 배치 — 처짐만큼 참관절과 다름이 잔차에 포함됨 (분해 대상).
CLI: audit [세션] — 전 trial 하강 창 100ms 표본 정적 감사 → _fs_static_audit.json
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "goal22" / "p25_task0"))
sys.path.insert(0, str(HERE.parent / "goal22" / "p25_deploy"))
sys.path.insert(0, str(HERE.parent / "goal22" / "p26_sea"))
import fs_data as FD                     # noqa: E402
import p25_a_twin as TW                  # noqa: E402
import safe                              # noqa: E402

RU = TW.RU
tw0 = TW.twin()
P = tw0["P"]; mj = P.J._P["mj"]; S = P.J._P["S"]
MODEL = tw0["model"]
A = P.A_PAPER


def hold_torque(q1_0, q2_0, t_settle=0.5):
    """자세 (q1_0,q2_0) 정적 유지에 트윈이 필요로 하는 축토크 (s1,s2) [Nm]
    — settle_state 루프 문자 미러 + 마지막 스텝 축토크 반환. 발 접지 FK 배치."""
    law_a, law_b, law_v0 = tw0["law"]
    kr = tw0["kr"]; sprm = tw0["sprm"]
    md = mj.MjData(MODEL)
    dof_knee = safe.dofadr(MODEL, "knee", mj)
    iq_k = safe.qadr(MODEL, "knee", mj)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(MODEL, md)
    fg = mj.mj_name2id(MODEL, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(MODEL, md)
    dt = MODEL.opt.timestep
    Ns = int(round(t_settle / dt))
    s1 = s2 = 0.0
    for k in range(Ns):
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
        c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
        c1 = float(np.clip(c1, -TW.R19.CLIP, TW.R19.CLIP)); c2 = float(np.clip(c2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = 0.0
        if sprm is not None:
            tql += RU.spr_tau(float(md.qpos[iq_k]), abs(s2), sprm)
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[dof_knee] = tql
        mj.mj_step(MODEL, md)
    # 수렴 검증: 잔여 속도
    ok = abs(md.qvel[1]) < 0.05 and abs(md.qvel[2]) < 0.05
    return s1, s2, bool(ok)


def audit_trial(d, seg, step_s=0.10):
    """하강 창 100ms 표본 정적 감사 → 표본별 (t, q1, q2, â1, â2, s1, s2, ok)."""
    t = d["t"]
    idx = np.where(seg["desc"])[0]
    if len(idx) < 10:
        return []
    dt = float(np.median(np.diff(t)))
    stride = max(1, int(step_s / dt))
    rows = []
    for i in idx[::stride]:
        # 준정적 확인 (표본이 저속인지)
        if abs(d["dq1"][i]) > 0.6 or abs(d["dq2"][i]) > 0.9:
            continue
        s1, s2, ok = hold_torque(float(d["q1"][i]), float(d["q2"][i]))
        rows.append(dict(t=float(t[i]), q1=float(d["q1"][i]), q2=float(d["q2"][i]),
                         a1=float(d["a1"][i]), a2=float(d["a2"][i]),
                         s1=s1, s2=s2, ok=ok))
    return rows


def main():
    only = sys.argv[2] if len(sys.argv) > 2 else None
    reg = FD.registry()
    OUT = {}
    for s, p, g, cvt, ho in reg:
        if cvt:
            continue                     # 0429 정적감사는 CVT 러너 후 (크랭크≠무릎)
        if only and s != only:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            rows = audit_trial(d, seg)
        except Exception as ex:
            print(f"{s}/{p.name}: FAIL {type(ex).__name__} {ex}", flush=True)
            continue
        if not rows:
            print(f"{s}/{p.name}: 표본 없음", flush=True)
            continue
        r1 = np.array([r["a1"] - r["s1"] for r in rows if r["ok"]])
        r2 = np.array([r["a2"] - r["s2"] for r in rows if r["ok"]])
        OUT.setdefault(s, {})[p.name] = dict(rows=rows, ho=ho)
        print(f"{s}/{p.name}: 표본 {len(rows)} (수렴 {sum(r['ok'] for r in rows)}) | "
              f"잔차 r1 평균 {r1.mean():+.2f}±{r1.std():.2f} | r2 {r2.mean():+.2f}±{r2.std():.2f} Nm", flush=True)
    jp = HERE / "_fs_static_audit.json"
    safe.atomic_json_write(jp, OUT)
    # 세션 요약
    print("\n=== 세션 요약 (정적 잔차 실측−트윈 [Nm]) ===")
    for s, trials in OUT.items():
        rr1 = np.concatenate([[r["a1"] - r["s1"] for r in tr["rows"] if r["ok"]] for tr in trials.values()])
        rr2 = np.concatenate([[r["a2"] - r["s2"] for r in tr["rows"] if r["ok"]] for tr in trials.values()])
        print(f"{s}: r1 {rr1.mean():+.2f}±{rr1.std():.2f} | r2 {rr2.mean():+.2f}±{rr2.std():.2f} (n={len(rr1)})")
    print("done →", jp)


if __name__ == "__main__":
    main()
