# -*- coding: utf-8 -*-
"""P22 Phase 1 — 베이스 파라미터(식별 가능 관성 조합) 분석.

방법 (수치, Pinocchio 불요 — 역동역학은 body 표준 관성파라미터에 정확히 선형):
 1. P19 후보 모델(평행사변형 flip + CVT l_i=25.08mm)에서 회귀자 변형 모델 생성
    (스프링/감쇠/frictionloss/armature 0 + equality/contact/passive/limit disable).
 2. 트리 회귀자: body {base,thigh,crank,coupler,calf} × 표준 10파라미터
    π_b = (m, m·cx, m·cy, m·cz, Ixx, Iyy, Izz, Ixy, Ixz, Iyz)  [I는 body frame "원점" 기준].
    기저: MuJoCo (mass, ipos, iquat, inertia) → 위 표준기저로 변환/설정 (eigh 재대각화).
    열 = 중앙 FD [mj_inverse(π0+δe) − mj_inverse(π0−δe)]/2δ — 선형이므로 δ 무관(2δ 검증).
 3. 폐쇄 투영: 독립속도 v=(bz, dq1, dqc), tree qvel = G(qc)·v (closure() FD),
    q̈_tree = G·v̇ + Ġ·v (Ġ = dG/dqc·dqc, FD). u = Gᵀτ_tree → (레일힘, 힙토크, 크랭크토크).
    레일행 drop. 비행모드: 레일행=0으로 ddbz 소거(π 의존 → 국소 야코비안, 중앙 FD가 흡수).
 4. 구조적 rank: 폐쇄일관 랜덤상태 (l_i=30 + 25.08 stack) SVD + pivoted QR → 베이스 조합.
 5. 마찰열 4개 (fv·dq, fc·tanh(dq/0.02) @ hip/crank) + armature열(=ddqc, crank행) 추가.
 6. 실데이터 (fit 세션 0421/0424/0602/0429, 비행창만, 0324 held-out 제외):
    ddq = Savitzky-Golay(dq, win=11, poly=3, deriv=1) — win 7/15 민감도 체크.
 7. fit 파라미터 15개의 회귀자 방향(빌더 FD) → 실데이터 top-k 식별부분공간 내 비율.

주의: 접촉(stance) 동역학은 이 회귀자 범위 밖 — 공중(관성+중력+마찰) 구조만.
실행: repo 루트에서 PYTHONIOENCODING=utf-8 python code/goal22/p22_beyond/p22_base_params.py [--quick]
"""
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "code" / "bench"))
import safe  # noqa: E402

safe.utf8_console()
import p19_adapter as AD  # noqa: E402  (sys.path 배선 포함)

QUICK = "--quick" in sys.argv
SEED = 22
NSYN = 300 if QUICK else 2000          # 구조적 샘플 수 (l_i당)
CAP_TRIAL = 40 if QUICK else 200       # 실데이터 trial당 최대 샘플
CAP_SENS = 60                          # SG 민감도 재실행용 cap
SGWIN = 11
NOISE = 0.4                            # Nm — 토크 노이즈 스케일 (지시값)
DELTA_REL = 1e-4                       # FD δ = DELTA_REL·scale
OUT_JSON = HERE / "p22_base_params_result.json"

BODIES = ["base", "thigh", "crank", "coupler", "calf"]
COMP = ["m", "hx", "hy", "hz", "Ixx", "Iyy", "Izz", "Ixy", "Ixz", "Iyz"]
JOINTS = ["base_z", "hip", "knee_motor", "cpin", "knee"]
LCHAR = dict(base=0.05, thigh=0.25, crank=0.03, coupler=0.25, calf=0.25)
PN_INER = [f"{b}.{c}" for b in BODIES for c in COMP]          # 50
PN_EXTRA = ["arm_knee", "fv_hip", "fc_hip", "fv_knee", "fc_knee"]  # 5
PNAMES = PN_INER + PN_EXTRA                                    # 55
NI, NX = len(PN_INER), len(PNAMES)
IDX_ARM, IDX_FV1, IDX_FC1, IDX_FV2, IDX_FC2 = NI, NI + 1, NI + 2, NI + 3, NI + 4

# fit 파라미터 15개: (이름, half-bound-width [SPEC/P19 탐색 스케일])
FITP = [("M_base", 0.40), ("M_thigh", 0.40), ("M_calf", 0.55), ("M_p", 1.05),
        ("M_c", 0.60), ("I_thigh", 0.70), ("I_calf", 0.70),
        ("com_dz_th", 0.10), ("com_dz_ca", 0.10), ("m_foot", 0.15),
        ("arm_knee", 0.0115),
        ("fv_hip", 0.625), ("fv_knee", 0.35), ("fc_hip", 0.295), ("fc_knee", 0.625)]

_R = {}          # 전역 컨텍스트
REPORT = []


def say(s=""):
    print(s, flush=True)
    REPORT.append(s)


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


# ══════════════════ 모델 래퍼 ══════════════════
def body_pi(model, bid, mj):
    m = float(model.body_mass[bid])
    c = np.array(model.body_ipos[bid])
    R9 = np.zeros(9)
    mj.mju_quat2Mat(R9, np.array(model.body_iquat[bid]))
    R = R9.reshape(3, 3)
    IC = R @ np.diag(model.body_inertia[bid]) @ R.T
    IO = IC + m * ((c @ c) * np.eye(3) - np.outer(c, c))
    h = m * c
    return np.array([m, h[0], h[1], h[2], IO[0, 0], IO[1, 1], IO[2, 2],
                     IO[0, 1], IO[0, 2], IO[1, 2]])


def set_body_pi(model, bid, pi, mj):
    m = float(pi[0])
    h = np.array(pi[1:4])
    c = h / m
    IO = np.array([[pi[4], pi[7], pi[8]],
                   [pi[7], pi[5], pi[9]],
                   [pi[8], pi[9], pi[6]]])
    IC = IO - m * ((c @ c) * np.eye(3) - np.outer(c, c))
    w, V = np.linalg.eigh(IC)
    if np.linalg.det(V) < 0:
        V[:, 0] = -V[:, 0]
    q = np.zeros(4)
    mj.mju_mat2Quat(q, np.ascontiguousarray(V.flatten()))
    model.body_mass[bid] = m
    model.body_ipos[bid] = c
    model.body_inertia[bid] = w
    model.body_iquat[bid] = q


class RModel:
    """회귀자 변형 모델 (passive/equality/contact 제거) + π get/set."""

    def __init__(self, build_fn, tag):
        mj = _R["mj"]
        self.mj = mj
        self.tag = tag
        model, _ = build_fn()
        # 변형: passive/armature 제거 + 제약 비활성
        model.dof_damping[:] = 0.0
        model.dof_frictionloss[:] = 0.0
        model.dof_armature[:] = 0.0
        model.jnt_stiffness[:] = 0.0
        DS = mj.mjtDisableBit
        model.opt.disableflags |= (DS.mjDSBL_EQUALITY | DS.mjDSBL_CONTACT
                                   | DS.mjDSBL_SPRING | DS.mjDSBL_DAMPER
                                   | DS.mjDSBL_LIMIT | DS.mjDSBL_FRICTIONLOSS)
        self.model = model
        self.d = mj.MjData(model)
        self.iq = np.array([safe.qadr(model, j, mj) for j in JOINTS])
        self.iv = np.array([safe.dofadr(model, j, mj) for j in JOINTS])
        self.bid = [mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, b) for b in BODIES]
        assert min(self.bid) >= 0, f"body 누락: {self.tag}"
        self.pi0 = self.get_pi()
        self._scr = mj.MjData(model)

    def get_pi(self):
        return np.concatenate([body_pi(self.model, b, self.mj) for b in self.bid])

    def set_pi(self, pi):
        for k, b in enumerate(self.bid):
            set_body_pi(self.model, b, pi[10 * k:10 * k + 10], self.mj)
        self.mj.mj_setConst(self.model, self._scr)

    def restore(self):
        self.set_pi(self.pi0)


# ══════════════════ 폐쇄 기하 ══════════════════
def G_terms(qc, l_i, qk0=None, eps=1e-4):
    """(qk, qpin, r=dqk/dqc, gp=dqpin/dqc, gpp, rp)."""
    CC = _R["CC"]
    qk, qp, r = CC.closure(qc, l_i, qk0)
    qk_p, qp_p, r_p = CC.closure(qc + eps, l_i, qk)
    qk_m, qp_m, r_m = CC.closure(qc - eps, l_i, qk)
    gp = wrap(qp_p - qp_m) / (2 * eps)
    gpp = (wrap(qp_p - qp) - wrap(qp - qp_m)) / eps ** 2
    rp = (r_p - r_m) / (2 * eps)
    return qk, qp, r, gp, gpp, rp


def make_state(bz, q1, qc, dq1, dqc, dd1, ddc, l_i, qk0=None):
    """폐쇄일관 tree 상태 1개: (qpos5, qvel5, dd0_5, G(5,3), qk)."""
    qk, qp, r, gp, gpp, rp = G_terms(qc, l_i, qk0)
    qpos = np.array([bz, q1, qc, qp, qk])
    G = np.zeros((5, 3))
    G[0, 0] = 1.0
    G[1, 1] = 1.0
    G[2, 2] = 1.0
    G[3, 2] = gp
    G[4, 2] = r
    qvel = G @ np.array([0.0, dq1, dqc])           # dbz=0 (갈릴레이 불변 — 검증됨)
    dd0 = np.array([0.0, 0.0, 0.0, gpp * dqc ** 2, rp * dqc ** 2])  # Ġ·v
    return qpos, qvel, dd0, G, qk


def pack_states(rows):
    """rows: list of (qpos, qvel, dd0, G, dd1, ddc, ddbz_free, dq1, dqc)."""
    st = {}
    st["Q"] = np.array([r[0] for r in rows])
    st["V"] = np.array([r[1] for r in rows])
    st["D0"] = np.array([r[2] for r in rows])
    st["G"] = np.array([r[3] for r in rows])
    st["dd1"] = np.array([r[4] for r in rows])
    st["ddc"] = np.array([r[5] for r in rows])
    st["ddbz"] = np.array([r[6] for r in rows])
    st["dq1"] = np.array([r[7] for r in rows])
    st["dqc"] = np.array([r[8] for r in rows])
    st["N"] = len(rows)
    return st


# ══════════════════ (a,b) 평가 + u 조립 ══════════════════
def eval_ab(rm, st):
    """각 샘플: a=GᵀMG(3×3), b=Gᵀ(M·Ġv + bias)."""
    mj, model, d = rm.mj, rm.model, rm.d
    N = st["N"]
    A = np.empty((N, 3, 3))
    B = np.empty((N, 3))
    tmp = np.zeros(model.nv)
    gcol = np.zeros(model.nv)
    for i in range(N):
        d.qpos[rm.iq] = st["Q"][i]
        d.qvel[rm.iv] = st["V"][i]
        d.qacc[rm.iv] = st["D0"][i]
        mj.mj_inverse(model, d)
        G = st["G"][i]
        B[i] = G.T @ d.qfrc_inverse[rm.iv]
        for c in range(3):
            gcol[:] = 0.0
            gcol[rm.iv] = G[:, c]
            mj.mj_mulM(model, d, tmp, gcol)
            A[i, :, c] = G.T @ tmp[rm.iv]
    return A, B


def u_rows(A, B, st):
    """반환 (Ufree(N,2), Uflight(N,2)) — 행 (hip, crank)."""
    dd1, ddc, ddbz = st["dd1"], st["ddc"], st["ddbz"]
    uf = np.empty((st["N"], 2))
    ug = np.empty((st["N"], 2))
    for r in (1, 2):
        uf[:, r - 1] = A[:, r, 0] * ddbz + A[:, r, 1] * dd1 + A[:, r, 2] * ddc + B[:, r]
    dbz_el = -(A[:, 0, 1] * dd1 + A[:, 0, 2] * ddc + B[:, 0]) / A[:, 0, 0]
    for r in (1, 2):
        ug[:, r - 1] = A[:, r, 0] * dbz_el + A[:, r, 1] * dd1 + A[:, r, 2] * ddc + B[:, r]
    return uf, ug, dbz_el


def group_u(rm, st):
    A, B = eval_ab(rm, st)
    return u_rows(A, B, st)


def build_Y(groups, scales, label):
    """중앙 FD로 π 50열 + armature/마찰 5열. 반환 dict(Yfree, Yflt, U0free, U0flt)."""
    t0 = time.time()
    Ntot = sum(st["N"] for _, st in groups)
    Yfree = np.zeros((2 * Ntot, NX))
    Yflt = np.zeros((2 * Ntot, NX))
    U0f = np.zeros((2 * Ntot,))
    U0g = np.zeros((2 * Ntot,))
    sl = []
    o = 0
    for rm, st in groups:
        sl.append(slice(o, o + 2 * st["N"]))
        o += 2 * st["N"]
    # baseline
    for (rm, st), s in zip(groups, sl):
        uf, ug, _ = group_u(rm, st)
        U0f[s] = uf.reshape(-1)
        U0g[s] = ug.reshape(-1)
    # 관성 50열 (중앙 FD)
    for j in range(NI):
        dj = DELTA_REL * scales[j]
        for (rm, st), s in zip(groups, sl):
            pi = rm.pi0.copy()
            pi[j] += dj
            rm.set_pi(pi)
            ufp, ugp, _ = group_u(rm, st)
            pi[j] -= 2 * dj
            rm.set_pi(pi)
            ufm, ugm, _ = group_u(rm, st)
            rm.restore()
            Yfree[s, j] = (ufp - ufm).reshape(-1) / (2 * dj)
            Yflt[s, j] = (ugp - ugm).reshape(-1) / (2 * dj)
    # armature 열: crank행 = ddqc (양 모드 동일 — 레일행에 안 들어감)
    for (rm, st), s in zip(groups, sl):
        col = np.zeros((st["N"], 2))
        col[:, 1] = st["ddc"]
        Yfree[s, IDX_ARM] = col.reshape(-1)
        Yflt[s, IDX_ARM] = col.reshape(-1)
        # 마찰 열 (hip행: dq1, tanh; crank행: dqc, tanh) — mj frame
        for idx, (row, arr) in [(IDX_FV1, (0, st["dq1"])),
                                (IDX_FC1, (0, np.tanh(st["dq1"] / 0.02))),
                                (IDX_FV2, (1, st["dqc"])),
                                (IDX_FC2, (1, np.tanh(st["dqc"] / 0.02)))]:
            col = np.zeros((st["N"], 2))
            col[:, row] = arr
            Yfree[s, idx] = col.reshape(-1)
            Yflt[s, idx] = col.reshape(-1)
    say(f"  [{label}] Y 구축 완료: rows={2 * Ntot}, cols={NX}, {time.time() - t0:.0f}s")
    return dict(Yfree=Yfree, Yflt=Yflt, U0free=U0f, U0flt=U0g, slices=sl)


# ══════════════════ 검증 ══════════════════
def sanity_variant(rm):
    mj, model, d = rm.mj, rm.model, rm.d
    d.qpos[rm.iq] = [1.0, -1.2, -2.0, 2.0 + 0.3, -2.0 + 0.1]  # 폐쇄 위반 상태
    d.qvel[:] = 3.0
    mj.mj_forward(model, d)
    ok_efc = (d.nefc == 0)
    ok_pas = float(np.max(np.abs(d.qfrc_passive))) < 1e-12
    ok_con = float(np.max(np.abs(d.qfrc_constraint))) < 1e-12
    say(f"  [{rm.tag}] disable 검증: nefc={d.nefc} (0이어야), "
        f"|qfrc_passive|max={np.max(np.abs(d.qfrc_passive)):.1e}, "
        f"|qfrc_constraint|max={np.max(np.abs(d.qfrc_constraint)):.1e} "
        f"→ {'PASS' if ok_efc and ok_pas and ok_con else 'FAIL'}")
    return ok_efc and ok_pas and ok_con


def sanity_tree_linear(rm, rng, nst=40):
    """(i) Y_tree·π0 == mj_inverse (임의 tree 상태, 폐쇄 불요) + 2δ 선형성."""
    mj, model, d = rm.mj, rm.model, rm.d
    states = [(rng.uniform(0.5, 1.5), rng.uniform(-3.2, -0.5), rng.uniform(-2.7, -0.15),
               rng.uniform(-np.pi, np.pi), rng.uniform(-2.7, -0.15),
               rng.uniform(-20, 20, 5), rng.uniform(-500, 500, 5)) for _ in range(nst)]

    def tau_all():
        out = np.empty((nst, 5))
        for i, (bz, q1, qc, qp, qk, v5, a5) in enumerate(states):
            d.qpos[rm.iq] = [bz, q1, qc, qp, qk]
            d.qvel[rm.iv] = v5
            d.qacc[rm.iv] = a5
            mj.mj_inverse(model, d)
            out[i] = d.qfrc_inverse[rm.iv]
        return out

    tau0 = tau_all()
    scales = _R["scales"]
    Yt = np.zeros((nst, 5, NI))
    Yt3 = np.zeros((nst, 5, NI))
    for j in range(NI):
        for mult, dst in [(1.0, Yt), (30.0, Yt3)]:
            dj = mult * DELTA_REL * scales[j]
            pi = rm.pi0.copy()
            pi[j] += dj
            rm.set_pi(pi)
            tp = tau_all()
            pi[j] -= 2 * dj
            rm.set_pi(pi)
            tm = tau_all()
            dst[:, :, j] = (tp - tm) / (2 * dj)
    rm.restore()
    pred = Yt @ rm.pi0[:NI]
    rel = np.linalg.norm(pred - tau0) / max(np.linalg.norm(tau0), 1e-12)
    dlin = np.linalg.norm(Yt - Yt3) / max(np.linalg.norm(Yt), 1e-12)
    say(f"  (i) Y·π0 vs mj_inverse 상대오차 = {rel:.2e} (<1e-6 요구) "
        f"→ {'PASS' if rel < 1e-6 else 'FAIL'}")
    say(f"      2δ 선형성 (δ vs 30δ 열 상대차) = {dlin:.2e} (<1e-6 요구) "
        f"→ {'PASS' if dlin < 1e-6 else 'FAIL'}")
    return rel < 1e-6 and dlin < 1e-6


def sanity_G_par():
    qk, qp, r, gp, gpp, rp = G_terms(-2.0, 0.03)
    ok = (abs(r - 1) < 1e-8 and abs(gp + 1) < 1e-8 and abs(gpp) < 1e-4 and abs(rp) < 1e-4
          and abs(qk + 2.0) < 1e-9)
    say(f"  (ii) 평행사변형 G: r={r:.9f} (→1), gp={gp:.9f} (→−1), "
        f"gpp={gpp:.1e}, rp={rp:.1e} → {'PASS' if ok else 'FAIL'}")
    return ok


def sanity_JG(build_fn, l_i, tag):
    """equality 켠 원본 모델에서 J_eq·G ≈ 0 (closure ↔ 모델 기하 일치)."""
    mj = _R["mj"]
    model, _ = build_fn()
    model.opt.jacobian = mj.mjtJacobian.mjJAC_DENSE
    d = mj.MjData(model)
    worst = 0.0
    qk0 = None
    for qc in (-2.4, -1.6, -0.8):
        qpos, qvel, dd0, G, qk0 = make_state(1.0, -1.2, qc, 0, 0, 0, 0, l_i, qk0)
        d.qpos[:] = 0.0
        d.qpos[[safe.qadr(model, j, mj) for j in JOINTS]] = qpos
        mj.mj_forward(model, d)
        eq = d.efc_type == mj.mjtConstraint.mjCNSTR_EQUALITY
        if not eq.any():
            say(f"  (J·G) {tag}: equality 행 없음?! FAIL")
            return False
        J = d.efc_J.reshape(d.nefc, model.nv)[eq]
        iv = [safe.dofadr(model, j, mj) for j in JOINTS]
        JG = J[:, iv] @ G
        worst = max(worst, float(np.max(np.abs(JG)) / max(np.max(np.abs(J)), 1e-12)))
    say(f"  (J·G) {tag}: max|J_eq·G|/|J| = {worst:.1e} (<1e-6 요구) "
        f"→ {'PASS' if worst < 1e-6 else 'FAIL'}")
    return worst < 1e-6


def sanity_galilean(rm):
    mj, model, d = rm.mj, rm.model, rm.d
    qpos, qvel, dd0, G, _ = make_state(1.0, -1.5, -1.8, 5.0, -8.0, 100.0, -200.0, 0.03)
    out = []
    for dbz in (0.0, 2.0):
        d.qpos[rm.iq] = qpos
        v = qvel.copy()
        v[0] = dbz
        d.qvel[rm.iv] = v
        d.qacc[rm.iv] = dd0
        mj.mj_inverse(model, d)
        out.append(d.qfrc_inverse[rm.iv].copy())
    diff = float(np.max(np.abs(out[0] - out[1])))
    say(f"  갈릴레이 불변 (dbz 0 vs 2 m/s): |Δτ|max = {diff:.1e} "
        f"→ {'PASS' if diff < 1e-9 else 'FAIL'}")
    return diff < 1e-9


# ══════════════════ 상태 샘플링 ══════════════════
def sample_syn(l_i, n, rng):
    rows = []
    for _ in range(n):
        qc = rng.uniform(-2.7, -0.15)
        q1 = rng.uniform(-3.2, -0.5)
        dq1, dqc = rng.uniform(-25, 25, 2)
        dd1, ddc = rng.uniform(-800, 800, 2)
        ddbz = rng.uniform(-40, 40)
        qpos, qvel, dd0, G, _ = make_state(1.0, q1, qc, dq1, dqc, dd1, ddc, l_i)
        rows.append((qpos, qvel, dd0, G, dd1, ddc, ddbz, dq1, dqc))
    return pack_states(rows)


def flight_window(d, on, toff):
    """이륙~착지 인덱스 창. grf 기반; 부적합 시 None."""
    g = d.get("grf_real")
    t = d["t"]
    if g is None or toff >= len(t) - 30:
        return None
    g = np.asarray(g, float)
    if not np.isfinite(g[toff:toff + 5]).all() or np.nanmean(np.abs(g[toff:toff + 5])) > 15:
        return None
    pk = float(np.nanmax(np.abs(g[:toff + 1]))) if toff > 0 else 0.0
    thr = max(30.0, 0.05 * pk)
    td = len(t) - 1
    ga = np.abs(g)
    for i in range(toff + 10, len(t) - 1):
        if ga[i] > thr and ga[i + 1] > thr:
            td = i
            break
    lo, hi = toff + 5, td - 5
    if hi - lo < 25:
        return None
    return lo, hi


def prep_real(sgwin, cap):
    """fit 세션 비행창 상태 (0324 제외). 반환 [(tag, l_i, states, meta)]."""
    J = _R["J"]
    sg = _R["savgol"]
    dd26 = _R["dd26"]
    out_nocvt = []
    meta = []
    OFF = {"jump_position_0421": ("o1_0421", "o2_0421"),
           "jump_0424": ("o1_0424", "o2_0424"), "jump_0602": (None, None)}
    for tr in J._P["cl"]:
        ds = tr["ds"]
        if ds == "jump_0324" or ds not in OFF:
            continue
        w = flight_window(tr["d"], tr["on"], tr["toff"])
        if w is None:
            meta.append((ds, str(tr["sub"]), 0, 0.0))
            continue
        k1, k2 = OFF[ds]
        o1 = dd26.get(k1, 0.0) if k1 else 0.0
        o2 = dd26.get(k2, 0.0) if k2 else 0.0
        rows, mrows = trial_states(tr["d"], w, o1, o2, 0.03, sgwin, cap)
        out_nocvt.extend(rows)
        meta.append((ds, str(tr["sub"]), len(rows), (w[1] - w[0]) * _dt(tr["d"])))
        _R["real_meas"].extend(mrows)
    cvt_groups = []
    CC = _R["CC"]
    o1c, o2c = _R["qoff429"]
    for sub in CC.SUBS429:
        d = CC.load_0429(sub)
        dq2 = np.asarray(d["dq2"])
        on = int(np.argmax(np.abs(dq2) > 1.0))
        g = np.asarray(d["grf_real"], float)
        pk = int(np.nanargmax(g))
        below = np.where(g[pk:] < 0.02 * g[pk])[0]
        toff = pk + int(below[0]) if len(below) else len(d["t"]) - 1
        w = flight_window(d, on, toff)
        if w is None:
            meta.append(("jump_0429", sub, 0, 0.0))
            continue
        rows, mrows = trial_states(d, w, o1c, o2c, d["l_i"], sgwin, cap)
        cvt_groups.append((sub, d["l_i"], pack_states(rows)))
        meta.append(("jump_0429", sub, len(rows), (w[1] - w[0]) * _dt(d)))
        _R["real_meas"].extend(mrows)
    return pack_states(out_nocvt) if out_nocvt else None, cvt_groups, meta


def _dt(d):
    return float(np.median(np.diff(d["t"])))


def trial_states(d, w, o1, o2, l_i, sgwin, cap):
    """비행창 → mj-frame 폐쇄일관 상태 리스트 + 측정토크(mj frame) 리스트."""
    sg = _R["savgol"]
    t = d["t"]
    dt = _dt(d)
    dq1s = sg(np.asarray(d["dq1"], float), sgwin, 3)
    dq2s = sg(np.asarray(d["dq2"], float), sgwin, 3)
    ddq1 = sg(np.asarray(d["dq1"], float), sgwin, 3, deriv=1, delta=dt)
    ddq2 = sg(np.asarray(d["dq2"], float), sgwin, 3, deriv=1, delta=dt)
    lo, hi = w
    idx = np.arange(lo, hi)
    if len(idx) > cap:
        idx = idx[np.linspace(0, len(idx) - 1, cap).astype(int)]
    rows, mrows = [], []
    qk0 = None
    J = _R["J"]
    for i in idx:
        q1m = -(float(d["q1"][i]) + o1) - np.pi / 2
        qcm = -(float(d["q2"][i]) + o2)
        v1, v2 = -dq1s[i], -dq2s[i]
        a1, a2 = -ddq1[i], -ddq2[i]
        if not np.isfinite([q1m, qcm, v1, v2, a1, a2]).all():
            continue
        if max(abs(v1), abs(v2)) > 50 or max(abs(a1), abs(a2)) > 4000:
            continue
        qpos, qvel, dd0, G, qk0 = make_state(1.0, q1m, qcm, v1, v2, a1, a2, l_i, qk0)
        rows.append((qpos, qvel, dd0, G, a1, a2, 0.0, v1, v2))
        m1 = float(J.ahat(_R["A_PAPER"], np.array([d["traw1"][i]]), np.array([d["dq1"][i]]))[0])
        m2 = float(J.ahat(_R["A_PAPER"], np.array([d["traw2"][i]]), np.array([d["dq2"][i]]))[0])
        mrows.append((-m1, -m2, qpos[4], qvel[3], qvel[4], v1, v2, G[3, 2], G[4, 2],
                      l_i))
    return rows, mrows


# ══════════════════ 분석 유틸 ══════════════════
def spectrum(Y_sc):
    U, s, Vt = np.linalg.svd(Y_sc, full_matrices=False)
    return s, Vt


def pretty_combo(vec, names, topn=6, thr=0.05):
    o = np.argsort(-np.abs(vec))
    mx = np.abs(vec[o[0]])
    terms = []
    for i in o[:topn]:
        if abs(vec[i]) < thr * mx:
            break
        terms.append(f"{vec[i]:+.3f}·{names[i]}")
    return " ".join(terms)


def main():
    t00 = time.time()
    np.set_printoptions(precision=4, suppress=True, linewidth=160)
    say("=" * 100)
    say("P22 Phase 1 — 베이스 파라미터 분석 (폐쇄체인 투영 회귀자)"
        + ("  [QUICK]" if QUICK else ""))
    say("=" * 100)

    # ── 부트스트랩 ──
    AD.ensure_init()
    import p19_judge as P
    import p14_judge as J
    import cvt_core as CC
    import mujoco as mj
    from scipy.signal import savgol_filter
    from scipy.linalg import qr as sqr
    cand = AD.load_candidate(REPO / "code/goal22/p19_jump/fourbar_p19_candidate.json")
    x32, v, sp, qoff = AD._p19_args(cand)
    ref = float(v[1])
    FR = J._P["FR"]
    dd26 = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    dd6 = dict(zip(_import_p13().N6, np.asarray(x32)[26:32]))
    _R.update(mj=mj, J=J, P=P, CC=CC, savgol=savgol_filter, dd26=dd26, dd6=dd6,
              x32=np.asarray(x32, float), ref=ref, sp=sp, qoff429=qoff,
              A_PAPER=P.A_PAPER, real_meas=[], pre30=float(v[2]),
              stiff=float(v[0]))
    say(f"[0] 후보: {cand['CANDIDATE']}  spring_at={sp} ref={ref:.3f} "
        f"pre30={float(v[2]):.3f}  qoff429=({qoff[0]:.4f},{qoff[1]:.4f})")

    build_par = lambda: P.build_flip(x32, ref, sp)
    build_cvt = lambda li: (lambda: P.build_cvt(x32, ref, sp, li))
    rm_par = RModel(build_par, "par(l_i=30)")
    rm_cvt = RModel(build_cvt(0.02508), "cvt(l_i=25.08)")
    dpi = float(np.max(np.abs(rm_par.pi0 - rm_cvt.pi0)))
    say(f"    π0 동일성 (par vs cvt 빌드): max|Δπ| = {dpi:.1e} "
        f"→ {'PASS' if dpi < 1e-10 else 'FAIL'}")
    say(f"    body 질량: " + "  ".join(
        f"{b}={rm_par.pi0[10 * k]:.4f}kg" for k, b in enumerate(BODIES))
        + f"  (합 {sum(rm_par.pi0[10 * k] for k in range(5)):.3f})")

    # 스케일 (θ = π/s): m→m0, h→m0·L, I→m0·L²; armature/마찰→탐색 half-width
    scales = np.empty(NX)
    for k, b in enumerate(BODIES):
        m0 = max(rm_par.pi0[10 * k], 1e-3)
        L = LCHAR[b]
        scales[10 * k] = m0
        scales[10 * k + 1:10 * k + 4] = m0 * L
        scales[10 * k + 4:10 * k + 10] = m0 * L * L
    scales[IDX_ARM] = 0.0115
    scales[[IDX_FV1, IDX_FC1, IDX_FV2, IDX_FC2]] = [0.625, 0.295, 0.35, 0.625]
    _R["scales"] = scales

    # ── [1] 사전 검증 ──
    say("\n[1] 사전 검증 (sanity)")
    rng = np.random.default_rng(SEED)
    ok = sanity_variant(rm_par) & sanity_variant(rm_cvt)
    ok &= sanity_G_par()
    ok &= sanity_JG(build_par, 0.03, "par body-connect")
    ok &= sanity_JG(build_cvt(0.02508), 0.02508, "cvt site-connect")
    ok &= sanity_galilean(rm_par)
    ok &= sanity_tree_linear(rm_par, rng)
    if not ok:
        say("!! sanity FAIL — 결과 신뢰 불가. 중단.")
        return

    # ── [2] 구조적 rank (합성 상태) ──
    say(f"\n[2] 구조적 식별성 — 합성 폐쇄일관 상태 {NSYN}×2 (l_i=30 + 25.08)")
    st_p = sample_syn(0.03, NSYN, rng)
    st_c = sample_syn(0.02508, NSYN, rng)
    syn = build_Y([(rm_par, st_p), (rm_cvt, st_c)], scales, "syn")
    Yfree_sc = syn["Yfree"] * scales
    Yflt_sc = syn["Yflt"] * scales
    s_free, Vt_free = spectrum(Yfree_sc)
    s_flt, Vt_flt = spectrum(Yflt_sc)
    tol = s_free[0] * 1e-7
    r_free = int((s_free > tol).sum())
    r_flt = int((s_flt > s_flt[0] * 1e-7).sum())
    say(f"  자유기저(ddbz 외생) σ/σ1: "
        + " ".join(f"{x:.1e}" for x in (s_free / s_free[0])[:min(30, NX)]))
    say(f"  구조적 rank (tol=σ1·1e-7): 자유기저 r={r_free} / 비행소거 r={r_flt} "
        f"(둘의 차 = 베이스 가속 정보의 몫)")
    # 죽은 열 (구조적 0)
    cn = np.linalg.norm(Yfree_sc, axis=0)
    dead = [PNAMES[i] for i in range(NX) if cn[i] < cn.max() * 1e-9]
    say(f"  구조적 0-열 ({len(dead)}개, 평면기구 예상: hy/Ixx/Izz/Ixy/Ixz/Iyz + base.*): ")
    say("    " + ", ".join(dead))
    # (iii) 재샘플 rank 불변
    rng2 = np.random.default_rng(SEED + 777)
    st_p2 = sample_syn(0.03, max(NSYN // 2, 200), rng2)
    st_c2 = sample_syn(0.02508, max(NSYN // 2, 200), rng2)
    syn2 = build_Y([(rm_par, st_p2), (rm_cvt, st_c2)], scales, "syn-reseed")
    s2, _ = spectrum(syn2["Yfree"] * scales)
    r2 = int((s2 > s2[0] * 1e-7).sum())
    say(f"  (iii) 재샘플 rank: {r2} vs {r_free} → {'PASS' if r2 == r_free else 'FAIL'}")
    # l_i 스택 효과: 평행사변형 단독 rank
    sp_only, _ = spectrum(Yfree_sc[:2 * st_p['N']])
    r_par_only = int((sp_only > sp_only[0] * 1e-7).sum())
    say(f"  l_i=30 단독 rank = {r_par_only} → CVT(25.08) 스택으로 +{r_free - r_par_only} "
        f"(CVT가 평행사변형 축퇴를 깸)")

    # pivoted QR → 베이스 조합 (자유기저)
    Q_, R_, piv = sqr(Yfree_sc, mode="economy", pivoting=True)
    pivots = piv[:r_free]
    deps = piv[r_free:]
    Bmat = np.linalg.lstsq(R_[:r_free, :r_free], R_[:r_free, r_free:], rcond=None)[0]
    say(f"\n  베이스 파라미터 (pivoted QR, {r_free}개) — 물리 단위 재그룹:")
    combos = []
    for k in range(r_free):
        pk = pivots[k]
        terms = [f"{PNAMES[pk]}"]
        for jj, dj in enumerate(deps):
            c_phys = Bmat[k, jj] * scales[pk] / scales[dj]
            if abs(Bmat[k, jj]) > 0.02:
                terms.append(f"{c_phys:+.4g}·{PNAMES[dj]}")
        combos.append(" ".join(terms))
        say(f"   B{k + 1:02d}: " + " ".join(terms[:7]) + (" ..." if len(terms) > 7 else ""))

    # ── [3] 마찰열 독립성 ──
    say("\n[3] 마찰열의 관성 스팬 독립성 (‖(I−P_in)f‖/‖f‖, 1=완전독립)")
    inert_cols = list(range(NI)) + [IDX_ARM]

    def fric_indep(Ysc, tagn, thr_abs=None):
        Uin, sin_, _ = np.linalg.svd(Ysc[:, inert_cols], full_matrices=False)
        rin = int((sin_ > (thr_abs if thr_abs else sin_[0] * 1e-7)).sum())
        P_ = Uin[:, :rin]
        outv = []
        for fi, fn in [(IDX_FV1, "fv_hip"), (IDX_FC1, "fc_hip"),
                       (IDX_FV2, "fv_knee"), (IDX_FC2, "fc_knee")]:
            f = Ysc[:, fi]
            res = f - P_ @ (P_.T @ f)
            outv.append((fn, float(np.linalg.norm(res) / max(np.linalg.norm(f), 1e-12))))
        say(f"  {tagn}: " + "  ".join(f"{n}={v:.3f}" for n, v in outv))
        return outv

    fi_syn = fric_indep(Yfree_sc, "합성(rich)")

    # ── [4] 실데이터 실용 식별성 ──
    say(f"\n[4] 실데이터 (fit 세션 비행창, SG win={SGWIN} poly=3, trial당 ≤{CAP_TRIAL})")
    st_real_nc, cvt_g, meta = prep_real(SGWIN, CAP_TRIAL)
    for ds in ("jump_position_0421", "jump_0424", "jump_0602", "jump_0429"):
        ms = [m for m in meta if m[0] == ds]
        used = [m for m in ms if m[2] > 0]
        say(f"  {ds:22s}: {len(used)}/{len(ms)} trial 사용, "
            f"샘플 {sum(m[2] for m in ms)}, 비행 {np.mean([m[3] for m in used]) if used else 0:.2f}s 평균")
    groups_real = ([(rm_par, st_real_nc)] if st_real_nc else [])
    rms_429 = []
    for sub, li, st in cvt_g:
        rmx = RModel(build_cvt(li), f"cvt-{sub}")
        assert float(np.max(np.abs(rmx.pi0 - rm_par.pi0))) < 1e-10
        rms_429.append(rmx)
        groups_real.append((rmx, st))
    real = build_Y(groups_real, scales, "real")
    Yr = real["Yflt"]                      # 실데이터는 비행소거 모드
    Yr_sc = Yr * scales
    s_r, Vt_r = spectrum(Yr_sc)
    kvis = int((s_r > NOISE).sum())
    kgood = int((s_r > 10 * NOISE).sum())
    say(f"  특이값 스펙트럼 σ_i [Nm/스케일]: "
        + " ".join(f"{x:.2g}" for x in s_r[:min(26, len(s_r))]))
    say(f"  조건수 σ1/σ_r(struct) = {s_r[0] / max(s_r[min(r_flt, len(s_r)) - 1], 1e-30):.1e}")
    say(f"  실용 rank: σ>{NOISE}Nm(불확실도<100%) → {kvis}개, "
        f"σ>{10 * NOISE}Nm(<10%) → {kgood}개  [구조적 비행 r={r_flt}]")
    say(f"  GAP = 구조적으로 가능하나 점프 데이터가 못 보는 조합: {r_flt - kvis}개")

    # 구조 조합별 실데이터 가시성
    say("  구조적 비행기저 방향별 실데이터 σ (‖Y_real·v_j‖):")
    for jj in range(r_flt):
        vj = Vt_flt[jj]
        lev = float(np.linalg.norm(Yr_sc @ vj))
        say(f"   S{jj + 1:02d} σ_syn={s_flt[jj]:9.3g} → 실데이터 {lev:9.3g} Nm "
            f"[{'보임' if lev > NOISE else '노이즈 아래'}]  {pretty_combo(vj, PNAMES, 4)}")

    fi_real = fric_indep(Yr_sc, f"실데이터(관성스팬=σ>{NOISE}Nm)", thr_abs=NOISE)

    # 측정토크 corr 체크 (정보용)
    corr_check(real, groups_real)

    # SG 민감도
    say(f"  SG 민감도 (win 7/11/15, cap {CAP_SENS}):")
    sens = {}
    for wn in (7, 11, 15):
        _R["real_meas"] = []
        st_nc, cg, _m = prep_real(wn, CAP_SENS)
        gr = ([(rm_par, st_nc)] if st_nc else [])
        for (sub, li, st), rmx in zip(cg, rms_429):
            gr.append((rmx, st))
        rr = build_Y(gr, scales, f"real-w{wn}")
        ss, _ = spectrum(rr["Yflt"] * scales)
        sens[wn] = ss
        say(f"   win={wn:2d}: σ1={ss[0]:.3g}  σ5={ss[4]:.3g}  σ10={ss[9]:.3g}  "
            f"σ>{NOISE} → {int((ss > NOISE).sum())}개")
    d711 = np.abs(sens[7][:10] - sens[11][:10]) / sens[11][:10]
    d1511 = np.abs(sens[15][:10] - sens[11][:10]) / sens[11][:10]
    say(f"   top-10 σ 변화율: win7 {100 * d711.max():.0f}% max / win15 {100 * d1511.max():.0f}% max")

    # ── [5] fit 파라미터 → 식별 부분공간 매핑 ──
    say(f"\n[5] fit 파라미터 방향의 식별성 (top-k 실데이터 부분공간, k={kvis})")
    D = fit_directions(build_par, rm_par)      # (NX, n_fitp) 물리 단위
    Vk = Vt_r[:kvis].T                          # (NX, k)
    Vstruct = Vt_free[:r_free].T
    say(f"  {'param':10s} {'frac_real_topk':>14s} {'frac_struct':>12s} "
        f"{'leverage[Nm/sweep]':>18s}  판정")
    frac_tab = {}
    for (pn, wsw), dcol in zip(FITP, D.T):
        dth = dcol / scales                    # θ 방향
        n = np.linalg.norm(dth)
        if n < 1e-15:
            say(f"  {pn:10s} {'—':>14s}  (0 방향?)")
            continue
        dth_h = dth / n
        fr = float(np.linalg.norm(Vk.T @ dth_h))
        fs = float(np.linalg.norm(Vstruct.T @ dth_h))
        lev = float(np.linalg.norm(Yr @ dcol)) * wsw
        tag = ("STICKER(널스페이스)" if fr < 0.35 else
               "약함" if fr < 0.7 else "OK")
        frac_tab[pn] = dict(frac_real=fr, frac_struct=fs, leverage=lev)
        say(f"  {pn:10s} {fr:14.3f} {fs:12.3f} {lev:18.3g}  {tag}")

    # fit-공간 Fisher: 우리 15개 나사 공간에서 실데이터가 보는 독립 방향 수
    say("\n[6] fit-파라미터 공간 Fisher (열 = Y·d_p·sweep, σ>0.4Nm = 보이는 방향)")
    cols = np.column_stack([np.asarray(Yr @ D[:, i]) * FITP[i][1]
                            for i in range(len(FITP))])
    sf, Vf = np.linalg.svd(cols, full_matrices=False)[1:3]
    nfvis = int((sf > NOISE).sum())
    say(f"  σ [Nm/sweep]: " + " ".join(f"{x:.2g}" for x in sf))
    say(f"  15개 나사 중 실데이터가 실제로 구분하는 독립 방향: {nfvis}개")
    fitn = [p[0] for p in FITP]
    for jj in range(len(sf)):
        vis = "보임" if sf[jj] > NOISE else "노이즈 아래"
        say(f"   F{jj + 1:02d} σ={sf[jj]:8.3g} [{vis}]  {pretty_combo(Vf[jj], fitn, 4)}")

    # 저장
    res = dict(
        quick=QUICK, nsyn=NSYN, cap=CAP_TRIAL, noise=NOISE,
        pnames=PNAMES, scales=scales.tolist(),
        rank_struct_free=r_free, rank_struct_flight=r_flt,
        rank_par_only=r_par_only,
        sv_struct_free=s_free.tolist(), sv_struct_flight=s_flt.tolist(),
        sv_real=s_r.tolist(), k_vis=kvis, k_good=kgood,
        dead_cols=dead, base_combos=combos,
        fric_indep_syn={n: v for n, v in fi_syn},
        fric_indep_real={n: v for n, v in fi_real},
        fit_fracs=frac_tab,
        fisher_fit_sv=sf.tolist(),
        fisher_fit_V=[[float(x) for x in row] for row in Vf],
        fit_names=fitn,
        meta_trials=[list(m) for m in meta],
        sg_sens={str(w): sens[w][:12].tolist() for w in sens},
        report="\n".join(REPORT))
    safe.atomic_json_write(OUT_JSON, res)
    say(f"\n저장: {OUT_JSON}")
    say(f"총 {time.time() - t00:.0f}s")


def corr_check(real, groups_real):
    """정보용: 비행창 예측토크(π0+기지 수동항) vs 측정 a_hat 토크."""
    meas = np.array([m[:2] for m in _R["real_meas"]])     # mj frame (hip, crank)
    if len(meas) * 2 != len(real["U0flt"]):
        say(f"  (corr 체크 스킵: 행수 불일치 {len(meas)} vs {len(real['U0flt']) // 2})")
        return
    U0 = real["U0flt"].reshape(-1, 2)
    dd26, dd6 = _R["dd26"], _R["dd6"]
    pred = U0.copy()
    for i, m in enumerate(_R["real_meas"]):
        _m1, _m2, qk_mj, dqpin, dqk, v1, v2, gp, r, li = m
        pred[i, 0] += dd26["fv_hip"] * v1 + dd26["fc_hip"] * np.tanh(v1 / 0.02)
        pred[i, 1] += dd26["fv_knee"] * v2 + dd26["fc_knee"] * np.tanh(v2 / 0.02)
        pred[i, 1] += gp * dd6["d_cpin"] * dqpin + r * dd6["d_kneep"] * dqk
        if _R["sp"] == "calf":
            pred[i, 1] += r * _R["stiff"] * (qk_mj - _R["ref"])
        if abs(li - 0.03) < 1e-6:
            # no-cvt 플랜트 프리로드: sim ctrl=−(s2+pre) ⇒ −s2 = u+passive+pre
            pred[i, 1] += _R["pre30"]
    for ch, nm in [(0, "hip"), (1, "crank")]:
        c = np.corrcoef(pred[:, ch], meas[:, ch])[0, 1]
        rmse = float(np.sqrt(np.mean((pred[:, ch] - meas[:, ch]) ** 2)))
        say(f"  (정보) 비행 예측 vs 측정 [{nm}]: corr={c:+.3f}  RMSE={rmse:.2f} Nm "
            f"(주의: 마찰 tanh 근사·레일마찰 미포함)")


def fit_directions(build_par, rm_par):
    """fit 파라미터 15개 → 55-dim 회귀자 방향 (물리 단위, per unit param)."""
    import p19_judge as P
    FR = _R["J"]._P["FR"]
    x32 = _R["x32"]
    ref, sp = _R["ref"], _R["sp"]
    D = np.zeros((NX, len(FITP)))
    STEP = dict(com_dz_th=0.002, com_dz_ca=0.002, m_foot=0.01)
    for col, (pn, _w) in enumerate(FITP):
        if pn == "arm_knee":
            D[IDX_ARM, col] = 1.0
            continue
        if pn in ("fv_hip", "fc_hip", "fv_knee", "fc_knee"):
            D[{"fv_hip": IDX_FV1, "fc_hip": IDX_FC1,
               "fv_knee": IDX_FV2, "fc_knee": IDX_FC2}[pn], col] = 1.0
            continue
        i = FR.NAMES.index(pn)
        dlt = STEP.get(pn, 0.02)
        mjm = _R["mj"]
        xp = x32.copy()
        xp[i] += dlt
        mp, _ = P.build_flip(xp, ref, sp)
        xp[i] -= 2 * dlt
        mm, _ = P.build_flip(xp, ref, sp)
        bidp = [mjm.mj_name2id(mp, mjm.mjtObj.mjOBJ_BODY, b) for b in BODIES]
        bidm = [mjm.mj_name2id(mm, mjm.mjtObj.mjOBJ_BODY, b) for b in BODIES]
        pip = np.concatenate([body_pi(mp, b, mjm) for b in bidp])
        pim = np.concatenate([body_pi(mm, b, mjm) for b in bidm])
        D[:NI, col] = (pip - pim) / (2 * dlt)
    return D


def _import_p13():
    import g21_p13_linkage as P13
    return P13


if __name__ == "__main__":
    main()
