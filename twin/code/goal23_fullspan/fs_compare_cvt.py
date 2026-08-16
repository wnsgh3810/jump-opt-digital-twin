# -*- coding: utf-8 -*-
"""fs_compare_cvt — CVT(0429) 전 trial 3자 비교: 실측 vs old α(5q 정본) vs 현행 fs.

CVT는 모델 경로가 달라 별도 (정본 CVT XML 캡처 + fs 6q 패치).
CL: fs_cvt_plot.cl5q(old) vs FR.rollout_cl_fs(fs, cvt 훅) — 점프(push) 구간
ModeA: fs_cvt.a_cvt_mirror(fs=False/True, R19 재생창)
출력: _compare/CVT_CL/<trial>.png · _compare/CVT_ModeA/<trial>.png
CLI: python fs_compare_cvt.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
for k, v in (("FS_FIXED", "1"), ("FS_FADE", "1"), ("FS_TAUOBS", "lpf"), ("FS_TC", "0.002"),
             ("FS_KNEE_REL", "0.1"), ("FS_KNEE_LOAD", "1"), ("FS_TAULIM", "20.5")):
    os.environ.setdefault(k, v)
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bench"))

# 모델 값을 탐색 결과 파일에서 바로 불러오는 길 (2026-08-13) — `fs_compare_plot` 과 같은 규약.
#   set FS_CMP_FROM=_GHB_sweep4.json  →  그 승자의 값 열두 개가 자동으로 들어간다.
#   모델을 짓기 **전에** 넣어야 하므로 다른 것들보다 먼저 부른다.
if os.environ.get("FS_CMP_FROM"):
    import _GHB_sweep as _SW                # 축 벡터 → 환경변수 변환의 단일 출처
    _SW.apply_from_json()

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
import safe
import fs_data as FD
import fs_cvt as FC
import fs_cvt_plot as CVP
import fs_compare_plot as CP
import fs_runner as FR
import mujoco as mjm

OUT = HERE / os.environ.get("FS_CMP_OUT", "_compare")   # 스택별 산출 분리 (기본 = 기존 경로)
# LI 하드코딩 폐지 (08-09) — trial 별 Clutch 실측을 쓴다 (fs_data.cvt_li)
TKD = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}


def main():
    model_c, model_cf, ctx = FC.build_cvt_pair()
    tw = ctx["tw"]; nm = ctx["nm"]
    o1, o2, cc = float(nm["o1_429"]), float(nm["o2_429"]), float(nm["C_CVT"])
    P = tw["P"]
    from cvt_core import qpos_from_crank
    ft0 = FR.fs_twin()
    ft = dict(ft0)
    ft["model"] = model_cf
    ft["iq"] = {n: safe.qadr(model_cf, n, mjm) for n in ("base_z", "hip_m", "hip", "knee_motor", "cpin", "knee")}
    ft["dof"] = {n: safe.dofadr(model_cf, n, mjm) for n in ft["iq"]}
    _mc = {}

    def _bind_li(li):
        """이 trial 의 l_i 로 **모델·초기화·전달비를 전부** 갱신 (l_i 는 링크 치수다)."""
        li = float(li); k = round(li, 7)
        if k not in _mc:
            _a, _b, _ = FC.build_cvt_pair(li)
            if _b is None:
                raise RuntimeError(f"fs 패치 CVT 모델 없음 (l_i={li})")
            _mc[k] = _b
        ft["model"] = _mc[k]
        ft["iq"] = {n: safe.qadr(_mc[k], n, mjm)
                    for n in ("base_z", "hip_m", "hip", "knee_motor", "cpin", "knee")}
        ft["dof"] = {n: safe.dofadr(_mc[k], n, mjm) for n in ft["iq"]}
        ft["cvt_init"] = lambda q1, q2, _l=float(li): qpos_from_crank(
            1.0, -q1 - np.pi / 2, -q2, _l)[0]
        qg, rg = FC.RU.rtab(float(li))
        ft["cvt_diss"] = (cc, qg, rg)
    SP = FR._sess_params()
    sp = SP["26.04.29"]
    # ★ 08-12 (사용자 지시): 폴더를 `CVT_CL`·`CVT_ModeA` 로 따로 빼지 않고
    #   점프 세션과 같은 `CL/26.04.29`·`ModeA/26.04.29` 아래에 넣는다.
    # ★ 08-12 (사용자 지시): **제목에 점프 높이**. 점프 높이는 주입 재생의 연장 재생으로만
    #   나오므로(정본 정의) 주입 재생을 **먼저** 돌려 값을 채운 뒤 폐루프 제목에서 재사용한다
    #   — 정본 `fs_compare_plot.main` 과 같은 순서다.
    _FOLD = {p.name: p for s_, p, g_, c_, h_ in FD.registry() if s_ == "26.04.29"}

    # ---- ModeA (R19 재생창) — 점프 높이를 먼저 채운다 ----
    _run_ma(model_c, model_cf, tw, o1, o2, cc, sp, P, _FOLD)

    # ---- CL (점프 구간) ----
    for s, p, g, cvt, ho in FD.registry():
        if s != "26.04.29" or ho or not g:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            _bind_li(d["l_i"])                 # ★ trial 별 실측 l_i
            pw = FD.plot_window(p, d)          # 원본 xlsx 창 = 점프 (훅 규약)
            tt = d["t"]
            mw = (tt >= pw[0]) & (tt <= pw[1])
            i0 = int(np.argmax(mw))
            t = tt[mw] - tt[i0]
            t_end = float(t[-1])
            init = (float(d["q1"][i0]), float(d["q2"][i0]), float(d["dq1"][i0]), float(d["dq2"][i0]),
                    float(d["raw1"][i0]), float(d["raw2"][i0]))
            Lf = FR.rollout_cl_fs(ft, t, CP.sh(d["qd1"][mw]), CP.sh(d["qd2"][mw]),
                                  CP.sh(d["dqd1"][mw]), CP.sh(d["dqd2"][mw]),
                                  tuple(g), t_end, two_stage=True, bias1=sp["bias1"],
                                  knee_deep=sp["knee_deep"], fade=True, taulim=None, init_meas=init)
            Lo = CVP.cl5q(model_c, tw, cc, d, seg, g, win=(mw, i0, init))
            if Lf is None or Lo is None:
                print(f"CL {p.name}: 실패"); continue
            m = np.ones(int(mw.sum()), bool)
            w = m
            dts = float(np.median(np.diff(Lo["t"])))
            sims = {
                "old": [np.interp(t, Lo["t"], Lo[k]) for k in ("q1", "q2", "dq1", "dq2")] +
                       [np.interp(t, Lo["t"], CVP.lpf(Lo["s1"], dts, 0.002)), np.interp(t, Lo["t"], Lo["s2"])],
                "fs": [np.interp(t, Lf["t"], Lf[k]) for k in ("thm1", "q2", "dq1", "dq2")] +
                      [np.clip(np.interp(t, Lf["t"], Lf["s1f"]), -20.5, 20.5), np.interp(t, Lf["t"], Lf["s2"])],
            }
            # ★★ 08-12 정정 (사용자 적발): 토크 기준선을 **모델마다 따로** 만든다.
            #   구판은 `d["a1"]`(=배포판 변환식으로 만든 값) 하나만 썼다. 그러면 현행 모델이
            #   자기 변환식으로 낸 토크를 **남의 변환식으로 만든 선**과 비교당한다 —
            #   비교가 성립하지 않는다. 정본(fs_compare_plot.cl_pair)은 08-11 에 이미 고쳤는데
            #   변속기 쪽에 반영이 안 돼 있었다 (사본이 둘이라 한쪽만 고쳐진 사고).
            meas_o = {k: d[k][mw] for k, _ in CP.CH}
            meas_f = dict(meas_o)
            meas_o["a1"] = CP.tau_ref(d["raw1"][mw], d["dq1"][mw], 0, old=True)
            meas_o["a2"] = CP.tau_ref(d["raw2"][mw], d["dq2"][mw], 1, old=True)
            meas_f["a1"] = CP.tau_ref(d["raw1"][mw], d["dq1"][mw], 0, old=False)
            meas_f["a2"] = CP.tau_ref(d["raw2"][mw], d["dq2"][mw], 1, old=False)
            _note = ("※ τ 는 각 모델의 변환식으로 실측 명령을 바꾼 값과 비교"
                     " (모터는 명령만 기록 — 축토크 실측은 없다).")
            _ht = CP.h_title("26.04.29", p.name)     # 주입 재생이 채운 값 (정본 정의)
            fig, ax = CP.panels(
                f"26.04.29 (CVT l_i=25mm) / {p.name} — CL 점프 구간 (창 시작 실측 앵커 · 통짜) · 실측 vs old α vs 현행 fs"
                + (chr(10) + _ht if _ht else ""),
                f"push RMSE  old: {CP.rmse_line(meas_o, m, sims['old'])}   "
                f"fs: {CP.rmse_line(meas_f, m, sims['fs'])}" + chr(10) + _note)
            for j, (a, (k, _)) in enumerate(zip(ax, CP.CH)):
                y, y2 = meas_o[k][w], meas_f[k][w]
                yo, yf = sims["old"][j][w], sims["fs"][j][w]
                if k in ("q1", "q2"):
                    y, y2 = np.degrees(y), np.degrees(y2)
                    yo, yf = np.degrees(yo), np.degrees(yf)
                _tau = k in ("a1", "a2")
                a.plot(tt[mw], y, lw=1.2, label="실측 명령 → 배포판 변환" if _tau else "실측")
                if _tau:
                    a.plot(tt[mw], y2, lw=1.2, alpha=0.9, label="실측 명령 → 현행 변환")
                    a.plot(tt[mw], d["raw1" if k == "a1" else "raw2"][mw], lw=1.0, alpha=0.85,
                           label="모터 명령 (엑셀 원본, 무변환)")
                a.plot(tt[mw], yo, "--", lw=1.0, label="old α (5q)")
                a.plot(tt[mw], yf, ":", lw=1.5, label="현행 fs (6q)")
            ax[0].legend(fontsize=8)
            for _i in (4, 5):
                ax[_i].legend(fontsize=6.5)
            fig.tight_layout()
            fp = OUT / "CL" / "26.04.29"; fp.mkdir(parents=True, exist_ok=True)
            fig.savefig(fp / f"{p.name}.png", dpi=105)
            plt.close(fig)
            print(f"CL {p.name}: OK", flush=True)
        except Exception as ex:
            print(f"CL {p.name}: ERR {type(ex).__name__} {ex}", flush=True)

    print("done", flush=True)


def _run_ma(model_c, model_cf, tw, o1, o2, cc, sp, P, FOLD):
    """ModeA (R19 재생창). 점프 높이를 `CP.H_LOG` 에 채워 폐루프 제목에서 재사용하게 한다."""
    for sub, d in [(sub, dd) for ds, sub, dd, *r in FC.TW.R19.TRIALS if ds == "jump_0429"]:
        try:
            r5 = FC.a_cvt_mirror(model_c, d, tw, o1, o2, cc, fs=False, ret_traces=True)
            r6 = FC.a_cvt_mirror(model_cf, d, tw, o1, o2, cc, fs=True, bias1=sp["bias1"], ret_traces=True)
            if r5 is None or r6 is None:
                print(f"MA {sub}: 실패"); continue
            T5, T6 = r5[3], r6[3]
            t = d["t"]
            # ★ 점프 높이 — 정본 정의(지면 기준 몸통 중심 최고, 주입 재생 연장)와 같은 값.
            #   `a_cvt_mirror` 가 세 번째로 돌려주는 것이 그것이다.
            _fold = FOLD.get(sub)
            _hv = CP.real_h(_fold) if _fold is not None else None
            CP.H_LOG[f"26.04.29|{sub}"] = (_hv, r5[2], r6[2])
            _ht = CP.h_title("26.04.29", sub)
            # ★ 08-12: 토크 기준선을 모델마다 (위 폐루프와 같은 정정)
            a1m = CP.tau_ref(d["traw1"], d["dq1"], 0, old=True)
            a2m = CP.tau_ref(d["traw2"], d["dq2"], 1, old=True)
            a1f = CP.tau_ref(d["traw1"], d["dq1"], 0, old=False)
            a2f = CP.tau_ref(d["traw2"], d["dq2"], 1, old=False)
            _note2 = ("※ τ 는 주입한 값이라 예측이 아니다. 두 선은 같은 명령을"
                      " 각 모델의 변환식으로 바꾼 것이다.")
            fig, ax = CP.panels(
                f"26.04.29 (CVT) / {sub} — ModeA 재생 (측정 토크 주입) · 실측 vs old α vs 현행 fs"
                + (chr(10) + _ht if _ht else ""),
                f"dq2 RMSE: old α {r5[0]:.2f} vs fs {r6[0]:.2f} | "
                f"q1 RMSE: {r5[1]:.2f} vs {r6[1]:.2f}" + chr(10) + _note2)
            series = [(np.degrees(d["q1"] + o1), np.degrees(T5["q1"]), np.degrees(T6["q1"])),
                      (np.degrees(d["q2"] + o2), np.degrees(T5["q2"]), np.degrees(T6["q2"])),
                      (d["dq1"], T5["dq1"], T6["dq1"]),
                      (d["dq2"], T5["dq2"], T6["dq2"]),
                      (a1m, None, a1f), (a2m, None, a2f)]
            for a, (k, lab), (ym, yo, yf) in zip(ax, CP.CH, series):
                if yo is None:      # τ 패널 — 주입한 명령을 두 변환식으로 각각 그린다
                    a.plot(t, ym, lw=1.2, label="실측 명령 → 배포판 변환")
                    a.plot(t, yf, lw=1.2, alpha=0.9, label="실측 명령 → 현행 변환")
                    a.plot(t, d["traw1"] if k == "a1" else d["traw2"], lw=1.0, alpha=0.85,
                           label="모터 명령 (엑셀 원본, 무변환)")
                    a.legend(fontsize=6.5)
                else:
                    a.plot(t, ym, lw=1.2, label="실측")
                    a.plot(T5["tl"], yo, "--", lw=1.0, label="old α (5q)")
                    a.plot(T6["tl"], yf, ":", lw=1.5, label="현행 fs (6q)")
            ax[0].legend(fontsize=8)
            fig.tight_layout()
            fp = OUT / "ModeA" / "26.04.29"; fp.mkdir(parents=True, exist_ok=True)
            fig.savefig(fp / f"{sub}.png", dpi=105)
            plt.close(fig)
            print(f"MA {sub}: OK", flush=True)
        except Exception as ex:
            print(f"MA {sub}: ERR {type(ex).__name__} {ex}", flush=True)



if __name__ == "__main__":
    main()
