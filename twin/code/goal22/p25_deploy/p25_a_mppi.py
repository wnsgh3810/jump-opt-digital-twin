# -*- coding: utf-8 -*-
"""p25_a_mppi — P25 Phase A (ii): MPPI (개루프 재계획 토크).

표준 MPPI (가중 = exp(−(J−J_min)/λ), 제어비용항 없는 순수 보상 가중 변형):
  · 제어 그리드 10 ms (dt=0.5 ms → 20 서브스텝) — 커맨드 창 [0, 0.6] s = 60 스텝.
  · 매 10 ms 재계획: horizon-to-go K = min(40, 남은 스텝) (0.4 s 룩어헤드),
    샘플 S개 iid 가우시안 노이즈 (σ=6.0 raw), 각 샘플을 트윈으로 롤아웃.
  · 샘플 코스트 = −(탄도 apex 추정 bz_T + max(vz_T,0)²/2g) + PEN_W·포락선 위반
    (crash → CRASH_F). 종단 추정이 유효한 이유: 커맨드 종료 후 물리는 수동 —
    이지 후 apex는 상태만으로 결정 (레일 1-DOF 베이스).
  · 실행 롤아웃 = 연속 단일 MjData (샘플은 별도 MjData에 상태 복사 — qpos/qvel
    + tm 필터 상태 c1f/c2f까지 상태로 취급). 0.6 s 후 비행은 a_full23 규약.
  · 커맨드 체인/플랜트 층 = rollout_ol과 동일 지점 미러 (tm 필터 → 클립 ±35.5 →
    ahat → supp+rise/게이트 스프링/힙 지지).
온도 λ: S=128 파일럿 {0.3, 1.0, 3.0} 실행 apex 비교 → 최선 λ로 S=256 본판.
시드 노미널 = 0602 측정 raw 푸시 (CMA (i)와 동일 정렬).

산출: p25_a_mppi.npz (공통 스키마 + U 노미널) + p25_a_res_mppi.json.
"""
import p25_a_twin as TW          # env 플래그는 TW import가 설정

import time
from pathlib import Path

import numpy as np

import p23_v6_runners as RU      # TW가 env 설정 후 import — 동일 모듈 인스턴스
import safe

HERE = Path(__file__).parent
DT_CTRL = 0.01                    # 재계획/제어 주기 [s]
K_MAX = 40                        # 룩어헤드 스텝 (0.4 s)
SIGMA = 6.0                       # 노이즈 σ [raw]
LAMS = (0.3, 1.0, 3.0)            # 파일럿 온도
S_PILOT, S_FINAL = 128, 256
G_ = 9.81


def _mk_ctx(tw):
    P = tw["P"]; mj = P.J._P["mj"]
    model = tw["model"]
    return dict(P=P, mj=mj, model=model,
                dof_knee=safe.dofadr(model, "knee", mj),
                iq_k=safe.qadr(model, "knee", mj),
                law=tw["law"], kr=tw["kr"], sprm=tw["sprm"],
                A=P.A_PAPER, tm=tw["tm"], dt=tw["dt"],
                sub=int(round(DT_CTRL / tw["dt"])),
                clip=TW.CLIP_RAW, hipa1=None)


def _substep(cx, md, c1_t, c2_t, fs):
    """1 서브스텝: tm 필터 → 클립 → ahat → 층 → mj_step (rollout_ol 커맨드 창 미러).
    fs = [c1f, c2f] (tm 필터 상태, in-place). 반환 (s1, s2, c1, c2) | None(발산)."""
    law_a, law_b, law_v0 = cx["law"]
    al = cx["dt"] / max(cx["tm"], cx["dt"])
    v1c = -md.qvel[1]; v2c = -md.qvel[2]
    fs[0] += al * (c1_t - fs[0]); fs[1] += al * (c2_t - fs[1])
    c1 = fs[0] if -cx["clip"] <= fs[0] <= cx["clip"] else (cx["clip"] if fs[0] > 0 else -cx["clip"])
    c2 = fs[1] if -cx["clip"] <= fs[1] <= cx["clip"] else (cx["clip"] if fs[1] > 0 else -cx["clip"])
    s1 = TW._ahat_s(cx["A"], c1, v1c)
    s2 = TW._ahat_s(cx["A"], c2, v2c)
    supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
    if cx["kr"]:
        supp += float(RU.rise_term(v2c, cx["kr"], law_v0))
    tql = 0.0
    if cx["sprm"] is not None:
        tql += RU.spr_tau(float(md.qpos[cx["iq_k"]]), abs(s2), cx["sprm"])
    md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
    md.qfrc_applied[cx["dof_knee"]] = tql
    try:
        cx["mj"].mj_step(cx["model"], md)
    except Exception:
        return None
    if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
        return None
    return s1, s2, c1, c2


def _sample_cost(cx, tw, qpos, qvel, fs0, U_seg):
    """1 샘플 롤아웃 코스트 (K 제어스텝 × sub 서브스텝) — 종단 탄도 apex 추정."""
    mj = cx["mj"]
    md = cx["md2"]
    md.qpos[:] = qpos; md.qvel[:] = qvel
    mj.mj_forward(cx["model"], md)
    fs = [fs0[0], fs0[1]]
    e = tw["env"]
    pen = 0.0
    for kk in range(U_seg.shape[1]):
        u1, u2 = U_seg[0, kk], U_seg[1, kk]
        for _ in range(cx["sub"]):
            r = _substep(cx, md, u1, u2, fs)
            if r is None:
                return TW.CRASH_F
            q1 = -md.qpos[1] - np.pi / 2; q2 = -md.qpos[2]
            pen += (max(q1 - e["q1"][1], 0.0) + max(e["q1"][0] - q1, 0.0)
                    + max(q2 - e["q2"][1], 0.0) + max(e["q2"][0] - q2, 0.0)) * cx["dt"]
    vz = float(md.qvel[0])
    apex_est = float(md.qpos[0]) + max(vz, 0.0) ** 2 / (2 * G_)
    return -apex_est + TW.PEN_W * pen


def run_mppi(tw, lam, S, seed, verbose=True):
    """MPPI 1회 전체 실행 → (h_plan, Lg(record), U_full, n_crash_samples)."""
    P = tw["P"]; mj = P.J._P["mj"]
    cx = _mk_ctx(tw)
    cx["md2"] = mj.MjData(cx["model"])
    rng = np.random.default_rng(seed)
    NC = int(round(TW.T_END / DT_CTRL))              # 60 제어스텝
    dt = cx["dt"]; sub = cx["sub"]

    # 시드 노미널: 측정 raw 푸시 (p25_a_cma_ol과 동일 정렬), 0.35 s 이후 0
    d0 = tw["d0"]; t = d0["t"]
    tp = float(t[int(np.argmax(np.abs(d0["dq2"])))])
    ts = tp - TW.T_PUSH * 0.85
    tc_grid = np.arange(NC) * DT_CTRL
    U = np.zeros((2, NC))
    m = tc_grid <= TW.T_PUSH
    U[0, m] = np.interp(ts + tc_grid[m], t, d0["traw1"])
    U[1, m] = np.interp(ts + tc_grid[m], t, d0["traw2"])
    ws = HERE / "p25_a_mppi.npz"
    if TW.OUT_TAG and ws.exists():    # 1차(35.5) 노미널을 새 클립으로 사영해 시드
        with np.load(ws) as z:
            if "U_nominal" in z and z["U_nominal"].shape == U.shape:
                U = np.asarray(z["U_nominal"], float)
                if verbose:
                    print(f"    warm-start: {ws.name} U_nominal 사영 (clip {cx['clip']})",
                          flush=True)
    U = np.clip(U, -cx["clip"], cx["clip"])

    st = TW.settle_state(tw, *tw["q0"])
    md = mj.MjData(cx["model"])
    md.qpos[:] = st["qpos"]; md.qvel[:] = st["qvel"]
    mj.mj_forward(cx["model"], md)
    fs_exec = [st["c1f"], st["c2f"]]

    N = int((TW.T_END + P.J.T_AFTER) / dt)
    Lg = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz",
                                   "raw1", "raw2", "grf"]}
    Lg["t"] = np.arange(N) * dt
    law_a = cx["law"][0]
    ncrash = 0
    ki = 0
    t0 = time.time()
    for j in range(NC):                              # ── 재계획 루프 (매 10 ms)
        K = min(K_MAX, NC - j)
        E_ = rng.normal(0.0, SIGMA, size=(S, 2, K))
        costs = np.empty(S)
        qp = md.qpos.copy(); qv = md.qvel.copy()
        for si in range(S):
            U_seg = np.clip(U[:, j:j + K] + E_[si], -cx["clip"], cx["clip"])
            costs[si] = _sample_cost(cx, tw, qp, qv, fs_exec, U_seg)
        ncrash += int(np.sum(costs >= TW.CRASH_F - 1e-9))
        w = np.exp(-(costs - costs.min()) / lam)
        w /= w.sum()
        U[:, j:j + K] = np.clip(
            U[:, j:j + K] + np.einsum("s,sjk->jk", w, E_), -cx["clip"], cx["clip"])
        # ── 첫 제어 실행 (연속 실행 MjData)
        u1, u2 = U[0, j], U[1, j]
        for _ in range(sub):
            r = _substep(cx, md, u1, u2, fs_exec)
            if r is None:
                raise RuntimeError(f"executed rollout crash at ctrl step {j}")
            s1, s2, c1, c2 = r
            Lg["q1"][ki] = -md.qpos[1] - np.pi / 2; Lg["q2"][ki] = -md.qpos[2]
            Lg["dq1"][ki] = -md.qvel[1]; Lg["dq2"][ki] = -md.qvel[2]
            Lg["sh1"][ki] = s1; Lg["sh2"][ki] = s2; Lg["bz"][ki] = md.qpos[0]
            Lg["raw1"][ki] = c1; Lg["raw2"][ki] = c2
            Lg["grf"][ki] = RU._grf_z(cx["model"], md)
            ki += 1
        if verbose and (j + 1) % 10 == 0:
            print(f"    replan {j + 1:2d}/{NC}  bz={md.qpos[0]:.3f}  "
                  f"vz={md.qvel[0]:.2f}  best J={costs.min():.3f}  "
                  f"[{time.time() - t0:.0f}s]", flush=True)
    # ── 비행 (a_full23 규약: s=0, extra=LAW_A, 스프링 h=0, 힙 e1=a1)
    while ki < N:
        md.ctrl[:] = [-(0.0 + RU.HIP["a1"]), -(0.0 + law_a)]
        md.qfrc_applied[cx["dof_knee"]] = 0.0
        mj.mj_step(cx["model"], md)
        Lg["q1"][ki] = -md.qpos[1] - np.pi / 2; Lg["q2"][ki] = -md.qpos[2]
        Lg["dq1"][ki] = -md.qvel[1]; Lg["dq2"][ki] = -md.qvel[2]
        Lg["bz"][ki] = md.qpos[0]
        Lg["grf"][ki] = RU._grf_z(cx["model"], md)
        ki += 1
    return TW.apex_of(Lg), Lg, U, ncrash


def main():
    safe.utf8_console()
    t0 = time.time()
    print("=== p25_a_mppi — MPPI (10ms 재계획, K<=40, 탄도 종단 추정) ===", flush=True)
    tw = TW.twin()
    print(f"init [{time.time() - t0:.0f}s] dt={tw['dt']}", flush=True)

    pilots = {}
    for lam in LAMS:
        print(f"  pilot λ={lam} (S={S_PILOT}) ...", flush=True)
        h, _, _, nc = run_mppi(tw, lam, S_PILOT, seed=11, verbose=False)
        pilots[lam] = dict(h_plan=float(h), crash_samples=int(nc))
        print(f"    λ={lam}: h={h:.4f} m  crash_samples={nc}", flush=True)
    lam_best = max(pilots, key=lambda k: pilots[k]["h_plan"])
    print(f"λ* = {lam_best} → 본판 S={S_FINAL}", flush=True)

    h_plan, Lg, U, ncrash = run_mppi(tw, lam_best, S_FINAL, seed=21, verbose=True)
    n_samples = S_FINAL * int(round(TW.T_END / DT_CTRL))
    stats = TW.stats_of(tw, Lg, t_push=TW.T_END)
    print(f"h_plan={h_plan:.4f} m  peak raw=({stats['peak_raw1']:.1f}, "
          f"{stats['peak_raw2']:.1f})  peak dq=({stats['peak_dq1']:.1f}, "
          f"{stats['peak_dq2']:.1f})  ceil_frac=({stats['ceil_frac_raw1']:.2f}, "
          f"{stats['ceil_frac_raw2']:.2f})  crash_samples={ncrash}/{n_samples}",
          flush=True)

    TAG = TW.OUT_TAG
    TW.save_npz(HERE / f"p25_a_mppi{TAG}.npz", Lg,
                extra=dict(U_nominal=U, dt_ctrl=np.array(DT_CTRL),
                           lam=np.array(lam_best), sigma=np.array(SIGMA)))
    safe.atomic_json_write(HERE / f"p25_a_res_mppi{TAG}.json", dict(
        gen=time.strftime("%Y-%m-%d %H:%M"), method="mppi",
        note=f"MPPI 10ms 재계획, S={S_FINAL}, K<=40 (0.4s 룩어헤드), σ={SIGMA} raw, "
             f"탄도 종단 apex 추정, 순수 보상 가중 (제어비용항 없음), "
             f"clip ±{TW.CLIP_RAW}",
        h_plan=float(h_plan), stats=stats, lam=float(lam_best), pilots=pilots,
        samples=S_FINAL, replans=int(round(TW.T_END / DT_CTRL)),
        crash_samples=int(ncrash), crash_rate=float(ncrash / n_samples),
        clip_raw=TW.CLIP_RAW,
        seed_trial=list(tw["seed_trial"]), npz=f"p25_a_mppi{TAG}.npz",
        wall_s=float(time.time() - t0)))
    print(f"saved p25_a_mppi{TAG}.npz + p25_a_res_mppi{TAG}.json "
          f"[{(time.time() - t0) / 60:.1f}m]", flush=True)


if __name__ == "__main__":
    main()
