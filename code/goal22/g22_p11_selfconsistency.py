"""GOAL22 P11 — 실험 B: 최적화 산출 (q*, dq*, τ*)로 트윈 PD 제어 시 τ 자기일관성.

deploy CSV (G22 CMA s0.85/s1.00; P13e 트윈에서 최적화)를:
  플랜트 = P13e (자기일관성) / P13h (모델 교차 = 불확실성 하 τ-갭 하한)
  모드   = PD only / PD+τ_ff / (참조) τ_ff only
로 폐루프 실행 → τ_applied vs τ* 비교 (push 구간 RMS/max), PD 기여, h.
τ는 shaft 공간 (트윈 자기일관성 실험 — 실기 전개 시 a_hat 역변환 별도).
게인: 실험 관례 중간값 hip 120/2.2, knee 150/2.5.
"""
import sys, json
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13

SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad")
OUT = Path(__file__).parent / "p11_selfconsistency.json"
KP1, KD1, KP2, KD2 = 120.0, 2.2, 150.0, 2.5
T_SETTLE = 0.4
T_AFTER = 0.9
CSVS = {"s0.85": Path(__file__).parent / "deploy_g22/jump_g22cma_s0.85_h0.975m.csv",
        "s1.00": Path(__file__).parent / "deploy_g22/jump_g22cma_s1.00_h1.209m.csv"}
_L = {}


def winit():
    PH.winit()
    P12 = P13._M["P12"]
    S = P12._G["S"]; FR = P12._G["FR"]; FL = P12._G["FL"]; mj = P12._G["mujoco"]

    def build(x32):
        dd = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
        S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
        S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
        S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
        sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
        xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                     dict(zip(P13.N6, np.asarray(x32)[26:32])))
        return mj.MjModel.from_xml_string(xml)

    x_e = np.array(json.load(open(REPO / "code/goal21/fourbar_honest_canonical.json"))["x"])
    x_h = np.array(json.load(open(Path(__file__).parent / "fourbar_p13h_candidate.json"))["x"])
    _L.update(mj=mj, S=P12._G["S"], m_e=build(x_e), m_h=build(x_h))


def run(plant, csv, mode):
    mj = _L["mj"]; S = _L["S"]; model = _L[plant]
    a = np.genfromtxt(csv, delimiter=",", names=True)
    t = a["t_s"]; T = float(t[-1])
    qd1, qd2 = a["q1_des_rad"], a["q2_des_rad"]
    vd1, vd2 = a["dq1_des_rad_s"], a["dq2_des_rad_s"]
    f1, f2 = a["tau1_ff_Nm"], a["tau2_ff_Nm"]
    d = mj.MjData(model)
    sq1, sq2 = -qd1[0] - np.pi / 2, -qd2[0]
    d.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, d)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    bz0 = 1.0 - float(d.geom_xpos[fg][2]) + S.FOOT_RADIUS
    d.qpos[:] = [bz0, sq1, sq2, -sq2, sq2]; d.qvel[:] = 0
    mj.mj_forward(model, d)
    dt = model.opt.timestep
    N = int((T_SETTLE + T + T_AFTER) / dt)
    tl = np.arange(N) * dt - T_SETTLE
    L = {k: np.zeros(N) for k in ["tau1", "tau2", "q1", "q2", "dq1", "dq2", "bz"]}
    for k in range(N):
        tc = tl[k]
        q1c = -d.qpos[1] - np.pi / 2; q2c = -d.qpos[2]
        v1c = -d.qvel[1]; v2c = -d.qvel[2]
        if tc < 0:
            c1 = S.SETTLE_KP * (qd1[0] - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (qd2[0] - q2c) - S.SETTLE_KD * v2c
        elif tc <= T:
            e1 = np.interp(tc, t, qd1) - q1c; e2 = np.interp(tc, t, qd2) - q2c
            ev1 = np.interp(tc, t, vd1) - v1c; ev2 = np.interp(tc, t, vd2) - v2c
            c1 = c2 = 0.0
            if "pd" in mode:
                c1 += KP1 * e1 + KD1 * ev1; c2 += KP2 * e2 + KD2 * ev2
            if "ff" in mode:
                c1 += float(np.interp(tc, t, f1)); c2 += float(np.interp(tc, t, f2))
        else:
            c1 = c2 = 0.0
        # 토크-속도 봉투 (계획 rollout과 동일 물리 — g22_p6_sampling.tau_avail)
        from g22_p6_sampling import tau_avail
        av1 = tau_avail(abs(v1c)); av2 = tau_avail(abs(v2c))
        c1 = float(np.clip(c1, -min(18, av1), min(18, av1)))
        c2 = float(np.clip(c2, -min(18, av2), min(18, av2)))
        d.ctrl[:] = [-c1, -c2]
        try:
            mj.mj_step(model, d)
        except Exception:
            return None, None
        L["tau1"][k] = c1; L["tau2"][k] = c2
        L["q1"][k] = -d.qpos[1] - np.pi / 2; L["q2"][k] = -d.qpos[2]
        L["dq1"][k] = -d.qvel[1]; L["dq2"][k] = -d.qvel[2]
        L["bz"][k] = d.qpos[0]
    L["t"] = tl
    mk = (tl >= 0) & (tl <= T)
    g = lambda arr: np.interp(t, tl[mk], arr[mk])
    r = lambda a_, b_: float(np.sqrt(np.mean((a_ - b_) ** 2)))
    met = dict(
        dtau1=r(g(L["tau1"]), f1), dtau2=r(g(L["tau2"]), f2),
        dtau1_max=float(np.max(np.abs(g(L["tau1"]) - f1))),
        dtau2_max=float(np.max(np.abs(g(L["tau2"]) - f2))),
        q1=r(g(L["q1"]), qd1), q2=r(g(L["q2"]), qd2),
        dq1=r(g(L["dq1"]), vd1), dq2=r(g(L["dq2"]), vd2),
        h=float(L["bz"].max()))
    return met, (L, t, f1, f2, qd2)


def main():
    winit()
    res = {}
    figs = {}
    for tag, csv in CSVS.items():
        for plant in ["m_e", "m_h"]:
            for mode in ["pd", "pdff", "ff"]:
                met, aux = run(plant, csv, mode)
                key = f"{tag}/{plant}/{mode}"
                res[key] = met
                if met:
                    print(f"{key:22s} τ-갭 RMS h/k {met['dtau1']:.2f}/{met['dtau2']:.2f} "
                          f"max {met['dtau1_max']:.1f}/{met['dtau2_max']:.1f}  "
                          f"q2 {met['q2']:.3f} dq2 {met['dq2']:.2f}  h {met['h']:.3f}", flush=True)
                if met and tag == "s0.85" and mode == "pdff":
                    figs[plant] = aux
    # 그림: s0.85 PD+ff, P13e vs P13h 플랜트
    fig, ax = plt.subplots(2, 2, figsize=(13, 7.5))
    for col, (plant, nm) in enumerate([("m_e", "플랜트=P13e(자기일관)"), ("m_h", "플랜트=P13h(교차)")]):
        if plant not in figs:
            continue
        L, t, f1, f2, qd2 = figs[plant]
        mk = (L["t"] >= -0.02) & (L["t"] <= t[-1] + 0.02)
        ax[0, col].plot(L["t"][mk] * 1e3, L["tau1"][mk], lw=1.3, label="tau 인가 (PD+ff)")
        ax[0, col].plot(t * 1e3, f1, lw=1.3, label="tau* 계획")
        ax[0, col].set_title(f"hip — {nm}"); ax[0, col].set_ylabel("tau [Nm]")
        ax[1, col].plot(L["t"][mk] * 1e3, L["tau2"][mk], lw=1.3, label="tau 인가 (PD+ff)")
        ax[1, col].plot(t * 1e3, f2, lw=1.3, label="tau* 계획")
        ax[1, col].set_title(f"knee — {nm}"); ax[1, col].set_ylabel("tau [Nm]")
    for a in ax.flat:
        a.grid(alpha=0.3); a.legend(fontsize=8); a.set_xlabel("t [ms]")
    fig.suptitle("실험 B — 최적화 tau* vs PD+ff 폐루프 인가 tau (deploy s0.85, 게인 120/2.2·150/2.5)")
    fig.tight_layout()
    fig.savefig(SCR / "g22_cl_gallery" / "expB_selfconsistency.png", dpi=115)
    json.dump(res, open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)


if __name__ == "__main__":
    main()
