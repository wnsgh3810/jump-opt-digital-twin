# -*- coding: utf-8 -*-
"""t0_cvt_deploy — P25-task0 CVT 배포 하네스 (no_cvt p25_d_deploy/p25_d_ff/t0_shaped의 CVT 미러).

배경: 기존 배포 하네스(p25_d_deploy)는 model_flip(무변속 l_i=30) 전용이라 CVT 계획
(t0wc_*)은 계획 시각화만 있고 배포 실험(채점·그래프·시뮬)이 통째로 없었다. 이 모듈이
CVT 폐루프 배포 경로를 신규 구축해 no_cvt와 대칭으로 F_τ·h_PD·그래프·canonical gif를 채운다.

CVT 폐루프 정본 배선 = t0wc_env/t0wc_rollout이 쓰는 것과 동일:
  RU.cl_run23_log(build_cvt23(l_i) 모델, is_cvt=True, l_i[m], d, g4, dqon, ffk,
                  A, TM, [1,1,1,1], LAW, c_cvt=C_CVT, o1=0, o2=0, ff_hip, spr=SPR, k_rise=KR)
  ─ 크랭크 좌표계: q_des/dq_des = 크랭크측(모터가 제어; npz q2/qm/qd2). 무릎각 변환은
    cl_run23_log 내부 폐쇄 솔버(qpos_from_crank)만 사용 — 재구현 없음.
  ─ 트윈 CVT 층: c_cvt 전달손실 + 게이트 스프링 + 상승항 + 힙 지지 (D.setup() = W.setup()과
    동일 후보 fourbar_p24a_candidate.json, v[20]=C_CVT). 골든 0429 재생 2.6057 검증된 경로.

3 모드 (no_cvt 미러):
  ffpd     = FF+PD  : ffk=ff_hip=True, tdes=raw*(계획), q_des=계획 qd/dqd (deploy_ff 대응)
  pd_only  = 순수PD : ffk=False, q_des=계획 크랭크각 qd/dqd (D.deploy 대응)
  pd_shaped= 성형PD : q_des = q_실현 + raw*/Kp (게인별), dq_des=dq_실현 (t0_shaped 대응)

배포 클립 = P25_CLIP_RAW=35.5 (하드웨어 천장; 계획 15Nm 캡은 npz raw에 이미 반영).
지표 = D.metrics_of 재사용 (스탠스 F_τ = RMSE(sh−τ*)/RMS(τ*), h_PD, H_fid, q/dq RMSE).

산출:
  t0_cvt_deploy_results.json  — 계획3 × 게인8 × 모드3 원장 (crash 명기)
  graphs/CVT/{ffpd,pd_only,pd_shaped}/<계획>_gain_<게인>.png  — 기준양식(fig_std)
  sims/canonical/CVT/{ffpd,pd_only}/<계획>_gain_<게인>.gif    — 최적게인 canonical 렌더

CLI: python t0_cvt_deploy.py {golden|run|graphs|sims|all}
"""
import os
import sys
import time
from pathlib import Path

for _k in ("P23_SPRING_GATED", "P23_RISE_GATED", "P24_HIP_LAW", "P24_REFIT"):
    os.environ.setdefault(_k, "1")
os.environ["P25_CLIP_RAW"] = "35.5"     # 배포 하드웨어 천장 (no_cvt 배포 규약과 동일)
os.environ["P25_GAINS_FULL"] = "1"      # 실 세션 게인 8종
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p25_deploy"))
sys.path.insert(0, str(HERE.parent / "p23_veins"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p25_d_deploy as D
import p23_v6_runners as RU
import safe

# 배포 대상 계획 (스템, 표시라벨) — l_i는 npz z["l_i"](mm)에서 읽음
PLANS = [("t0wc_cl_li2508", "CL l_i=25.08 (검증앵커)"),
         ("t0wc_cl_liopt", "CL l_i=26.25 (최적)"),
         ("t0wc_ol_li2508", "OL l_i=25.08")]
MODES = ("ffpd", "pd_only", "pd_shaped")
MODE_TAG = {"ffpd": "FF+PD", "pd_only": "순수PD", "pd_shaped": "성형PD"}

_CVT_MODELS = {}   # l_i[m] → build_cvt23 모델 (전역 캐시)


def _cvt_model(l_i_m):
    key = round(float(l_i_m), 6)
    if key not in _CVT_MODELS:
        D.setup()
        _CVT_MODELS[key] = RU.build_cvt23(D.G["X32"], D.G["REF"], D.G["SP"],
                                          key, D.G["D_DQ"])
    return _CVT_MODELS[key]


def _crop_channels(npz_path):
    """npz raw/q/dq를 load_plan과 동일한 t≥0 마스크로 크롭 (plan['t']와 인덱스 정합)."""
    z = np.load(npz_path, allow_pickle=True)
    tz = np.asarray(z["t"], float).ravel()
    mk = tz >= -1e-12

    def g(k):
        return np.asarray(z[k], float).ravel()[mk] if k in z.files else None
    return dict(raw1=g("raw1"), raw2=g("raw2"), q1=g("q1"), q2=g("q2"),
                dq1=g("dq1"), dq2=g("dq2"),
                l_i_mm=float(z["l_i"]) if "l_i" in z.files else float("nan"))


def deploy_cvt(npz_path, gains, l_i_mm=None, mode="ffpd", return_log=False):
    """CVT 계획 npz를 트윈 CVT 폐루프 PD로 배포 → 지표 dict (D.metrics_of 재사용).

    gains: 프리셋 이름 (D.GAINS 키) 또는 (kp1,kd1,kp2,kd2) 튜플.
    l_i_mm: CVT 링크 길이 [mm]. None이면 npz z['l_i']에서 읽음.
    mode: 'ffpd' | 'pd_only' | 'pd_shaped'.
    """
    D.setup()
    if isinstance(gains, str):
        glabel, g4 = gains, D.GAINS[gains]
    else:
        g4 = tuple(float(x) for x in gains)
        assert len(g4) == 4, f"gains 튜플은 (kp1,kd1,kp2,kd2) 4원 — got {gains}"
        glabel = "_".join(f"{x:g}" for x in g4)
    kp1, kd1, kp2, kd2 = g4
    assert mode in MODES, f"mode ∈ {MODES} — got {mode}"

    plan = D.load_plan(npz_path)          # t, qd(N,2), dqd, tau, tau_src, h_plan (크랭크좌표)
    ch = _crop_channels(npz_path)
    if l_i_mm is None:
        l_i_mm = ch["l_i_mm"]
    l_i_m = round(float(l_i_mm) / 1000.0, 6)
    t = plan["t"]

    d = dict(t=t, qd1=plan["qd"][:, 0].copy(), qd2=plan["qd"][:, 1].copy(),
             dqd1=plan["dqd"][:, 0].copy(), dqd2=plan["dqd"][:, 1].copy())
    ffk = ff_hip = False
    plan_metric = plan

    if mode == "ffpd":
        if ch["raw1"] is None:
            raise ValueError(f"ffpd: raw1/raw2 없음 — {npz_path}")
        d["tdes1"], d["tdes2"] = ch["raw1"], ch["raw2"]
        ffk = ff_hip = True
    elif mode == "pd_only":
        pass                              # q_des = 계획 크랭크각 (load_plan qd), FF 없음
    elif mode == "pd_shaped":
        if ch["raw1"] is None:
            raise ValueError(f"pd_shaped: raw1/raw2 없음 — {npz_path}")
        qd1 = ch["q1"] + ch["raw1"] / kp1     # q_des = q_실현 + raw*/Kp (게인별)
        qd2 = ch["q2"] + ch["raw2"] / kp2
        d.update(qd1=qd1, qd2=qd2, dqd1=ch["dq1"].copy(), dqd2=ch["dq2"].copy())
        # 지표용 계획: q_des=성형, dq_des=dq실현, τ*=계획 tau 그대로 (t0_shaped 규약)
        plan_metric = dict(plan, qd=np.column_stack([qd1, qd2]),
                           dqd=np.column_stack([ch["dq1"], ch["dq2"]]))

    model = _cvt_model(l_i_m)
    L = RU.cl_run23_log(model, True, l_i_m, d, g4, True, ffk,
                        D.G["A"], D.G["TM"], [1, 1, 1, 1], D.G["LAW"],
                        c_cvt=D.G["C_CVT"], o1=0.0, o2=0.0, ff_hip=ff_hip,
                        spr=D.G["SPR"], k_rise=D.G["KR"])
    base = dict(plan=Path(npz_path).name, gains_label=glabel, gains=list(g4),
                l_i_mm=round(float(l_i_mm), 4), mode=MODE_TAG[mode], mode_key=mode,
                model="p24a_cvt", c_cvt=round(float(D.G["C_CVT"]), 5))
    if L is None:
        return dict(base, crash=True, h_PD=float("nan"), h_plan=plan["h_plan"],
                    H_fid=float("nan"), F_tau=float("nan"),
                    F_tau_hip=float("nan"), F_tau_knee=float("nan"),
                    dq_rmse=float("nan"), q_rmse=float("nan"))
    out = dict(base, crash=False, dt=float(model.opt.timestep),
               **D.metrics_of(L, plan_metric))
    if return_log:
        out["log"] = L
        out["_plan"] = plan
        out["_plan_metric"] = plan_metric
    return out


# ══════════════════ 골든 (계획 게인 재배포 새니티) ══════════════════
def golden():
    """검증앵커 t0wc_cl_li2508을 그 계획 자신의 게인(150_2.2_500_4)으로 재배포 →
    F_τ가 폭발하지 않고 계획 h를 합리적으로 재현하는지 확인 (cl_run23_log 정본 경로)."""
    D.setup()
    z = np.load(HERE / "t0wc_cl_li2508.npz", allow_pickle=True)
    pg = [float(x) for x in z["gains"]]     # 계획 생성 게인
    glabel = "_".join(f"{x:g}" for x in pg)
    print(f"═══ GOLDEN — t0wc_cl_li2508 계획게인 {glabel} 재배포 ═══", flush=True)
    rows = {}
    for mode in MODES:
        r = deploy_cvt(HERE / "t0wc_cl_li2508.npz", pg, mode=mode)
        rows[mode] = r
        if r.get("crash"):
            print(f"  [{mode:9s}] CRASH", flush=True)
            continue
        print(f"  [{mode:9s}] F_τ={100*r['F_tau']:6.1f}% (hip {100*r['F_tau_hip']:5.1f}% / "
              f"knee {100*r['F_tau_knee']:5.1f}%)  h_PD={r['h_PD']:.3f} / h_plan={r['h_plan']:.3f} m "
              f"(H_fid {100*r['H_fid']:.1f}%)  liftoff {1000*r['t_liftoff']:.0f}ms", flush=True)
    ff = rows["ffpd"]
    ok = (not ff.get("crash")) and np.isfinite(ff["F_tau"]) and ff["F_tau"] < 1.5 \
        and abs(ff["h_PD"] - ff["h_plan"]) < 0.25
    print(f"  GOLDEN {'PASS' if ok else 'WARN'} — FF+PD F_τ={100*ff['F_tau']:.1f}% "
          f"(폭발 아님 & h 재현 합리)", flush=True)
    summ = {m: {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                for k, v in rows[m].items() if not isinstance(v, (list, np.ndarray))}
            for m in MODES}
    safe.atomic_json_write(HERE / "t0_cvt_golden.json",
                           dict(plan="t0wc_cl_li2508", plan_gains=pg,
                                golden_pass=bool(ok), rows=summ))
    return ok, rows


# ══════════════════ 채점 + 그래프 ══════════════════
def run_all(make_graphs=True):
    """계획3 × 게인8 × 모드3 배포 → 원장 + (옵션) 기준양식 그래프."""
    D.setup()
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["font.family"] = "Malgun Gothic"
    matplotlib.rcParams["axes.unicode_minus"] = False
    from t0_figs import _chan, _log_chan
    from t0_ours import fig_std, rmse_vs

    ledger = {}
    ng = 0
    for stem, lab in PLANS:
        f = HERE / f"{stem}.npz"
        if not f.exists():
            print(f"  (skip 없음: {stem})", flush=True)
            continue
        z = np.load(f, allow_pickle=True)
        l_i_mm = float(z["l_i"])
        P = _chan(z)
        # CL 계획: 명령(qd)이 실현궤적과 다르면 q_des 오버레이 (do_nc 규약)
        has_cmd = False
        if "qd1" in z.files:
            tall = np.asarray(z["t"], float)
            mm = tall >= -1e-12
            qd1a = np.asarray(z["qd1"], float)[mm]
            qd2a = np.asarray(z["qd2"], float)[mm]
            if np.max(np.abs(qd1a - P["q1"])) > 1e-6:
                has_cmd = True
                Pcmd = dict(P, qd1=qd1a, qd2=qd2a,
                            ddq1=np.asarray(z["dqd1"], float)[mm],
                            ddq2=np.asarray(z["dqd2"], float)[mm])
        for mode in MODES:
            best = None
            for gk in D.GAINS:
                r = deploy_cvt(f, gk, l_i_mm=l_i_mm, mode=mode, return_log=make_graphs)
                key = f"{stem}|{mode}|{gk}"
                ledger[key] = {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                               for k, v in r.items()
                               if not isinstance(v, (list, np.ndarray, dict))
                               and not k.startswith("_")}
                if r.get("crash"):
                    print(f"[{stem}|{mode:9s}|{gk:16s}] CRASH", flush=True)
                    continue
                if best is None or r["F_tau"] < best[1]:
                    best = (gk, r["F_tau"])
                if make_graphs:
                    Dc = _log_chan(r["log"])
                    tlo = r.get("t_liftoff", float("nan"))
                    # 성형은 q_des가 실현+성형이라 오버레이 생략 (t0_shaped 규약);
                    # ffpd/pd_only + CL 계획만 명령 오버레이
                    Pg = Pcmd if (has_cmd and mode in ("ffpd", "pd_only")) else P
                    rq2 = rmse_vs(P, Dc, "q2", tlo if np.isfinite(tlo) else 0.3)
                    rdq2 = rmse_vs(P, Dc, "dq2", tlo if np.isfinite(tlo) else 0.3)
                    ttl = (f"{stem}/{gk} [{MODE_TAG[mode]} CVT p24a · l_i={l_i_mm:.2f}mm, task0 15Nm] — "
                           f"q2(크랭크) RMSE {rq2:.3f} rad · dq2 {rdq2:.2f} · "
                           f"h_PD {r['h_PD']:.2f} / h_plan {r['h_plan']:.2f} m  (F_τ {100*r['F_tau']:.1f}%)")
                    out = HERE / "graphs" / "CVT" / mode / f"{stem}_gain_{gk}.png"
                    out.parent.mkdir(parents=True, exist_ok=True)
                    fig_std(Pg, Dc, out, ttl, tlo)
                    ng += 1
            if best is not None:
                print(f"[{stem}|{mode:9s}] best gain {best[0]} (F_τ {100*best[1]:.1f}%)", flush=True)
    safe.atomic_json_write(HERE / "t0_cvt_deploy_results.json", ledger)
    print(f"LEDGER saved t0_cvt_deploy_results.json ({len(ledger)} rows, {ng} graphs)", flush=True)
    return ledger


# ══════════════════ canonical 시뮬 (최적게인) ══════════════════
def render_sims(ledger=None):
    """FF+PD 최저 F_τ 게인 = 최적게인 → ffpd·pd_only canonical gif (qpos_cvt 4절링크)."""
    import mujoco
    import t0_mjc_render as R
    R.D.setup()
    if ledger is None:
        ledger = safe.read_json(HERE / "t0_cvt_deploy_results.json")

    summ = {}
    for stem, lab in PLANS:
        f = HERE / f"{stem}.npz"
        if not f.exists():
            continue
        z = np.load(f, allow_pickle=True)
        l_i_mm = float(z["l_i"])
        l_i_m = round(l_i_mm / 1000.0, 6)
        # FF+PD 최저 F_τ 게인 선택
        cand = [(gk, ledger.get(f"{stem}|ffpd|{gk}", {}))
                for gk in D.GAINS]
        cand = [(gk, m) for gk, m in cand
                if m and not m.get("crash") and np.isfinite(m.get("F_tau", np.nan))]
        if not cand:
            print(f"  (skip sims {stem}: FF+PD 전 게인 crash)", flush=True)
            continue
        best_gk = min(cand, key=lambda x: x[1]["F_tau"])[0]
        # l_i별 CVT XML 임시 저장 (컴파일 직후 즉시 — mj_saveLastXML 전역성)
        mc = RU.build_cvt23(R.D.G["X32"], R.D.G["REF"], R.D.G["SP"], l_i_m, R.D.G["D_DQ"])
        xmlc = R.SCR / f"twin_cvt_{stem}.xml"
        mujoco.mj_saveLastXML(str(xmlc), mc)
        for mode in ("ffpd", "pd_only"):
            r = deploy_cvt(f, best_gk, l_i_mm=l_i_mm, mode=mode, return_log=True)
            if r.get("crash"):
                print(f"  [{stem}|{mode}|{best_gk}] CRASH — gif skip", flush=True)
                continue
            L = r["log"]
            outdir = HERE / "sims" / "canonical" / "CVT" / mode
            outdir.mkdir(parents=True, exist_ok=True)
            R.OUT = outdir
            tag = f"{stem}_gain_{best_gk}"
            row = R.render(tag, L["t"], R.qpos_cvt(L["bz"], L["q1"], L["q2"], l_i_m),
                           L["grf"], xmlc,
                           f"task0 CVT {lab} {MODE_TAG[mode]} {best_gk}",
                           float(r["h_PD"]), "h_PD(deploy)", float(r["h_plan"]))
            row.update(mode=MODE_TAG[mode], gain=best_gk, l_i_mm=l_i_mm,
                       F_tau=round(float(r["F_tau"]), 4))
            summ[f"{stem}|{mode}|{best_gk}"] = row
            print(f"  gif {mode}: {tag}  (dh={row['dh_mm']:+.2f}mm)", flush=True)
    safe.atomic_json_write(HERE / "sims" / "canonical" / "CVT" /
                           "mjc_cvt_deploy_summary.json", summ)
    print(f"SIMS saved ({len(summ)} gifs)", flush=True)
    return summ


def main():
    safe.utf8_console()
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    t0 = time.time()
    if stage in ("golden", "all"):
        ok, _ = golden()
        if stage == "golden":
            print(f"[{time.time()-t0:.0f}s]", flush=True)
            return
    led = None
    if stage in ("run", "graphs", "all"):
        led = run_all(make_graphs=(stage in ("graphs", "all", "run")))
    if stage in ("sims", "all"):
        render_sims(led)
    print(f"DONE [{time.time()-t0:.0f}s]", flush=True)


if __name__ == "__main__":
    main()
