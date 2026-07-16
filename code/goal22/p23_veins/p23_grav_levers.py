# -*- coding: utf-8 -*-
"""p23_grav_levers — P23 Phase 1: 공중 s2s(26.03.19)로 중력 레버·마찰 직접 측정.

'저울(체중계)·균형점 실측'의 데이터 대체: 로봇을 공중에 매달고(베이스 용접) 다리만
움직인 세션이라 접촉력도 레일힘도 없다. 이때 관절 모터가 낸 토크는 오직
  (중력 레버) + (마찰) + (아주 약한 관성항)
만 설명하면 된다 → 회귀로 다리의 질량×무게중심 조합을 '측정'한다 (점수적합 아님).

방법 (p22_base_params 기계 재사용):
  - 베이스 용접 = 2-DOF (hip, crank; knee/coupler는 폐쇄 kinematics로 종속).
    p22의 free-행에서 ddbz=0, dbz=0으로 두면 정확히 용접-베이스 방정식 (레일행 drop).
  - 좌표 변환 = 레거시 s2s_air 정본 (mshoot_s2s_air_holdout.prep_air):
      q1_model = -(q1_data + o1) - pi/2,  qc_model = -(q2_data + o2),  v/tau도 부호 반전.
      o1_0319/o2_0319 = 현행 스택 값 (s2s_gnd_0319 적합 인코더 영점) — 민감도로 o=0도.
  - dq/ddq: 측정 dq 채널의 Savitzky-Golay (win 11/7/15 민감도, poly 3).
  - 토크: xlsx traw → Paper a_hat (레거시 npz 캐시 미사용 — csv 오염 계보 우회).
  - 식별 가능 조합: 용접-2DOF 구조 전용 합성 기저 (pivoted QR) 재계산.

★ 실측 축퇴 (이 세션의 본질): corr(q1m, qk) = -0.9985 — 힙·무릎이 한 경로로 같이
  움직인다 (포즈 분산의 99.95%가 1축). 따라서 k1/k2류 개별 레버 분리는 구조적으로
  불가능하고, 정직한 산출물은
    (i) whitened-SVD 가시 부분공간(σ>3)에서의 방향별 측정 vs 모델,
    (ii) 경로를 따라가는 준정적(중력) 토크 프로파일 — 적합복원 vs 저속표본중앙값 vs 모델,
    (iii) 마찰·무릎상수 (+널성분 비율 표기).
  a_hat sgn(v) 채터: PRIMARY = |dq_raw|<0.3 행 마스크 (관절별). 무마스크는 민감도.

실행: repo 루트에서 PYTHONIOENCODING=utf-8 python code/goal22/p23_veins/p23_grav_levers.py [--quick]
"""
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "code" / "bench"))
sys.path.insert(0, str(REPO / "code" / "goal22" / "p22_beyond"))
sys.path.insert(0, str(HERE))
import safe  # noqa: E402

safe.utf8_console()
import p22_base_params as PB  # noqa: E402  (AD 배선 포함)
import p23_loaders as LD      # noqa: E402

QUICK = "--quick" in sys.argv
SEED = 23
LI = 0.030                     # ★ 가정 (Clutch 미기록)
NSYN = 400 if QUICK else 1500
CAP = 80 if QUICK else 220     # 사이클당 최대 샘플 (메인)
CAP_SENS = 80                  # 민감도 재실행 cap
SGWIN = 11
NOISE = 0.4                    # Nm 토크 노이즈 스케일 (지시값)
DQ_MASK = 0.3                  # rad/s — a_hat sgn 채터 마스크
DQ_SLOW = 0.2                  # rad/s — 저속(준정적) 표본 판정
SVD_THR = 3.0                  # whitened σ 문턱 (방향별 3σ 이상만 채택)
EDGE = 8                       # 사이클 양끝 SG 에지 버림
NBIN = 25                      # 경로 bin 수
OUT_JSON = HERE / "p23_grav_levers_result.json"

R = {}
REPORT = []


def say(s=""):
    print(s, flush=True)
    REPORT.append(s)


def rms(a):
    a = np.asarray(a, float)
    return float(np.sqrt(np.mean(a ** 2))) if a.size else float("nan")


# ══════════════════ 초기화 ══════════════════
def init():
    PB.AD.ensure_init()
    import p19_judge as P
    import p14_judge as J
    import cvt_core as CC
    import mujoco as mj
    from scipy.signal import savgol_filter
    cand = PB.AD.load_candidate(REPO / "code/goal22/p19_jump/fourbar_p19_candidate.json")
    x32, v, sp, _qoff = PB.AD._p19_args(cand)
    ref = float(v[1])
    FR = J._P["FR"]
    dd26 = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    import g21_p13_linkage as P13
    dd6 = dict(zip(P13.N6, np.asarray(x32)[26:32]))
    PB._R.update(mj=mj, J=J, P=P, CC=CC, savgol=savgol_filter)
    R.update(mj=mj, J=J, P=P, CC=CC, savgol=savgol_filter, x32=np.asarray(x32, float),
             ref=ref, sp=sp, dd26=dd26, dd6=dd6, A=P.A_PAPER,
             stiff=float(v[0]), pre30=float(v[2]),
             o1=float(dd26["o1_0319"]), o2=float(dd26["o2_0319"]))
    rm = PB.RModel(lambda: P.build_flip(x32, ref, sp), "par-weld(l_i=30)")
    R["rm"] = rm
    # 스케일 (p22와 동일 규약)
    scales = np.empty(PB.NX)
    for k, b in enumerate(PB.BODIES):
        m0 = max(rm.pi0[10 * k], 1e-3)
        L = PB.LCHAR[b]
        scales[10 * k] = m0
        scales[10 * k + 1:10 * k + 4] = m0 * L
        scales[10 * k + 4:10 * k + 10] = m0 * L * L
    scales[PB.IDX_ARM] = 0.0115
    scales[[PB.IDX_FV1, PB.IDX_FC1, PB.IDX_FV2, PB.IDX_FC2]] = [0.625, 0.295, 0.35, 0.625]
    R["scales"] = scales
    PB._R["scales"] = scales
    # p22b 후보 (마찰·질량 비교 2열)
    try:
        cb = PB.AD.load_candidate(REPO / "code/goal22/p22_beyond/fourbar_p22b_candidate.json")
        xb, vb, spb, _ = PB.AD._p19_args(cb)
        ddb = dict(zip(FR.NAMES, np.asarray(xb)[:26]))
        ddb6 = dict(zip(P13.N6, np.asarray(xb)[26:32]))
        rmb = PB.RModel(lambda: P.build_flip(xb, float(vb[1]), spb), "p22b-weld")
        R.update(rm_b=rmb, dd26_b=ddb, dd6_b=ddb6, stiff_b=float(vb[0]),
                 pre30_b=float(vb[2]), ref_b=float(vb[1]))
    except Exception as e:
        say(f"  (p22b 후보 로드 실패 — P19만 비교: {e})")
        R["rm_b"] = None


# ══════════════════ 상태 생성 ══════════════════
def real_states(cycles, o1, o2, sgwin, cap):
    """실측 사이클 → 용접-베이스 free 상태 + 행 메타. 반환 (st, md)."""
    sg = R["savgol"]
    J, A = R["J"], R["A"]
    rows = []
    md = dict(cyc=[], qk=[], q1m=[], m1=[], m2=[], adq1=[], adq2=[])
    for ci, c in enumerate(cycles):
        t = c["t"]
        dt = float(np.median(np.diff(t)))
        n = len(t)
        if n < 2 * EDGE + sgwin:
            continue
        dq1s = sg(np.asarray(c["dq1"], float), sgwin, 3)
        dq2s = sg(np.asarray(c["dq2"], float), sgwin, 3)
        dd1 = sg(np.asarray(c["dq1"], float), sgwin, 3, deriv=1, delta=dt)
        dd2 = sg(np.asarray(c["dq2"], float), sgwin, 3, deriv=1, delta=dt)
        a1 = J.ahat(A, c["traw1"], c["dq1"])
        a2 = J.ahat(A, c["traw2"], c["dq2"])
        idx = np.arange(EDGE, n - EDGE)
        if len(idx) > cap:
            idx = idx[np.linspace(0, len(idx) - 1, cap).astype(int)]
        qk0 = None
        for i in idx:
            q1m = -(float(c["q1"][i]) + o1) - np.pi / 2
            qcm = -(float(c["q2"][i]) + o2)
            v1, v2 = -dq1s[i], -dq2s[i]
            aa1, aa2 = -dd1[i], -dd2[i]
            if not np.isfinite([q1m, qcm, v1, v2, aa1, aa2]).all():
                continue
            qpos, qvel, dd0, G, qk0 = PB.make_state(1.0, q1m, qcm, v1, v2, aa1, aa2,
                                                    LI, qk0)
            rows.append((qpos, qvel, dd0, G, aa1, aa2, 0.0, v1, v2))
            md["cyc"].append(ci)
            md["qk"].append(qk0)
            md["q1m"].append(q1m)
            md["m1"].append(-float(a1[i]))
            md["m2"].append(-float(a2[i]))
            md["adq1"].append(abs(float(c["dq1"][i])))
            md["adq2"].append(abs(float(c["dq2"][i])))
    st = PB.pack_states(rows, "free")
    return st, {k: np.asarray(v) for k, v in md.items()}


def syn_states_welded(n, rng):
    """용접-2DOF 구조 기저용 합성 상태 (양의 크랭크 분기 = 실데이터 위상)."""
    rows = []
    for _ in range(n):
        q1 = rng.uniform(-2.0, -0.2)
        qc = rng.uniform(0.9, 2.9)
        dq1, dqc = rng.uniform(-20, 20, 2)
        dd1, ddc = rng.uniform(-600, 600, 2)
        qpos, qvel, dd0, G, _ = PB.make_state(1.0, q1, qc, dq1, dqc, dd1, ddc, LI)
        rows.append((qpos, qvel, dd0, G, dd1, ddc, 0.0, dq1, dqc))
    return PB.pack_states(rows, "free")


def static_states(poses):
    """poses = [(q1, qc), ...] → 무속도 상태 (중력만)."""
    rows = []
    meta = []
    for q1, qc in poses:
        qpos, qvel, dd0, G, qk = PB.make_state(1.0, q1, qc, 0.0, 0.0, 0.0, 0.0, LI)
        rows.append((qpos, qvel, dd0, G, 0.0, 0.0, 0.0, 0.0, 0.0))
        meta.append((q1, qc, qk))
    return PB.pack_states(rows, "free"), meta


def build_free_Y(st, tag, rm=None):
    """p22 build_Y 재사용 → 용접행 = Yfree (ddbz=0 저장됨). U0free = π0 역동역학."""
    out = PB.build_Y([(rm or R["rm"], st)], R["scales"], tag)
    return out["Yfree"], out["U0free"]


def u0_of(rm, st):
    """π0 역동역학(중력·관성)만 — FD 없이 (모델 비교용)."""
    uf, _ = PB.group_u(rm, st)
    return uf.reshape(-1)


# ══════════════════ 사전 검증 ══════════════════
def sanity_JG_branch():
    """양의 크랭크 분기에서도 equality 원본 모델과 closure가 일치하는지 (J·G≈0)."""
    mj = R["mj"]
    model, _ = R["P"].build_flip(R["x32"], R["ref"], R["sp"])
    model.opt.jacobian = mj.mjtJacobian.mjJAC_DENSE
    d = mj.MjData(model)
    worst = 0.0
    qk0 = None
    for qc in (1.6, 2.0, 2.5):
        qk, qp, r, gp, gpp, rp = PB.G_terms(qc, LI, qk0)
        qk0 = qk
        G = PB.G_mat(r, gp)
        d.qpos[:] = 0.0
        d.qpos[[safe.qadr(model, j, mj) for j in PB.JOINTS]] = [1.0, -1.0, qc, qp, qk]
        mj.mj_forward(model, d)
        eq = d.efc_type == mj.mjtConstraint.mjCNSTR_EQUALITY
        if not eq.any():
            say("  (J·G+분기) equality 행 없음?! FAIL")
            return False
        Jm = d.efc_J.reshape(d.nefc, model.nv)[eq]
        iv = [safe.dofadr(model, j, mj) for j in PB.JOINTS]
        JG = Jm[:, iv] @ G
        worst = max(worst, float(np.max(np.abs(JG)) / max(np.max(np.abs(Jm)), 1e-12)))
    ok = worst < 1e-6
    say(f"  (J·G 양의분기 qc=1.6/2.0/2.5) max|J_eq·G|/|J| = {worst:.1e} → "
        f"{'PASS' if ok else 'FAIL'}")
    return ok


def sanity_lin_weld(Y, U0, tag):
    """용접행 선형성: Yfree[:, :NI]·π0 == U0free."""
    pred = Y[:, :PB.NI] @ R["rm"].pi0
    rel = np.linalg.norm(pred - U0) / max(np.linalg.norm(U0), 1e-12)
    ok = rel < 1e-6
    say(f"  ({tag}) Y·π0 vs mj_inverse 상대오차 = {rel:.2e} → {'PASS' if ok else 'FAIL'}")
    return ok


# ══════════════════ 행 유틸 ══════════════════
def extras_const(md):
    """crank행 상수열 (2N,1)."""
    N = len(md["qk"])
    E = np.zeros((2 * N, 1))
    E[1::2, 0] = 1.0
    return E


def extras_spring(md, qk_c):
    N = len(md["qk"])
    E = np.zeros((2 * N, 1))
    E[1::2, 0] = md["qk"] - qk_c
    return E


def targets(md):
    N = len(md["m1"])
    y = np.empty(2 * N)
    y[0::2] = md["m1"]
    y[1::2] = md["m2"]
    return y


def row_arrays(md):
    N = len(md["cyc"])
    joint = np.empty(2 * N, int)     # 0=hip, 1=crank
    joint[0::2] = 0
    joint[1::2] = 1
    cyc = np.repeat(md["cyc"], 2)
    keep = np.empty(2 * N, bool)
    keep[0::2] = md["adq1"] >= DQ_MASK
    keep[1::2] = md["adq2"] >= DQ_MASK
    return joint, cyc, keep


# ══════════════════ 절단-SVD WLS ══════════════════
def tsvd_fit(X, y, joint, sthr=SVD_THR, it=2):
    """관절별 노이즈 2-pass 재가중 + whitened SVD 절단 (σ>sthr 방향만 채택).

    반환: beta(절단해), se(채택 부분공간 내), nf(널성분 비율), spec(σ), kvis,
          Vt, Ut_y(방향별 측정계수), sig(관절별 σ_res), cov(채택 공분산), res.
    """
    sig = np.array([1.0, 1.0])
    beta = np.zeros(X.shape[1])
    for _ in range(it + 1):
        w = 1.0 / sig[joint]
        Xw = X * w[:, None]
        yw = y * w
        U, s, Vt = np.linalg.svd(Xw, full_matrices=False)
        kvis = max(int((s > sthr).sum()), 1)
        c = (U[:, :kvis].T @ yw) / s[:kvis]        # 방향별 측정계수 (whitened)
        beta = Vt[:kvis].T @ c
        res = y - X @ beta
        new = []
        for j in (0, 1):
            m = joint == j
            dof = max(int(m.sum()) - kvis // 2, 1)
            new.append(float(np.sqrt(np.sum(res[m] ** 2) / dof)))
        sig = np.array(new)
    cov = Vt[:kvis].T @ np.diag(1.0 / s[:kvis] ** 2) @ Vt[:kvis]
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    nf = np.sqrt(np.maximum(1.0 - np.sum(Vt[:kvis] ** 2, axis=0), 0.0))
    return dict(beta=beta, se=se, nf=nf, spec=s, kvis=kvis, Vt=Vt, dir_c=c,
                sig=sig, cov=cov, res=res)


# ══════════════════ 메인 ══════════════════
def main():
    t00 = time.time()
    np.set_printoptions(precision=4, suppress=True, linewidth=160)
    say("=" * 100)
    say("P23 Phase 1 — 공중 s2s 중력 레버·마찰 직접 측정 (용접-베이스 회귀자)"
        + ("  [QUICK]" if QUICK else ""))
    say("=" * 100)

    init()
    rm = R["rm"]
    scales = R["scales"]
    say(f"[0] 후보: P19 (fourbar_p19_candidate)  sp={R['sp']} ref={R['ref']:.3f} "
        f"stiff={R['stiff']:.3f} pre30={R['pre30']:.3f}")
    say(f"    0319 오프셋 (s2s_gnd 적합, 현행 스택): o1={R['o1']:+.4f} o2={R['o2']:+.4f} rad")
    say("    body 질량: " + "  ".join(
        f"{b}={rm.pi0[10 * k]:.4f}kg" for k, b in enumerate(PB.BODIES)))
    say(f"    l_i = {LI * 1000:.1f}mm (★가정 — Clutch 미기록)")

    # ── [1] sanity ──
    say("\n[1] 사전 검증")
    rng = np.random.default_rng(SEED)
    ok = PB.sanity_variant(rm)
    ok &= PB.sanity_G_par()
    ok &= sanity_JG_branch()
    ok &= PB.sanity_galilean(rm)
    ok &= PB.sanity_tree_linear(rm, rng, nst=25)
    if not ok:
        say("!! sanity FAIL — 중단.")
        return

    # ── [2] 실데이터 상태 ──
    say(f"\n[2] 실데이터: s2s_air 14사이클 (SG win={SGWIN}, 사이클당 ≤{CAP})")
    cycles, meta = LD.load_s2s_air()
    say(f"    로더: {len(cycles)}사이클, dt={meta['dt_ms']}ms, "
        f"마지막 잘림 drop={meta['dropped_truncated_last']}")
    st, md = real_states(cycles, R["o1"], R["o2"], SGWIN, CAP)
    N = st["N"]
    joint, cyc, keep = row_arrays(md)
    y = targets(md)
    # 경로 축퇴 진단 + 경로 좌표 s (rad 단위 PC1)
    P2 = np.column_stack([md["q1m"] - md["q1m"].mean(), md["qk"] - md["qk"].mean()])
    _, sv2, vt2 = np.linalg.svd(P2, full_matrices=False)
    pc1 = vt2[0]
    if pc1[1] < 0:
        pc1 = -pc1
    s_path = P2 @ pc1
    corr_qq = float(np.corrcoef(md["q1m"], md["qk"])[0, 1])
    say(f"    샘플 {N} (행 {2 * N}) — q1m[{md['q1m'].min():+.2f},{md['q1m'].max():+.2f}] "
        f"qk[{md['qk'].min():+.2f},{md['qk'].max():+.2f}] rad")
    say(f"    ★경로 축퇴: corr(q1m,qk)={corr_qq:+.4f}, PC1 분산비 "
        f"{sv2[0] ** 2 / np.sum(sv2 ** 2):.5f}, PC1방향 (Δq1,Δqk)=({pc1[0]:+.3f},{pc1[1]:+.3f})"
        f" → 개별 레버 분리 불가, 경로 프로파일·가시방향으로 보고")
    say(f"    측정 |τ| rms: hip {rms(md['m1']):.3f} Nm / crank {rms(md['m2']):.3f} Nm")
    say(f"    마스크 |dq_raw|≥{DQ_MASK}: hip행 {int(keep[0::2].sum())}/{N} "
        f"crank행 {int(keep[1::2].sum())}/{N} 생존 "
        f"(a_hat sgn(v) 채터 ±(0.269+0.049|Iq|) Nm 회피 — PRIMARY)")

    Yr, U0r = build_free_Y(st, "real")
    ok &= sanity_lin_weld(Yr, U0r, "real 용접행")
    Yr_sc = Yr * scales

    # ── [3] 용접-2DOF 구조 기저 (재계산) ──
    say(f"\n[3] 용접-2DOF 구조 기저 — 합성 {NSYN} 상태 (양의 크랭크 분기, l_i=30)")
    st_syn = syn_states_welded(NSYN, rng)
    Ys, U0s = build_free_Y(st_syn, "syn-weld")
    ok &= sanity_lin_weld(Ys, U0s, "syn 용접행")
    Ys_sc = Ys * scales
    s_syn = np.linalg.svd(Ys_sc, compute_uv=False)
    r_w = int((s_syn > s_syn[0] * 1e-7).sum())
    cn = np.linalg.norm(Ys_sc, axis=0)
    dead = [PB.PNAMES[i] for i in range(PB.NX) if cn[i] < cn.max() * 1e-9]
    say(f"    구조 rank = {r_w} / 55  (죽은 열 {len(dead)}개: base 전부 + 평면 성분)")
    from scipy.linalg import qr as sqr
    Q_, R_, piv = sqr(Ys_sc, mode="economic", pivoting=True)
    pivots = piv[:r_w]
    deps = piv[r_w:]
    Bmat = np.linalg.lstsq(R_[:r_w, :r_w], R_[:r_w, r_w:], rcond=None)[0]
    fold_err = np.linalg.norm(Yr_sc[:, deps] - Yr_sc[:, pivots] @ Bmat) / \
        max(np.linalg.norm(Yr_sc[:, deps]), 1e-12)
    say(f"    접힘 검증: ‖Yr[dep] − Yr[piv]·B‖/‖Yr[dep]‖ = {fold_err:.2e} "
        f"→ {'PASS' if fold_err < 1e-5 else 'FAIL'}")
    ok &= fold_err < 1e-5

    combos_txt = []
    for k in range(r_w):
        pk = pivots[k]
        terms = [PB.PNAMES[pk]]
        for jj, dj in enumerate(deps):
            if abs(Bmat[k, jj]) > 0.02:
                cph = Bmat[k, jj] * scales[pk] / scales[dj]
                terms.append(f"{cph:+.4g}·{PB.PNAMES[dj]}")
        combos_txt.append(" ".join(terms))

    # 모델 θ0 (P19 / p22b) — crank행 유효점성 = fv_knee + d_cpin + d_kneep (l_i=30)
    def theta0_of(rm_x, dd26, dd6):
        th = np.zeros(PB.NX)
        th[:PB.NI] = rm_x.pi0
        th[PB.IDX_ARM] = dd26["arm_knee"]
        th[PB.IDX_FV1] = dd26["fv_hip"]
        th[PB.IDX_FC1] = dd26["fc_hip"]
        th[PB.IDX_FV2] = dd26["fv_knee"] + dd6["d_cpin"] + dd6["d_kneep"]
        th[PB.IDX_FC2] = dd26["fc_knee"]
        return th

    th0 = theta0_of(rm, R["dd26"], R["dd6"])
    th0_b = theta0_of(R["rm_b"], R["dd26_b"], R["dd6_b"]) if R.get("rm_b") else None

    def fold_beta(th):
        tt = th / scales
        return tt[pivots] + Bmat @ tt[deps]        # 스케일 공간 β̃

    b0 = fold_beta(th0)
    b0_b = fold_beta(th0_b) if th0_b is not None else None
    qk_c = float(md["qk"].mean())
    const0 = R["pre30"] + R["stiff"] * (qk_c - R["ref"])   # 모델 무릎상수 (스프링 선형화)
    b0_ext = np.concatenate([b0, [const0]])

    # ── [4] PRIMARY 적합: 기저 + 무릎상수, 마스크, 절단-SVD ──
    E1 = extras_const(md)
    X = np.column_stack([Yr_sc[:, pivots], E1])
    nb = r_w
    names_fit = [f"C{k + 1:02d}" for k in range(nb)] + ["knee_const"]

    say(f"\n[4] PRIMARY 적합 — 기저 {nb} + 무릎상수, |dq|≥{DQ_MASK} 마스크, "
        f"whitened-SVD 절단 σ>{SVD_THR}")
    F = tsvd_fit(X[keep], y[keep], joint[keep])
    say(f"    행 {int(keep.sum())}  σ_res hip={F['sig'][0]:.3f} crank={F['sig'][1]:.3f} Nm"
        f"  (노이즈 지시값 {NOISE})")
    say("    whitened 스펙트럼 σ_i: " + " ".join(f"{x:.1f}" for x in F["spec"]))
    say(f"    가시 방향 {F['kvis']}/{X.shape[1]} (σ>{SVD_THR})")
    # 무마스크·스프링열 변형
    F_full = tsvd_fit(X, y, joint)
    Xsp = np.column_stack([Yr_sc[:, pivots], E1, extras_spring(md, qk_c)])
    F_sp = tsvd_fit(Xsp[keep], y[keep], joint[keep])

    # 모델 예측 잔차 (정확식: U0 + 해석열·모델마찰 + 준정적층)
    def model_pred_exact(rm_x, stiff, pre30, ref_x, dd26, dd6, st_x, Y_x, md_x):
        u0 = u0_of(rm_x, st_x)
        fr = np.array([dd26["arm_knee"], dd26["fv_hip"], dd26["fc_hip"],
                       dd26["fv_knee"] + dd6["d_cpin"] + dd6["d_kneep"], dd26["fc_knee"]])
        p = u0 + Y_x[:, PB.NI:] @ fr
        qs = np.zeros_like(p)
        qs[1::2] = stiff * (md_x["qk"] - ref_x) + pre30
        return p, p + qs

    mp_no, mp_qs = model_pred_exact(rm, R["stiff"], R["pre30"], R["ref"],
                                    R["dd26"], R["dd6"], st, Yr, md)
    if R.get("rm_b"):
        mpb_no, mpb_qs = model_pred_exact(R["rm_b"], R["stiff_b"], R["pre30_b"],
                                          R["ref_b"], R["dd26_b"], R["dd6_b"], st, Yr, md)
    say("\n    잔차 RMSE [Nm] (masked 행):")
    say(f"      {'':30s} {'hip':>8s} {'crank':>8s}")
    rows_res = [("측정−적합(PRIMARY 절단해)", X @ F["beta"]),
                ("측정−모델 P19 (관성·마찰만)", mp_no),
                ("측정−모델 P19 (+스프링+pre30)", mp_qs)]
    if R.get("rm_b"):
        rows_res += [("측정−모델 p22b (관성·마찰만)", mpb_no),
                     ("측정−모델 p22b (+스프링+pre30)", mpb_qs)]
    rows_res.append(("측정−0 (원신호 rms)", np.zeros_like(y)))
    res_table = {}
    for lab, pred in rows_res:
        r_ = y - pred
        h_, c_ = rms(r_[keep & (joint == 0)]), rms(r_[keep & (joint == 1)])
        res_table[lab] = (h_, c_)
        say(f"      {lab:30s} {h_:8.3f} {c_:8.3f}")

    # ── [5a] 가시 방향별 측정 vs 모델 ──
    say(f"\n[5a] 가시 방향별 (whitened-SVD, 계수공간 단위벡터) — 측정 ±1σ vs 모델")
    say(f"     {'#':>3s} {'σ_i':>7s} {'측정':>9s} {'±1σ':>7s} {'P19':>9s}"
        + ((f" {'p22b':>9s}") if b0_b is not None else "") + "  방향 (상위 성분)")
    dir_rows = []
    b0b_ext = (np.concatenate([b0_b, [R["pre30_b"] + R["stiff_b"]
                                      * (qk_c - R["ref_b"])]])
               if b0_b is not None else None)
    for i in range(F["kvis"]):
        vi = F["Vt"][i]
        mv = float(F["dir_c"][i])
        m0 = float(vi @ b0_ext)
        mb = float(vi @ b0b_ext) if b0b_ext is not None else None
        nm = PB.pretty_combo(vi, names_fit, 3)
        dir_rows.append(dict(i=i + 1, sv=float(F["spec"][i]), meas=mv,
                             sd=float(1.0 / F["spec"][i]), p19=m0, p22b=mb, dir=nm))
        say(f"     {i + 1:3d} {F['spec'][i]:7.1f} {mv:9.3f} {1.0 / F['spec'][i]:7.3f} "
            f"{m0:9.3f}" + ((f" {mb:9.3f}") if mb is not None else "") + f"  {nm}")
    say("     (C## = 아래 [5b] 조합 번호. 측정계수/모델계수는 whitened 좌표 —"
        " 방향 내부 비교용, 물리단위는 [5b]·[6])")

    # ── [5b] 조합 테이블 (물리 단위) + 널성분 비율 ──
    say(f"\n[5b] 식별 조합 테이블 — 물리 단위, 절단해 (널성분비 nf>0.5 = 이 데이터로 축퇴)")
    say(f"    {'#':>3s} {'combo':46s} {'측정':>9s} {'±1σ':>8s} {'nf':>5s} {'P19':>9s}"
        + ((f" {'p22b':>9s}") if b0_b is not None else ""))
    tab = []
    for k in range(nb + 1):
        if k < nb:
            pk = pivots[k]
            sc_k = scales[pk]
            cname = combos_txt[k]
        else:
            sc_k = 1.0
            cname = "knee_const [Nm]"
        mv = float(F["beta"][k] * sc_k)
        sv_ = float(F["se"][k] * sc_k)
        nf = float(F["nf"][k])
        m0 = float(b0_ext[k] * sc_k)
        mb = float(b0b_ext[k] * sc_k) if b0b_ext is not None else None
        tag = "축퇴" if nf > 0.5 else ""
        tab.append(dict(combo=cname, meas=mv, sd=sv_, nf=nf, p19=m0, p22b=mb, note=tag))
        say(f"    {k + 1:3d} {cname[:46]:46s} {mv:9.4f} {sv_:8.4f} {nf:5.2f} {m0:9.4f}"
            + ((f" {mb:9.4f}") if mb is not None else "") + f"  {tag}")
    say(f"    (모델 knee_const = pre30 {R['pre30']:.3f} + 스프링@qk_c "
        f"{R['stiff'] * (qk_c - R['ref']):+.3f} = {const0:.3f} — pre30가 점프 세션 층인지"
        " 전 세션 층인지가 이 측정의 판정 대상)")
    ksp = float(F_sp["beta"][-1])
    ksp_se = float(F_sp["se"][-1])
    ksp_nf = float(F_sp["nf"][-1])
    say(f"    (변형: +스프링기울기열) knee_spring = {ksp:+.3f}±{ksp_se:.3f} Nm/rad "
        f"(nf={ksp_nf:.2f}; 모델 stiff={R['stiff']:.3f}) — 경로 축퇴로 중력레버와 혼선, 참고만")

    # ── [6] 경로 준정적 프로파일 (헤드라인) ──
    say(f"\n[6] s2s 경로 준정적 토크 프로파일 [Nm, 모델 프레임] — bin {NBIN}개")
    say("    3원 대조: ①저속표본 중앙값(무가정 측정) ②적합복원(dq=0 외삽) ③모델")
    qbin = np.quantile(s_path, np.linspace(0, 1, NBIN + 1))
    binid = np.clip(np.searchsorted(qbin, s_path, side="right") - 1, 0, NBIN - 1)
    poses = []
    bin_meta = []
    for b in range(NBIN):
        m = binid == b
        if m.sum() < 4:
            continue
        q1b = float(np.median(md["q1m"][m]))
        qkb = float(np.median(md["qk"][m]))
        # 저속 표본 (양방향 통과 중앙값 → 쿨롱 상쇄, sgn 채터 중앙값에 둔감)
        sl1 = m & (md["adq1"] < DQ_SLOW)
        sl2 = m & (md["adq2"] < DQ_SLOW)
        med1 = float(np.median(md["m1"][sl1])) if sl1.sum() >= 5 else float("nan")
        med2 = float(np.median(md["m2"][sl2])) if sl2.sum() >= 5 else float("nan")
        poses.append((q1b, qkb))
        bin_meta.append(dict(s=float(np.median(s_path[m])), q1=q1b, qk=qkb,
                             med1=med1, med2=med2,
                             n=int(m.sum()), n_slow=(int(sl1.sum()), int(sl2.sum()))))
    st_p, meta_p = static_states(poses)
    Yp, _ = build_free_Y(st_p, "static-path")
    Yp_sc = Yp * scales
    qks = np.array([m[2] for m in meta_p])
    Ep = np.zeros((2 * len(meta_p), 1))
    Ep[1::2, 0] = 1.0
    Xp = np.column_stack([Yp_sc[:, pivots], Ep])
    pf = Xp @ F["beta"]
    se_p = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", Xp, F["cov"], Xp), 0.0))
    md_p = dict(qk=qks)
    pm_no, pm_qs = model_pred_exact(rm, R["stiff"], R["pre30"], R["ref"],
                                    R["dd26"], R["dd6"], st_p, Yp, md_p)
    if R.get("rm_b"):
        pmb_no, pmb_qs = model_pred_exact(R["rm_b"], R["stiff_b"], R["pre30_b"],
                                          R["ref_b"], R["dd26_b"], R["dd6_b"],
                                          st_p, Yp, md_p)
    say(f"    {'s':>6s} {'q1m':>7s} {'qk':>6s} | {'hip저속중앙':>10s} {'hip적합':>8s} "
        f"{'±1σ':>5s} {'hipP19':>8s} | {'cr저속중앙':>9s} {'cr적합':>8s} {'±1σ':>5s} "
        f"{'crP19+qs':>9s} {'crP19-qs':>9s}")
    path_tab = []
    for j, bm in enumerate(bin_meta):
        h_f, c_f = float(pf[2 * j]), float(pf[2 * j + 1])
        h_se, c_se = float(se_p[2 * j]), float(se_p[2 * j + 1])
        h_m, c_mq = float(pm_no[2 * j]), float(pm_qs[2 * j + 1])
        c_mn = float(pm_no[2 * j + 1])
        path_tab.append(dict(**bm, hip_fit=h_f, hip_se=h_se, hip_p19=h_m,
                             cr_fit=c_f, cr_se=c_se, cr_p19_qs=c_mq, cr_p19_noqs=c_mn,
                             hip_p22b=(float(pmb_no[2 * j]) if R.get("rm_b") else None),
                             cr_p22b_qs=(float(pmb_qs[2 * j + 1]) if R.get("rm_b") else None)))
        say(f"    {bm['s']:6.2f} {bm['q1']:7.3f} {bm['qk']:6.3f} | {bm['med1']:10.3f} "
            f"{h_f:8.3f} {h_se:5.2f} {h_m:8.3f} | {bm['med2']:9.3f} {c_f:8.3f} "
            f"{c_se:5.2f} {c_mq:9.3f} {c_mn:9.3f}")
    # 경로 기울기 (Nm per rad of lean, s = PC1 rad)
    sarr = np.array([b["s"] for b in bin_meta])
    lever = {}
    for nm, arr in (("hip 저속중앙", np.array([b["med1"] for b in bin_meta])),
                    ("hip 적합", pf[0::2]), ("hip P19", pm_no[0::2]),
                    ("crank 저속중앙", np.array([b["med2"] for b in bin_meta])),
                    ("crank 적합", pf[1::2]), ("crank P19(+qs)", pm_qs[1::2]),
                    ("crank P19(−qs)", pm_no[1::2])):
        mfin = np.isfinite(arr)
        if mfin.sum() < 3:
            continue
        A_ = np.column_stack([sarr[mfin], np.ones(mfin.sum())])
        cc, *_ = np.linalg.lstsq(A_, arr[mfin], rcond=None)
        lever[nm] = (float(cc[0]), float(cc[1]))
    say("    경로 레버 dτ/ds [Nm/rad] (+절편 [Nm], s=PC1 좌표):")
    for nm, (sl, ic) in lever.items():
        say(f"      {nm:16s} 기울기 {sl:+8.3f}  절편 {ic:+7.3f}")
    if R.get("rm_b"):
        say(f"    p22b 경로 RMSE 참고: hip(관성·마찰만) "
            f"{rms(np.array([b['med1'] for b in bin_meta]) - pmb_no[0::2]):.3f} / "
            f"crank(+qs) {rms(np.array([b['med2'] for b in bin_meta]) - pmb_qs[1::2]):.3f}")

    # ── [7] 마찰 (물리 단위 + nf) ──
    say("\n[7] 마찰·armature (회귀공간 값 — 빌더 매핑: fv=dof damping, fc=frictionloss"
        "→tanh(dq/0.02) 근사; crank행 점성 모델값 = fv_knee+d_cpin+d_kneep)")
    fr_rows = []
    for nm, pi_idx, mdl_p19, mdl_b in (
            ("fv_hip [Nm·s/rad]", PB.IDX_FV1, R["dd26"]["fv_hip"],
             R.get("dd26_b", {}).get("fv_hip")),
            ("fc_hip [Nm]", PB.IDX_FC1, R["dd26"]["fc_hip"],
             R.get("dd26_b", {}).get("fc_hip")),
            ("fv_crank(유효) [Nm·s/rad]", PB.IDX_FV2,
             R["dd26"]["fv_knee"] + R["dd6"]["d_cpin"] + R["dd6"]["d_kneep"],
             (R["dd26_b"]["fv_knee"] + R["dd6_b"]["d_cpin"] + R["dd6_b"]["d_kneep"])
             if R.get("rm_b") else None),
            ("fc_crank [Nm]", PB.IDX_FC2, R["dd26"]["fc_knee"],
             R.get("dd26_b", {}).get("fc_knee")),
            ("arm_knee [kg·m²]", PB.IDX_ARM, R["dd26"]["arm_knee"],
             R.get("dd26_b", {}).get("arm_knee"))):
        if pi_idx not in pivots:
            say(f"    {nm}: 피벗 아님 (조합에 흡수) — 스킵")
            continue
        kloc = list(pivots).index(pi_idx)
        mv = float(F["beta"][kloc] * scales[pi_idx])
        sv_ = float(F["se"][kloc] * scales[pi_idx])
        nf = float(F["nf"][kloc])
        fr_rows.append(dict(name=nm, meas=mv, sd=sv_, nf=nf, p19=float(mdl_p19),
                            p22b=(float(mdl_b) if mdl_b is not None else None)))
        say(f"    {nm:26s} 측정 {mv:8.4f} ±{sv_:.4f} (nf={nf:.2f})   P19 {mdl_p19:8.4f}"
            + ((f"   p22b {mdl_b:8.4f}") if mdl_b is not None else ""))
    say("    (주의: 측정 fc는 '관절 쿨롱 − a_hat 모터마찰 보정오차'의 합 — Paper A2/A3가"
        " 이 레짐에서 과보정이면 음수 가능)")

    # ── [8] 교차검증 ──
    say("\n[8] 교차검증 — 사이클 1-10 적합 → 11-14 예측 (masked 행, 절단해)")
    tr_m = keep & (cyc < 10)
    te_m = keep & (cyc >= 10)
    f_tr = tsvd_fit(X[tr_m], y[tr_m], joint[tr_m])
    res_te = y - X @ f_tr["beta"]
    say(f"    학습행 {int(tr_m.sum())} / 시험행 {int(te_m.sum())}  "
        f"(kvis={f_tr['kvis']}/{X.shape[1]})")
    say(f"      {'':26s} {'hip':>8s} {'crank':>8s}")
    cv_rows = [("train 잔차", res_te, tr_m),
               ("held-out 잔차", res_te, te_m),
               ("held-out 모델 P19(+qs)", y - mp_qs, te_m),
               ("held-out 모델 P19(−qs)", y - mp_no, te_m),
               ("held-out 원신호 rms", y, te_m)]
    cv = {}
    for lab, r_, mm in cv_rows:
        h_, c_ = rms(r_[mm & (joint == 0)]), rms(r_[mm & (joint == 1)])
        cv[lab] = (h_, c_)
        say(f"      {lab:26s} {h_:8.3f} {c_:8.3f}")

    # ── [9] 민감도 ──
    say(f"\n[9] 민감도 (cap {CAP_SENS}) — 헤드라인: 경로레버 기울기(적합)·마찰·무릎상수")

    def headline(md_x, st_x, Y_x, tag):
        jx, cx, kx = row_arrays(md_x)
        yx = targets(md_x)
        Xx = np.column_stack([(Y_x * scales)[:, pivots], extras_const(md_x)])
        fx = tsvd_fit(Xx[kx], yx[kx], jx[kx])
        pfx = Xp @ fx["beta"]
        A_ = np.column_stack([sarr, np.ones(len(sarr))])
        sl_h = float(np.linalg.lstsq(A_, pfx[0::2], rcond=None)[0][0])
        sl_c = float(np.linalg.lstsq(A_, pfx[1::2], rcond=None)[0][0])
        iv1 = list(pivots).index(PB.IDX_FV1)
        iv2 = list(pivots).index(PB.IDX_FV2)
        ic1 = list(pivots).index(PB.IDX_FC1)
        ic2 = list(pivots).index(PB.IDX_FC2)
        out = dict(lever_hip=sl_h, lever_crank=sl_c, kvis=int(fx["kvis"]),
                   fv_hip=float(fx["beta"][iv1] * scales[PB.IDX_FV1]),
                   fv_crank=float(fx["beta"][iv2] * scales[PB.IDX_FV2]),
                   fc_hip=float(fx["beta"][ic1] * scales[PB.IDX_FC1]),
                   fc_crank=float(fx["beta"][ic2] * scales[PB.IDX_FC2]),
                   knee_const=float(fx["beta"][nb]),
                   sig=[float(v) for v in fx["sig"]])
        say(f"    {tag:14s}: lever h/c {sl_h:+7.3f}/{sl_c:+7.3f}  fv {out['fv_hip']:.3f}/"
            f"{out['fv_crank']:.3f}  fc {out['fc_hip']:+.3f}/{out['fc_crank']:+.3f}  "
            f"const {out['knee_const']:+.3f}  kvis={out['kvis']}")
        return out

    sens = {}
    for wn in (7, 11, 15):
        st_w, md_w = real_states(cycles, R["o1"], R["o2"], wn, CAP_SENS)
        Yw, _ = build_free_Y(st_w, f"real-w{wn}")
        sens[f"sg{wn}"] = headline(md_w, st_w, Yw, f"SG win={wn}")
    st_o, md_o = real_states(cycles, 0.0, 0.0, SGWIN, CAP_SENS)
    Yo, _ = build_free_Y(st_o, "real-o0")
    sens["off0"] = headline(md_o, st_o, Yo, "오프셋 o=0")
    # 무마스크 (동일 X, keep=all)
    pf_full = Xp @ F_full["beta"]
    A_ = np.column_stack([sarr, np.ones(len(sarr))])
    sens["nomask"] = dict(
        lever_hip=float(np.linalg.lstsq(A_, pf_full[0::2], rcond=None)[0][0]),
        lever_crank=float(np.linalg.lstsq(A_, pf_full[1::2], rcond=None)[0][0]),
        knee_const=float(F_full["beta"][nb]), kvis=int(F_full["kvis"]))
    say(f"    {'무마스크':14s}: lever h/c {sens['nomask']['lever_hip']:+7.3f}/"
        f"{sens['nomask']['lever_crank']:+7.3f}  const "
        f"{sens['nomask']['knee_const']:+.3f}  kvis={sens['nomask']['kvis']}")

    # ── 저장 ──
    res = dict(
        quick=QUICK, li=LI, sgwin=SGWIN, cap=CAP, noise=NOISE, dq_mask=DQ_MASK,
        svd_thr=SVD_THR, o1_0319=R["o1"], o2_0319=R["o2"], qk_center=qk_c,
        n_samples=int(N), n_rows_masked=int(keep.sum()),
        path=dict(corr_q1_qk=corr_qq, pc1=[float(x) for x in pc1],
                  pc1_var=float(sv2[0] ** 2 / np.sum(sv2 ** 2))),
        rank_welded=r_w, kvis=int(F["kvis"]),
        spec=[float(x) for x in F["spec"]],
        dead_cols=dead, combos=combos_txt,
        pivots=[PB.PNAMES[p] for p in pivots],
        dir_table=dir_rows, combo_table=tab, friction=fr_rows,
        knee_spring_variant=dict(meas=ksp, sd=ksp_se, nf=ksp_nf, model=R["stiff"]),
        sig_res=dict(hip=float(F["sig"][0]), crank=float(F["sig"][1])),
        fold_err=float(fold_err),
        res_table={k: list(v) for k, v in res_table.items()},
        path_profile=path_tab, path_lever={k: list(v) for k, v in lever.items()},
        cv={k: list(v) for k, v in cv.items()},
        cv_kvis=int(f_tr["kvis"]),
        sens=sens,
        report="\n".join(REPORT))
    safe.atomic_json_write(OUT_JSON, res)
    say(f"\n저장: {OUT_JSON}")
    say(f"총 {time.time() - t00:.0f}s")


if __name__ == "__main__":
    main()
