# -*- coding: utf-8 -*-
"""P22 probe T3 — SIM-FREE 에너지 원장 (measurement under-read vs plant mis-model 판별).

아이디어: 전류 기반 토크 추정(Paper a_hat)으로 계산한 푸시 구간 입력일 W_in 이
실제 로봇이 벌어들인 역학적 에너지 하한 E_req = M·g·(h_real − bz0) 보다 작으면
전류 기반 추정이 현실을 under-read 한다는 증거 (시뮬 파라미터와 무관).

규약 (전부 기존 repo 규약 재사용):
  - h_real: 카메라 실측 절대 apex 높이 [m] (Real Data.txt 첫 줄, base_z 절대좌표와
    직접 비교하는 것이 repo 규약: fs_metric h_pred=qpos[0]+v²/2g vs h_real,
    h_sim=bz.max() vs h_real). 출처 = g22_p19_all_results/<ds>/traj/<sub>__A.npz 메타.
  - bz0 (선 자세/크라우치 기준 높이): 러너 초기화 FK 그대로 —
    qpos=[1, -q1-π/2, -q2, ...] (CVT는 qpos_from_crank 폐쇄) → mj_forward →
    bz0 = 1 − foot_geom_z + FOOT_RADIUS (발바닥이 바닥에 닿는 base z).
    측정각 q(t=0) 원본 사용 (fit q-오프셋 미적용; 민감도만 보고).
  - 이륙 t_lo: no-cvt = g22_p13_phases.phases() (GRF<5N after onset),
    0429 = p19_run.all_trials 규약 (GRF 피크 후 <2%·peak). ±30ms 민감도.
  - 토크 변환: P.J.ahat(P.A_PAPER, traw, dq) [Nm] (Pure Paper — repo 철칙).
  - M = 3.2 kg (사용자 실측 = PH.TOTAL), g = 9.81.

held-out 26.03.24 은 표시만 하고 판정/상관에서 제외. 데이터 원본 읽기 전용.
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
import sys
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "code" / "bench"))
import p19_adapter as AD          # noqa: E402  (sys.path 셋업 포함)
import safe                        # noqa: E402

safe.utf8_console()
AD.ensure_init()
import p19_judge as P              # noqa: E402
import p19_run as R                # noqa: E402
from cvt_core import qpos_from_crank  # noqa: E402

MJ = P.J._P["mj"]
S = P.J._P["S"]
M_TOT = 3.2
G = 9.81
NPZ_ROOT = Path((LEGACY_ROOT + "/g22_p19_all_results"))
DSDIR = {"jump_0324": "jump_0324_heldout", "jump_position_0421": "jump_position_0421",
         "jump_0424": "jump_0424", "jump_0602": "jump_0602",
         "jump_0429": "jump_0429_cvt"}
MAIN_DS = ("jump_0424", "jump_0602", "jump_0429")   # 판정/상관 대상

# FK용 모델 (p19_all_results와 동일 후보 — FK는 링크 기하만 사용, 동역학 파라미터 무관)
CAND = AD.load_candidate(REPO / "code/goal22/p19_jump/fourbar_p19_candidate.json")
X32, V, SP, _QOFF = AD._p19_args(CAND)
MODEL_F, _ = P.build_flip(X32, V[1], SP)
_MODEL_C = {}


def model_of(is_cvt, l_i):
    if not is_cvt:
        return MODEL_F
    key = round(float(l_i), 5)
    if key not in _MODEL_C:
        _MODEL_C[key], _ = P.build_cvt(X32, V[1], SP, l_i)
    return _MODEL_C[key]


def bz_fk(md, model, is_cvt, l_i, q1, q2, qk_prev=None):
    """측정각 → 발바닥 접지 base z (러너 init FK 규약). 반환 (bz, com_off, qk)."""
    sq1, sq2 = -q1 - np.pi / 2, -q2
    qk = None
    if is_cvt:
        qp, qk, _ = qpos_from_crank(1.0, sq1, sq2, l_i, qk_prev)
        md.qpos[:] = qp
    else:
        md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    MJ.mj_forward(model, md)
    fg = MJ.mj_name2id(model, MJ.mjtObj.mjOBJ_GEOM, "foot")
    bz = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    com_off = float(md.subtree_com[0][2]) - 1.0     # CoM z − base z (자세 함수)
    return bz, com_off, qk


def leg_ke(md, model, q1, q2, dq1, dq2):
    """이륙 시점 다리 상대 운동에너지 추정 (base 고정, flip 모델 질량행렬) [J]."""
    sq1, sq2 = -q1 - np.pi / 2, -q2
    md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    md.qvel[:] = 0
    MJ.mj_forward(model, md)
    Mfull = np.zeros((model.nv, model.nv))
    MJ.mj_fullM(model, Mfull, md.qM)
    v = np.array([0.0, -dq1, -dq2, dq2, -dq2])
    return 0.5 * float(v @ Mfull @ v)


def toff_0429(d):
    """p19_run.all_trials와 동일: GRF 피크 후 <2%·peak."""
    g = d["grf_real"]
    pk = int(np.argmax(g))
    below = np.where(g[pk:] < 0.02 * g[pk])[0]
    i = pk + below[0] if len(below) else len(d["t"]) - 1
    return int(i)


def win_upto(t, pw, t_end):
    m = t <= t_end
    return float(np.trapezoid(pw[m], t[m]))


def main():
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    cl_idx = {(tr["ds"], str(tr["sub"])): (int(tr["on"]), int(tr["toff"]))
              for tr in P.J._P["cl"]}
    A = P.A_PAPER
    rows = []
    for ds, sub, d, gains, dqon, ffk, mask, is_cvt, l_i in R.TRIALS:
        if ds == "jump_0324":
            continue                     # held-out — fit/판정 절대 금지
        t = d["t"]
        # ── 이륙 시각 (repo 규약) ──
        if is_cvt:
            i_off = toff_0429(d)
            i_on = int(np.argmax(np.abs(d["dq2"]) > 1.0))
        else:
            i_on, i_off = cl_idx[(ds, str(sub))]
        i_off = min(i_off, len(t) - 1)
        t_lo = float(t[i_off])
        # ── W_in = ∫(a1·dq1 + a2·dq2)dt, [0, t_lo] ──
        a1 = P.J.ahat(A, d["traw1"], d["dq1"])
        a2 = P.J.ahat(A, d["traw2"], d["dq2"])
        pw = a1 * d["dq1"] + a2 * d["dq2"]
        W_in = win_upto(t, pw, t_lo)
        W_m = win_upto(t, pw, t_lo - 0.03)
        W_p = win_upto(t, pw, t_lo + 0.03)
        W_on = W_in - win_upto(t, pw, float(t[i_on]))   # 온셋~이륙 (시작점 민감도)
        # ── FK 기준 높이 & 이륙 운동학 ──
        model = model_of(is_cvt, l_i)
        md = MJ.MjData(model)
        bz0, c0, qk = bz_fk(md, model, is_cvt, l_i, d["q1"][0], d["q2"][0])
        # 스탠스 FK 높이 궤적 (이륙 직전 base 속도 → 운동학 apex 예측)
        i1 = min(i_off + 3, len(t) - 1)
        i_a = max(0, i_off - 60)
        bz_tr = []
        qkp = qk
        for i in range(i_a, i1 + 1):
            b, _, qkp = bz_fk(md, model, is_cvt, l_i, d["q1"][i], d["q2"][i], qkp)
            bz_tr.append(b)
        bz_tr = np.array(bz_tr)
        tt = t[i_a:i1 + 1]
        vz = np.gradient(bz_tr, tt)
        k_lo = i_off - i_a
        v_lo = float(np.median(vz[max(0, k_lo - 4):k_lo + 1]))   # 이륙 직전 ~20ms 중앙값
        bz_lo, c_lo, _ = bz_fk(md, model, is_cvt, l_i, d["q1"][i_off], d["q2"][i_off], qk)
        h_kin = bz_lo + max(v_lo, 0.0) ** 2 / (2 * G)
        # 운동학적 이륙 후보 = FK 탄도 apex(hk)의 피크 (GRF-tail 앞, 진짜 이륙 근사)
        hk_tr = bz_tr + np.maximum(vz, 0.0) ** 2 / (2 * G)
        k_hk = int(np.argmax(hk_tr))
        t_true = float(tt[k_hk]); hk_max = float(hk_tr[k_hk]); bz_hk = float(bz_tr[k_hk])
        W_true = win_upto(t, pw, t_true)          # 가장 보수적(작은) W_in 창
        # ── h_real (repo 규약 소스: p19_all_results npz 메타) ──
        z = np.load(NPZ_ROOT / DSDIR[ds] / "traj" / f"{sub}__A.npz", allow_pickle=True)
        h_real = float(z["h_real"])
        bz_npz0 = float(z["bz"][int(np.argmin(np.abs(z["t"] - 0.0)))])
        # ── 엄밀 창: apex까지의 모터 일 (모터는 내부력 — 접지 여부와 무관하게 계상) ──
        t_apex = t_true + np.sqrt(2 * max(h_real - bz_hk, 0.0) / G)
        apex_clip = t_apex > t[-1]
        W_apex = win_upto(t, pw, min(t_apex, t[-1]))
        # ── 원장 ──
        E_req = M_TOT * G * (h_real - bz0)
        rho = W_in / E_req if E_req > 0 else np.nan
        dW = E_req - W_in
        E_req_com = E_req + M_TOT * G * (c_lo - c0)   # CoM 규약 보정 (apex 자세≈이륙 자세 가정)
        # 다리 상대 KE (이륙 시점, flip 질량행렬 추정 — E_req에 미포함인 하한 보강분)
        ke = leg_ke(MJ.MjData(MODEL_F), MODEL_F, d["q1"][i_off], d["q2"][i_off],
                    d["dq1"][i_off], d["dq2"][i_off])
        # 강도 지표 ([0, t_lo] 창)
        m = t <= t_lo
        rows.append(dict(
            ds=ds, sub=str(sub), t_lo=t_lo, W_in=W_in, W_m=W_m, W_p=W_p, W_on=W_on,
            E_req=E_req, rho=rho, dW=dW, h_real=h_real, bz0=bz0, bz_npz0=bz_npz0,
            bz_lo=bz_lo, v_lo=v_lo, h_kin=h_kin, ke_leg=ke,
            t_true=t_true, hk_max=hk_max, W_true=W_true,
            t_apex=t_apex, apex_clip=bool(apex_clip), W_apex=W_apex,
            E_req_com=E_req_com, dW_strict=E_req_com - W_apex,
            dcom=(c_lo - c0) * M_TOT * G,
            pk_dq2=float(np.max(np.abs(d["dq2"][m]))),
            pk_traw2=float(np.max(np.abs(d["traw2"][m]))),
            i_traw2sq=float(np.trapezoid(d["traw2"][m] ** 2, t[m])),
            i_absa2=float(np.trapezoid(np.abs(a2[m]), t[m])),
            i_abspw=float(np.trapezoid(np.abs(pw[m]), t[m])),
        ))

    # ── 표 출력 ──
    hdr = (f"{'ds':18s} {'sub':20s} {'t_lo':>6s} {'W_in':>7s} {'W-30':>7s} {'W+30':>7s} "
           f"{'E_req':>7s} {'rho':>6s} {'dW':>7s} {'h_real':>6s} {'bz0':>6s} "
           f"{'h_kin':>6s} {'v_lo':>5s} {'KEleg':>6s}")
    print("\n=== SIM-FREE 에너지 원장 (푸시 구간 [0, t_lo]) ===")
    print(hdr)
    for r in rows:
        print(f"{r['ds']:18s} {r['sub']:20s} {r['t_lo']:6.3f} {r['W_in']:7.2f} "
              f"{r['W_m']:7.2f} {r['W_p']:7.2f} {r['E_req']:7.2f} {r['rho']:6.3f} "
              f"{r['dW']:7.2f} {r['h_real']:6.3f} {r['bz0']:6.3f} "
              f"{r['h_kin']:6.3f} {r['v_lo']:5.2f} {r['ke_leg']:6.2f}")

    # ── 보조 표: 이륙 규약 변형 + 엄밀(apex) 창 ──
    print("\n=== 창 변형: 운동학 이륙(t_true=hk 피크) / apex까지 (엄밀 원장) ===")
    print(f"{'ds':18s} {'sub':20s} {'t_true':>6s} {'W_true':>7s} {'hk_max':>6s} "
          f"{'t_apex':>6s} {'W_apex':>7s} {'E_com':>6s} {'dW_str':>7s} {'clip':>4s}")
    for r in rows:
        print(f"{r['ds']:18s} {r['sub']:20s} {r['t_true']:6.3f} {r['W_true']:7.2f} "
              f"{r['hk_max']:6.3f} {r['t_apex']:6.3f} {r['W_apex']:7.2f} "
              f"{r['E_req_com']:6.2f} {r['dW_strict']:7.2f} {str(r['apex_clip'])[:4]:>4s}")

    # ── 세션 요약 + 판정 ──
    print("\n=== 세션 요약 ===")
    for ds in sorted(set(r["ds"] for r in rows)):
        rs = [r for r in rows if r["ds"] == ds]
        Wm = np.mean([r["W_in"] for r in rs]); Em = np.mean([r["E_req"] for r in rs])
        print(f"{ds:20s} n={len(rs):2d}  W_in={Wm:6.2f} J  E_req={Em:6.2f} J  "
              f"rho(mean)={np.mean([r['rho'] for r in rs]):.3f}  "
              f"dW(mean)={np.mean([r['dW'] for r in rs]):+.2f} J  "
              f"|dW|>0 trials: {sum(1 for r in rs if r['dW'] > 0)}/{len(rs)}")
    main_rows = [r for r in rows if r["ds"] in MAIN_DS]
    W = np.array([r["W_in"] for r in main_rows]); E = np.array([r["E_req"] for r in main_rows])
    dW = E - W
    print(f"\n판정 대상(0424+0602+0429, n={len(main_rows)}): "
          f"W_in 합 {W.sum():.1f} J vs E_req 합 {E.sum():.1f} J, "
          f"dW 합 {dW.sum():+.1f} J ({100*dW.sum()/max(W.sum(),1e-9):+.1f}% of W_in), "
          f"W_in<E_req 인 트라이얼 {int((dW>0).sum())}/{len(main_rows)}")
    for tag, wk, ek in (("W_true vs E_req  (가장 보수적 창)", "W_true", "E_req"),
                        ("W_apex vs E_com  (엄밀 원장)", "W_apex", "E_req_com")):
        Wx = np.array([r[wk] for r in main_rows]); Ex = np.array([r[ek] for r in main_rows])
        dx = Ex - Wx
        print(f"  변형 [{tag}]: W 합 {Wx.sum():.1f} vs E 합 {Ex.sum():.1f}, "
              f"dW 합 {dx.sum():+.1f} J, W<E 트라이얼 {int((dx>0).sum())}/{len(main_rows)}")

    # ── 형태(shape) 상관: dW / rho vs 강도 지표 ──
    print("\n=== dW·rho vs 강도 상관 (Pearson r) ===")
    keys = ["pk_dq2", "pk_traw2", "i_traw2sq", "i_absa2", "i_abspw", "W_in"]
    def corr_tab(rs, tag):
        if len(rs) < 3:
            return
        dw = np.array([r["dW"] for r in rs]); rh = np.array([r["rho"] for r in rs])
        line_d = " ".join(f"{k}:{np.corrcoef(dw, [r[k] for r in rs])[0,1]:+.2f}" for k in keys)
        line_r = " ".join(f"{k}:{np.corrcoef(rh, [r[k] for r in rs])[0,1]:+.2f}" for k in keys)
        print(f"[{tag}] n={len(rs)}\n  dW : {line_d}\n  rho: {line_r}")
    corr_tab(main_rows, "pooled 0424+0602+0429")
    for ds in MAIN_DS:
        corr_tab([r for r in rows if r["ds"] == ds], ds)

    # ── 보조 진단 출력 ──
    print("\n=== 보조: 규약/민감도 체크 ===")
    db = [abs(r["bz0"] - r["bz_npz0"]) for r in rows]
    print(f"bz0(FK, 오프셋 미적용) vs npz bz(t=0, fit 오프셋+settle): "
          f"|차이| 중앙값 {np.median(db)*100:.2f} cm, 최대 {np.max(db)*100:.2f} cm")
    dk = [r["h_kin"] - r["h_real"] for r in main_rows]
    print(f"운동학 apex 예측 h_kin(GRF-toff 시점) − h_real: 평균 {np.mean(dk)*100:+.1f} cm, "
          f"중앙값 {np.median(dk)*100:+.1f} cm (음수 = 카메라가 인코더 운동학보다 높음)")
    dk2 = [r["hk_max"] - r["h_real"] for r in main_rows]
    print(f"운동학 apex 예측 hk_max(피크 시점) − h_real: 평균 {np.mean(dk2)*100:+.1f} cm, "
          f"중앙값 {np.median(dk2)*100:+.1f} cm — 카메라·인코더 정합성 체크")
    tg = [r["t_lo"] - r["t_true"] for r in main_rows]
    print(f"GRF-toff − 운동학 이륙(hk 피크): 평균 {np.mean(tg)*1000:.0f} ms (loadcell tail)")
    print(f"다리 상대 KE(이륙): 평균 {np.mean([r['ke_leg'] for r in main_rows]):.2f} J "
          f"(E_req에 미포함 — 하한 보강분)")
    print(f"CoM–base 오프셋 변화 M·g·Δc (크라우치→이륙): "
          f"평균 {np.mean([r['dcom'] for r in main_rows]):+.2f} J (base-z 규약의 CoM 보정)")
    on_d = [r["W_in"] - r["W_on"] for r in main_rows]
    print(f"적분 시작점 [0 vs onset]: W 차이 평균 {np.mean(on_d):+.3f} J (홀드 구간 기여)")

    out = HERE / "p22_probe_t3_result.json"
    safe.atomic_json_write(out, dict(rows=rows))
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()
