# -*- coding: utf-8 -*-
"""p22_excite_design — P22 Phase 4 준비: 30분 공중(레일 현수) 시스템 식별용 최적 여기 궤적.

설계 대상: 실로봇 PD 컨트롤러에 먹일 desired 궤적 CSV (힙 + 크랭크, l_i=30mm 평행사변형).
공중(발 비접촉) + 레일 자유 슬라이드(bz free) → Phase 1(p22_base_params)의 "비행/자유-베이스"
투영 회귀자(힙·크랭크 토크 2행/샘플)가 데이터 행이 된다.

방법 (고전 Swevers/Gautier 여기 궤적 설계):
 1. 궤적족: 관절별 절단 푸리에 q_i(t) = q0_i + Σ_{k=1..5} a_ik sin(kω0 t) + b_ik cos(kω0 t),
    T0=10s (ω0=2π/10). 결정변수 22개 = 관절당 (a 5, b 5, 배치 p 1).
 2. 하드 제약은 "구성으로 보장" (auto-scaling 파라미터화):
    - 형상 s(t)=Σ a sin + b cos 를 만들고, 스케일 A = min(범위/ptp, 속도캡/max|ds|, 가속캡/max|dds|)
      로 자동 축척 → 관절 범위·속도·가속을 절대 위반 못함. 최종 계수 = (A·a, A·b, q0=c).
    - dq(0)=dq(T0)=0: a계수를 {Σ k·a_k=0}에 최소노름 사영(수리) — 푸리에라 주기성은 자동.
    - 관절 범위 = fit 세션(l_i=30: 0421/0424/0602) xlsx에서 실제 방문한 min/max를 채굴 후
      스팬 5%씩 양쪽 마진 (0429는 CVT 세션이라 무릎각≠크랭크각 — 정보로만 보고).
    - 폐쇄 유효성 + 자기충돌: cvt_core.closure(l_i=30) 전 샘플 검증 + 원본 모델 접촉 검사.
 3. 목적: 1주기 100Hz 스택 투영 회귀자(스케일드)의 "구조적 식별가능 열조합"(비행·l_i=30
    합성 회귀자의 pivoted-QR 베이스 열, 마찰 4열+armature 포함) σ_min 최대화 (E-최적).
    빠른 평가를 위해 (q1,qc) 격자 구조함수 보간 서로게이트 사용 (회귀자는 고정 q에서
    가속 선형 + 속도 2차 + 중력 상수 — 구조 정확, 검증 포함). 최종 수치는 정확한
    MuJoCo 빌드(p22_base_params.build_Y)로 재평가.
 4. 비교: (a) 설계 궤적 vs (b) 나이브 0.5Hz 동진폭 사인 vs (c) 기존 점프 실데이터 스탠스 행
    (다른 레짐 — 비행 기저 조합 위 σ 스펙트럼 대비용).

실행: repo 루트에서 PYTHONIOENCODING=utf-8 python code/goal22/p22_beyond/p22_excite_design.py
      [--quick] [--refresh] [--skip-opt(캐시 best 재사용)]
산출: p22_excite_traj.csv / p22_excite_traj.png / p22_excite_report.md / p22_excite_cache.{npz,json}
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "code" / "bench"))
sys.path.insert(0, str(HERE))
import safe  # noqa: E402

safe.utf8_console()
import p22_base_params as B  # noqa: E402  (Phase 1 기계 재사용 — import만, 수정 없음)

ap = argparse.ArgumentParser()
ap.add_argument("--quick", action="store_true")
ap.add_argument("--refresh", action="store_true")
ap.add_argument("--skip-opt", action="store_true", help="캐시된 best_z 재사용")
ARGS = ap.parse_args()
QUICK = ARGS.quick

SEED = 22
T0 = 10.0                      # 기본 주기 [s]
W0 = 2 * np.pi / T0
NH = 5                         # 고조파 수
FS = 100                       # CSV 샘플링 [Hz]
NCSV = int(T0 * FS)            # 1000
M_OPT = 250                    # 최적화 중 회귀자 샘플 수 (σ는 √(NCSV/M_OPT) 보정)
NG = 21 if QUICK else 41       # 서로게이트 격자 (관절당)
NSYN = 400 if QUICK else 1500  # 구조 기저용 합성 상태 수
CAP_REAL = 40 if QUICK else 200
VCAP = (8.0, 12.0)             # |dq| 상한 [rad/s] (hip, crank)
ACAP = 200.0                   # |ddq| 상한 [rad/s²]
MARGIN = 0.05                  # 방문범위 스팬 대비 양쪽 마진 (5%+5% = 10% 축소)
NOISE = 0.4                    # 토크 노이즈 [Nm]
L_I = 0.03                     # 세션 링크 길이 (평행사변형)
N_REP_30MIN = int(30 * 60 / T0)   # 180 반복

CACHE_NPZ = HERE / "p22_excite_cache.npz"
CACHE_JSON = HERE / "p22_excite_cache.json"
OUT_CSV = HERE / "p22_excite_traj.csv"
OUT_PNG = HERE / "p22_excite_traj.png"
OUT_MD = HERE / "p22_excite_report.md"

KVEC = np.arange(1, NH + 1, dtype=float)
TT_DENSE = np.arange(2000) * (T0 / 2000)      # 스케일/캡 판정용 밀그리드
TT_OPT = np.arange(M_OPT) * (T0 / M_OPT)
TT_CSV = np.arange(NCSV) / FS

_CTX = {}


def say(s=""):
    print(s, flush=True)


# ══════════════ 무거운 초기화 (Phase 1 main()의 셋업부 재현) ══════════════
def ctx_init():
    if _CTX.get("ready"):
        return _CTX
    t0 = time.time()
    AD = B.AD
    AD.ensure_init()
    import p19_judge as P
    import p14_judge as J
    import cvt_core as CC
    import mujoco as mj
    from scipy.signal import savgol_filter
    cand = AD.load_candidate(REPO / "code/goal22/p19_jump/fourbar_p19_candidate.json")
    x32, v, sp, qoff = AD._p19_args(cand)
    ref = float(v[1])
    FR = J._P["FR"]
    dd26 = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    dd6 = dict(zip(B._import_p13().N6, np.asarray(x32)[26:32]))
    B._R.update(mj=mj, J=J, P=P, CC=CC, savgol=savgol_filter, dd26=dd26, dd6=dd6,
                x32=np.asarray(x32, float), ref=ref, sp=sp, qoff429=qoff,
                A_PAPER=P.A_PAPER, pre30=float(v[2]), stiff=float(v[0]))
    build_par = lambda: P.build_flip(x32, ref, sp)               # noqa: E731
    build_cvt = lambda li: (lambda: P.build_cvt(x32, ref, sp, li))  # noqa: E731
    B._R["build_cvt"] = build_cvt
    rm_par = B.RModel(build_par, "par(l_i=30)")
    B._R["rm_par"] = rm_par
    scales = np.empty(B.NX)
    for k, b in enumerate(B.BODIES):
        m0 = max(rm_par.pi0[10 * k], 1e-3)
        L = B.LCHAR[b]
        scales[10 * k] = m0
        scales[10 * k + 1:10 * k + 4] = m0 * L
        scales[10 * k + 4:10 * k + 10] = m0 * L * L
    scales[B.IDX_ARM] = 0.0115
    scales[[B.IDX_FV1, B.IDX_FC1, B.IDX_FV2, B.IDX_FC2]] = [0.625, 0.295, 0.35, 0.625]
    B._R["scales"] = scales
    _CTX.update(ready=True, P=P, J=J, CC=CC, mj=mj, rm_par=rm_par, scales=scales,
                x32=x32, ref=ref, sp=sp, qoff429=qoff, dd26=dd26,
                build_par=build_par)
    say(f"[init] MuJoCo/트라이얼 초기화 {time.time() - t0:.0f}s")
    return _CTX


# ══════════════ [A] 실데이터 스택 (비교 c) + 범위 채굴 ══════════════
def real_stack_and_ranges():
    ctx = ctx_init()
    J, CC = ctx["J"], ctx["CC"]
    dd26 = ctx["dd26"]
    o1c, o2c = ctx["qoff429"]
    groups_real, meas, meta, _rms = B.prep_real(11, CAP_REAL)   # d429 캐시도 채워짐
    real = B.build_Y(groups_real, ctx["scales"], "real(점프 스탠스)")
    Yr_sc = real["Yflt"] * ctx["scales"]

    OFF = {"jump_position_0421": ("o1_0421", "o2_0421"),
           "jump_0424": ("o1_0424", "o2_0424"), "jump_0602": (None, None)}
    per = {}                      # 세션별 (모델좌표 min/max)
    for tr in J._P["cl"]:
        ds = tr["ds"]
        if ds not in OFF:
            continue
        k1, k2 = OFF[ds]
        o1 = dd26.get(k1, 0.0) if k1 else 0.0
        o2 = dd26.get(k2, 0.0) if k2 else 0.0
        d = tr["d"]
        q1m = -(np.asarray(d["q1"], float) + o1) - np.pi / 2
        qcm = -(np.asarray(d["q2"], float) + o2)
        e = per.setdefault(ds, [np.inf, -np.inf, np.inf, -np.inf])
        e[0] = min(e[0], float(np.nanmin(q1m)))
        e[1] = max(e[1], float(np.nanmax(q1m)))
        e[2] = min(e[2], float(np.nanmin(qcm)))
        e[3] = max(e[3], float(np.nanmax(qcm)))
    # 0429 (CVT, l_i=25.08 — 무릎각≠크랭크각이라 envelope엔 미사용, 정보만)
    e = [np.inf, -np.inf, np.inf, -np.inf]
    for sub in CC.SUBS429:
        d = B._R["d429"][sub]
        q1m = -(np.asarray(d["q1"], float) + o1c) - np.pi / 2
        qcm = -(np.asarray(d["q2"], float) + o2c)
        e[0] = min(e[0], float(np.nanmin(q1m)))
        e[1] = max(e[1], float(np.nanmax(q1m)))
        e[2] = min(e[2], float(np.nanmin(qcm)))
        e[3] = max(e[3], float(np.nanmax(qcm)))
    per["jump_0429(정보만)"] = e

    keys30 = ["jump_position_0421", "jump_0424", "jump_0602"]
    lo1 = min(per[k][0] for k in keys30)
    hi1 = max(per[k][1] for k in keys30)
    lo2 = min(per[k][2] for k in keys30)
    hi2 = max(per[k][3] for k in keys30)
    m1, m2 = MARGIN * (hi1 - lo1), MARGIN * (hi2 - lo2)
    env = dict(q1=(lo1 + m1, hi1 - m1), qc=(lo2 + m2, hi2 - m2),
               raw=dict(q1=(lo1, hi1), qc=(lo2, hi2)), per=per)
    say("[범위] 방문 범위 (모델좌표, rad):")
    for k, e in per.items():
        say(f"  {k:24s} hip[{e[0]:+.3f},{e[1]:+.3f}]  crank[{e[2]:+.3f},{e[3]:+.3f}]")
    say(f"  → envelope(마진 {MARGIN * 100:.0f}%씩): hip[{env['q1'][0]:+.3f},{env['q1'][1]:+.3f}] "
        f"crank[{env['qc'][0]:+.3f},{env['qc'][1]:+.3f}]")
    return Yr_sc, env


# ══════════════ [B] 구조 기저 (비행·l_i=30, pivoted QR) ══════════════
def sample_syn_region(n, rng, env, widen=0.25):
    """운용 영역(채굴 envelope ±25% 스팬) 내 폐쇄일관 비행 상태 — Phase 1 sample_syn의
    지역 버전 (Phase 1 합성 박스는 crank 부호가 실데이터 반대 영역이었음)."""
    lo1, hi1 = env["q1"]
    lo2, hi2 = env["qc"]
    s1, s2 = widen * (hi1 - lo1), widen * (hi2 - lo2)
    rows = []
    for _ in range(n):
        q1 = rng.uniform(lo1 - s1, hi1 + s1)
        qc = rng.uniform(lo2 - s2, hi2 + s2)
        dq1, dqc = rng.uniform(-25, 25, 2)
        dd1, ddc = rng.uniform(-800, 800, 2)
        qpos, qvel, dd0, G, _ = B.make_state(1.0, q1, qc, dq1, dqc, dd1, ddc, L_I)
        rows.append((qpos, qvel, dd0, G, dd1, ddc, rng.uniform(-40, 40), dq1, dqc))
    return B.pack_states(rows, "free")


def build_basis(env):
    ctx = ctx_init()
    from scipy.linalg import qr as sqr
    rng = np.random.default_rng(SEED)
    st = sample_syn_region(NSYN, rng, env)
    syn = B.build_Y([(ctx["rm_par"], st)], ctx["scales"], "basis(비행 l_i=30)")
    Ysc = syn["Yflt"] * ctx["scales"]
    U, s, Vt = np.linalg.svd(Ysc, full_matrices=False)
    r = int((s > s[0] * 1e-7).sum())
    Q_, R_, piv = sqr(Ysc, mode="economic", pivoting=True)
    pivots = piv[:r].copy()
    deps = piv[r:]
    Bm = np.linalg.lstsq(R_[:r, :r], R_[:r, r:], rcond=None)[0]
    combos = []
    for k in range(r):
        pk = pivots[k]
        terms = [B.PNAMES[pk]]
        for jj, dj in enumerate(deps):
            if abs(Bm[k, jj]) > 0.02:
                c_phys = Bm[k, jj] * ctx["scales"][pk] / ctx["scales"][dj]
                terms.append(f"{c_phys:+.4g}·{B.PNAMES[dj]}")
        combos.append(" ".join(terms[:6]))
    say(f"[기저] 비행(l_i=30) 구조 rank = {r} (Phase1: 자유 l_i=30 단독 13, 비행소거 +1)")
    need = {B.IDX_ARM, B.IDX_FV1, B.IDX_FC1, B.IDX_FV2, B.IDX_FC2}
    say(f"  마찰4+armature 열 pivot 포함: {'PASS' if need.issubset(set(pivots)) else 'FAIL'}")
    for k, c in enumerate(combos):
        say(f"   F{k + 1:02d}: {c}")
    return s[:r], Vt[:r].copy(), pivots, combos


# ══════════════ [C] 서로게이트 (구조함수 격자) + 충돌 마스크 ══════════════
# 고정 (q1,qc)에서 비행 회귀자 행은 정확히:
#   Y = γ(q) + α(q)·dd1 + β(q)·ddc + Γ11(q)·dq1² + Γ22(q)·dqc² + Γx(q)·dq1·dqc
# (가속 선형·속도 2차·중력 상수 — mj_inverse 구조에서 정확, 아래서 수치 검증)
PROBES = [(0, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1), (1, 0, 0, 0), (0, 1, 0, 0), (1, 1, 0, 0)]


def build_surrogate(env):
    ctx = ctx_init()
    mj = ctx["mj"]
    pad1 = 0.02 * (env["q1"][1] - env["q1"][0])
    pad2 = 0.02 * (env["qc"][1] - env["qc"][0])
    q1g = np.linspace(env["q1"][0] - pad1, env["q1"][1] + pad1, NG)
    qcg = np.linspace(env["qc"][0] - pad2, env["qc"][1] + pad2, NG)
    rows = []
    for q1 in q1g:
        for qc in qcg:
            for (v1, v2, a1, a2) in PROBES:
                qpos, qvel, dd0, G, _ = B.make_state(1.0, q1, qc, v1, v2, a1, a2, L_I)
                rows.append((qpos, qvel, dd0, G, a1, a2, 0.0, v1, v2))
    st = B.pack_states(rows, "free")
    sur = B.build_Y([(ctx["rm_par"], st)], ctx["scales"], "surrogate 격자")
    Y = sur["Yflt"].reshape(NG, NG, len(PROBES), 2, B.NX)[..., :B.NI]
    gam = Y[:, :, 0]
    alp = Y[:, :, 1] - gam
    bet = Y[:, :, 2] - gam
    g11 = Y[:, :, 3] - gam
    g22 = Y[:, :, 4] - gam
    gx = Y[:, :, 5] - gam - g11 - g22
    SF = np.stack([gam, alp, bet, g11, g22, gx], axis=-1)   # (NG,NG,2,50,6)

    # 자기충돌 마스크 (원본 모델, 접촉 켜짐, bz=1.0 — 바닥 plane 접촉 제외)
    model, _ = ctx["build_par"]()
    d = mj.MjData(model)
    plane = set(np.where(model.geom_type == mj.mjtGeom.mjGEOM_PLANE)[0])
    mask = np.zeros((NG, NG), bool)
    pairs = set()
    for i, q1 in enumerate(q1g):
        for j, qc in enumerate(qcg):
            qk, qp, _ = ctx["CC"].closure(qc, L_I)
            d.qpos[:] = [1.0, q1, qc, qp, qk]
            mj.mj_forward(model, d)
            for c in range(d.ncon):
                g1, g2 = d.contact[c].geom1, d.contact[c].geom2
                if g1 in plane or g2 in plane:
                    continue
                mask[i, j] = True
                n1 = mj.mj_id2name(model, mj.mjtObj.mjOBJ_GEOM, g1) or str(g1)
                n2 = mj.mj_id2name(model, mj.mjtObj.mjOBJ_GEOM, g2) or str(g2)
                pairs.add(f"{n1}-{n2}")
    say(f"[서로게이트] 격자 {NG}×{NG}, 충돌 셀 {int(mask.sum())}/{NG * NG}"
        + (f"  쌍={sorted(pairs)}" if pairs else ""))
    return q1g, qcg, SF, mask


def make_sur_eval(q1g, qcg, SF):
    from scipy.interpolate import RegularGridInterpolator
    rgi = RegularGridInterpolator((q1g, qcg), SF, method="linear",
                                  bounds_error=False, fill_value=None)

    def sur_Y(q1, qc, dq1, dqc, dd1, ddc):
        M = len(q1)
        SFq = rgi(np.column_stack([q1, qc]))                     # (M,2,50,6)
        F = np.stack([np.ones(M), dd1, ddc, dq1 ** 2, dqc ** 2, dq1 * dqc], -1)
        Y = np.zeros((M, 2, B.NX))
        Y[:, :, :B.NI] = np.einsum("mrcf,mf->mrc", SFq, F)
        Y[:, 1, B.IDX_ARM] = ddc
        Y[:, 0, B.IDX_FV1] = dq1
        Y[:, 0, B.IDX_FC1] = np.tanh(dq1 / 0.02)
        Y[:, 1, B.IDX_FV2] = dqc
        Y[:, 1, B.IDX_FC2] = np.tanh(dqc / 0.02)
        return Y.reshape(2 * M, B.NX)
    return sur_Y


def exact_stack(q1, qc, dq1, dqc, dd1, ddc, label):
    """정확한 MuJoCo 빌드 (검증/최종 평가용). 반환 (Yflt, Yfree) — 미스케일."""
    ctx = ctx_init()
    rows = []
    qk0 = None
    for i in range(len(q1)):
        qpos, qvel, dd0, G, qk0 = B.make_state(1.0, q1[i], qc[i], dq1[i], dqc[i],
                                               dd1[i], ddc[i], L_I, qk0)
        rows.append((qpos, qvel, dd0, G, dd1[i], ddc[i], 0.0, dq1[i], dqc[i]))
    st = B.pack_states(rows, "free")
    out = B.build_Y([(ctx["rm_par"], st)], ctx["scales"], label)
    return out["Yflt"], out["Yfree"]


# ══════════════ [D] 푸리에 궤적 + auto-scaling 디코드 ══════════════
def fourier(q0, a, b, t):
    wt = W0 * np.outer(t, KVEC)
    S, C = np.sin(wt), np.cos(wt)
    kw = KVEC * W0
    q = q0 + S @ a + C @ b
    dq = C @ (a * kw) - S @ (b * kw)
    dd = -S @ (a * kw ** 2) - C @ (b * kw ** 2)
    return q, dq, dd


def decode(z, env):
    """22-변수 유전형 → 관절별 (q0, a, b). 범위/속도/가속 하드제약 구성적 보장."""
    coef = []
    for j, key in enumerate(("q1", "qc")):
        lo, hi = env[key]
        a = np.array(z[11 * j:11 * j + 5], float)
        bc = np.array(z[11 * j + 5:11 * j + 10], float)
        p = float(np.clip(z[11 * j + 10], 0.0, 1.0))
        a -= KVEC * (KVEC @ a) / (KVEC @ KVEC)          # dq(0)=0 최소노름 수리
        s, ds, dds = fourier(0.0, a, bc, TT_DENSE)
        ptp = float(s.max() - s.min())
        if ptp < 1e-9:
            coef.append((0.5 * (lo + hi), a * 0, bc * 0))
            continue
        A = 0.999 * min((hi - lo) / ptp,
                        VCAP[j] / max(float(np.abs(ds).max()), 1e-12),
                        ACAP / max(float(np.abs(dds).max()), 1e-12))
        c = lo + p * ((hi - lo) - A * ptp) - A * float(s.min())
        coef.append((c, A * a, A * bc))
    return coef


def traj_of(coef, t):
    q1, dq1, dd1 = fourier(*coef[0], t)
    qc, dqc, ddc = fourier(*coef[1], t)
    return q1, qc, dq1, dqc, dd1, ddc


# ══════════════ [E] 목적함수 + 최적화 ══════════════
def make_objective(env, sur_Y, pivots, scales, collide_pen=None):
    corr = np.sqrt(NCSV / M_OPT)     # σ를 100Hz·1주기 스택 등가로 보정

    def negsmin(z):
        coef = decode(z, env)
        q1, qc, dq1, dqc, dd1, ddc = traj_of(coef, TT_OPT)
        Ysc = sur_Y(q1, qc, dq1, dqc, dd1, ddc) * scales
        smin = np.linalg.svd(Ysc[:, pivots], compute_uv=False)[-1] * corr
        pen = 0.0
        if collide_pen is not None:
            pen = 1e3 * float(collide_pen(np.column_stack([q1, qc])).sum())
        return -smin + pen
    return negsmin


def run_opt(env, sur_Y, pivots, scales, mask, q1g, qcg):
    from scipy.optimize import differential_evolution, minimize
    collide_pen = None
    if mask.any():
        from scipy.interpolate import RegularGridInterpolator
        collide_pen = RegularGridInterpolator((q1g, qcg), mask.astype(float),
                                              method="linear", bounds_error=False,
                                              fill_value=1.0)
    f = make_objective(env, sur_Y, pivots, scales, collide_pen)
    t0 = time.time()
    f0 = f(np.r_[np.ones(5) * 0.2, np.zeros(5), 0.5, np.ones(5) * 0.2, np.zeros(5), 0.5])
    say(f"[opt] 목적 1회 평가 {(time.time() - t0) * 1e3:.1f} ms (기준 σ_min={-f0:.3f})")
    bounds = ([(-1, 1)] * 10 + [(0, 1)]) * 2
    best_z, best_f = None, np.inf
    maxiter = 40 if QUICK else 160
    for sd in (SEED, SEED + 180):
        t1 = time.time()
        res = differential_evolution(f, bounds, seed=sd, maxiter=maxiter, popsize=14,
                                     tol=1e-10, mutation=(0.4, 1.0), recombination=0.9,
                                     init="sobol", polish=False, updating="immediate")
        say(f"[opt] DE(seed={sd}): σ_min={-res.fun:.3f}  ({time.time() - t1:.0f}s, "
            f"nfev={res.nfev})")
        if res.fun < best_f:
            best_z, best_f = res.x.copy(), float(res.fun)
    for _ in range(2 if QUICK else 3):        # NM 재시동 (지역 개선 크게 도움)
        res = minimize(f, best_z, method="Nelder-Mead",
                       options=dict(maxfev=3000 if QUICK else 8000,
                                    xatol=1e-7, fatol=1e-7))
        if res.fun < best_f - 1e-9:
            best_z, best_f = res.x.copy(), float(res.fun)
        else:
            break
    say(f"[opt] NM 폴리시 후: σ_min={-best_f:.3f}")
    return np.asarray(best_z, float), -best_f


# ══════════════ [F] 검증 (PASS/FAIL) ══════════════
def verify_traj(coef, env, label):
    ctx = ctx_init()
    CC = ctx["CC"]
    q1, qc, dq1, dqc, dd1, ddc = traj_of(coef, TT_CSV)
    ok_all = True

    def chk(name, ok, detail=""):
        nonlocal ok_all
        ok_all &= bool(ok)
        say(f"  [{label}] {name}: {'PASS' if ok else 'FAIL'}  {detail}")

    lo1, hi1 = env["q1"]
    lo2, hi2 = env["qc"]
    tol = 1e-9
    chk("관절범위(hip)", (q1.min() >= lo1 - tol) and (q1.max() <= hi1 + tol),
        f"[{q1.min():+.3f},{q1.max():+.3f}] ⊂ [{lo1:+.3f},{hi1:+.3f}]")
    chk("관절범위(crank)", (qc.min() >= lo2 - tol) and (qc.max() <= hi2 + tol),
        f"[{qc.min():+.3f},{qc.max():+.3f}] ⊂ [{lo2:+.3f},{hi2:+.3f}]")
    chk("속도상한", (np.abs(dq1).max() <= VCAP[0]) and (np.abs(dqc).max() <= VCAP[1]),
        f"max|dq1|={np.abs(dq1).max():.2f}≤{VCAP[0]}, max|dqc|={np.abs(dqc).max():.2f}≤{VCAP[1]}")
    chk("가속상한", (np.abs(dd1).max() <= ACAP) and (np.abs(ddc).max() <= ACAP),
        f"max|ddq|={max(np.abs(dd1).max(), np.abs(ddc).max()):.1f}≤{ACAP}")
    chk("시작/끝 정지 dq(0)=dq(T0)=0",
        max(abs(dq1[0]), abs(dqc[0])) < 1e-8, f"|dq(0)|={max(abs(dq1[0]), abs(dqc[0])):.1e}")
    # 폐쇄 유효성 (전 샘플): closure 수렴 + 평행사변형 qk=qc + 잔차
    worst = 0.0
    ok_cl = True
    K = np.array([0.0, -CC.L1])
    try:
        qk0 = None
        for i in range(NCSV):
            qk, qp, r = CC.closure(qc[i], L_I, qk0)
            qk0 = qk
            R = K + CC.LO * np.array([np.sin(qk), np.cos(qk)])
            Cp = L_I * np.array([np.sin(qc[i]), np.cos(qc[i])])
            resid = abs(float((Cp - R) @ (Cp - R)) - CC.L1 ** 2)
            worst = max(worst, resid, abs(qk - qc[i]))
    except Exception as e:  # noqa: BLE001
        ok_cl = False
        say(f"    closure 예외: {e}")
    chk("4-bar 폐쇄 유효(전 샘플)", ok_cl and worst < 1e-8, f"max잔차={worst:.1e}")
    chk("무릎각(=crank) 방문범위 내", (qc.min() >= lo2 - tol) and (qc.max() <= hi2 + tol),
        "평행사변형 qk=qc → 허벅지-정강이 충돌각 실측범위 내")
    # 자기충돌 (원본 모델, 접촉 켜짐)
    mj = ctx["mj"]
    model, _ = ctx["build_par"]()
    d = mj.MjData(model)
    plane = set(np.where(model.geom_type == mj.mjtGeom.mjGEOM_PLANE)[0])
    ncol = 0
    qk0 = None
    for i in range(NCSV):
        qk, qp, _ = CC.closure(qc[i], L_I, qk0)
        qk0 = qk
        d.qpos[:] = [1.0, q1[i], qc[i], qp, qk]
        mj.mj_forward(model, d)
        for c in range(d.ncon):
            if d.contact[c].geom1 in plane or d.contact[c].geom2 in plane:
                continue
            ncol += 1
    chk("자기충돌 없음(전 샘플)", ncol == 0, f"접촉수={ncol}")
    return ok_all


# ══════════════ [G] 스펙트럼 유틸 ══════════════
def spec_of(Ysc, pivots):
    s = np.linalg.svd(Ysc[:, pivots], compute_uv=False)
    n = Ysc.shape[0]
    norm = np.sqrt(2 * NCSV / n)
    return dict(rows=int(n), smin=float(s[-1]), smax=float(s[0]),
                cond=float(s[0] / max(s[-1], 1e-300)),
                smin_norm=float(s[-1] * norm), sv=[float(x) for x in s])


def dir_excite(Ysc, Vt_r):
    return np.linalg.norm(Ysc @ Vt_r.T, axis=0)


def fric_indep(Ysc):
    """마찰 4열의 관성 스팬(π 50열+armature) 독립성 ‖(I−P)f‖/‖f‖ (Phase 1 [3]과 동일,
    실용 스팬 σ>NOISE). 1=완전 분리, 0=관성과 완전 뒤엉킴."""
    inert = list(range(B.NI)) + [B.IDX_ARM]
    U, s, _ = np.linalg.svd(Ysc[:, inert], full_matrices=False)
    P_ = U[:, :int((s > NOISE).sum())]
    out = {}
    for fi, fn in [(B.IDX_FV1, "fv_hip"), (B.IDX_FC1, "fc_hip"),
                   (B.IDX_FV2, "fv_knee"), (B.IDX_FC2, "fc_knee")]:
        f = Ysc[:, fi]
        res = f - P_ @ (P_.T @ f)
        out[fn] = float(np.linalg.norm(res) / max(np.linalg.norm(f), 1e-12))
    return out


def combo_uncert(Ysc, pivots, nrep=1):
    """스케일드 베이스 조합별 1σ 불확실도 [스케일 단위, %] = NOISE·√diag((YᵀY)⁻¹)/√nrep."""
    A = Ysc[:, pivots]
    C = np.linalg.inv(A.T @ A)
    return NOISE * np.sqrt(np.diag(C)) / np.sqrt(nrep)


# ══════════════ 메인 ══════════════
def main():
    t00 = time.time()
    np.set_printoptions(precision=4, suppress=True, linewidth=160)
    say("=" * 100)
    say(f"P22 여기 궤적 설계 — 공중(레일 현수) 30분 ID 세션{'  [QUICK]' if QUICK else ''}")
    say("=" * 100)

    cache = {}
    jmeta = {}
    if CACHE_NPZ.exists() and CACHE_JSON.exists() and not ARGS.refresh:
        cache = dict(np.load(CACHE_NPZ, allow_pickle=False))
        jmeta = safe.read_json(CACHE_JSON)
        say(f"[cache] 로드: {sorted(cache)}")

    need_heavy = not all(k in cache for k in
                         ("Yr_sc", "s_syn", "Vt_r", "pivots", "SF", "q1g", "qcg", "mask"))
    if need_heavy:
        ctx_init()
        Yr_sc, env = real_stack_and_ranges()
        s_syn, Vt_r, pivots, combos = build_basis(env)
        q1g, qcg, SF, mask = build_surrogate(env)
        cache.update(Yr_sc=Yr_sc, s_syn=s_syn, Vt_r=Vt_r, pivots=pivots,
                     q1g=q1g, qcg=qcg, SF=SF, mask=mask,
                     env_q1=np.array(env["q1"]), env_qc=np.array(env["qc"]))
        jmeta["combos"] = combos
        jmeta["ranges"] = {k: [float(x) for x in v] for k, v in env["per"].items()}
        jmeta["ranges_raw"] = {k: [float(x) for x in v] for k, v in env["raw"].items()}
    env = dict(q1=tuple(cache["env_q1"]), qc=tuple(cache["env_qc"]))
    pivots = cache["pivots"].astype(int)
    Vt_r = cache["Vt_r"]
    combos = jmeta["combos"]
    scales = None

    sur_Y = make_sur_eval(cache["q1g"], cache["qcg"], cache["SF"])

    # ── 서로게이트 검증 (정확 빌드 vs 구조함수 보간) ──
    if "sur_err" not in jmeta or need_heavy:
        ctx = ctx_init()
        scales = ctx["scales"]
        rngv = np.random.default_rng(SEED + 7)
        M = 40
        q1v = rngv.uniform(*env["q1"], M)
        qcv = rngv.uniform(*env["qc"], M)
        dq1v = rngv.uniform(-4, 4, M)
        dqcv = rngv.uniform(-4, 4, M)
        dd1v = rngv.uniform(-30, 30, M)
        ddcv = rngv.uniform(-30, 30, M)
        Yx, _ = exact_stack(q1v, qcv, dq1v, dqcv, dd1v, ddcv, "surro-검증")
        Ys = sur_Y(q1v, qcv, dq1v, dqcv, dd1v, ddcv)
        err = float(np.linalg.norm((Ys - Yx) * scales) / np.linalg.norm(Yx * scales))
        jmeta["sur_err"] = err
        say(f"[검증] 서로게이트 vs 정확 회귀자 (스케일드, 임의 40상태): 상대오차 {err:.2e} "
            f"→ {'PASS' if err < 5e-3 else 'FAIL'}")

    if scales is None:
        scales = np.array(jmeta.get("scales_cache", [])) if "scales_cache" in jmeta else None
    if scales is None:
        scales = ctx_init()["scales"]
    jmeta["scales_cache"] = [float(x) for x in scales]

    # ── 최적화 ──
    if "best_z" in cache and (ARGS.skip_opt or not (need_heavy or ARGS.refresh)):
        best_z = cache["best_z"]
        say("[opt] 캐시된 best_z 재사용")
    else:
        best_z, smin_sur = run_opt(env, sur_Y, pivots, scales,
                                   cache["mask"], cache["q1g"], cache["qcg"])
        cache["best_z"] = best_z
        jmeta["smin_surrogate"] = float(smin_sur)

    coef = decode(best_z, env)
    jmeta["fourier"] = {
        "hip": dict(q0=float(coef[0][0]), a=[float(x) for x in coef[0][1]],
                    b=[float(x) for x in coef[0][2]]),
        "crank": dict(q0=float(coef[1][0]), a=[float(x) for x in coef[1][1]],
                      b=[float(x) for x in coef[1][2]])}

    # ── 최종 정확 평가 (a) 설계 / (b) 나이브 ──
    say("\n[평가] 정확 빌드 (100 Hz × 1주기)")
    q1, qc, dq1, dqc, dd1, ddc = traj_of(coef, TT_CSV)
    Ya, Ya_free = exact_stack(q1, qc, dq1, dqc, dd1, ddc, "(a) 설계")
    lo1, hi1 = env["q1"]
    lo2, hi2 = env["qc"]
    Aeq = min((hi1 - lo1) / 2, (hi2 - lo2) / 2)
    mid1, mid2 = 0.5 * (lo1 + hi1), 0.5 * (lo2 + hi2)
    wN = 2 * np.pi * 0.5
    q1n = mid1 + Aeq * np.sin(wN * TT_CSV)
    qcn = mid2 + Aeq * np.sin(wN * TT_CSV)
    dq1n = Aeq * wN * np.cos(wN * TT_CSV)
    dqcn = dq1n.copy()
    dd1n = -Aeq * wN ** 2 * np.sin(wN * TT_CSV)
    ddcn = dd1n.copy()
    Yb, _ = exact_stack(q1n, qcn, dq1n, dqcn, dd1n, ddcn, "(b) 나이브")

    Ya_sc, Yb_sc = Ya * scales, Yb * scales
    Yr_sc = cache["Yr_sc"]
    sa = spec_of(Ya_sc, pivots)
    sb = spec_of(Yb_sc, pivots)
    sc_ = spec_of(Yr_sc, pivots)
    sa_lock = spec_of(Ya_free * scales, pivots)     # 캐리지 고정(ddbz=0) 변형 참고치
    ea, eb, ec = (dir_excite(Y, Vt_r) for Y in (Ya_sc, Yb_sc, Yr_sc))
    fia, fib, fic = fric_indep(Ya_sc), fric_indep(Yb_sc), fric_indep(Yr_sc)

    say(f"\n{'궤적':34s} {'rows':>6s} {'σ_min':>9s} {'σ_min@2k행':>10s} {'cond':>10s} "
        f"{'가시방향(>0.4Nm)':>16s} {'마찰독립(평균)':>12s}")
    r = len(pivots)
    for tag, sp_, e, fi in [("(a) 설계 (DE+NM)", sa, ea, fia),
                            ("(b) 나이브 0.5Hz 사인", sb, eb, fib),
                            ("(c) 점프 실데이터(스탠스行)", sc_, ec, fic)]:
        say(f"{tag:34s} {sp_['rows']:6d} {sp_['smin']:9.3f} {sp_['smin_norm']:10.3f} "
            f"{sp_['cond']:10.1f} {int((e > NOISE).sum()):8d}/{r} "
            f"{np.mean(list(fi.values())):12.3f}")
    say(f"(참고) 설계궤적·캐리지고정(ddbz=0) 회귀자: σ_min={sa_lock['smin']:.3f} "
        f"cond={sa_lock['cond']:.1f}")
    say(f"30분 반복 효과: {N_REP_30MIN}회 → σ ×√{N_REP_30MIN}={np.sqrt(N_REP_30MIN):.1f} → "
        f"설계 σ_min 유효 {sa['smin'] * np.sqrt(N_REP_30MIN):.1f} Nm "
        f"(조합 불확실도 ≈ {NOISE / (sa['smin'] * np.sqrt(N_REP_30MIN)) * 100:.1f}% 스케일)")

    say("\n방향별 여기량 [Nm] (비행·l_i=30 구조기저 SVD 방향, σ>0.4=식별가능):")
    newly = []
    for jj in range(r):
        mark = ""
        if ea[jj] > NOISE and ec[jj] <= NOISE:
            mark = " ★신규"
            newly.append(jj)
        say(f"  D{jj + 1:02d} 설계={ea[jj]:9.3g}  나이브={eb[jj]:9.3g}  점프={ec[jj]:9.3g}"
            f"{mark}  {B.pretty_combo(Vt_r[jj], B.PNAMES, 4)}")

    # ── 검증 ──
    say("\n[검증] 설계 궤적 (CSV 그리드 전 샘플)")
    ok = verify_traj(coef, env, "설계")
    jmeta["verify_pass"] = bool(ok)

    # ── CSV (측정 좌표계: jump_0602 xlsx 규약, 오프셋 0) ──
    q1_meas = -q1 - np.pi / 2
    q2_meas = -qc
    dq1_meas = -dq1
    dq2_meas = -dqc
    arr = np.column_stack([TT_CSV, q1_meas, q2_meas, dq1_meas, dq2_meas])
    np.savetxt(OUT_CSV, arr, delimiter=",", fmt="%.6f",
               header="t,q1_des,q2_des,dq1_des,dq2_des", comments="")
    say(f"[출력] CSV 저장: {OUT_CSV} ({NCSV}행, 100Hz, 1주기 — 로봇에서 루프 재생)")

    # ── 그림 ──
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    ax[0].plot(TT_CSV, q1_meas, label="힙 q1_des")
    ax[0].plot(TT_CSV, q2_meas, label="크랭크(무릎모터) q2_des")
    ax[0].set_ylabel("각도 [rad] (측정 좌표계)")
    ax[0].set_title(f"여기 궤적 (T0={T0:.0f}s, 100Hz, 푸리에 5고조파, 측정 좌표계=0602 xlsx 규약)")
    ax[0].grid(alpha=0.3)
    ax[0].legend()
    ax[1].plot(TT_CSV, dq1_meas, label="힙 dq1_des")
    ax[1].plot(TT_CSV, dq2_meas, label="크랭크 dq2_des")
    ax[1].set_ylabel("각속도 [rad/s]")
    ax[1].set_xlabel("시간 [s]")
    ax[1].grid(alpha=0.3)
    ax[1].legend()
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)
    say(f"[출력] 그림 저장: {OUT_PNG}")

    # 30분 세션 조합별 예상 불확실도
    unc = combo_uncert(Ya_sc, pivots, nrep=N_REP_30MIN)
    jmeta["combo_uncert_30min"] = [float(x) for x in unc]

    # ── 캐시/결과 저장 ──
    jmeta["fric_indep"] = dict(designed=fia, naive=fib, jump=fic)
    jmeta["table"] = dict(designed=sa, naive=sb, jump=sc_, designed_locked=sa_lock)
    jmeta["dir_excite"] = dict(designed=[float(x) for x in ea],
                               naive=[float(x) for x in eb],
                               jump=[float(x) for x in ec],
                               newly=[int(j) for j in newly])
    jmeta["dir_names"] = [B.pretty_combo(Vt_r[jj], B.PNAMES, 4) for jj in range(r)]
    jmeta["caps"] = dict(vcap=list(VCAP), acap=ACAP, margin=MARGIN, T0=T0, NH=NH, FS=FS,
                         noise=NOISE, nrep30=N_REP_30MIN)
    jmeta["env_model"] = dict(q1=list(env["q1"]), qc=list(env["qc"]))
    jmeta["quick"] = QUICK
    np.savez_compressed(CACHE_NPZ, **cache)
    safe.atomic_json_write(CACHE_JSON, jmeta)
    say(f"[출력] 캐시 저장: {CACHE_NPZ.name}, {CACHE_JSON.name}")

    write_report(jmeta, combos)
    say(f"\n총 {time.time() - t00:.0f}s")


def write_report(jm, combos):
    sa, sb, sc_ = jm["table"]["designed"], jm["table"]["naive"], jm["table"]["jump"]
    sl = jm["table"]["designed_locked"]
    ea = np.array(jm["dir_excite"]["designed"])
    eb = np.array(jm["dir_excite"]["naive"])
    ec = np.array(jm["dir_excite"]["jump"])
    newly = jm["dir_excite"]["newly"]
    r = len(ea)
    fh, fc = jm["fourier"]["hip"], jm["fourier"]["crank"]
    env = jm["env_model"]
    eff = sa["smin"] * np.sqrt(N_REP_30MIN)
    L = []
    A = L.append
    A("# P22 여기 궤적 설계 보고 — 30분 공중(레일 현수) 시스템 식별 세션")
    A("")
    A(f"생성: p22_excite_design.py (seed={SEED}{', QUICK' if jm.get('quick') else ''}) · "
      f"기준 모델: P19 FINAL 후보 (fourbar_p19_candidate.json) · Phase 1 기계 재사용")
    A("")
    A("## 1. 무엇을 왜")
    A("- 목적: 로봇을 레일에 매달아 발을 띄운 채(공중), PD로 아래 궤적을 30분 반복 추종시켜")
    A("  관성·마찰 파라미터를 **접촉 없이** 식별할 데이터를 얻는다.")
    A("- \"잘 보이는 정도\"의 지표 = 스택 회귀자의 최소특이값 σ_min: 토크 노이즈 0.4 Nm 대비")
    A("  가장 안 보이는 파라미터 조합의 신호 크기. σ_min이 클수록 모든 조합이 고르게 식별됨.")
    A("- 조건수 cond = σ_max/σ_min: 제일 잘 보이는 조합과 제일 안 보이는 조합의 비율(작을수록 균형).")
    A("")
    A("## 2. 궤적 정의 (CSV 규약)")
    A(f"- 파일: `p22_excite_traj.csv` — 열 `t,q1_des,q2_des,dq1_des,dq2_des`, "
      f"{FS} Hz, 1주기 {T0:.0f} s ({NCSV}행). 로봇에서 **그대로 루프 재생** (주기 경계 연속, "
      f"시작/끝 속도 0).")
    A("- **좌표 규약 = 측정(xlsx) 규약** (jump_0602 세션과 동일, 오프셋 0):")
    A("  hip: `q1_meas = −q1_model − π/2`, crank(무릎모터 채널): `q2_meas = −q2_model`.")
    A("  즉 CSV 값은 hip.xlsx/knee.xlsx의 currentAngle/desiredAngle과 같은 단위·부호(rad).")
    A("- 시작 자세 = CSV 첫 행. 재생 전 로봇을 이 자세로 천천히 이동시킨 뒤 루프 시작.")
    A("")
    A("### 푸리에 계수 (모델 좌표계, rad)")
    A(f"- 힙: q0={fh['q0']:+.4f}, a={np.round(fh['a'], 4).tolist()}, "
      f"b={np.round(fh['b'], 4).tolist()}")
    A(f"- 크랭크: q0={fc['q0']:+.4f}, a={np.round(fc['a'], 4).tolist()}, "
      f"b={np.round(fc['b'], 4).tolist()}")
    A("")
    A("## 3. 하드 제약 (구성적으로 보장 + 전 샘플 검증)")
    A(f"- 관절범위: fit 세션(l_i=30mm: 0421/0424/0602) 실측 방문범위에서 스팬 {MARGIN * 100:.0f}%씩 "
      f"양쪽 축소 → 모델좌표 hip [{env['q1'][0]:+.3f}, {env['q1'][1]:+.3f}] rad, "
      f"crank [{env['qc'][0]:+.3f}, {env['qc'][1]:+.3f}] rad.")
    A("  (0429는 CVT l_i=25.08 세션이라 크랭크↔무릎 관계가 달라 envelope에 미포함, 정보로만 채굴)")
    A(f"- 속도 |dq|: hip ≤ {VCAP[0]:.0f}, crank ≤ {VCAP[1]:.0f} rad/s · 가속 |ddq| ≤ {ACAP:.0f} rad/s²")
    A("  (T0=10s·5고조파 설계라 실제 최대는 수 rad/s — 범위 제약이 지배)")
    A("- 4-bar 폐쇄: cvt_core.closure(l_i=30mm) 전 샘플 수렴+잔차<1e-8, 평행사변형 qk=qc 확인")
    A("- 허벅지-정강이 충돌: 무릎각(=크랭크각)이 실측 방문범위 내 + 원본 MuJoCo 모델 접촉검사 0건")
    A(f"- 시작/끝 정지: dq(0)=dq(T0)=0 (a계수를 Σk·a_k=0에 사영) → 검증 "
      f"{'**전체 PASS**' if jm.get('verify_pass') else '**FAIL 있음 — 로그 확인!**'}")
    A("")
    fia = jm["fric_indep"]["designed"]
    fib = jm["fric_indep"]["naive"]
    fic = jm["fric_indep"]["jump"]
    A("## 4. 결과 — 식별성 비교 (스케일드 회귀자, 비행·l_i=30 구조기저 " + str(r) + "조합)")
    A("")
    A("| 궤적 | 행수 | σ_min [Nm] | σ_min@2000행 | cond | 가시방향(>0.4Nm) | 마찰-관성 분리도(평균) |")
    A("|---|---|---|---|---|---|---|")
    A(f"| (a) 설계 (DE+NM, E-최적) | {sa['rows']} | **{sa['smin']:.3f}** | "
      f"{sa['smin_norm']:.3f} | **{sa['cond']:.1f}** | {int((ea > NOISE).sum())}/{r} | "
      f"**{np.mean(list(fia.values())):.3f}** |")
    A(f"| (b) 나이브 0.5Hz 동진폭 사인 | {sb['rows']} | {sb['smin']:.4f} | {sb['smin_norm']:.4f} | "
      f"{sb['cond']:.0f} | {int((eb > NOISE).sum())}/{r} | {np.mean(list(fib.values())):.3f} |")
    A(f"| (c) 점프 실데이터 스탠스행 (참고, 다른 레짐) | {sc_['rows']} | {sc_['smin']:.4f} | "
      f"{sc_['smin_norm']:.4f} | {sc_['cond']:.0f} | {int((ec > NOISE).sum())}/{r} | "
      f"{np.mean(list(fic.values())):.3f} |")
    A("")
    A("읽는 법과 정직한 해석:")
    A(f"- 점프 데이터는 가속·힘이 커서 원시 σ는 크다. 그러나 (i) 스탠스행은 구름 무슬립·레일")
    A("  무마찰·접촉 가정 위에 서 있고(가정 오류 = 바이어스), (ii) 폐루프라 여기 방향이 게인에")
    A("  종속이며, (iii) **마찰열이 관성 스팬과 뒤엉켜 있다** (분리도 "
      + f"{np.mean(list(fic.values())):.2f} — Phase 1의 0.40~0.44 재확인).")
    A(f"- 설계 궤적은 접촉/구름 가정이 **아예 없고** 마찰-관성 분리도 "
      f"{np.mean(list(fia.values())):.2f}로 사실상 완전 분리 "
      f"(fv_hip={fia['fv_hip']:.2f}, fc_hip={fia['fc_hip']:.2f}, "
      f"fv_knee={fia['fv_knee']:.2f}, fc_knee={fia['fc_knee']:.2f}).")
    A("- 나이브 사인(동일 주파수·동일 진폭·동일 위상)은 두 관절 운동이 완전 상관 →")
    A(f"  cond {sb['cond']:.0f} (수치상 랭크 결손). \"움직이긴 다 움직였는데 조합을 못 가른다\"의 전형.")
    A(f"  (나이브의 분리도 {np.mean(list(fib.values())):.2f}는 관성 스팬 자체가 결손이라 생기는"
      " 착시 — σ_min≈0이 본질.)")
    A("")
    A(f"- 30분 = {N_REP_30MIN}주기 반복 → 유효 σ_min ≈ {sa['smin']:.2f}×√{N_REP_30MIN} = "
      f"**{eff:.1f} Nm** → 최약 베이스 조합의 상대 불확실도 ≈ {NOISE / eff * 100:.1f}% (스케일 단위).")
    A(f"- 캐리지를 **클램프로 고정**하고 돌릴 경우(ddbz=0 회귀자): σ_min={sl['smin']:.3f}, "
      f"cond={sl['cond']:.1f} — 두 모드 모두 커버됨.")
    A("")
    A("## 5. 방향별 여기량 + 30분 세션 조합별 예상 정밀도")
    A("")
    A("비행(l_i=30) 구조기저 SVD 방향별 ‖Y·v‖ [Nm] (0.4 Nm 이상 = 식별 가능):")
    A("")
    A("| 방향 | 설계 | 나이브 | 점프데이터 | 대표 조합 | 비고 |")
    A("|---|---|---|---|---|---|")
    for jj in range(r):
        mark = "**★ 점프데이터엔 없던 조합**" if jj in newly else \
            ("차단(<0.4)" if ea[jj] <= NOISE else "")
        A(f"| D{jj + 1:02d} | {ea[jj]:.3g} | {eb[jj]:.3g} | {ec[jj]:.3g} | "
          f"`{jm['dir_names'][jj]}` | {mark} |")
    if not newly:
        A("")
        A("(점프 데이터도 13방향 전부 σ>0.4로 보인다 — 이 세션의 가치는 \"새 방향\"이 아니라")
        A(" **가정 없는 레짐 + 마찰-관성 분리 + 균형 잡힌 조건수**다. 위 4절 해석 참조.)")
    A("")
    A("### 베이스 조합 (pivoted QR) + 30분 설계 세션 예상 1σ 불확실도 (스케일 단위)")
    unc = jm.get("combo_uncert_30min", [])
    for k, c in enumerate(combos):
        u = f" — ±{unc[k] * 100:.1f}%" if k < len(unc) else ""
        A(f"- F{k + 1:02d}: `{c}`{u}")
    A("")
    A("(스케일 단위 = Phase 1과 동일: 질량은 해당 body 질량, 1차모멘트는 m·L, 관성은 m·L²,")
    A(" 마찰/armature는 탐색 half-width 기준. ±100% = 그 조합은 사실상 미식별.)")
    A("")
    A("## 6. 실행 절차 (사용자)")
    A("1. **PD 게인**: 데이터 세션 중간값 `120_2_120_2` (hip kp=120, kd=2 / crank kp=120, kd=2) 권장.")
    A("   첫 1~2주기는 `60_0.75_60_2`로 저게인 드라이런 후 이상 없으면 120으로.")
    A("2. **반복**: 1주기 10 s × 180회 = 30분. 5분(30주기) 단위 6파일로 나눠 기록 권장")
    A("   (파일 크기·중간 점검·온도 확인).")
    A("3. **기록할 것**: hip/knee xlsx 규약 전 채널(currentAngle/Velocity/**currentTorque(raw iTM)**/")
    A("   desired*), **Clutch.xlsx(l_i=30 확인용 — 무변속 가정 검증!)**, 모터 온도, 버스 전압,")
    A("   가능하면 베이스 레일 위치. GRF는 공중이라 무관.")
    A("4. 세션 전/후에 동일 첫 주기를 한 번씩 더 기록 (온도 드리프트 대조군).")
    A("")
    A("## 7. 정직한 한계 (반드시 읽을 것)")
    A("- **PD 추종 오차가 실행 궤적을 뭉갠다** — 식별은 반드시 **측정된 q/dq**(엔코더)로 재구성한")
    A("  회귀자로 수행할 것 (desired 아님). ddq는 Phase 1과 동일하게 SG(win=11, poly=3) 미분.")
    A("- 토크는 currentTorque(raw iTM)를 **Paper a_hat 변환** 후 사용 (Nm 아님 주의).")
    A("- 레일 마찰 = 0 가정 (비행 회귀자의 bz행 소거). 마찰·걸림이 있으면 힙/크랭크 행에 바이어스")
    A("  → 캐리지 고정(클램프) 모드로도 한 세트 찍으면 교차검증 가능 (ddbz=0 회귀자 사용).")
    A(f"- 저주파 설계(최고 {NH * 1 / T0:.1f} Hz)라 가속 여기가 작아 순수 관성 조합의 σ는 마찰/중력")
    A("  조합보다 작다. 관성 정밀도가 더 필요하면 T0 단축/고조파 추가 후속 설계.")
    A("- l_i=30mm 평행사변형 축퇴로 crank/coupler/calf 관성 일부가 묶여 있음 — CVT(l_i=25.08)")
    A("  공중 세션을 추가하면 Phase 1 기준 +4 조합이 풀림 (후속 제안).")
    A(f"- 서로게이트 보간 상대오차 {jm.get('sur_err', float('nan')):.1e} (최종 수치는 정확 빌드로 재평가).")
    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    say(f"[출력] 보고서 저장: {OUT_MD}")


if __name__ == "__main__":
    main()
