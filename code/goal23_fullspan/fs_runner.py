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
    """fs 모델 + 정본 층 파라미터 캐시. FS_HIPM_DAMP/FL/ARM으로 hip_m 감쇠/마찰/관성 재검 (F30)."""
    arm = float(os.environ.get("FS_HIPM_ARM", str(arm)))
    bs = float(os.environ.get("FS_BS", str(bs)))
    dm = float(os.environ.get("FS_HIPM_DAMP", "0.312066"))
    fl = float(os.environ.get("FS_HIPM_FL", "0.238254"))
    key = (ks, bs, arm, dm, fl)
    if key not in _CACHE:
        if "base" not in _CACHE:
            base_xml, tw = FM.capture_base_xml()
            _CACHE["base"] = (base_xml, tw)
        base_xml, tw = _CACHE["base"]
        model, xml = FM.build_fs(ks=ks, bs=bs, arm=arm, base_xml=base_xml, dm=dm, fl=fl)
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



def _tau2s(d, k_lo=96.0, k_hi=323.0, tau0=9.0):
    """2단 스프링 토크 (처짐 d[rad] → Nm). d0=tau0/k_lo에서 연속."""
    d0 = tau0 / k_lo
    a = abs(d)
    t = k_lo * a if a <= d0 else tau0 + k_hi * (a - d0)
    return np.sign(d) * t


def rollout_cl_fs(ft, tg, qd1g, qd2g, dqd1g, dqd2g, gains, t_end, t_after=0.05, two_stage=False, bias1=0.0, knee_deep=None, fade=False, taulim=None):
    """CL 통짜 — settle 후 폴더 게인 PD(θ_m 기준, hip α 없음·knee α는 gains에 이미 반영)."""
    model = ft["model"]; P = ft["P"]
    law_a, law_b, law_v0 = ft["law"]; kr = ft["kr"]; sprm = ft["sprm"]
    iq, dof = ft["iq"], ft["dof"]
    A = P.A_PAPER
    kp1, kd1, kp2, kd2 = gains
    md, _, _ = _settle(ft, float(qd1g[0]), float(qd2g[0]))
    dt = model.opt.timestep
    tc_f = float(os.environ.get("FS_TC", "0.010"))
    s1f = 0.0
    af = dt / max(tc_f, dt)
    N = int(round((t_end + t_after) / dt))
    keys = ("t", "thm1", "q1", "q2", "dq1", "dq2", "s1", "s2", "defl", "bz", "tsp1", "s1f")
    Lg = {k: np.zeros(N) for k in keys}
    # F28b 하중 인식 간섭: N(t)=sim 발 접촉 수직력 / mg 스케일 (하강≈1 → 세션 적합 보존)
    load_on = os.environ.get("FS_KNEE_LOAD") == "1" and knee_deep
    if load_on:
        _fg = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
        _Nmg = float(model.body_mass.sum() * 9.81)
        _cf = np.zeros(6)
    for k in range(N):
        tc = k * dt
        tm_ = min(tc, t_end)
        qd1 = float(np.interp(tm_, tg, qd1g)); qd2 = float(np.interp(tm_, tg, qd2g))
        dqd1 = float(np.interp(tm_, tg, dqd1g)); dqd2 = float(np.interp(tm_, tg, dqd2g))
        thm = -md.qpos[iq["hip_m"]] - np.pi / 2
        q2c = -md.qpos[iq["knee_motor"]]
        v1c = -md.qvel[dof["hip_m"]]
        v2c = -md.qvel[dof["knee_motor"]]
        b_eff = 0.0
        if tc <= t_end:
            c1 = kp1 * (qd1 - thm) + kd1 * (dqd1 - v1c)
            c2 = kp2 * (qd2 - q2c) + kd2 * (dqd2 - v2c)
        else:
            c1 = c2 = 0.0
        c1 = float(np.clip(c1, -TW.R19.CLIP, TW.R19.CLIP))
        c2 = float(np.clip(c2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        if taulim is not None:
            s1 = float(np.clip(s1, -taulim, taulim))   # F26 진단: 세션 토크 상한 (실측 플래토 판독)
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = RU.spr_tau(float(md.qpos[iq["knee"]]), abs(s2), sprm) if sprm is not None else 0.0
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[dof["knee"]] = tql
        if two_stage or bias1:
            dq_s = float(md.qpos[iq["hip"]])
            corr = (FM.KS_HIP * dq_s - _tau2s(dq_s)) if two_stage else 0.0
            b_eff = bias1
            if fade and abs(v1c) > 1.0:
                b_eff = bias1 * max(0.0, 1.0 - (abs(v1c) - 1.0) / 2.0)
            md.qfrc_applied[dof["hip"]] = corr + b_eff
        if knee_deep:
            kd_, q20_ = knee_deep
            q2r = -float(md.qpos[iq["knee_motor"]])
            tau_ext = kd_ * max(0.0, q20_ - q2r)
            _rel = os.environ.get("FS_KNEE_REL")
            if _rel is not None and v2c > 0.2:
                tau_ext *= float(_rel)
            elif fade and v2c > 1.0:
                tau_ext *= max(0.0, 1.0 - (v2c - 1.0) / 2.0)
            if load_on:
                Nf = 0.0
                for ci in range(md.ncon):
                    _c = md.contact[ci]
                    if _c.geom1 == _fg or _c.geom2 == _fg:
                        mjm.mj_contactForce(model, md, ci, _cf)
                        Nf += abs(float(_cf[0]))
                tau_ext *= min(Nf / _Nmg, 3.0)
            md.qfrc_applied[dof["knee_motor"]] = -tau_ext
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
        Lg["tsp1"][k] = _tau2s(float(md.qpos[iq["hip"]])) + (b_eff if (two_stage or bias1) else 0.0)
        s1f += af * (s1 - s1f)
        Lg["s1f"][k] = s1f
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





def baseline_fs2():
    """fs 2단+세션 바이어스 (캘리브: 하강·복귀 정적 감사 → (r1d+r1u)/2, 채점 창 밖 = 무누수)."""
    import json
    import fs_data as FD
    import fs_metric as FMET
    ft = fs_twin()
    TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
    down = safe.read_json(HERE / "_fs_static_audit.json")
    up = safe.read_json(HERE / "_fs_updown.json")
    BIAS = {}
    for s in down:
        r1d = np.mean([r["a1"] - r["s1"] for tr in down[s].values() for r in tr["rows"] if r["ok"]])
        if s in up and up[s]:
            r1u = np.mean([v["r1_up"] for v in up[s].values()])
            BIAS[s] = float((r1d + r1u) / 2)
        else:
            BIAS[s] = float(r1d)
    print("세션 바이어스:", {k: round(v, 2) for k, v in BIAS.items()})
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
                              gm, seg["t_lo"] - d["t"][i0], two_stage=True, bias1=BIAS.get(s, 0.0))
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
    json.dump(OUT, open(HERE / "_fs_baseline_fs2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n=== fs2(2단+세션바이어스) 세션 요약 ===")
    for s, rows in OUT.items():
        a = np.mean(rows, axis=0)
        print(f"{s}: q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f} τ1 {a[4]:.2f} τ2 {a[5]:.2f}")
    print("done")





def modea_fs():
    """ModeA mshoot fs판 (0.4s 창·측정상태 리셋) — 양방향 심판의 나머지 절반. 세션 바이어스 동일 주입."""
    import json
    import fs_data as FD
    import fs_metric as FMET
    ft = fs_twin()
    down = safe.read_json(HERE / "_fs_static_audit.json")
    up = safe.read_json(HERE / "_fs_updown.json")
    BIAS = {}
    for s in down:
        r1d = np.mean([r["a1"] - r["s1"] for tr in down[s].values() for r in tr["rows"] if r["ok"]])
        r1u = np.mean([v["r1_up"] for v in up[s].values()]) if s in up and up[s] else r1d
        BIAS[s] = float((r1d + r1u) / 2)
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
        except Exception:
            continue
        t = d["t"]
        rows = []
        w0 = seg["t_desc"]
        while w0 + 0.05 < seg["t_lo"]:
            wl = min(0.4, seg["t_lo"] - w0)
            m = (t >= w0) & (t <= w0 + wl)
            if m.sum() < 20:
                w0 += 0.3
                continue
            i0 = int(np.argmax(m))
            tg = t[m] - w0
            L = rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                                float(d["q1"][i0]), float(d["q2"][i0]),
                                float(d["dq1"][i0]), float(d["dq2"][i0]),
                                float(tg[-1] - 0.004), bias1=BIAS.get(s, 0.0))
            if L is None:
                w0 += 0.3
                continue
            gi = lambda k: np.interp(tg, L["t"], L[k])
            mm = tg >= 0.02
            r = FMET._rmse6({k: d[k][m] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}, mm,
                            gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"), gi("s1"), gi("s2"))
            rows.append(r)
            w0 += 0.3
        if rows:
            a = np.mean(rows, axis=0)
            OUT.setdefault(s, []).append(list(a))
            print(f"{s}/{p.name}: MA q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f}", flush=True)
    json.dump(OUT, open(HERE / "_fs_modea_fs2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n=== fs2 ModeA 세션 요약 ===")
    for s, rows in OUT.items():
        a = np.mean(rows, axis=0)
        print(f"{s}: q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f} τ1 {a[4]:.2f} τ2 {a[5]:.2f}")
    print("done")


def rollout_ol_fs_b(ft, tg, raw1g, raw2g, q1_0, q2_0, dq1_0, dq2_0, t_end, t_after=0.004, bias1=0.0, knee_deep=None, fade=False, bz_floor=None, knee_rel=None):
    """rollout_ol_fs + 2단·바이어스 qfrc (mshoot용 래퍼 — 별도 구현 유지로 원본 무변경)."""
    model = ft["model"]; P = ft["P"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = ft["law"]; kr = ft["kr"]; sprm = ft["sprm"]
    iq, dof = ft["iq"], ft["dof"]
    A = P.A_PAPER
    md = mjm.MjData(model)
    r1_0 = float(np.interp(0.0, tg, raw1g))
    s1_0 = float(P.J.ahat(A, np.array([np.clip(r1_0, -TW.R19.CLIP, TW.R19.CLIP)]), np.array([float(dq1_0)]))[0])
    defl0 = np.clip(np.sign(s1_0) * (abs(s1_0) / 96.0 if abs(s1_0) <= 9 else 9 / 96.0 + (abs(s1_0) - 9) / 323.0), -0.3, 0.3)
    md.qpos[iq["hip_m"]] = -q1_0 - np.pi / 2 - defl0
    md.qpos[iq["hip"]] = defl0
    md.qpos[iq["knee_motor"]] = -q2_0
    md.qpos[iq["cpin"]] = q2_0
    md.qpos[iq["knee"]] = -q2_0
    md.qpos[iq["base_z"]] = 1.0
    mjm.mj_forward(model, md)
    fg = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[iq["base_z"]] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    if bz_floor is not None:
        md.qpos[iq["base_z"]] = max(float(md.qpos[iq["base_z"]]), bz_floor)   # 엔드스톱 위 초기화 (착좌)
    Lseg = 0.25
    c1_, c12 = np.cos(q1_0), np.cos(q1_0 + q2_0)
    dbz = -Lseg * (c1_ * dq1_0 + c12 * (dq1_0 + dq2_0))
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
    load_on = os.environ.get("FS_KNEE_LOAD") == "1" and knee_deep
    if load_on:
        _Nmg = float(model.body_mass.sum() * 9.81)
        _cf = np.zeros(6)
    for k in range(N):
        tc = k * dt
        v1c = -md.qvel[dof["hip_m"]]
        v2c = -md.qvel[dof["knee_motor"]]
        r1 = float(np.interp(tc, tg, raw1g)) if tc <= t_end else 0.0
        r2 = float(np.interp(tc, tg, raw2g)) if tc <= t_end else 0.0
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
        dq_s = float(md.qpos[iq["hip"]])
        b_eff = bias1
        if fade and abs(v1c) > 1.0:
            b_eff = bias1 * max(0.0, 1.0 - (abs(v1c) - 1.0) / 2.0)   # 저속 전용 (마찰성 가설)
        md.qfrc_applied[dof["hip"]] = (FM.KS_HIP * dq_s - _tau2s(dq_s)) + b_eff
        if knee_deep:
            kd_, q20_ = knee_deep
            q2r = -float(md.qpos[iq["knee_motor"]])
            tau_ext = kd_ * max(0.0, q20_ - q2r)     # 로봇 좌표 신전(+) 방향 받침
            _rel = knee_rel if knee_rel is not None else (float(os.environ["FS_KNEE_REL"]) if "FS_KNEE_REL" in os.environ else None)
            if _rel is not None:
                if v2c > 0.2:
                    tau_ext *= _rel                                   # 방출 분율 (부분 소산 모델)
            elif fade and v2c > 1.0:
                tau_ext *= max(0.0, 1.0 - (v2c - 1.0) / 2.0)         # 고속 신전 시 소산 (방출 무반환)
            if load_on:
                Nf = 0.0
                for ci in range(md.ncon):
                    _c = md.contact[ci]
                    if _c.geom1 == fg or _c.geom2 == fg:
                        mjm.mj_contactForce(model, md, ci, _cf)
                        Nf += abs(float(_cf[0]))
                tau_ext *= min(Nf / _Nmg, 3.0)
            md.qfrc_applied[dof["knee_motor"]] = -tau_ext
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

def fit_knee_deep():
    """세션별 (q2_0, k_d) 적합 — 하강 창(깊은 부분)만 사용 (규칙 4). HO 0324 포함(자체 캘리브 관찰용)."""
    import json
    import fs_data as FD
    down = safe.read_json(HERE / "_fs_static_audit.json")
    up = safe.read_json(HERE / "_fs_updown.json")
    def bias_of(s):
        r1d = np.mean([r["a1"] - r["s1"] for tr in down[s].values() for r in tr["rows"] if r["ok"]])
        r1u = np.mean([v["r1_up"] for v in up[s].values()]) if s in up and up[s] else r1d
        return float((r1d + r1u) / 2)
    ft = fs_twin()
    FIT = {}
    for s, base in FD.SESS_FIT.items():
        if s in FD.CVT_SESS:
            continue
        trials = FD.trials_of(base)[:2]     # 세션당 2 trial로 적합 (속도)
        b = bias_of(s) if s in down else 0.0
        def deep_err(knee_deep):
            errs = []
            for p in trials:
                d = FD.load2(p); seg = FD.segment(d); t = d["t"]
                w0 = seg["t_desc"]
                while w0 + 0.05 < seg["t_lo"]:
                    wl = min(0.4, seg["t_lo"] - w0)
                    m = (t >= w0) & (t <= w0 + wl)
                    if m.sum() < 20:
                        w0 += 0.3
                        continue
                    if np.degrees(np.mean(d["q2"][m])) > -125:
                        w0 += 0.3
                        continue
                    i0 = int(np.argmax(m)); tg = t[m] - w0
                    L = rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                                        float(d["q1"][i0]), float(d["q2"][i0]),
                                        float(d["dq1"][i0]), float(d["dq2"][i0]),
                                        float(tg[-1] - 0.004), bias1=b, knee_deep=knee_deep)
                    if L is not None:
                        mm = tg >= 0.02
                        q2s = np.interp(tg, L["t"], L[k]) if (k := "q2") else None
                        errs.append(np.degrees(np.sqrt(np.mean((d["q2"][m][mm] - q2s[mm]) ** 2))))
                    w0 += 0.3
            return float(np.mean(errs)) if errs else None
        e0 = deep_err(None)
        if e0 is None:
            print(f"{s}: 깊은 창 없음 — 요소 불필요", flush=True)
            FIT[s] = None
            continue
        best = (e0, None)
        for q20 in (-2.20, -2.27, -2.36, -2.44):
            for kd in (2.5, 5.0, 10.0, 20.0):
                e = deep_err((kd, q20))
                if e is not None and e < best[0]:
                    best = (e, (kd, q20))
        FIT[s] = dict(err0=round(e0, 2), err=round(best[0], 2),
                      kd=best[1][0] if best[1] else 0.0,
                      q20_deg=round(float(np.degrees(best[1][1])), 1) if best[1] else None)
        print(f"{s}: {e0:.2f}° → {best[0]:.2f}° (k_d {FIT[s]['kd']}, 결합 {FIT[s]['q20_deg']}°)", flush=True)
    import json as _j
    safe.atomic_json_write(HERE / "_fs_knee_deep.json", FIT)
    print("done")
def _sess_params():
    import fs_data as FD
    down = safe.read_json(HERE / "_fs_static_audit.json")
    up = safe.read_json(HERE / "_fs_updown.json")
    kd = safe.read_json(HERE / "_fs_knee_deep.json")
    P = {}
    for s in list(down.keys()) + ["26.07.25"]:
        if s in P:
            continue
        r1d = np.mean([r["a1"] - r["s1"] for tr in down[s].values() for r in tr["rows"] if r["ok"]]) if s in down else 0.0
        r1u = np.mean([v["r1_up"] for v in up[s].values()]) if s in up and up[s] else r1d
        b = float((r1d + r1u) / 2)
        k = kd.get(s)
        knee = (float(k["kd"]), float(np.radians(k["q20_deg"]))) if (k and k.get("kd")) else None
        P[s] = dict(bias1=b, knee_deep=knee)
    # 0429 CVT: fs_calib_cvt 감사 (복귀 표본 없음 → 하강 단독; 크랭크 잔차 +0.08≈0라 knee_deep 없음)
    cvt_p = HERE / "_fs_cvt_audit.json"
    if cvt_p.exists():
        cv = safe.read_json(cvt_p)
        rr = [r["a1"] - r["s1"] for tr in cv.values() for r in tr["down"] if r["ok"]]
        if rr:
            P["26.04.29"] = dict(bias1=float(np.mean(rr)), knee_deep=None)
    return P


def baseline_fs3():
    import json
    import fs_data as FD
    import fs_metric as FMET
    ft = fs_twin()
    TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
    SP = _sess_params()
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt or ho or not g:
            continue
        sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
        tl_ = None
        _tlm = os.environ.get("FS_TAULIM")
        if _tlm == "1":
            _tj = HERE / "_fs_taulim.json"
            if _tj.exists():
                _te = safe.read_json(_tj).get(s)
                tl_ = float(_te["lim"]) if (_te and _te.get("active")) else None
        elif _tlm in ("2", "3"):              # F26 재공략: trial 입자도 (진단 — 판독원=푸시 창)
            _tj = HERE / "_fs_taulim_trial.json"
            if _tj.exists():
                _te = safe.read_json(_tj).get(f"{s}/{p.name}")
                tl_ = float(_te["lim"]) if (_te and _te.get("active")) else None
        obs_lim = tl_ if _tlm == "3" else None
        if _tlm == "3":
            tl_ = None                        # 3 = 관측 전용 클립 (동역학 무손 — F30 트레이드오프 해소 시도)
        try:
            d = FD.load2(p); seg = FD.segment(d)
            gm = (g[0], g[1], g[2] * TK.get(g[2], 0.656), g[3] * 0.20)
            i0 = max(0, seg["i_desc"] - 5)
            t = d["t"][i0:] - d["t"][i0]
            L = rollout_cl_fs(ft, t, d["qd1"][i0:], d["qd2"][i0:], d["dqd1"][i0:], d["dqd2"][i0:],
                              gm, seg["t_lo"] - d["t"][i0], two_stage=True,
                              bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                              fade=os.environ.get("FS_FADE") == "1", taulim=tl_)
            if L is None:
                continue
            gi = lambda k: np.interp(t, L["t"], L[k])
            for wn in ("score", "push"):
                m = seg[wn][i0:][: len(t)]
                _to = os.environ.get("FS_TAUOBS")
                if _to == "sess":
                    _wj = HERE / "_fs_tauobs_w.json"
                    _w = float(safe.read_json(_wj).get(s, 0.5)) if _wj.exists() else 0.5
                    t1obs = _w * gi("s1f") + (1 - _w) * gi("tsp1")
                    if obs_lim is not None:
                        t1obs = np.clip(t1obs, -obs_lim, obs_lim)
                else:
                    t1obs = (gi("tsp1") if _to == "spr" else
                             gi("s1f") if _to == "lpf" else
                             0.5 * gi("s1f") + 0.5 * gi("tsp1") if _to == "blend" else gi("s1"))
                r = FMET._rmse6({k: d[k][i0:] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}, m,
                                gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"), t1obs, gi("s2"))
                OUT.setdefault(s, {}).setdefault(wn, []).append(list(r))
            print(f"{s}/{p.name}: OK", flush=True)
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__}", flush=True)
    json.dump(OUT, open(HERE / "_fs3_cl.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for wn in ("score", "push"):
        print(f"\n=== fs3 CL {wn} 창 세션 요약 ===")
        for s, d_ in OUT.items():
            a = np.mean(d_[wn], axis=0)
            print(f"{s}: q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f} τ1 {a[4]:.2f} τ2 {a[5]:.2f}")
    print("done")


def modea_fs3():
    import json
    import fs_data as FD
    import fs_metric as FMET
    ft = fs_twin()
    SP = _sess_params()
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
        try:
            d = FD.load2(p); seg = FD.segment(d)
        except Exception:
            continue
        t = d["t"]
        rows = []
        w0 = seg["t_desc"]
        while w0 + 0.05 < seg["t_lo"]:
            wl = min(0.4, seg["t_lo"] - w0)
            m = (t >= w0) & (t <= w0 + wl)
            if m.sum() < 20:
                w0 += 0.3
                continue
            i0 = int(np.argmax(m)); tg = t[m] - w0
            L = rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                                float(d["q1"][i0]), float(d["q2"][i0]),
                                float(d["dq1"][i0]), float(d["dq2"][i0]),
                                float(tg[-1] - 0.004), bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                                fade=os.environ.get("FS_FADE") == "1")
            if L is None:
                w0 += 0.3
                continue
            gi = lambda k: np.interp(tg, L["t"], L[k])
            mm = tg >= 0.02
            rows.append(FMET._rmse6({k: d[k][m] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}, mm,
                                    gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"), gi("s1"), gi("s2")))
            w0 += 0.3
        if rows:
            OUT.setdefault(s, []).append(list(np.mean(rows, axis=0)))
            print(f"{s}/{p.name}: OK", flush=True)
    json.dump(OUT, open(HERE / "_fs3_ma.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n=== fs3 ModeA 세션 요약 ===")
    for s, rows in OUT.items():
        a = np.mean(rows, axis=0)
        print(f"{s}: q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f} τ1 {a[4]:.2f} τ2 {a[5]:.2f}")
    print("done")

def tauobs_compare():
    """τ1 관측 4안 동시 채점 (푸시 창) — 한 패스: s1 / lpf10(s1f) / 스프링측(tsp1) / 블렌드 0.5."""
    import fs_data as FD
    ft = fs_twin()
    TKK = np.array([60, 120, 250, 500]); TKV = np.array([0.85, 0.789, 0.656, 0.40])
    SP = _sess_params()
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt or ho or not g or s == "26.04.21":
            continue
        sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
        try:
            d = FD.load2(p); seg = FD.segment(d)
            gm = (g[0], g[1], g[2] * float(np.interp(g[2], TKK, TKV)) if False else g[2] * {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}.get(g[2], 0.656), g[3] * 0.20)
            gm = (g[0], g[1], gm[2], gm[3])
            i0 = max(0, seg["i_desc"] - 5)
            t = d["t"][i0:] - d["t"][i0]
            L = rollout_cl_fs(ft, t, d["qd1"][i0:], d["qd2"][i0:], d["dqd1"][i0:], d["dqd2"][i0:],
                              gm, seg["t_lo"] - d["t"][i0], two_stage=True,
                              bias1=sp["bias1"], knee_deep=sp["knee_deep"], fade=True)
            if L is None:
                continue
            m = seg["push"][i0:][: len(t)]
            a1 = d["a1"][i0:][: len(t)]
            res = {}
            for nm, key in (("s1", "s1"), ("lpf", "s1f"), ("spr", "tsp1")):
                o = np.interp(t, L["t"], L[key])
                res[nm] = float(np.sqrt(np.mean((a1[m] - o[m]) ** 2)))
            ob = 0.5 * np.interp(t, L["t"], L["s1f"]) + 0.5 * np.interp(t, L["t"], L["tsp1"])
            res["blend"] = float(np.sqrt(np.mean((a1[m] - ob[m]) ** 2)))
            # 게인 인식 (trial 입자도): 전류루프 지연 관점 — 저게인(60)=스프링측, 고게인(120+)=lpf10
            w = float(np.clip((g[0] - 60.0) / 60.0, 0.0, 1.0))
            og = w * np.interp(t, L["t"], L["s1f"]) + (1 - w) * np.interp(t, L["t"], L["tsp1"])
            res["gain"] = float(np.sqrt(np.mean((a1[m] - og[m]) ** 2)))
            OUT.setdefault(s, []).append(res)
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__}", flush=True)
    print("\n=== 푸시 τ1 관측 5안 (세션 평균) ===")
    tot = {k: [] for k in ("s1", "lpf", "spr", "blend", "gain")}
    for s, rows in OUT.items():
        a = {k: float(np.mean([r[k] for r in rows])) for k in tot}
        for k in tot:
            tot[k].append(a[k])
        print(f"{s}: s1 {a['s1']:.2f} | lpf10 {a['lpf']:.2f} | spr {a['spr']:.2f} | blend {a['blend']:.2f} | gain {a['gain']:.2f}")
    print("전체 평균: " + " | ".join(f"{k} {np.mean(v):.2f}" for k, v in tot.items()))
    print("done")


def tauobs_desc():
    """관측 블렌드 w의 세션 상수화 판별: 하강 창에서 w* 캘리브 → 푸시 제로샷 평가.
    w=0(스프링측)~1(lpf10) 11단계. 누수 없음 (w 선정에 푸시 창 미사용). 오라클 병기."""
    import fs_data as FD
    ft = fs_twin()
    SP = _sess_params()
    W = np.linspace(0, 1, 11)
    ACC = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt or ho or not g or s == "26.04.21":
            continue
        sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
        try:
            d = FD.load2(p); seg = FD.segment(d)
            gm = (g[0], g[1], g[2] * {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}.get(g[2], 0.656), g[3] * 0.20)
            i0 = max(0, seg["i_desc"] - 5)
            t = d["t"][i0:] - d["t"][i0]
            L = rollout_cl_fs(ft, t, d["qd1"][i0:], d["qd2"][i0:], d["dqd1"][i0:], d["dqd2"][i0:],
                              gm, seg["t_lo"] - d["t"][i0], two_stage=True,
                              bias1=sp["bias1"], knee_deep=sp["knee_deep"], fade=True)
            if L is None:
                continue
            a1 = d["a1"][i0:][: len(t)]
            lp = np.interp(t, L["t"], L["s1f"]); tp = np.interp(t, L["t"], L["tsp1"])
            row = {}
            for wn in ("desc", "push"):
                m = seg[wn][i0:][: len(t)]
                row[wn] = [float(np.sqrt(np.mean((a1[m] - (w * lp + (1 - w) * tp)[m]) ** 2))) for w in W]
            ACC.setdefault(s, []).append(row)
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__}", flush=True)
    print("\n=== 관측 w 세션 상수화: 하강 캘리브 → 푸시 제로샷 (τ1 RMSE) ===")
    zs, bl, orc, WS = [], [], [], {}
    for s, rows in ACC.items():
        dmean = np.mean([r["desc"] for r in rows], axis=0)
        pmean = np.mean([r["push"] for r in rows], axis=0)
        iw = int(np.argmin(dmean)); io = int(np.argmin(pmean))
        zs.append(pmean[iw]); bl.append(pmean[5]); orc.append(pmean[io])
        WS[s] = float(W[iw])
        print(f"{s}: w*_desc={W[iw]:.1f} → 푸시 {pmean[iw]:.2f} | blend0.5 {pmean[5]:.2f} | "
              f"오라클 w={W[io]:.1f} {pmean[io]:.2f}", flush=True)
    print(f"전체: 제로샷 {np.mean(zs):.2f} | blend0.5 {np.mean(bl):.2f} | 오라클 {np.mean(orc):.2f}")
    safe.atomic_json_write(HERE / "_fs_tauobs_w.json", WS)
    print("done → _fs_tauobs_w.json")

if __name__ == "__main__":
    import sys as _s
    a = _s.argv[1] if len(_s.argv) > 1 else ""
    if a == "baseline":
        golden_g5(); baseline_fs()
    elif a == "baseline2":
        baseline_fs2()
    elif a == "modea":
        modea_fs()
    elif a == "kneedeep":
        fit_knee_deep()
    elif a == "tauobs":
        tauobs_compare()
    elif a == "tauobs2":
        tauobs_desc()
    elif a == "fs3":
        baseline_fs3(); modea_fs3()
    else:
        golden_g5()
