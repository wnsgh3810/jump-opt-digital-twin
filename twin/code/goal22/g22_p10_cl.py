"""GOAL22 P10-A2 — 실험 A: 실데이터 (q_des, dq_des)로 P13h 트윈 폐루프 PD 재현.

법칙 (P10-A1 회귀로 확정):
  0324: hip PD(dq_des=0), knee PD(dq_des=0)+tau_ff(desiredTorque)
  0421: PD(dq_des=0) / 0424·0602: PD(dq_des 인가)
게인 = 폴더 라벨 그대로 + clip(±18) + paper a_hat 액추에이터 변환 (포화·손실을 물리로 재현).
비교: shaft τ_sim vs paper(currentTorque) [P13h 규약: 실측 τ에 −1.5ms 시프트],
      cmd τ_sim vs raw currentTorque, 상태 q/dq, h.
변형 (ii): 게인 4개(log)를 상태 매칭으로 Nelder-Mead 재적합 후 동일 비교 (사용자 지시).
"""
# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------
import sys, json
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
sys.path.insert(0, (LEGACY_ROOT + "/goal12/data_loaders"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13
from g22_p10_pdlaw import SETS, label_gains, read_joint
from load_combined_15trial import paper_a_hat

SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad")
PNGD = SCR / "g22_cl_gallery"; PNGD.mkdir(parents=True, exist_ok=True)
OUT = Path(__file__).parent / "p10_cl.json"
SD = -0.0015
T_SETTLE = 0.4
T_AFTER = 0.6
OFFK = {"jump_0324": ("o1_0324", "o2_0324"), "jump_position_0421": ("o1_0421", "o2_0421"),
        "jump_0424": ("o1_0424", "o2_0424")}
# 공급 토크 천장 (소프트웨어 PD 클립 아님 — 사용자 07-09 확인).
# 토크 채널은 12bit ±18 랩 -> 사용자 MATLAB 언랩(span36, max_wrap1, 복원한계 ±54)으로 복원됨.
# 진짜 천장 증거는 0424/0602의 ~35.5 (게인 60~500 무관 플래토 = 드라이버 전류 한계 추정).
# 0324(18.8)/0421(29)의 낮은 최대값은 수요 한계일 뿐 -> 전 세션 공통 35.5 적용.
CUR_CAP = {"jump_0324": 35.5, "jump_position_0421": 35.5,
           "jump_0424": 35.5, "jump_0602": 35.5}
_L = {}


def winit():
    PH.winit()
    P12 = P13._M["P12"]
    if P12._G["trials"] is None:
        P12.build_trials()
    x_h = np.array(json.load(open(Path(__file__).parent / "fourbar_p13h_candidate.json"))["x"])
    S = P12._G["S"]; FR = P12._G["FR"]; FL = P12._G["FL"]; mj = P12._G["mujoco"]
    dd = dict(zip(FR.NAMES, x_h[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, x_h[26:32])))
    _L.update(model=mj.MjModel.from_xml_string(xml), mj=mj, S=S, dd=dd, P12=P12)
    # h_real 지도
    hmap = {}
    for tr_ in P12._G["trials"]:
        if tr_["isj"]:
            hmap[(tr_["ds"], str(tr_["sub"]))] = float(tr_["h_real"])
    _L["hmap"] = hmap


def load_trial_xlsx(ds, root, sub):
    hip = read_joint(root / sub / "hip.xlsx")
    knee = read_joint(root / sub / "knee.xlsx")
    n = min(len(hip["Time"]), len(knee["Time"]))
    t = hip["Time"][:n] - hip["Time"][0]
    try:
        grf = pd.read_excel(root / sub / "GRF.xlsx")["Current_GRF"].values.astype(float)
        grf_real = grf[:n] if len(grf) >= n else None
    except Exception:
        grf_real = None
    d = dict(t=t)
    for nm, src in [("1", hip), ("2", knee)]:
        d["q" + nm] = src["currentAngle"][:n]
        d["qd" + nm] = src["desiredAngle"][:n]
        d["dq" + nm] = src["currentAngleVelocity"][:n]
        d["dqd" + nm] = src["desiredAngleVelocity"][:n]
        d["traw" + nm] = src["currentTorque"][:n]
        d["tdes" + nm] = src["desiredTorque"][:n]
    d["tau1_paper"] = paper_a_hat(d["traw1"], d["dq1"])
    d["tau2_paper"] = paper_a_hat(d["traw2"], d["dq2"])
    d["grf_real"] = grf_real
    return d


def run_cl(ds, d, gains, use_ff_knee, use_dqdes):
    """폐루프 sim. 반환 로그 dict (canonical frame) 또는 None."""
    mj = _L["mj"]; S = _L["S"]; model = _L["model"]; dd = _L["dd"]
    kp1, kd1, kp2, kd2 = gains
    k1, k2 = OFFK.get(ds, (None, None))
    o1 = dd.get(k1, 0.0) if k1 else 0.0; o2 = dd.get(k2, 0.0) if k2 else 0.0
    t = d["t"]
    qd1 = d["qd1"] + o1; qd2 = d["qd2"] + o2       # sim 좌표계 보정
    dqd1 = d["dqd1"] if use_dqdes else np.zeros_like(t)
    dqd2 = d["dqd2"] if use_dqdes else np.zeros_like(t)
    md = mj.MjData(model)
    sq1, sq2 = -qd1[0] - np.pi / 2, -qd2[0]
    # FK 초기 높이
    md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    bz0 = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qpos[:] = [bz0, sq1, sq2, -sq2, sq2]; md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((T_SETTLE + t[-1] + T_AFTER) / dt)
    tl = np.arange(N) * dt - T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "cmd1", "cmd2",
                                  "sh1", "sh2", "bz", "grf"]}
    for k in range(N):
        tc = tl[k]
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        if tc < 0:
            c1 = S.SETTLE_KP * (qd1[0] - q1c) + S.SETTLE_KD * (0 - v1c)
            c2 = S.SETTLE_KP * (qd2[0] - q2c) + S.SETTLE_KD * (0 - v2c)
        else:
            tm = min(tc, t[-1])
            c1 = kp1 * (np.interp(tm, t, qd1) - q1c) + kd1 * (np.interp(tm, t, dqd1) - v1c)
            c2 = kp2 * (np.interp(tm, t, qd2) - q2c) + kd2 * (np.interp(tm, t, dqd2) - v2c)
            if use_ff_knee:
                c2 += np.interp(tm, t, d["tdes2"])
        # 캡/클립 전혀 없음 (사용자 07-09 최종): PD 커맨드 -> a_hat만.
        # 데이터의 |raw| 천장 ~35.5(속도 무관 평탄)는 하드웨어 전류 한계로 추정되나
        # 정체 미확정(R-Link 설정 확인 대기) — sim에 인위 반영하지 않음.
        c1 = float(c1); c2 = float(c2)
        s1 = float(paper_a_hat(np.array([c1]), np.array([v1c]))[0])
        s2 = float(paper_a_hat(np.array([c2]), np.array([v2c]))[0])
        md.ctrl[:] = [-s1, -s2]
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        L["q1"][k] = -md.qpos[1] - np.pi / 2; L["q2"][k] = -md.qpos[2]
        L["dq1"][k] = -md.qvel[1]; L["dq2"][k] = -md.qvel[2]
        L["cmd1"][k] = c1; L["cmd2"][k] = c2; L["sh1"][k] = s1; L["sh2"][k] = s2
        L["bz"][k] = md.qpos[0]
        gz = 0.0
        for ci in range(md.ncon):
            cf = np.zeros(6)
            mj.mj_contactForce(model, md, ci, cf)
            gz += (md.contact[ci].frame.reshape(3, 3).T @ cf[:3])[2]
        L["grf"][k] = gz
    L["t"] = tl
    L["o"] = (o1, o2)
    return L


def metrics(ds, d, L):
    t = d["t"]
    mk = (L["t"] >= 0) & (L["t"] <= t[-1])
    f = lambda a: np.interp(t, L["t"][mk], a[mk])
    r = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
    # P13h 규약: 실측 τ 타임라인 −1.5ms 정렬
    tp1 = np.interp(t - SD, t, d["tau1_paper"]); tp2 = np.interp(t - SD, t, d["tau2_paper"])
    tr1 = np.interp(t - SD, t, d["traw1"]); tr2 = np.interp(t - SD, t, d["traw2"])
    o1, o2 = L["o"]
    return dict(
        tau1=r(f(L["sh1"]), tp1), tau2=r(f(L["sh2"]), tp2),
        tau1_raw=r(f(L["cmd1"]), tr1), tau2_raw=r(f(L["cmd2"]), tr2),
        tau1_pk=(float(np.max(np.abs(f(L["sh1"])))), float(np.max(np.abs(tp1)))),
        tau2_pk=(float(np.max(np.abs(f(L["sh2"])))), float(np.max(np.abs(tp2)))),
        q1=r(f(L["q1"]) - o1, d["q1"]), q2=r(f(L["q2"]) - o2, d["q2"]),
        dq1=r(f(L["dq1"]), d["dq1"]), dq2=r(f(L["dq2"]), d["dq2"]),
        h=float(L["bz"].max()))


def fig_trial(ds, sub, d, L, m, tag):
    """패널 순서 (사용자 07-09): q(합침), dq1, dq2 / tau_hip, tau_knee, GRF(실측 포함).
    q_des만 점선, 나머지 전부 실선. ASCII-safe 라벨."""
    t = d["t"]
    mk = (L["t"] >= -0.02) & (L["t"] <= t[-1] + 0.01)
    o1, o2 = L["o"]
    tp1 = np.interp(t - SD, t, d["tau1_paper"]); tp2 = np.interp(t - SD, t, d["tau2_paper"])
    fig, ax = plt.subplots(2, 3, figsize=(14.5, 7))
    # [0,0] q 합침 — 기본 3색만 (사용자 07-09): 파랑=sim, 주황=real, 초록=q_des
    ax[0, 0].plot(L["t"][mk], np.degrees(L["q1"][mk] - o1), "C0", lw=1.3, label="q1 sim")
    ax[0, 0].plot(t, np.degrees(d["q1"]), "C1", lw=1.3, label="q1 real")
    ax[0, 0].plot(L["t"][mk], np.degrees(L["q2"][mk] - o2), "C0", lw=1.3, label="q2 sim")
    ax[0, 0].plot(t, np.degrees(d["q2"]), "C1", lw=1.3, label="q2 real")
    ax[0, 0].plot(t, np.degrees(d["qd1"]), "C2--", lw=1.1, label="q_des")
    ax[0, 0].plot(t, np.degrees(d["qd2"]), "C2--", lw=1.1, label="_nolegend_")
    ax[0, 0].set_ylabel("q [deg]")
    # [0,1] dq1 / [0,2] dq2
    ax[0, 1].plot(L["t"][mk], L["dq1"][mk], lw=1.3, label="sim")
    ax[0, 1].plot(t, d["dq1"], lw=1.3, label="real")
    ax[0, 1].set_ylabel("dq1 hip [rad/s]")
    ax[0, 2].plot(L["t"][mk], L["dq2"][mk], lw=1.3, label="sim")
    ax[0, 2].plot(t, d["dq2"], lw=1.3, label="real")
    ax[0, 2].set_ylabel("dq2 knee [rad/s]")
    # [1,0] tau hip / [1,1] tau knee
    ax[1, 0].plot(L["t"][mk], L["sh1"][mk], lw=1.3, label="sim shaft tau")
    ax[1, 0].plot(t, tp1, lw=1.3, label="real paper tau (-1.5ms)")
    ax[1, 0].set_ylabel("hip tau [Nm]")
    ax[1, 1].plot(L["t"][mk], L["sh2"][mk], lw=1.3, label="sim shaft tau")
    ax[1, 1].plot(t, tp2, lw=1.3, label="real paper tau (-1.5ms)")
    ax[1, 1].set_ylabel("knee tau [Nm]")
    # [1,2] GRF (sim + 실측)
    ax[1, 2].plot(L["t"][mk], L["grf"][mk], lw=1.3, label="sim")
    if d.get("grf_real") is not None:
        ax[1, 2].plot(t, d["grf_real"], lw=1.3, label="real")
    ax[1, 2].set_ylabel("GRF z [N]")
    for a in ax.flat:
        a.grid(alpha=0.3); a.legend(fontsize=7); a.set_xlabel("t [s]")
    hr = m.get("h_real", float("nan"))
    fig.suptitle(f"{ds}/{sub} [{tag}] — 폐루프 PD 재현 (P13h)  "
                 f"tau RMSE hip {m['tau1']:.2f} / knee {m['tau2']:.2f} Nm · "
                 f"h_sim {m['h']:.2f} m / h_real {hr:.2f} m")
    fig.tight_layout()
    fig.savefig(PNGD / f"{ds}__{sub}__{tag}.png", dpi=100)
    plt.close(fig)


def main():
    winit()
    res = {}
    from scipy.optimize import minimize
    for ds, (root, subs) in SETS.items():
        use_dqdes = ds in ("jump_0424", "jump_0602")
        for sub in subs:
            d = load_trial_xlsx(ds, root, sub)
            lg = label_gains(ds, sub)
            ffk = (ds == "jump_0324")
            L = run_cl(ds, d, lg, ffk, use_dqdes)
            if L is None:
                print(ds, sub, "CRASH", flush=True)
                continue
            m = metrics(ds, d, L)
            m["h_real"] = _L["hmap"].get((ds, sub), np.nan)
            fig_trial(ds, sub, d, L, m, "label")
            # (ii) 상태-매칭 게인 재적합
            def obj(lx):
                g = np.exp(lx)
                Lx = run_cl(ds, d, g, ffk, use_dqdes)
                if Lx is None:
                    return 1e6
                mx = metrics(ds, d, Lx)
                return 100 * (mx["q1"] + mx["q2"]) + 10 * (mx["dq1"] + mx["dq2"])
            r0 = minimize(obj, np.log(np.maximum(lg, 0.05)), method="Nelder-Mead",
                          options={"maxfev": 120, "xatol": 0.02, "fatol": 0.05})
            gfit = np.exp(r0.x)
            Lf = run_cl(ds, d, gfit, ffk, use_dqdes)
            mf = metrics(ds, d, Lf) if Lf else None
            if Lf:
                mf["h_real"] = m["h_real"]
                fig_trial(ds, sub, d, Lf, mf, "fit")
            # canonical 애니메이션용 궤적 저장 (label/fit 둘 다)
            npzd = Path(__file__).parent / "p10_cl_traj"; npzd.mkdir(exist_ok=True)
            for tag, LL in [("label", L), ("fit", Lf)]:
                if LL is None:
                    continue
                np.savez(npzd / f"{ds}__{sub}__{tag}.npz",
                         t=LL["t"], q1=LL["q1"], q2=LL["q2"], bz=LL["bz"],
                         dq1=LL["dq1"], dq2=LL["dq2"], sh1=LL["sh1"], sh2=LL["sh2"],
                         grf=LL["grf"], o=np.array(LL["o"]),
                         t_real=d["t"], q1_real=d["q1"], q2_real=d["q2"])
            res[f"{ds}/{sub}"] = dict(label=m, fit=mf,
                                      gains_label=list(lg),
                                      gains_fit=[float(v) for v in gfit])
            print(f"{ds}/{sub}: [label] τ1 {m['tau1']:.2f} τ2 {m['tau2']:.2f} "
                  f"q2 {m['q2']:.3f} dq2 {m['dq2']:.2f} h {m['h']:.2f}/{m['h_real']:.2f}"
                  + (f"  [fit] τ1 {mf['tau1']:.2f} τ2 {mf['tau2']:.2f} q2 {mf['q2']:.3f} "
                     f"dq2 {mf['dq2']:.2f} h {mf['h']:.2f}" if mf else ""), flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
    # 데이터셋 요약
    print("\n=== 실험 A 요약 (데이터셋 평균, label 게인) ===")
    for ds in SETS:
        ks = [k for k in res if k.startswith(ds + "/") and res[k]["label"]]
        if not ks:
            continue
        avg = lambda f: np.mean([res[k]["label"][f] for k in ks])
        print(f"{ds:22s} τ_hip {avg('tau1'):.2f}Nm τ_knee {avg('tau2'):.2f}Nm "
              f"q1 {avg('q1'):.3f} q2 {avg('q2'):.3f} dq1 {avg('dq1'):.2f} dq2 {avg('dq2'):.2f}",
              flush=True)
    print("saved", OUT.name, flush=True)


if __name__ == "__main__":
    main()
