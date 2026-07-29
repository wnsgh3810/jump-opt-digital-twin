# -*- coding: utf-8 -*-
"""fs_runner — 내장 스프링 모델(fs_model)용 CL/ModeA 러너 (이름 기반 어드레싱).

CL: 폴더 게인 PD가 인코더(θ_m=hip_m)에 작용 — hip α 없음 (스프링 창발), knee는 OLD α.
    커맨드층 미러: raw PD → 클립(CLIP=35.5) → a_hat(Paper) → 축토크 + 지지법칙/무릎 스프링층.
ModeA: 측정 raw 주입 (hip_m/knee_motor), 동일 플랜트.
τ1 채점 대응물 = s1(모터 축토크, 전류센서 아날로그 — 내장 스프링에선 과도역 포함해 이것이 정답).
v1 스프링 = XML 선형 k150 (H10: 140~200 평탄대역). 2단 보정은 후속 축.
골든: G5 등가성 — 온건역(27일)에서 변형 C CL과 비교.
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
for _p in ("p25_task0", "p25_deploy", "p23_veins", "p19_jump", "p18_cvt"):
    sys.path.insert(0, str(HERE.parent / "goal22" / _p))
import p25_a_twin as TW          # noqa: E402
import safe                      # noqa: E402
import mujoco as mjm             # noqa: E402
import fs_model as FM            # noqa: E402

RU = TW.RU
_CACHE = {}


def fs_twin(ks=FM.KS_HIP, bs=FM.BS_HIP, arm=FM.ARM_HIP):
    """fs 모델 + 정본 층 파라미터 캐시."""
    key = (ks, bs, arm)
    if key not in _CACHE:
        if "base" not in _CACHE:
            base_xml, tw = FM.capture_base_xml()
            _CACHE["base"] = (base_xml, tw)
        base_xml, tw = _CACHE["base"]
        model, xml = FM.build_fs(ks=ks, bs=bs, arm=arm, base_xml=base_xml)
        iq = {n: safe.qadr(model, n, mjm) for n in
              ("base_z", "hip_m", "hip", "knee_motor", "cpin", "knee")}
        dof = {n: safe.dofadr(model, n, mjm) for n in iq}
        _CACHE[key] = dict(model=model, xml=xml, tw=tw, iq=iq, dof=dof,
                           P=tw["P"], law=tw["law"], kr=tw["kr"], sprm=tw["sprm"])
    return _CACHE[key]


def _settle(ft, q1_0, q2_0, t_settle=None):
    """settle (cl_run23 settle 블록 미러 — PD는 hip_m 인코더에)."""
    model = ft["model"]; P = ft["P"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = ft["law"]; kr = ft["kr"]; sprm = ft["sprm"]
    iq, dof = ft["iq"], ft["dof"]
    A = P.A_PAPER
    md = mjm.MjData(model)
    md.qpos[iq["base_z"]] = 1.0
    md.qpos[iq["hip_m"]] = -q1_0 - np.pi / 2
    md.qpos[iq["hip"]] = 0.0
    md.qpos[iq["knee_motor"]] = -q2_0
    md.qpos[iq["cpin"]] = q2_0
    md.qpos[iq["knee"]] = -q2_0
    mjm.mj_forward(model, md)
    fg = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[iq["base_z"]] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mjm.mj_forward(model, md)
    dt = model.opt.timestep
    Ns = int(round((t_settle or P.J.T_SETTLE) / dt))
    c1f = c2f = 0.0
    for k in range(Ns):
        thm = -md.qpos[iq["hip_m"]] - np.pi / 2
        q2c = -md.qpos[iq["knee_motor"]]
        v1c = -md.qvel[dof["hip_m"]]
        v2c = -md.qvel[dof["knee_motor"]]
        c1 = S.SETTLE_KP * (q1_0 - thm) - S.SETTLE_KD * v1c
        c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
        c1f, c2f = c1, c2
        c1 = float(np.clip(c1, -TW.R19.CLIP, TW.R19.CLIP))
        c2 = float(np.clip(c2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = RU.spr_tau(float(md.qpos[iq["knee"]]), abs(s2), sprm) if sprm is not None else 0.0
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[dof["knee"]] = tql
        mjm.mj_step(model, md)
    return md, c1f, c2f


def rollout_cl_fs(ft, tg, qd1g, qd2g, dqd1g, dqd2g, gains, t_end, t_after=0.05):
    """CL 통짜 — settle 후 폴더 게인 PD(θ_m 기준, hip α 없음·knee α는 gains에 이미 반영)."""
    model = ft["model"]; P = ft["P"]
    law_a, law_b, law_v0 = ft["law"]; kr = ft["kr"]; sprm = ft["sprm"]
    iq, dof = ft["iq"], ft["dof"]
    A = P.A_PAPER
    kp1, kd1, kp2, kd2 = gains
    md, _, _ = _settle(ft, float(qd1g[0]), float(qd2g[0]))
    dt = model.opt.timestep
    N = int(round((t_end + t_after) / dt))
    keys = ("t", "thm1", "q1", "q2", "dq1", "dq2", "s1", "s2", "defl", "bz")
    Lg = {k: np.zeros(N) for k in keys}
    for k in range(N):
        tc = k * dt
        tm_ = min(tc, t_end)
        qd1 = float(np.interp(tm_, tg, qd1g)); qd2 = float(np.interp(tm_, tg, qd2g))
        dqd1 = float(np.interp(tm_, tg, dqd1g)); dqd2 = float(np.interp(tm_, tg, dqd2g))
        thm = -md.qpos[iq["hip_m"]] - np.pi / 2
        q2c = -md.qpos[iq["knee_motor"]]
        v1c = -md.qvel[dof["hip_m"]]
        v2c = -md.qvel[dof["knee_motor"]]
        if tc <= t_end:
            c1 = kp1 * (qd1 - thm) + kd1 * (dqd1 - v1c)
            c2 = kp2 * (qd2 - q2c) + kd2 * (dqd2 - v2c)
        else:
            c1 = c2 = 0.0
        c1 = float(np.clip(c1, -TW.R19.CLIP, TW.R19.CLIP))
        c2 = float(np.clip(c2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = RU.spr_tau(float(md.qpos[iq["knee"]]), abs(s2), sprm) if sprm is not None else 0.0
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[dof["knee"]] = tql
        mjm.mj_step(model, md)
        if not np.isfinite(md.qpos).all():
            return None
        Lg["t"][k] = tc
        Lg["thm1"][k] = -md.qpos[iq["hip_m"]] - np.pi / 2
        Lg["q1"][k] = -(md.qpos[iq["hip_m"]] + md.qpos[iq["hip"]]) - np.pi / 2
        Lg["q2"][k] = -md.qpos[iq["knee_motor"]]
        Lg["dq1"][k] = -md.qvel[dof["hip_m"]]
        Lg["dq2"][k] = -md.qvel[dof["knee_motor"]]
        Lg["s1"][k] = s1
        Lg["s2"][k] = s2
        Lg["defl"][k] = md.qpos[iq["hip"]]
        Lg["bz"][k] = md.qpos[iq["base_z"]]
    return Lg


def rollout_ol_fs(ft, tg, raw1g, raw2g, q1_0, q2_0, dq1_0, dq2_0, t_end, t_after=0.05):
    """ModeA — 측정 raw 주입 (mshoot 창용: 측정상태 초기화, 스프링 처짐은 정적 τ/k로 시드)."""
    model = ft["model"]; P = ft["P"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = ft["law"]; kr = ft["kr"]; sprm = ft["sprm"]
    iq, dof = ft["iq"], ft["dof"]
    A = P.A_PAPER
    md = mjm.MjData(model)
    r1_0 = float(np.interp(0.0, tg, raw1g))
    v1_0 = float(dq1_0)
    s1_0 = float(P.J.ahat(A, np.array([np.clip(r1_0, -TW.R19.CLIP, TW.R19.CLIP)]), np.array([v1_0]))[0])
    defl0 = np.clip(s1_0 / FM.KS_HIP, -0.3, 0.3)
    md.qpos[iq["hip_m"]] = -q1_0 - np.pi / 2 - defl0
    md.qpos[iq["hip"]] = defl0
    md.qpos[iq["knee_motor"]] = -q2_0
    md.qpos[iq["cpin"]] = q2_0
    md.qpos[iq["knee"]] = -q2_0
    md.qpos[iq["base_z"]] = 1.0
    mjm.mj_forward(model, md)
    fg = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[iq["base_z"]] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    L = 0.25
    c1, c12 = np.cos(q1_0), np.cos(q1_0 + q2_0)
    dbz = -L * (c1 * dq1_0 + c12 * (dq1_0 + dq2_0))
    md.qvel[:] = 0
    md.qvel[dof["base_z"]] = dbz
    md.qvel[dof["hip_m"]] = -dq1_0
    md.qvel[dof["knee_motor"]] = -dq2_0
    md.qvel[dof["cpin"]] = dq2_0
    md.qvel[dof["knee"]] = -dq2_0
    mjm.mj_forward(model, md)
    dt = model.opt.timestep
    N = int(round((t_end + t_after) / dt))
    keys = ("t", "thm1", "q1", "q2", "dq1", "dq2", "s1", "s2")
    Lg = {k: np.zeros(N) for k in keys}
    for k in range(N):
        tc = k * dt
        v1c = -md.qvel[dof["hip_m"]]
        v2c = -md.qvel[dof["knee_motor"]]
        if tc <= t_end:
            r1 = float(np.interp(tc, tg, raw1g)); r2 = float(np.interp(tc, tg, raw2g))
        else:
            r1 = r2 = 0.0
        r1 = float(np.clip(r1, -TW.R19.CLIP, TW.R19.CLIP))
        r2 = float(np.clip(r2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([r1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([r2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = RU.spr_tau(float(md.qpos[iq["knee"]]), abs(s2), sprm) if sprm is not None else 0.0
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[dof["knee"]] = tql
        mjm.mj_step(model, md)
        if not np.isfinite(md.qpos).all():
            return None
        Lg["t"][k] = tc
        Lg["thm1"][k] = -md.qpos[iq["hip_m"]] - np.pi / 2
        Lg["q1"][k] = -(md.qpos[iq["hip_m"]] + md.qpos[iq["hip"]]) - np.pi / 2
        Lg["q2"][k] = -md.qpos[iq["knee_motor"]]
        Lg["dq1"][k] = -md.qvel[dof["hip_m"]]
        Lg["dq2"][k] = -md.qvel[dof["knee_motor"]]
        Lg["s1"][k] = s1
        Lg["s2"][k] = s2
    return Lg


def golden_g5():
    """G5 등가성: 온건역(27일 150 trial) CL — fs(k150) vs 변형 C 기록치 vs 실측."""
    import fs_data as FD
    import fs_metric as FMET
    ft = fs_twin()
    d = FD.load2(FD.SESS_FIT["26.07.27"] / "150_2.2_250_3")
    seg = FD.segment(d)
    TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
    g = (150.0, 2.2, 250.0 * TK[250], 3.0 * 0.20)
    i0 = max(0, seg["i_desc"] - 5)
    t = d["t"][i0:] - d["t"][i0]
    t_end = seg["t_lo"] - d["t"][i0]
    L = rollout_cl_fs(ft, t, d["qd1"][i0:], d["qd2"][i0:], d["dqd1"][i0:], d["dqd2"][i0:], g, t_end)
    if L is None:
        print("G5: 발산!")
        return False
    m = seg["score"][i0:][: len(t)]
    gi = lambda k: np.interp(t, L["t"], L[k])
    r = FMET._rmse6({k: d[k][i0:] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}, m,
                    gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"), gi("s1"), gi("s2"))
    print(f"G5 fs(k150) 전구간: q1 {r[0]:.2f}° q2 {r[1]:.2f}° dq1 {r[2]:.2f} dq2 {r[3]:.2f} τ1 {r[4]:.2f} τ2 {r[5]:.2f}")
    print("   변형 C 기록치     : q1 0.87° q2 0.81° dq1 0.22 dq2 0.25 τ1 1.19 τ2 0.63 (베이스라인 JSON)")
    ok = r[0] < 1.5 and r[4] < 2.5
    print("G5", "근접" if ok else "괴리 — 진단 필요")
    return ok


if __name__ == "__main__":
    import sys as _s
    if len(_s.argv) > 1 and _s.argv[1] == "baseline":
        golden_g5()
        baseline_fs()
    else:
        golden_g5()


def baseline_fs():
    """fs(k150) CL 전 trial 채점 — 비CVT fit 세션 (베이스라인 대조용)."""
    import json
    import fs_data as FD
    import fs_metric as FMET
    ft = fs_twin()
    TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt or ho or not g:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            gm = (g[0], g[1], g[2] * TK.get(g[2], 0.656), g[3] * 0.20)
            i0 = max(0, seg["i_desc"] - 5)
            t = d["t"][i0:] - d["t"][i0]
            L = rollout_cl_fs(ft, t, d["qd1"][i0:], d["qd2"][i0:], d["dqd1"][i0:], d["dqd2"][i0:],
                              gm, seg["t_lo"] - d["t"][i0])
            if L is None:
                print(f"{s}/{p.name}: 발산", flush=True)
                continue
            m = seg["score"][i0:][: len(t)]
            gi = lambda k: np.interp(t, L["t"], L[k])
            r = FMET._rmse6({k: d[k][i0:] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}, m,
                            gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"), gi("s1"), gi("s2"))
            OUT.setdefault(s, []).append(list(r))
            print(f"{s}/{p.name}: q1 {r[0]:.2f} q2 {r[1]:.2f} dq1 {r[2]:.2f} dq2 {r[3]:.2f} τ1 {r[4]:.2f} τ2 {r[5]:.2f}", flush=True)
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__} {ex}", flush=True)
    json.dump(OUT, open(HERE / "_fs_baseline_fsmodel.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n=== fs(k150) 세션 요약 ===")
    for s, rows in OUT.items():
        a = np.mean(rows, axis=0)
        print(f"{s}: q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f} τ1 {a[4]:.2f} τ2 {a[5]:.2f}")
    print("done")
