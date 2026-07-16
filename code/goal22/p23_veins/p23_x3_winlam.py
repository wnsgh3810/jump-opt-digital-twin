# -*- coding: utf-8 -*-
"""p23_x3_winlam — P23 Phase 3: 동적 푸시 부족분(l_i=30 '상승 성분' +2~3Nm) 3택 판별의
측정부. 6세션 전 점프 trial에 대해 창별 무릎 보충 λ2* + 힙 보충 λ1*를 동일 프로토콜로 측정.

세션 (family):
  PD: jump_position_0421 / jump_0424 / jump_0602 (P12 judge trials, p22_eval.ensure_init —
      fix0421 적용 = 0421 csv ×1.35 오염 제거본), jump_0319pd (신규 로더 p23_x3_loaders)
  FF: jump_0422 (p23_loaders, xlsx 직행), jump_0319tau (p23_loaders)
  held-out(jump_0324)은 사용하지 않음 (게이트 전용 철칙).

★ 단일 프로토콜 (전 세션 공통 — 세션별 튜닝 없음, p20_exp4.win_scan / exp7 계보):
  - 플랜트: P19 후보 (fourbar_p19_candidate.json → build_flip, l_i=30 평행사변형), dt=0.5ms
  - 토크: â = ahat(A_PAPER, raw_xlsx, dq_meas), 센서 지연 SD=−1.5ms interp (P19 규약)
  - q-오프셋: 전 세션 o1=o2=0 (신규 세션에 적합된 오프셋이 없으므로 무튜닝 통일 —
    P20 '오프셋 0 통일 재측정'과 동일 조건. 적합 오프셋 대비 λ* 산포가 커지는 비용 감수)
  - 창: W=0.12s, 시작 t0 ∈ [0.02, toff−0.05] step 0.015 (toff = GRF peak 후 <2%peak 시각;
    GRF 없으면 기록 끝). 기록이 전부 푸시 창(0.27~0.32s)이라 유지+푸시 전체를 덮는다.
  - 리셋: 접촉 FK(bz 재구성, closure 기반) → 측정 상태로 qpos/qvel 세팅 (exp4 fk_bz 패턴)
  - 점수: 100·(RMSE q1+q2) + 50·(RMSE dq1+dq2), 창 내 측정 샘플 (mshoot W_Q/W_DQ)
  - λ2(무릎): 그리드 [−3, +7] step 0.5 → argmin 포물선 보정. 민감도 (max−min)/min < 2% 창 제외
  - λ1(힙):   λ2를 그 창의 λ2*로 고정한 뒤 그리드 [−4, +4] step 0.5 (좌표 하강 1패스)
출력: p23_x3_rows.json — 창별 {세션, family, day, sub, t0, t0−toff, λ2*, λ1*, edge/민감도,
      창 평균 |â2|·dq2·q2·|â1|·dq1·q1·|Iq2|}.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))

import p22_eval as EV                      # noqa: E402  (judge trials + fix0421)
import p23_loaders as L                    # noqa: E402
import p23_x3_loaders as XL                # noqa: E402

W = 0.12
STEP = 0.015
T0MIN = 0.02
TOFF_GUARD = 0.05
LGRID2 = np.arange(-8.0, 10.01, 0.5)       # 무릎 λ (0319pd 창들이 ±3~7 경계 검열 → 확장)
LGRID1 = np.arange(-6.0, 6.01, 0.5)        # 힙 λ
SENS_MIN = 0.02                            # exp4/exp7 민감도 컷 동일
JDS_PD = ("jump_position_0421", "jump_0424", "jump_0602")
DAY = {"jump_position_0421": "04-21", "jump_0424": "04-24", "jump_0602": "06-02",
       "jump_0422": "04-22", "jump_0319tau": "03-19", "jump_0319pd": "03-19"}
FAM = {"jump_position_0421": "PD", "jump_0424": "PD", "jump_0602": "PD",
       "jump_0319pd": "PD", "jump_0422": "FF", "jump_0319tau": "FF"}
OUT = HERE / "p23_x3_rows.json"

_G = {}


def init():
    EV.ensure_init()
    import p19_judge as P
    import p19_adapter as AD
    from p14_judge import KT, GR, CF
    from cvt_core import closure
    CAND = AD.load_candidate(HERE.parent / "p19_jump/fourbar_p19_candidate.json")
    X32, V, SP, _ = AD._p19_args(CAND)
    model, _ = P.build_flip(X32, V[1], SP)
    mj = P.J._P["mj"]
    S = P.J._P["S"]
    MS = P.J._P["P12"]._G["MS"]
    _G.update(P=P, mj=mj, S=S, MS=MS, model=model, closure=closure,
              KT=KT, GR=GR, CF=CF, A=P.A_PAPER, SD=P.SD,
              P12=P.J._P["P12"], X32=X32)


def toff_of(t, g):
    """GRF 이륙 시각 — p19 규약 (peak 후 <2% peak). GRF 없으면 기록 끝."""
    if g is None or len(g) != len(t) or not np.isfinite(g).any():
        return float(t[-1])
    g = np.nan_to_num(np.asarray(g, float))
    pk = int(np.argmax(g))
    below = np.where(g[pk:] < 0.02 * g[pk])[0]
    return float(t[pk + below[0]]) if len(below) else float(t[-1])


def fk_bz(data, q1mj, qcmj, l_i, qk_prev):
    mj, S, model = _G["mj"], _G["S"], _G["model"]
    qk, qp, _ = _G["closure"](float(qcmj), l_i, qk_prev)
    data.qpos[:] = [1.0, q1mj, qcmj, qp, qk]
    data.qvel[:] = 0
    mj.mj_forward(model, data)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    return 1.0 - float(data.geom_xpos[fg][2]) + S.FOOT_RADIUS, qk, qp


def replay(data, qpos0, qvel0, thg, tkg, ts, t, mk, q1mj, qcmj, dq1m, dq2m):
    """창 replay 1회 → 점수 (exp4 동일: 크래시 = W_Q·2 + W_DQ·20)."""
    mj, model, MS = _G["mj"], _G["model"], _G["MS"]
    nst = len(thg)
    data.qpos[:] = qpos0
    data.qvel[:] = qvel0
    mj.mj_forward(model, data)
    q1a = np.empty(nst); q2a = np.empty(nst); dq1a = np.empty(nst); dq2a = np.empty(nst)
    for k in range(nst):
        data.ctrl[:] = [-thg[k], -tkg[k]]
        try:
            mj.mj_step(model, data)
        except Exception:
            return MS.W_Q * 2 + MS.W_DQ * 20
        q1a[k] = data.qpos[1]; q2a[k] = data.qpos[2]
        dq1a[k] = data.qvel[1]; dq2a[k] = data.qvel[2]
    if not np.isfinite(q1a).all():
        return MS.W_Q * 2 + MS.W_DQ * 20
    r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mk], ts, sim) - real[mk]) ** 2)))
    return (MS.W_Q * (r(q1a, q1mj) + r(q2a, qcmj))
            + MS.W_DQ * (r(dq1a, dq1m) + r(dq2a, dq2m)))


def lam_star(grid, scores):
    """argmin + 포물선 보정 → (λ*, edge?, 민감도)."""
    scores = np.asarray(scores, float)
    sens = float((scores.max() - scores.min()) / max(scores.min(), 1e-9))
    i = int(np.argmin(scores))
    if i in (0, len(grid) - 1):
        return float(grid[i]), True, sens
    a, b, c = scores[i - 1], scores[i], scores[i + 1]
    den = a - 2 * b + c
    step = float(grid[1] - grid[0])
    off = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
    return float(grid[i] + np.clip(off, -1, 1) * step), False, sens


def scan_trial(ds, sub, d, grf):
    """1 trial → 창 rows. d: 측정좌표 d-dict (t q1 q2 dq1 dq2 traw1 traw2)."""
    P, mj, model = _G["P"], _G["mj"], _G["model"]
    A, SD = _G["A"], _G["SD"]
    KT, GR, CF = _G["KT"], _G["GR"], _G["CF"]
    t = d["t"]
    l_i = 0.030
    toff = toff_of(t, grf)
    a1 = P.J.ahat(A, d["traw1"], d["dq1"])
    a2 = P.J.ahat(A, d["traw2"], d["dq2"])
    th0 = np.interp(t - SD, t, a1)
    tk0 = np.interp(t - SD, t, a2)
    q1mj = -d["q1"] - np.pi / 2
    qcmj = -d["q2"]
    ddq1 = np.gradient(d["dq1"], t)          # 필터된 dq의 수치미분 (H-B 관성 판별용)
    ddq2 = np.gradient(d["dq2"], t)
    data = mj.MjData(model)
    bz = np.zeros_like(t); qks = np.zeros_like(t); qps = np.zeros_like(t)
    qk_prev = None
    for i in range(len(t)):
        bz[i], qk_prev, qp_ = fk_bz(data, q1mj[i], qcmj[i], l_i, qk_prev)
        qks[i] = qk_prev; qps[i] = qp_
    vbz = np.gradient(bz, t)
    dt = model.opt.timestep
    rows = []
    n_skip = 0
    for t0 in np.arange(T0MIN, toff - TOFF_GUARD + 1e-9, STEP):
        i0 = int(np.searchsorted(t, t0))
        if i0 >= len(t) - 5:
            continue
        t1 = min(t0 + W, t[-1])
        nst = int(round((t1 - t0) / dt))
        if nst < 20:
            continue
        ts = t0 + (np.arange(nst) + 1) * dt
        mk = (t >= ts[0]) & (t <= ts[-1])
        if mk.sum() < 3:
            continue
        tcg = t0 + np.arange(nst) * dt
        thg = np.interp(tcg, t, th0)
        tkg = np.interp(tcg, t, tk0)
        # closure 기반 리셋 상태 (exp4 동일)
        qk2, qp2, _ = _G["closure"](float(qcmj[i0]) + 1e-4, l_i, qks[i0])
        r_ = (qk2 - qks[i0]) / 1e-4
        gp = (qp2 - qps[i0]) / 1e-4
        dqc = -d["dq2"][i0]
        qpos0 = [bz[i0], q1mj[i0], qcmj[i0], qps[i0], qks[i0]]
        qvel0 = [vbz[i0], -d["dq1"][i0], dqc, gp * dqc, r_ * dqc]
        args = (ts, t, mk, q1mj, qcmj, -d["dq1"], -d["dq2"])
        # ── 무릎 λ2 스캔 ──
        sc2 = [replay(data, qpos0, qvel0, thg, tkg + lam, *args) for lam in LGRID2]
        lam2, edge2, sens2 = lam_star(LGRID2, sc2)
        if sens2 < SENS_MIN:
            n_skip += 1
            continue
        # ── 힙 λ1 스캔 (λ2 고정) ──
        sc1 = [replay(data, qpos0, qvel0, thg + lam, tkg + lam2, *args) for lam in LGRID1]
        lam1, edge1, sens1 = lam_star(LGRID1, sc1)
        if sens1 < SENS_MIN:
            lam1, edge1 = float("nan"), False
        wm = (t >= t0) & (t <= t1)
        rows.append(dict(
            ds=ds, sub=str(sub), family=FAM[ds], day=DAY[ds],
            t0=float(t0), t0_rel=float(t0 - toff), toff=toff, W=W,
            lam2=lam2, lam2_edge=bool(edge2), sens2=sens2,
            lam1=lam1, lam1_edge=bool(edge1), sens1=float(sens1),
            a2m=float(np.mean(np.abs(a2[wm]))), dq2m=float(np.mean(d["dq2"][wm])),
            q2m=float(np.mean(d["q2"][wm])),
            a1m=float(np.mean(np.abs(a1[wm]))), dq1m=float(np.mean(d["dq1"][wm])),
            q1m=float(np.mean(d["q1"][wm])),
            ddq2m=float(np.mean(ddq2[wm])), ddq1m=float(np.mean(ddq1[wm])),
            iq2m=float(np.mean(np.abs((CF / (GR * KT)) * d["traw2"][wm]))),
            dq2_start=float(d["dq2"][i0])))
    return rows, n_skip


def pd_trial_dicts():
    """P12 judge trials (fix0421 적용본) → 측정좌표 d-dict."""
    P12 = _G["P12"]
    out = []
    for tr in P12._G["trials"]:
        ds = tr["ds"]
        if ds not in JDS_PD:
            continue
        pp = tr["pp"]; t = pp["t"]
        # 일관성 검증: pp(mj좌표) ↔ td(측정좌표). q는 무필터 항등 변환이어야 함.
        assert len(tr["raw1"]) == len(t) and len(tr["raw2"]) == len(t), \
            f"{ds}/{tr['sub']}: raw/t 길이 불일치"
        dev = float(np.max(np.abs((-pp["q1m"] - np.pi / 2) - np.asarray(tr["td"]["q1"]))))
        assert dev < 1e-9, f"{ds}/{tr['sub']}: pp/q1 불일치 {dev}"
        # dq: pp 캐시 = savgol(-dq,11,3) — 전 세션 공통 필터 규약 (로더 세션도 동일 적용)
        d = dict(t=t, q1=-pp["q1m"] - np.pi / 2, q2=-pp["q2m"],
                 dq1=-pp["dq1m"], dq2=-pp["dq2m"],
                 traw1=np.asarray(tr["raw1"], float),
                 traw2=np.asarray(tr["raw2"], float))
        g = np.asarray(tr["td"].get("grf_z", []), float)
        out.append((ds, tr["sub"], d, g if len(g) == len(t) else None))
    return out


def main():
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    t_start = time.time()
    print("=== p23_x3_winlam — 6세션 창별 λ2*/λ1* 측정 (단일 프로토콜) ===", flush=True)
    init()
    print(f"init done [{time.time() - t_start:.0f}s] — 플랜트 P19 후보, dt="
          f"{_G['model'].opt.timestep}", flush=True)

    from scipy.signal import savgol_filter

    def _filt(d):
        """로더 세션 dq에 P12 pp와 동일한 savgol(11,3) 필터 적용 (프로토콜 통일)."""
        d = dict(d)
        d["dq1"] = savgol_filter(np.asarray(d["dq1"], float), 11, 3)
        d["dq2"] = savgol_filter(np.asarray(d["dq2"], float), 11, 3)
        return d

    trials = pd_trial_dicts()
    for sub in L.SUBS_0422:
        d, m = L.load_jump_0422(sub)
        trials.append(("jump_0422", sub, _filt(d), d["grf_real"]))
    d, m = L.load_jump_0319tau()
    trials.append(("jump_0319tau", "no_tr_tau", _filt(d), d["grf_real"]))
    d, m = XL.load_jump_0319pd()
    trials.append(("jump_0319pd", "NO_TR_JUMP", _filt(d), d["grf_real"]))
    print(f"trials: {len(trials)} (PD {sum(1 for x in trials if FAM[x[0]] == 'PD')} / "
          f"FF {sum(1 for x in trials if FAM[x[0]] == 'FF')})", flush=True)

    all_rows = []
    tot_skip = 0
    for ds, sub, d, grf in trials:
        tw = time.time()
        rows, n_skip = scan_trial(ds, sub, d, grf)
        tot_skip += n_skip
        all_rows.extend(rows)
        lam2s = [r["lam2"] for r in rows]
        print(f"  {ds}/{sub}: {len(rows)}창 (skip {n_skip}) λ2* "
              f"{np.mean(lam2s) if lam2s else float('nan'):+.2f}±"
              f"{np.std(lam2s) if lam2s else 0:.2f} [{time.time() - tw:.0f}s]", flush=True)

    meta = dict(
        protocol=dict(W=W, step=STEP, t0min=T0MIN, toff_guard=TOFF_GUARD,
                      lgrid2=[float(LGRID2[0]), float(LGRID2[-1]), 0.5],
                      lgrid1=[float(LGRID1[0]), float(LGRID1[-1]), 0.5],
                      sens_min=SENS_MIN, offsets="o1=o2=0 전 세션 통일 (무튜닝)",
                      plant="fourbar_p19_candidate.json (build_flip, l_i=30)",
                      sd=float(_G["SD"]), score="100·(q1+q2 RMSE)+50·(dq1+dq2 RMSE)",
                      torque="ahat(A_PAPER, raw_xlsx, dq_meas); 0421은 fix0421(xlsx 통일) 적용",
                      reset="접촉 FK-bz + closure (p20_exp4.win_scan 계보)",
                      hip_pass="λ2를 창별 λ2*로 고정 후 λ1 스캔 (좌표하강 1패스)"),
        li_note="0319/0422 l_i=30.00은 가정 (Clutch 미기록)",
        n_rows=len(all_rows), n_skipped_insensitive=tot_skip,
        elapsed_s=round(time.time() - t_start, 1))
    json.dump(dict(meta=meta, rows=all_rows), open(OUT, "w"), indent=1)
    print(f"\nsaved {OUT} — {len(all_rows)} rows, skip {tot_skip} "
          f"[{(time.time() - t_start) / 60:.1f}m]", flush=True)


if __name__ == "__main__":
    main()
