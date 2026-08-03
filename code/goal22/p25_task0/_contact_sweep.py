# -*- coding: utf-8 -*-
"""접촉 스윕 (Stage 2) — 레벨1 μ × 레벨2 접선 컴플라이언스.
μ ∈ {1.0, 0.9, 0.85} (데이터 하한 μ_s≥0.85 준수) × solreffriction ∈ {강체, 0.02, 0.05}.
평가: 스크리닝 6 CL 슬립궤적 RMSE + 이지속도 오차 + Mode A 가드(0602×2+0424+exp4 멀티플슈팅)."""
import os, sys, json, time, tempfile
for k in ("P23_SPRING_GATED", "P23_RISE_GATED", "P24_HIP_LAW", "P24_REFIT"):
    os.environ.setdefault(k, "1")
from pathlib import Path
import numpy as np
import pandas as pd
import mujoco
from scipy.signal import savgol_filter
from scipy.interpolate import CubicSpline

HERE = Path(__file__).parent
for p in [HERE, HERE.parent / 'p25_deploy', HERE.parent / 'p23_veins', HERE.parent.parent / 'bench']:
    sys.path.insert(0, str(p))
import p25_a_twin as TW
import t0nc_cma as C
import safe

tw = TW.twin()
P = tw["P"]; A = P.A_PAPER; ahat = P.J.ahat
C.TG = np.arange(0.0, TW.T_END + tw['dt'], tw['dt'])
model0 = tw["model"]
FOOT = mujoco.mj_name2id(model0, mujoco.mjtObj.mjOBJ_GEOM, "foot")
ROOT = Path("C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
Lm = 0.25


def onset(q, thr=1.0):
    b = np.min(q); i = np.where(q > b + thr)[0]
    return int(i[0]) if len(i) else 0


def grids(npz):
    z = np.load(HERE / npz)
    s1 = CubicSpline(C.KTC, z['knots_qd1'], bc_type='natural')
    s2 = CubicSpline(C.KTC, z['knots_qd2'], bc_type='natural')
    return s1(C.TG), s2(C.TG), s1(C.TG, 1), s2(C.TG, 1)


def old_fam(G):
    th = {60: 0.70, 120: 0.50, 150: 0.40}
    tk = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
    return (th.get(G[0], 0.40), 0.20, tk.get(G[2], 0.656), 0.20)


CLT = [("exp1", "26_07_22", "150_2.2_250_3", "t0nc_cl_pd15.npz", (150, 2.2, 250, 3), 0.13),
       ("exp1", "26_07_22", "150_3.3_500_5", "t0nc_cl_pd15.npz", (150, 3.3, 500, 5), 0.13),
       ("exp2", "26_07_23", "150_2.2_250_3", "t0nc_cl_v4.npz", (150, 2.2, 250, 3), 0.19),
       ("exp3", "26_07_24", "150_2.2_250_3", "t0nc_cl_v7.npz", (150, 2.2, 250, 3), 0.13),
       ("exp4", "26_07_25", "150_2.2_250_3", "t0nc_cl_v8.npz", (150, 2.2, 250, 3), 0.13),
       ("exp4", "26_07_25", "200_2.5_250_3", "t0nc_cl_v8.npz", (200, 2.5, 250, 3), 0.13)]

MEAS = {}
for expn, date, gf, npz, G, wb in CLT:
    hp = pd.read_excel(ROOT / date / gf / "hip.xlsx")
    kn = pd.read_excel(ROOT / date / gf / "knee.xlsx")
    n = min(len(hp), len(kn)); hp = hp.iloc[:n].reset_index(drop=True); kn = kn.iloc[:n].reset_index(drop=True)
    t = hp['Time'].values - hp['Time'].values[0]
    if date in ("26_07_22", "26_07_23"):
        o = onset(np.degrees(hp['desiredAngle'].values)); t = t - t[o]
    m = (t >= 0) & (t <= wb)
    q1 = hp['currentAngle'].values; q2 = kn['currentAngle'].values
    fkx = Lm * (np.cos(q1) + np.cos(q1 + q2))
    i0 = int(np.argmax(m))
    slip = (fkx - fkx[i0]) * 1000
    wl = min(11, (n // 2) * 2 - 1)
    bz = savgol_filter(-Lm * (np.sin(q1) + np.sin(q1 + q2)), wl, 3)
    vbz = np.gradient(bz, t)
    try:
        gr = pd.read_excel(ROOT / date / gf / "GRF.xlsx")
        tg = gr['Time'].values - gr['Time'].values[0]
        if date in ("26_07_22", "26_07_23"):
            oo = onset(np.degrees(hp['desiredAngle'].values))
            tg = tg - (hp['Time'].values[oo] - hp['Time'].values[0])
        grm = np.interp(t, tg, gr['Current_GRF'].values)
        idx = np.where(m & (grm > 15))[0]
        ilo = idx[-1] if len(idx) else np.where(m)[0][-1]
    except Exception:
        ilo = np.where(m)[0][-1]
    mv = (t >= t[ilo] - 0.03) & (t <= t[ilo])
    vlo = float(vbz[mv].max()) if mv.any() else 0.0
    MEAS[(expn, gf)] = dict(t=t[m], slip=slip[m], vlo=vlo)

# Mode A 가드 준비
import p25_d_deploy as D
import p23_v6_runners as RU
D.setup(); GD = D.G
ksv, krefv, _ = RU.spr_resolve(model0, GD["SPR"])
dof_knee = safe.dofadr(model0, "knee", mujoco)
iq_k = safe.qadr(model0, "knee", mujoco)
SD = P.SD
MAT = [("0602", "26_06_02/position", "60_0.75_60_2", 0.14),
       ("0602", "26_06_02/position", "150_2.2_250_3", 0.14),
       ("0424", "26_04_24", "150_2.2_250_3", 0.14),
       ("exp4", "26_07_25", "150_2.2_250_3", None)]
MA = {}
for lab, date, gf, wb in MAT:
    hp = pd.read_excel(ROOT / date / gf / "hip.xlsx")
    kn = pd.read_excel(ROOT / date / gf / "knee.xlsx")
    n = min(len(hp), len(kn)); hp = hp.iloc[:n].reset_index(drop=True); kn = kn.iloc[:n].reset_index(drop=True)
    t = hp['Time'].values - hp['Time'].values[0]
    q1 = hp['currentAngle'].values; v1 = hp['currentAngleVelocity'].values; raw1 = hp['currentTorque'].values
    tk_ = kn['Time'].values - kn['Time'].values[0]
    q2 = np.interp(t, tk_, kn['currentAngle'].values)
    v2 = np.interp(t, tk_, kn['currentAngleVelocity'].values)
    raw2 = np.interp(t, tk_, kn['currentTorque'].values)
    nn = len(t); wl = min(11, (nn // 2) * 2 - 1)
    q1m = -q1 - np.pi / 2; q2m = -q2
    dq1m = savgol_filter(-v1, wl, 3); dq2m = savgol_filter(-v2, wl, 3)
    lam = RU.supp_vec(raw2, v2, GD["LAW"]) + RU.rise_term(v2, GD["KR"], GD["LAW"][2])
    a1v = ahat(A, raw1, v1) + RU.hip_supp_vec(raw1, v1, raw2, v2)
    th = -(a1v); tkq = -(ahat(A, raw2, v2) + lam)
    tau_h = np.interp(t - SD, t, th); tau_k = np.interp(t - SD, t, tkq)
    hl = RU.hl_vec(raw2, v2, GD["SPR"])
    if wb is not None:
        o = onset(np.degrees(hp['desiredAngle'].values)); t_lo = t[o]; t_hi = min(t[o] + wb, t[-1])
    else:
        t_lo, t_hi = t[0], t[-1]
    MA[lab + "/" + gf] = dict(t=t, q1m=q1m, q2m=q2m, dq1m=dq1m, dq2m=dq2m,
                              tau_h=tau_h, tau_k=tau_k, hl=hl, lo=t_lo, hi=t_hi)


def modea_score(model):
    d = mujoco.MjData(model)
    fg = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "foot")
    RF = float(model.geom_size[fg][0])
    tot = 0.0
    for k_, pp in MA.items():
        t = pp['t']; nn = len(t)
        bz = np.zeros(nn)
        for i in range(nn):
            d.qpos[:] = [1.0, pp['q1m'][i], pp['q2m'][i], -pp['q2m'][i], pp['q2m'][i]]
            mujoco.mj_forward(model, d)
            bz[i] = 1.0 - float(d.geom_xpos[fg][2]) + RF
        vbz = np.gradient(bz, t)
        dt = model.opt.timestep
        starts = []
        t0_ = pp['lo']
        while t0_ <= pp['hi'] - 0.05:
            starts.append(int(np.argmin(np.abs(t - t0_)))); t0_ += 0.05
        for i0 in starts:
            t1 = min(t[i0] + 0.10, t[-1])
            d.qpos[:] = [bz[i0], pp['q1m'][i0], pp['q2m'][i0], -pp['q2m'][i0], pp['q2m'][i0]]
            d.qvel[:] = [vbz[i0], pp['dq1m'][i0], pp['dq2m'][i0], -pp['dq2m'][i0], pp['dq2m'][i0]]
            mujoco.mj_forward(model, d)
            nst = int(round((t1 - t[i0]) / dt))
            ts = []; Q1 = []; Q2 = []; V1 = []; V2 = []
            ok = True
            for kk in range(nst):
                tc = t[i0] + kk * dt
                d.ctrl[:] = [np.interp(tc, t, pp['tau_h']), np.interp(tc, t, pp['tau_k'])]
                d.qfrc_applied[dof_knee] = ksv * (krefv - float(d.qpos[iq_k])) * float(np.interp(tc, t, pp['hl']))
                try:
                    mujoco.mj_step(model, d)
                except Exception:
                    ok = False; break
                ts.append(tc + dt); Q1.append(d.qpos[1]); Q2.append(d.qpos[2])
                V1.append(d.qvel[1]); V2.append(d.qvel[2])
            if not ok or len(ts) < 3:
                tot += 10.0
                continue
            ts = np.array(ts)
            m = (t >= ts[0]) & (t <= ts[-1])
            if m.sum() < 3:
                continue

            def r(sim, real):
                return float(np.sqrt(np.mean((np.interp(t[m], ts, np.array(sim)) - real[m]) ** 2)))
            tot += r(Q1, pp['q1m']) + r(Q2, pp['q2m']) + 0.1 * (r(V1, pp['dq1m']) + r(V2, pp['dq2m']))
    return tot


def build_variant(mu, sf):
    xmlp = Path(tempfile.gettempdir()) / '_twin_sweep.xml'
    mujoco.mj_saveLastXML(str(xmlp), model0)
    floor_name = None
    for i in range(model0.ngeom):
        nm = mujoco.mj_id2name(model0, mujoco.mjtObj.mjOBJ_GEOM, i)
        if model0.geom_bodyid[i] == 0 and nm:
            floor_name = nm
    if sf is not None and floor_name:
        x = xmlp.read_text()
        pair = ('<contact><pair geom1="foot" geom2="' + floor_name + '" condim="3" '
                'friction="' + f"{mu} {mu} 0.005 0.0001 0.0001" + '" '
                'solreffriction="' + f"{sf} 1" + '"/></contact>')
        x2 = safe.xml_patch(x, "</mujoco>", pair + "</mujoco>", count=1)
        xmlp.write_text(x2)
    m2 = mujoco.MjModel.from_xml_path(str(xmlp))
    fg = mujoco.mj_name2id(m2, mujoco.mjtObj.mjOBJ_GEOM, "foot")
    m2.geom_friction[fg][0] = mu
    for i in range(m2.ngeom):
        if m2.geom_bodyid[i] == 0:
            m2.geom_friction[i][0] = mu
    return m2


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


BAITS = {}
for expn, date, gf, npz, G, wb in CLT:
    if npz not in BAITS:
        BAITS[npz] = grids(npz)

t0 = time.time()
RES = []
for mu in [1.0, 0.9, 0.85]:
    for sf in [None, 0.02, 0.05]:
        try:
            m2 = build_variant(mu, sf)
        except Exception as e:
            print(f"mu={mu} sf={sf}: build FAIL {e}", flush=True)
            RES.append(dict(mu=mu, sf=sf or 0, fail="build"))
            continue
        old_model = tw["model"]
        tw["model"] = m2
        slips = []; vlos = []
        okall = True
        for expn, date, gf, npz, G, wb in CLT:
            g1, g2, dg1, dg2 = BAITS[npz]
            try:
                L = TW.rollout_cl(tw, C.TG, g1, g2, dg1, dg2, G, alphas=old_fam(G),
                                  t_end=TW.T_END, record=True)
            except Exception as e:
                okall = False
                print(f"  rollout FAIL {expn}/{gf}: {e}", flush=True)
                break
            D_ = MEAS[(expn, gf)]
            q1s = np.interp(D_['t'], L['t'], L['q1'])
            q2s = np.interp(D_['t'], L['t'], L['q2'])
            fx = Lm * (np.cos(q1s) + np.cos(q1s + q2s))
            ss = (fx - fx[0]) * 1000
            slips.append(rms(ss - D_['slip']))
            bzs = np.interp(D_['t'], L['t'], L['bz'])
            vzs = np.gradient(bzs, D_['t'])
            vlos.append(abs(float(vzs[-5:].max()) - D_['vlo']))
        tw["model"] = old_model
        if not okall:
            RES.append(dict(mu=mu, sf=sf or 0, fail="rollout"))
            continue
        ma = modea_score(m2)
        RES.append(dict(mu=mu, sf=sf or 0, slip=float(np.mean(slips)),
                        vlo=float(np.mean(vlos)), modeA=float(ma)))
        print(f"mu={mu} sf={sf}: slipRMSE {np.mean(slips):.1f}mm  vlo오차 {np.mean(vlos):.2f}m/s  "
              f"ModeA가드 {ma:.3f}  [{time.time() - t0:.0f}s]", flush=True)
json.dump(RES, open(HERE / '_contact_sweep.json', 'w'))
print("DONE")
