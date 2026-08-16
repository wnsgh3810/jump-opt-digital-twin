# -*- coding: utf-8 -*-
"""fs_cvt_plot — 0429: 실측 vs old α(5q 정본) vs 현행 fs(6q) 겹침 그래프.

ModeA(측정 raw 주입, R19 재생창): q1·q2(크랭크)·dq1·dq2 + τ 주입(공통) 패널.
CL(폴더 게인 PD, *2 fullspan i_desc~t_lo): q1·q2·dq1·dq2·τ1(lpf 관측)·τ2.
old α CL = 5q 직결 hip 미러 (TK·kd0.2 동일 컨벤션, 벨트 α 집약 표현 공유).
출력: _plots/*.png. CLI: python fs_cvt_plot.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
for k, v in (("FS_FIXED", "1"), ("FS_FADE", "1"), ("FS_TAUOBS", "lpf"), ("FS_TC", "0.010"),
             ("FS_KNEE_REL", "0.1"), ("FS_KNEE_LOAD", "1"), ("FS_TAULIM", "20.5")):
    os.environ.setdefault(k, v)
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bench"))

# ── 탐색 결과 파일에서 모델 값을 직접 불러오는 길 (08-16 추가 — 무변속 판과 동일하게) ──
#   무변속 비교 그림(`fs_compare_plot`)은 이미 이 길이 있는데 여기만 없었다. 그래서 변속
#   세션 그림은 손으로 환경변수를 넣어 줄 때만 만들 수 있었고, 회차 폴더에 자주 빠졌다.
#   같은 변환 함수(`_GHB_sweep.apply_from_json`)를 쓰므로 그림과 점수가 같은 지점을 가리킨다.
#     set FS_CMP_FROM=_GHB_sweep8.json     ← 어느 탐색 결과를 그릴지
#     set FS_CMP_OUT_CVT=_compare_H8_260816 ← 산출 폴더 (무변속 판과 같은 폴더로 맞춘다)
if os.environ.get("FS_CMP_FROM"):
    import _GHB_sweep as _SW
    _SW.apply_from_json()

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
import safe
import fs_cvt as FC
import fs_runner as FR
import fs_data as FD
import mujoco as mjm
from _G10_energy import real_h            # 점프높이 실측 (Real Data.txt)

TW = FC.TW; RU = FC.RU
OUT = HERE / os.environ.get("FS_CMP_OUT_CVT", "_plots")   # 스택별 분리 (repo 안 = _compare_* 관례)
OUT.mkdir(parents=True, exist_ok=True)
# ★ 08-09: l_i 하드코딩 폐지. trial 마다 `fs_data.cvt_li(trial폴더)` 로 읽는다.
#   (구 0.02499 는 "실측" 주석과 달리 센서 범위 25.06~25.10 **밖**이었다 — 점수 튜닝값)
LI = 0.02508    # 폴백 기본값 — 결과 경로는 trial 값으로 덮어쓸 것
TKD = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}


def lpf(x, dt, tc=0.010):
    a = dt / (tc + dt)
    y = np.zeros_like(x); acc = float(x[0])
    for i in range(len(x)):
        acc += a * (float(x[i]) - acc); y[i] = acc
    return y


TAG = os.environ.get("FS_STACK_TAG", "fs")


def tri(ax, t0, y0, t1, y1, t2, y2, ylab):
    ln, = ax.plot(t0, y0, lw=1.0, label="실측")
    ax.plot(t1, y1, "--", lw=1.0, label="배포모델 (OLD=p24, 5q)")
    ax.plot(t2, y2, ":", lw=1.4, label=f"현행 ({TAG}, 6q)")
    ax.set_ylabel(ylab)
    ax.grid(alpha=0.3)


def _rmse(y, ys, deg=False):
    """실측 y 와 sim ys 의 RMSE. 각도 채널은 ° 로 (비CVT 보드와 같은 단위 규약)."""
    e = float(np.sqrt(np.mean((np.asarray(y) - np.asarray(ys)) ** 2)))
    return e * (180.0 / np.pi if deg else 1.0)


def cl5q(model, tw, cc, d, seg, g, win=None, li=None):
    """old α CL 미러 (5q 직결 hip): settle→폴더 게인 PD(TK·kd0.2)→supp/spr/CVT소산."""
    P = tw["P"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = tw["law"]; kr = tw["kr"]; sprm = tw["sprm"]
    A = P.A_PAPER
    from cvt_core import qpos_from_crank
    if win is not None:                       # P16: 점프 창 시작 실측 앵커 (ModeA 동일 규칙)
        mw, i0, init = win
        t = d["t"][mw] - d["t"][i0]
        qd1g, qd2g = d["qd1"][mw], d["qd2"][mw]
        dqd1g, dqd2g = d["dqd1"][mw], d["dqd2"][mw]
        t_end = float(t[-1])
    else:
        mw = None
        i0 = max(0, seg["i_desc"] - 5)
        t = d["t"][i0:] - d["t"][i0]
        qd1g, qd2g = d["qd1"][i0:], d["qd2"][i0:]
        dqd1g, dqd2g = d["dqd1"][i0:], d["dqd2"][i0:]
        t_end = seg["t_lo"] - d["t"][i0]
    kp1, kd1 = g[0], g[1]
    import fs_compare_plot as _CP                      # P18: 표 밖 게인 log-kp 보간 (fallback 0.656 금지)
    kp2 = g[2] * _CP.alpha_of(TKD, g[2]); kd2 = g[3] * 0.20
    _li = float(LI if li is None else li)              # ★ trial 별 실측 l_i (OLD 쪽도 동일 적용)
    md = mjm.MjData(model)
    _a1 = -(init[0] if win is not None else float(qd1g[0])) - np.pi / 2
    _a2 = -(init[1] if win is not None else float(qd2g[0]))
    md.qpos[:] = qpos_from_crank(1.0, _a1, _a2, _li)[0]
    mjm.mj_forward(model, md)
    fg = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    if win is not None:                       # 실측 속도 주입 (5q 좌표: [bz, hip, crank, cpin, knee])
        _c1, _c12 = np.cos(init[0]), np.cos(init[0] + init[1])
        md.qvel[:] = [-0.25 * (_c1 * init[2] + _c12 * (init[2] + init[3])), -init[2], -init[3], init[3], -init[3]]
    mjm.mj_forward(model, md)
    dt = model.opt.timestep
    qg, rg = RU.rtab(_li)
    for k in range(0 if win is not None else int(round(P.J.T_SETTLE / dt))):        # settle (앵커판은 생략)
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        c1 = S.SETTLE_KP * (float(qd1g[0]) - q1c) - S.SETTLE_KD * v1c
        c2 = S.SETTLE_KP * (float(qd2g[0]) - q2c) - S.SETTLE_KD * v2c
        c1 = float(np.clip(c1, -TW.R19.CLIP, TW.R19.CLIP)); c2 = float(np.clip(c2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = RU.spr_tau(float(md.qpos[4]), abs(s2), sprm) if sprm is not None else 0.0
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[4] = tql
        mjm.mj_step(model, md)
    N = int(round((t_end + 0.05) / dt))
    L = {k: np.zeros(N) for k in ("t", "q1", "q2", "dq1", "dq2", "s1", "s2")}
    for k in range(N):
        tc = k * dt
        tm_ = min(tc, t_end)
        qd1 = float(np.interp(tm_, t, qd1g)); qd2 = float(np.interp(tm_, t, qd2g))
        dqd1 = float(np.interp(tm_, t, dqd1g)); dqd2 = float(np.interp(tm_, t, dqd2g))
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        if tc <= t_end:
            c1 = kp1 * (qd1 - q1c) + kd1 * (dqd1 - v1c)
            c2 = kp2 * (qd2 - q2c) + kd2 * (dqd2 - v2c)
        else:
            c1 = c2 = 0.0
        c1 = float(np.clip(c1, -TW.R19.CLIP, TW.R19.CLIP)); c2 = float(np.clip(c2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = RU.spr_tau(float(md.qpos[4]), abs(s2), sprm) if sprm is not None else 0.0
        rr = float(np.interp(float(md.qpos[2]), qg, rg))
        amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
        tql += -cc * abs(s2) * amp * float(np.tanh(float(md.qvel[4]) / 1.0))
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[4] = tql
        mjm.mj_step(model, md)
        if not np.isfinite(md.qpos).all():
            return None
        L["t"][k] = tc
        L["q1"][k] = -md.qpos[1] - np.pi / 2
        L["q2"][k] = -md.qpos[2]
        L["dq1"][k] = -md.qvel[1]
        L["dq2"][k] = -md.qvel[2]
        L["s1"][k] = s1
        L["s2"][k] = s2
    return L


SESS = "26.04.29"
H_CVT = {}          # trial → (영상 h, OLD h, 현행 h)


def h_title(trial):
    """제목용 점프높이 한 줄 — 비CVT 보드(fs_compare_plot.h_title)와 **같은 정의·같은 문장**.
    지면 기준 베이스 중심 최고높이, ModeA 재생 +0.6s(T_AFTER) 연장에서 판독.
    CL 은 이륙에서 롤아웃이 끝나 최고점이 없으므로 같은 trial 의 ModeA 값을 쓰고 그렇게 표기한다."""
    v = H_CVT.get(trial)
    if not v:
        return ""
    hv, ho_, hf_ = v
    if hv:
        return (f"점프높이(ModeA 연장재생)  영상 {hv:.3f} m  ·  OLD {ho_:.3f} m "
                f"({100*(ho_/hv-1):+.1f}%)  →  {TAG} {hf_:.3f} m ({100*(hf_/hv-1):+.1f}%)")
    return f"점프높이(ModeA 연장재생)  영상 실측 없음  ·  OLD {ho_:.3f} m → {TAG} {hf_:.3f} m"


def main():
    model_c, model_cf, ctx = FC.build_cvt_pair()
    tw = ctx["tw"]; nm = ctx["nm"]
    o1, o2, cc = float(nm["o1_429"]), float(nm["o2_429"]), float(nm["C_CVT"])
    P = tw["P"]
    REG = {p.name: p for s, p, g, cvt, ho in FD.registry() if s == SESS}
    GAIN = {p.name: g for s, p, g, cvt, ho in FD.registry() if s == SESS}
    agg = {}

    _mc = {}

    def _models(li):
        """이 trial 의 l_i 로 **5q(OLD)·6q(현행) 모델을 둘 다** 다시 짓는다 (캐시).

        l_i 는 4절 입력링크 길이 = 모델 치수 자체다. 한쪽만 갱신하면 비교가 불공정해지고,
        초기화만 바꾸면 루프 구속이 t=0 에 어긋나 솔버가 스냅한다 (fs_cvt._bind_li 와 같은 이유).
        """
        key = round(float(li), 7)
        if key not in _mc:
            _a, _b, _ = FC.build_cvt_pair(float(li))
            if _b is None:
                raise RuntimeError(f"fs 패치 CVT 모델 없음 (l_i={li})")
            _mc[key] = (_a, _b)
        return _mc[key]

    # ---- ModeA (R19 재생창) ----
    subs = [(sub, d) for ds, sub, d, *rest in TW.R19.TRIALS if ds == "jump_0429"]
    print(f"R19 0429 subs: {[s for s, _ in subs]}", flush=True)
    # ★ 승격 판단에는 **전 trial** 이 필요하다 (FS_CVT_ALL=1). 기본은 기존 2건 유지.
    _want = None if os.environ.get("FS_CVT_ALL") == "1" else ("150_2.2_250_3", "60_0.75_60_2")
    for sub, d in [x for x in subs if (_want is None or x[0] in _want)]:
        if sub in REG:
            d["l_i"] = FD.cvt_li(REG[sub])          # ★ 이 trial 의 Clutch 실측 (세션 상수 금지)
        _li = float(d.get("l_i", LI))
        model_c, model_cf = _models(_li)
        r5 = FC.a_cvt_mirror(model_c, d, tw, o1, o2, cc, fs=False, ret_traces=True)
        r6 = FC.a_cvt_mirror(model_cf, d, tw, o1, o2, cc, fs=True, bias1=0.85, ret_traces=True)
        if r5 is None or r6 is None:
            print(f"{sub}: ModeA 실패", flush=True)
            continue
        T5, T6 = r5[3], r6[3]
        H_CVT[sub] = (real_h(REG[sub]) if sub in REG else None, r5[2], r6[2])
        t = d["t"]
        # 채널 RMSE (τ 는 주입값이라 공통 — 비CVT ModeA 보드와 동일 규약)
        _M = [np.degrees(d["q1"]) + np.degrees(o1), np.degrees(d["q2"]) + np.degrees(o2),
              d["dq1"], d["dq2"]]
        _S5 = [np.degrees(np.interp(t, T5["tl"], T5["q1"])), np.degrees(np.interp(t, T5["tl"], T5["q2"])),
               np.interp(t, T5["tl"], T5["dq1"]), np.interp(t, T5["tl"], T5["dq2"])]
        _S6 = [np.degrees(np.interp(t, T6["tl"], T6["q1"])), np.degrees(np.interp(t, T6["tl"], T6["q2"])),
               np.interp(t, T6["tl"], T6["dq1"]), np.interp(t, T6["tl"], T6["dq2"])]
        agg.setdefault("ModeA", []).append(
            (sub, [_rmse(a, b) for a, b in zip(_M, _S5)], [_rmse(a, b) for a, b in zip(_M, _S6)]))
        a1m = P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"])
        a2m = P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"])
        fig, ax = plt.subplots(2, 3, figsize=(15, 7), sharex=True)
        tri(ax[0, 0], t, np.degrees(d["q1"]) + np.degrees(o1), T5["tl"], np.degrees(T5["q1"]), T6["tl"], np.degrees(T6["q1"]), "q1 [°]")
        tri(ax[0, 1], t, np.degrees(d["q2"]) + np.degrees(o2), T5["tl"], np.degrees(T5["q2"]), T6["tl"], np.degrees(T6["q2"]), "q2 크랭크 [°]")
        tri(ax[1, 0], t, d["dq1"], T5["tl"], T5["dq1"], T6["tl"], T6["dq1"], "dq1 [rad/s]")
        tri(ax[1, 1], t, d["dq2"], T5["tl"], T5["dq2"], T6["tl"], T6["dq2"], "dq2 크랭크 [rad/s]")
        ax[0, 2].plot(t, a1m, lw=1.0)
        ax[0, 2].set_ylabel("τ1 주입 (공통) [Nm]"); ax[0, 2].grid(alpha=0.3)
        ax[1, 2].plot(t, a2m, lw=1.0)
        ax[1, 2].set_ylabel("τ2 주입 (공통) [Nm]"); ax[1, 2].grid(alpha=0.3)
        ax[0, 0].legend(fontsize=8)
        for a in ax[1]:
            a.set_xlabel("t [s]")
        fig.suptitle(f"{SESS} CVT (l_i={_li*1000:.2f}mm) ModeA — {sub}\n"
                     + (h_title(sub) + "\n" if h_title(sub) else "")
                     + f"창 RMSE (q1°/q2°/dq1/dq2)  OLD: "
                     + " / ".join("%.2f" % x for x in agg["ModeA"][-1][1])
                     + f"   {TAG}: " + " / ".join("%.2f" % x for x in agg["ModeA"][-1][2]))
        fig.tight_layout()
        fp = OUT / "ModeA" / SESS
        fp.mkdir(parents=True, exist_ok=True)
        fig.savefig(fp / f"{sub}.png", dpi=110)
        plt.close(fig)
        print(f"  ModeA {sub}: OK (l_i {_li*1000:.2f}mm)", flush=True)

    # ---- CL (*2 fullspan) ----
    ft0 = FR.fs_twin()
    from cvt_core import qpos_from_crank
    ft = dict(ft0)

    def _bind_li(li):
        """trial 별 실측 l_i 로 **모델·폐쇄 초기화·전달비를 전부** 갱신 (fs_cvt._bind_li 규약)."""
        _mcf = _models(float(li))[1]
        ft["model"] = _mcf
        ft["iq"] = {n: safe.qadr(_mcf, n, mjm)
                    for n in ("base_z", "hip_m", "hip", "knee_motor", "cpin", "knee")}
        ft["dof"] = {n: safe.dofadr(_mcf, n, mjm) for n in ft["iq"]}
        ft["cvt_init"] = lambda q1, q2, _l=float(li): qpos_from_crank(
            1.0, -q1 - np.pi / 2, -q2, _l)[0]
        _qg, _rg = RU.rtab(float(li))
        ft["cvt_diss"] = (cc, _qg, _rg)
    import fs_compare_plot as _CP                # 규약 ④: 표 밖 게인 log-kp 보간 (상수 fallback 금지)
    SP = FR._sess_params()
    sp = SP[SESS]
    for s, p, g, cvt, ho in FD.registry():
        if s != SESS:
            continue
        if os.environ.get("FS_CVT_ALL") != "1" and p.name not in ("150_2.2_250_3", "60_0.75_60_2"):
            continue
        d = FD.load2(p); seg = FD.segment(d)
        _li = float(d.get("l_i", LI))
        _bind_li(_li)                       # ★ 이 trial 의 Clutch 실측
        _mc5 = _models(_li)[0]
        gm = (g[0], g[1], g[2] * _CP.alpha_of(TKD, g[2]), g[3] * 0.20)
        i0 = max(0, seg["i_desc"] - 5)
        t = d["t"][i0:] - d["t"][i0]
        t_end = seg["t_lo"] - d["t"][i0]
        Lf = FR.rollout_cl_fs(ft, t, d["qd1"][i0:], d["qd2"][i0:], d["dqd1"][i0:], d["dqd2"][i0:],
                              gm, t_end, two_stage=True, bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                              fade=True, taulim=None)
        Lo = cl5q(_mc5, tw, cc, d, seg, g, li=_li)
        if Lf is None or Lo is None:
            print(f"{p.name}: CL 실패 (fs {Lf is None} old {Lo is None})", flush=True)
            continue
        dt5 = float(np.median(np.diff(Lo["t"])))
        pm = seg["push"][i0:][: len(t)]
        t_push0 = float(t[pm][0]) if pm.sum() else 0.0
        # ★ 규약 ①: 그래프·채점 창 = 원본 hip/knee.xlsx 스팬 (fs_data.plot_window) — 단일 출처.
        #   구판은 push−0.05s 로 직접 잘랐다 (창 규약 위반 · 비CVT 보드와 비교 불가).
        _pw = FD.plot_window(p, d)
        if _pw is None:
            w0, w1 = t_push0 - 0.05, t_end
        else:
            w0, w1 = _pw[0] - d["t"][i0], _pw[1] - d["t"][i0]   # d["t"] 상대축 → 롤아웃 t 축
            w1 = min(w1, t_end)             # 이륙 이후 sim 은 커맨드 0 관례라 비교 무의미
        mseg = (t >= w0) & (t <= w1)
        tm = t[mseg]
        mo = (Lo["t"] >= w0) & (Lo["t"] <= w1)
        mf = (Lf["t"] >= w0) & (Lf["t"] <= w1)
        s1o_l = lpf(Lo["s1"], dt5)
        fig, ax = plt.subplots(2, 3, figsize=(15, 7), sharex=True)
        tri(ax[0, 0], tm, np.degrees(d["q1"][i0:][mseg]), Lo["t"][mo], np.degrees(Lo["q1"][mo]), Lf["t"][mf], np.degrees(Lf["thm1"][mf]), "q1 [°]")
        tri(ax[0, 1], tm, np.degrees(d["q2"][i0:][mseg]), Lo["t"][mo], np.degrees(Lo["q2"][mo]), Lf["t"][mf], np.degrees(Lf["q2"][mf]), "q2 크랭크 [°]")
        tri(ax[1, 0], tm, d["dq1"][i0:][mseg], Lo["t"][mo], Lo["dq1"][mo], Lf["t"][mf], Lf["dq1"][mf], "dq1 [rad/s]")
        tri(ax[1, 1], tm, d["dq2"][i0:][mseg], Lo["t"][mo], Lo["dq2"][mo], Lf["t"][mf], Lf["dq2"][mf], "dq2 크랭크 [rad/s]")
        tri(ax[0, 2], tm, d["a1"][i0:][mseg], Lo["t"][mo], s1o_l[mo], Lf["t"][mf], Lf["s1f"][mf], "τ1 (lpf 관측) [Nm]")
        tri(ax[1, 2], tm, d["a2"][i0:][mseg], Lo["t"][mo], Lo["s2"][mo], Lf["t"][mf], Lf["s2"][mf], "τ2 [Nm]")
        ax[0, 0].legend(fontsize=8)
        for a in ax[1]:
            a.set_xlabel("t [s]")
        for a in ax.flat:
            a.axvline(t_push0, lw=0.6, alpha=0.4)
            a.axvline(t_end, lw=0.6, alpha=0.4)
        # 채널 RMSE (창 안, 실측 시각에 sim 보간) — 비CVT CL 보드와 같은 6채널·같은 단위
        _MC = [np.degrees(d["q1"][i0:][mseg]), np.degrees(d["q2"][i0:][mseg]),
               d["dq1"][i0:][mseg], d["dq2"][i0:][mseg],
               d["a1"][i0:][mseg], d["a2"][i0:][mseg]]
        _oI = lambda k, deg=False: (np.degrees if deg else (lambda z: z))(np.interp(tm, Lo["t"], Lo[k]))
        _fI = lambda k, deg=False: (np.degrees if deg else (lambda z: z))(np.interp(tm, Lf["t"], Lf[k]))
        _O = [_oI("q1", True), _oI("q2", True), _oI("dq1"), _oI("dq2"),
              np.interp(tm, Lo["t"], s1o_l), _oI("s2")]
        _F = [_fI("thm1", True), _fI("q2", True), _fI("dq1"), _fI("dq2"), _fI("s1f"), _fI("s2")]
        eo = [_rmse(a, b) for a, b in zip(_MC, _O)]
        ef = [_rmse(a, b) for a, b in zip(_MC, _F)]
        agg.setdefault("CL", []).append((p.name, eo, ef))
        fig.suptitle(f"{SESS} CVT (l_i={_li*1000:.2f}mm) CL 점프 창 — {p.name}  "
                     f"[게인 {g[0]:g}/{g[1]:g}/{g[2]:g}/{g[3]:g}]\n"
                     + (h_title(p.name) + "\n" if h_title(p.name) else "")
                     + f"창 RMSE (q1°/q2°/dq1/dq2/τ1/τ2)  OLD: " + " / ".join("%.2f" % x for x in eo)
                     + f"   {TAG}: " + " / ".join("%.2f" % x for x in ef))
        fig.tight_layout()
        fp = OUT / "CL" / SESS
        fp.mkdir(parents=True, exist_ok=True)
        fig.savefig(fp / f"{p.name}.png", dpi=110)
        plt.close(fig)
        print(f"  CL {p.name}: OK (l_i {_li*1000:.2f}mm)", flush=True)
    write_summary(agg)
    print(f"\ndone → {OUT}", flush=True)


MA_CH = ["q1 [°]", "q2 [°]", "dq1", "dq2"]
CL_CH = ["q1 [°]", "q2 [°]", "dq1", "dq2", "τ1", "τ2"]


def write_summary(agg):
    """세션 요약 막대 + README 표 — 비CVT 보드(fs_compare_plot)와 같은 읽는 법."""
    lines = [f"# 0429 CVT 3자 비교 (실측 / 배포모델 OLD=p24 / 현행 {TAG})", "",
             "- `ModeA/26.04.29/<trial>.png` — 측정 토크 주입 재생 (PD가 오차를 못 숨김 = 1급 심판)",
             "- `CL/26.04.29/<trial>.png` — 폐루프, 점프 창 (원본 xlsx 스팬)",
             "- l_i(변속 링크 길이)는 **trial 마다 그 trial 의 Clutch.xlsx 중앙값**을 쓴다.",
             "  OLD·현행 **양쪽 모두** 같은 l_i 로 모델을 다시 지어 비교한다 (공정성).", ""]
    for mode, rows in sorted(agg.items()):
        if not rows:
            continue
        CHN = MA_CH if mode == "ModeA" else CL_CH
        O = np.array([r[1] for r in rows], float)
        F = np.array([r[2] for r in rows], float)
        fig, a = plt.subplots(figsize=(7.5, 4))
        x = np.arange(len(CHN))
        a.bar(x - 0.19, O.mean(axis=0), 0.38, label="배포모델 (OLD=p24)")
        a.bar(x + 0.19, F.mean(axis=0), 0.38, label=f"현행 ({TAG})")
        a.set_xticks(x); a.set_xticklabels(CHN)
        a.set_ylabel("RMSE (창 평균)")
        a.set_title(f"{SESS} CVT — {mode} 채널별 (trial {len(rows)}개 평균)")
        a.legend(); a.grid(alpha=0.3, axis="y")
        fig.tight_layout()
        fd = OUT / mode / SESS
        fd.mkdir(parents=True, exist_ok=True)
        fig.savefig(fd / "_summary.png", dpi=105)
        plt.close(fig)
        lines += [f"## {mode}", "",
                  "| trial | " + " | ".join(CHN) + " |",
                  "|---|" + "---|" * len(CHN)]
        for nm_, eo, ef in rows:
            lines.append(f"| {nm_} | " + " | ".join(f"{a_:.2f}→{b_:.2f}" for a_, b_ in zip(eo, ef)) + " |")
        lines.append("| **평균** | " + " | ".join(
            f"**{a_:.2f}→{b_:.2f}**" for a_, b_ in zip(O.mean(axis=0), F.mean(axis=0))) + " |")
        won = int((F.mean(axis=1) < O.mean(axis=1)).sum())
        lines += ["", f"채널 평균 기준 **현행 승 {won}/{len(rows)} trial**.", ""]
    (OUT / "README_CVT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    safe.atomic_json_write(OUT / "_rmse_cvt.json", {          # 원수치 동봉 (표 재파싱 금지)
        f"{mode}|{SESS}": dict(n=len(rows), ch=(MA_CH if mode == "ModeA" else CL_CH),
                               old=np.mean([r[1] for r in rows], axis=0).tolist(),
                               new=np.mean([r[2] for r in rows], axis=0).tolist(),
                               trials={r[0]: dict(old=r[1], new=r[2]) for r in rows})
        for mode, rows in agg.items() if rows})
    safe.atomic_json_write(OUT / "_jumph_cvt.json",
                           {f"{SESS}|{k}": v for k, v in H_CVT.items()})


if __name__ == "__main__":
    main()
