# -*- coding: utf-8 -*-
"""P22 Phase 1 — 베이스 파라미터(식별 가능 관성 조합) 분석.

방법 (수치, Pinocchio 불요 — 역동역학은 body 표준 관성파라미터에 정확히 선형):
 1. P19 후보 모델(평행사변형 flip + CVT l_i=25.08mm)에서 회귀자 변형 모델 생성
    (스프링/감쇠/frictionloss/armature 0 + equality/contact 등 disable).
    ★ body_sameframe=0 필수 (컴파일러 최적화가 body_iquat 갱신을 무시 — 디버그로 발견).
 2. 트리 회귀자: body {base,thigh,crank,coupler,calf} × 표준 10파라미터
    π_b = (m, m·cx, m·cy, m·cz, Ixx, Iyy, Izz, Ixy, Ixz, Iyz)  [I는 body frame "원점" 기준].
    기저: MuJoCo (mass, ipos, iquat, inertia) ↔ 표준기저 변환 (eigh 재대각화) — 왕복 검증.
    열 = 중앙 FD — 선형이므로 δ 무관(2δ 검증). +armature열(=ddqc) +마찰열 4개.
 3. 폐쇄 투영: 독립속도 v=(bz, dq1, dqc), tree qvel = G(qc)·v (closure() FD),
    q̈ = G·v̇ + Ġ·v. u = Gᵀτ_tree = (레일힘, 힙토크, 크랭크토크). 레일행 drop.
    비행모드: 레일행=0으로 ddbz 소거 (π 의존 → 국소 야코비안, 중앙 FD가 흡수).
 4. ★스탠스 투영 (실측 발견 대응): 실데이터 xlsx는 이륙 3~9샘플 후 기록 종료 —
    비행 데이터가 아예 없다. 대신 발 구름(no-slip rolling) 구속과 폐쇄를 동시에 소거하는
    1-DOF 방향 n(q) (n = ax×az)로 투영: n2·τ_hip + n3·τ_crank = nᵀGᵀ(M q̈ + c).
    접촉력·폐쇄력 모두 소거 (레일은 마찰 0 가정). 행 노이즈 = 0.4·√(n2²+n3²) = 0.4 (정규화).
 5. 구조적 rank: 폐쇄일관 랜덤상태 (l_i=30 + 25.08 stack) SVD + pivoted QR → 베이스 조합.
 6. 실데이터: fit 세션(0421/0424/0602/0429)만, 0324 held-out 제외.
    ddq = Savitzky-Golay(dq, win=11, poly=3, deriv=1) — win 7/15 민감도 체크.
 7. fit 파라미터 15개의 회귀자 방향(빌더 FD) → 실데이터 top-k 식별부분공간 내 비율.

한계 (정직): 스탠스 행은 발 미끄럼 없음 + 구름 반경 = geom 반경 + 레일 마찰 0 가정.
접촉 컴플라이언스 동역학(임팩트·솔버층)은 범위 밖. 비행 구조는 합성으로만 제시.
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
NSYN = 250 if QUICK else 1500          # 구조적 샘플 수 (l_i당, 자유/스탠스 각각)
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
        model.dof_damping[:] = 0.0
        model.dof_frictionloss[:] = 0.0
        model.dof_armature[:] = 0.0
        model.jnt_stiffness[:] = 0.0
        DS = mj.mjtDisableBit
        model.opt.disableflags |= (DS.mjDSBL_EQUALITY | DS.mjDSBL_CONTACT
                                   | DS.mjDSBL_SPRING | DS.mjDSBL_DAMPER
                                   | DS.mjDSBL_LIMIT | DS.mjDSBL_FRICTIONLOSS)
        # ★ 핵심 fix (디버그로 발견): 컴파일러가 iquat==identity body에 sameframe
        # 최적화 플래그를 박아 mj_kinematics가 body_iquat 갱신을 "무시"한다.
        # π 섭동은 iquat를 회전시키므로 반드시 전 body sameframe=NONE으로 해제.
        model.body_sameframe[:] = 0
        self.model = model
        self.d = mj.MjData(model)
        self.iq = np.array([safe.qadr(model, j, mj) for j in JOINTS])
        self.iv = np.array([safe.dofadr(model, j, mj) for j in JOINTS])
        self.bid = [mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, b) for b in BODIES]
        assert min(self.bid) >= 0, f"body 누락: {self.tag}"
        self.fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
        self.rf = float(model.geom_size[self.fg][0])   # 발 실린더 반경
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


def G_mat(r, gp):
    G = np.zeros((5, 3))
    G[0, 0] = 1.0
    G[1, 1] = 1.0
    G[2, 2] = 1.0
    G[3, 2] = gp
    G[4, 2] = r
    return G


def make_state(bz, q1, qc, dq1, dqc, dd1, ddc, l_i, qk0=None):
    """비행/자유용 폐쇄일관 tree 상태: (qpos5, qvel5, dd0_5, G, qk)."""
    qk, qp, r, gp, gpp, rp = G_terms(qc, l_i, qk0)
    G = G_mat(r, gp)
    qpos = np.array([bz, q1, qc, qp, qk])
    qvel = G @ np.array([0.0, dq1, dqc])           # dbz=0 (갈릴레이 불변 — 검증됨)
    dd0 = np.array([0.0, 0.0, 0.0, gpp * dqc ** 2, rp * dqc ** 2])  # Ġ·v
    return qpos, qvel, dd0, G, qk


def stance_geo(rm, q1, qc, l_i, qk0=None):
    """스탠스 기하: 폐쇄 + 발 구름 구속 → 1-DOF 방향 n (√(n2²+n3²)=1 정규화)."""
    mjm = rm.mj
    model, d = rm.model, rm.d
    qk, qp, r, gp, gpp, rp = G_terms(qc, l_i, qk0)
    G = G_mat(r, gp)
    d.qpos[rm.iq] = [1.0, q1, qc, qp, qk]
    d.qvel[rm.iv] = 0.0
    mjm.mj_forward(model, d)
    pt = d.geom_xpos[rm.fg].copy()
    jacp = np.zeros((3, model.nv))
    mjm.mj_jac(model, d, jacp, None, pt, rm.bid[4])   # calf
    Jx = jacp[0, rm.iv]
    Jz = jacp[2, rm.iv]
    # 구름: v_center_x = rf·ω_calf (ω_y = dq_hip + dq_knee)
    ax = Jx @ G - rm.rf * np.array([0.0, 1.0, r])
    az = Jz @ G
    n = np.cross(ax, az)
    nj = np.hypot(n[1], n[2])
    if nj < 1e-9:
        return None
    n = n / nj
    bz_fk = 1.0 + (rm.rf - pt[2])     # 발 중심 z=rf가 되게 하는 bz
    return dict(qk=qk, qp=qp, r=r, gp=gp, gpp=gpp, rp=rp, G=G, n=n, bz=bz_fk)


# ══════════════════ 상태 팩 ══════════════════
def pack_states(rows, kind):
    """rows(자유/비행): (qpos,qvel,dd0,G,dd1,ddc,ddbz,dq1,dqc)
       rows(스탠스):    (qpos,qvel,dd0,G,vdot3,n3,dq1,dqc)"""
    if not rows:
        return None
    st = {"kind": kind, "N": len(rows)}
    st["Q"] = np.array([r[0] for r in rows])
    st["V"] = np.array([r[1] for r in rows])
    st["D0"] = np.array([r[2] for r in rows])
    st["G"] = np.array([r[3] for r in rows])
    if kind == "stance":
        st["vdot"] = np.array([r[4] for r in rows])
        st["n"] = np.array([r[5] for r in rows])
        st["dq1"] = np.array([r[6] for r in rows])
        st["dqc"] = np.array([r[7] for r in rows])
        st["nr"] = 1
    else:
        st["dd1"] = np.array([r[4] for r in rows])
        st["ddc"] = np.array([r[5] for r in rows])
        st["ddbz"] = np.array([r[6] for r in rows])
        st["dq1"] = np.array([r[7] for r in rows])
        st["dqc"] = np.array([r[8] for r in rows])
        st["nr"] = 2
    return st


# ══════════════════ (a,b) 평가 + 행 조립 ══════════════════
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


def group_u(rm, st):
    """자유/비행: (Ufree(N,2), Uflight(N,2)) — 행 (hip, crank).
       스탠스: (Ust(N,1), Ust(N,1))."""
    A, B = eval_ab(rm, st)
    if st["kind"] == "stance":
        u3 = np.einsum("nij,nj->ni", A, st["vdot"]) + B
        us = np.einsum("ni,ni->n", st["n"], u3)[:, None]
        return us, us
    dd1, ddc, ddbz = st["dd1"], st["ddc"], st["ddbz"]
    uf = np.empty((st["N"], 2))
    ug = np.empty((st["N"], 2))
    for r in (1, 2):
        uf[:, r - 1] = A[:, r, 0] * ddbz + A[:, r, 1] * dd1 + A[:, r, 2] * ddc + B[:, r]
    dbz_el = -(A[:, 0, 1] * dd1 + A[:, 0, 2] * ddc + B[:, 0]) / A[:, 0, 0]
    for r in (1, 2):
        ug[:, r - 1] = A[:, r, 0] * dbz_el + A[:, r, 1] * dd1 + A[:, r, 2] * ddc + B[:, r]
    return uf, ug


def analytic_cols(st):
    """armature + 마찰 4열 (해석적). 반환 (rows, 5)."""
    N = st["N"]
    if st["kind"] == "stance":
        n2 = st["n"][:, 1]
        n3 = st["n"][:, 2]
        out = np.zeros((N, 5))
        out[:, 0] = n3 * st["vdot"][:, 2]                    # armature: n3·ddqc
        out[:, 1] = n2 * st["dq1"]
        out[:, 2] = n2 * np.tanh(st["dq1"] / 0.02)
        out[:, 3] = n3 * st["dqc"]
        out[:, 4] = n3 * np.tanh(st["dqc"] / 0.02)
        return out
    out = np.zeros((2 * N, 5))
    out[1::2, 0] = st["ddc"]                                 # crank행 armature
    out[0::2, 1] = st["dq1"]
    out[0::2, 2] = np.tanh(st["dq1"] / 0.02)
    out[1::2, 3] = st["dqc"]
    out[1::2, 4] = np.tanh(st["dqc"] / 0.02)
    return out


def build_Y(groups, scales, label):
    """중앙 FD로 π 50열 + 해석 5열. 반환 dict(Yfree, Yflt, U0free, U0flt, slices)."""
    t0 = time.time()
    groups = [(rm, st) for rm, st in groups if st is not None and st["N"] > 0]
    Ntot = sum(st["nr"] * st["N"] for _, st in groups)
    Yfree = np.zeros((Ntot, NX))
    Yflt = np.zeros((Ntot, NX))
    U0f = np.zeros(Ntot)
    U0g = np.zeros(Ntot)
    sl = []
    o = 0
    for _, st in groups:
        sl.append(slice(o, o + st["nr"] * st["N"]))
        o += st["nr"] * st["N"]
    for (rm, st), s in zip(groups, sl):
        uf, ug = group_u(rm, st)
        U0f[s] = uf.reshape(-1)
        U0g[s] = ug.reshape(-1)
        ac = analytic_cols(st)
        Yfree[s, NI:] = ac
        Yflt[s, NI:] = ac
    for j in range(NI):
        dj = DELTA_REL * scales[j]
        for (rm, st), s in zip(groups, sl):
            pi = rm.pi0.copy()
            pi[j] += dj
            rm.set_pi(pi)
            ufp, ugp = group_u(rm, st)
            pi[j] -= 2 * dj
            rm.set_pi(pi)
            ufm, ugm = group_u(rm, st)
            rm.restore()
            Yfree[s, j] = (ufp - ufm).reshape(-1) / (2 * dj)
            Yflt[s, j] = (ugp - ugm).reshape(-1) / (2 * dj)
    say(f"  [{label}] Y 구축: rows={Ntot}, cols={NX}, {time.time() - t0:.0f}s")
    return dict(Yfree=Yfree, Yflt=Yflt, U0free=U0f, U0flt=U0g, slices=sl,
                groups=groups)


# ══════════════════ 검증 ══════════════════
def sanity_variant(rm):
    mj, model, d = rm.mj, rm.model, rm.d
    d.qpos[rm.iq] = [1.0, -1.2, -2.0, 2.0 + 0.3, -2.0 + 0.1]  # 폐쇄 위반 상태
    d.qvel[:] = 3.0
    mj.mj_forward(model, d)
    ok = (d.nefc == 0 and np.max(np.abs(d.qfrc_passive)) < 1e-12
          and np.max(np.abs(d.qfrc_constraint)) < 1e-12)
    say(f"  [{rm.tag}] disable 검증: nefc={d.nefc}, |passive|={np.max(np.abs(d.qfrc_passive)):.1e}, "
        f"|constraint|={np.max(np.abs(d.qfrc_constraint)):.1e} → {'PASS' if ok else 'FAIL'}")
    return ok


def sanity_tree_linear(rm, rng, nst=40):
    """(i) Y_tree·π0 == mj_inverse (임의 tree 상태) + 2δ 선형성."""
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
    say(f"  (i) Y·π0 vs mj_inverse 상대오차 = {rel:.2e} (<1e-6) → {'PASS' if rel < 1e-6 else 'FAIL'}")
    say(f"      2δ 선형성 (δ vs 30δ) = {dlin:.2e} (<1e-6) → {'PASS' if dlin < 1e-6 else 'FAIL'}")
    return rel < 1e-6 and dlin < 1e-6


def sanity_G_par():
    qk, qp, r, gp, gpp, rp = G_terms(-2.0, 0.03)
    ok = (abs(r - 1) < 1e-8 and abs(gp + 1) < 1e-8 and abs(gpp) < 1e-4 and abs(rp) < 1e-4
          and abs(qk + 2.0) < 1e-9)
    say(f"  (ii) 평행사변형 G: r={r:.9f} (→1), gp={gp:.9f} (→−1), gpp={gpp:.1e}, rp={rp:.1e} "
        f"→ {'PASS' if ok else 'FAIL'}")
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
        qk, qp, r, gp, gpp, rp = G_terms(qc, l_i, qk0)
        qk0 = qk
        G = G_mat(r, gp)
        d.qpos[:] = 0.0
        d.qpos[[safe.qadr(model, j, mj) for j in JOINTS]] = [1.0, -1.2, qc, qp, qk]
        mj.mj_forward(model, d)
        eq = d.efc_type == mj.mjtConstraint.mjCNSTR_EQUALITY
        if not eq.any():
            say(f"  (J·G) {tag}: equality 행 없음?! FAIL")
            return False
        J = d.efc_J.reshape(d.nefc, model.nv)[eq]
        iv = [safe.dofadr(model, j, mj) for j in JOINTS]
        JG = J[:, iv] @ G
        worst = max(worst, float(np.max(np.abs(JG)) / max(np.max(np.abs(J)), 1e-12)))
    say(f"  (J·G) {tag}: max|J_eq·G|/|J| = {worst:.1e} (<1e-6) → {'PASS' if worst < 1e-6 else 'FAIL'}")
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
    say(f"  갈릴레이 불변 (dbz 0 vs 2): |Δτ|max = {diff:.1e} → {'PASS' if diff < 1e-9 else 'FAIL'}")
    return diff < 1e-9


# ══════════════════ 합성 샘플링 ══════════════════
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
    return pack_states(rows, "free")


def sample_syn_stance(rm, l_i, n, rng):
    rows = []
    eps = 1e-5
    for _ in range(n):
        qc = rng.uniform(-2.6, -0.3)
        q1 = rng.uniform(-3.0, -0.8)
        g0 = stance_geo(rm, q1, qc, l_i)
        if g0 is None:
            continue
        s = rng.uniform(-15, 15)
        sdot = rng.uniform(-500, 500)
        nvec = g0["n"]
        gp_ = stance_geo(rm, q1 + eps * nvec[1] * s, qc + eps * nvec[2] * s, l_i, g0["qk"])
        gm_ = stance_geo(rm, q1 - eps * nvec[1] * s, qc - eps * nvec[2] * s, l_i, g0["qk"])
        if gp_ is None or gm_ is None:
            continue
        ndot = (gp_["n"] - gm_["n"]) / (2 * eps)
        v = nvec * s
        vdot = nvec * sdot + ndot * s
        qpos = np.array([g0["bz"], q1, qc, g0["qp"], g0["qk"]])
        qvel = g0["G"] @ v
        dd0 = np.array([0, 0, 0, g0["gpp"] * v[2] ** 2, g0["rp"] * v[2] ** 2])
        rows.append((qpos, qvel, dd0, g0["G"], vdot, nvec, v[1], v[2]))
    return pack_states(rows, "stance")


# ══════════════════ 실데이터 ══════════════════
def _dt(d):
    return float(np.median(np.diff(d["t"])))


def flight_window(d, toff):
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
    return (lo, hi) if hi - lo >= 25 else None


def stance_window(d, toff):
    g = d.get("grf_real")
    if g is None:
        return None
    lo, hi = 3, min(toff - 5, len(d["t"]) - 3)
    if hi - lo < 30:
        return None
    return lo, hi


def toff_of(d, tr=None):
    if tr is not None:
        return tr["toff"]
    dq2 = np.asarray(d["dq2"])
    on = int(np.argmax(np.abs(dq2) > 1.0))
    g = np.asarray(d["grf_real"], float)
    pk = int(np.nanargmax(g))
    below = np.where(g[pk:] < 0.02 * g[pk])[0]
    return pk + int(below[0]) if len(below) else len(d["t"]) - 1


def trial_states(rm, d, o1, o2, l_i, sgwin, cap, toff):
    """스탠스(+비행) 상태 + 측정 결합토크. 반환 (stance_rows, meas_rows, fl_rows, n_fl)."""
    sg = _R["savgol"]
    J = _R["J"]
    t = d["t"]
    dt = _dt(d)
    dq1s = sg(np.asarray(d["dq1"], float), sgwin, 3)
    dq2s = sg(np.asarray(d["dq2"], float), sgwin, 3)
    ddq1 = sg(np.asarray(d["dq1"], float), sgwin, 3, deriv=1, delta=dt)
    ddq2 = sg(np.asarray(d["dq2"], float), sgwin, 3, deriv=1, delta=dt)
    grf = np.asarray(d["grf_real"], float)
    rows, mrows = [], []
    # ── 스탠스 ──
    w = stance_window(d, toff)
    if w is not None:
        lo, hi = w
        idxw = np.arange(lo, hi)
        # 전 구간 기하 (bz_fk 시계열 → SG 미분)
        geos = []
        qk0 = None
        for i in idxw:
            q1m = -(float(d["q1"][i]) + o1) - np.pi / 2
            qcm = -(float(d["q2"][i]) + o2)
            g0 = stance_geo(rm, q1m, qcm, l_i, qk0)
            qk0 = g0["qk"] if g0 else None
            geos.append(g0)
        okm = np.array([g0 is not None for g0 in geos])
        bz_t = np.array([g0["bz"] if g0 else np.nan for g0 in geos])
        if okm.sum() > sgwin + 4 and okm.all():
            dbz_t = sg(bz_t, sgwin, 3, deriv=1, delta=dt)
            ddbz_t = sg(bz_t, sgwin, 3, deriv=2, delta=dt)
            sel = np.arange(len(idxw))
            if len(sel) > cap:
                sel = sel[np.linspace(0, len(sel) - 1, cap).astype(int)]
            for k in sel:
                i = int(idxw[k])
                g0 = geos[k]
                if not (np.isfinite(grf[i]) and grf[i] > 8.0):
                    continue
                v1, v2 = -dq1s[i], -dq2s[i]
                a1, a2 = -ddq1[i], -ddq2[i]
                if not np.isfinite([v1, v2, a1, a2, dbz_t[k], ddbz_t[k]]).all():
                    continue
                if max(abs(v1), abs(v2)) > 50 or max(abs(a1), abs(a2)) > 4000:
                    continue
                q1m = -(float(d["q1"][i]) + o1) - np.pi / 2
                qcm = -(float(d["q2"][i]) + o2)
                v = np.array([dbz_t[k], v1, v2])
                vdot = np.array([ddbz_t[k], a1, a2])
                qpos = np.array([g0["bz"], q1m, qcm, g0["qp"], g0["qk"]])
                qvel = g0["G"] @ v
                dd0 = np.array([0, 0, 0, g0["gpp"] * v2 ** 2, g0["rp"] * v2 ** 2])
                rows.append((qpos, qvel, dd0, g0["G"], vdot, g0["n"], v1, v2))
                m1 = float(J.ahat(_R["A_PAPER"], np.array([d["traw1"][i]]),
                                  np.array([d["dq1"][i]]))[0])
                m2 = float(J.ahat(_R["A_PAPER"], np.array([d["traw2"][i]]),
                                  np.array([d["dq2"][i]]))[0])
                mrows.append(dict(kind="stance", m1=-m1, m2=-m2, n=g0["n"],
                                  qk=g0["qk"], dqpin=float(qvel[3]), dqk=float(qvel[4]),
                                  v1=v1, v2=v2, gp=g0["gp"], r=g0["r"], l_i=l_i))
    # ── 비행 (기록이 있으면 — 실제로는 전무) ──
    fl_rows = []
    wf = flight_window(d, toff)
    if wf is not None:
        lo, hi = wf
        idx = np.arange(lo, hi)
        if len(idx) > cap:
            idx = idx[np.linspace(0, len(idx) - 1, cap).astype(int)]
        qk0 = None
        for i in idx:
            q1m = -(float(d["q1"][i]) + o1) - np.pi / 2
            qcm = -(float(d["q2"][i]) + o2)
            v1, v2 = -dq1s[i], -dq2s[i]
            a1, a2 = -ddq1[i], -ddq2[i]
            if not np.isfinite([q1m, qcm, v1, v2, a1, a2]).all():
                continue
            qpos, qvel, dd0, G, qk0 = make_state(1.0, q1m, qcm, v1, v2, a1, a2, l_i, qk0)
            fl_rows.append((qpos, qvel, dd0, G, a1, a2, 0.0, v1, v2))
    return rows, mrows, fl_rows


def prep_real(sgwin, cap, rms_429=None):
    """fit 세션 (0324 제외) → [(rm, states)] 그룹 + meta. 스탠스+비행."""
    J = _R["J"]
    CC = _R["CC"]
    dd26 = _R["dd26"]
    rm_par = _R["rm_par"]
    OFF = {"jump_position_0421": ("o1_0421", "o2_0421"),
           "jump_0424": ("o1_0424", "o2_0424"), "jump_0602": (None, None)}
    meas = []
    meta = []
    st_rows, fl_rows = [], []
    for tr in J._P["cl"]:
        ds = tr["ds"]
        if ds == "jump_0324" or ds not in OFF:
            continue
        k1, k2 = OFF[ds]
        o1 = dd26.get(k1, 0.0) if k1 else 0.0
        o2 = dd26.get(k2, 0.0) if k2 else 0.0
        rows, mrows, fr = trial_states(rm_par, tr["d"], o1, o2, 0.03, sgwin, cap,
                                       toff_of(tr["d"], tr))
        st_rows.extend(rows)
        meas.extend(mrows)
        fl_rows.extend(fr)
        meta.append((ds, str(tr["sub"]), len(rows), len(fr)))
    groups = []
    if st_rows or fl_rows:
        groups.append((rm_par, pack_states(st_rows, "stance")))
        if fl_rows:
            groups.append((rm_par, pack_states(fl_rows, "free")))
    o1c, o2c = _R["qoff429"]
    new_rms = rms_429 is None
    if new_rms:
        rms_429 = []
    ir = 0
    for sub in CC.SUBS429:
        d = CC.load_0429(sub) if new_rms else _R["d429"][sub]
        if new_rms:
            _R.setdefault("d429", {})[sub] = d
        if new_rms:
            rmx = RModel(_R["build_cvt"](d["l_i"]), f"cvt-{sub}")
            assert float(np.max(np.abs(rmx.pi0 - rm_par.pi0))) < 1e-10
            rms_429.append(rmx)
        rmx = rms_429[ir]
        ir += 1
        rows, mrows, fr = trial_states(rmx, d, o1c, o2c, d["l_i"], sgwin, cap,
                                       toff_of(d))
        if rows:
            groups.append((rmx, pack_states(rows, "stance")))
        meas.extend(mrows)
        meta.append(("jump_0429", sub, len(rows), len(fr)))
    return groups, meas, meta, rms_429


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


def corr_check(real, meas):
    """정보용: 스탠스 예측(π0+기지 수동항+프리로드) vs 측정 결합토크."""
    dd26, dd6 = _R["dd26"], _R["dd6"]
    # 스탠스 행 위치: groups 순서와 meas 순서 동일 (prep_real 구성)
    st_idx = [i for i, m in enumerate(meas) if m["kind"] == "stance"]
    u0 = []
    for (rm, st), s in zip(real["groups"], real["slices"]):
        if st["kind"] == "stance":
            u0.append(real["U0flt"][s])
    if not u0:
        say("  (corr 체크: 스탠스 행 없음 — 스킵)")
        return
    u0 = np.concatenate(u0)
    if len(u0) != len(st_idx):
        say(f"  (corr 체크 스킵: 행수 불일치 {len(u0)} vs {len(st_idx)})")
        return
    pred, mv = [], []
    for uu, mi in zip(u0, st_idx):
        m = meas[mi]
        n2, n3 = m["n"][1], m["n"][2]
        p = uu
        p += n2 * (dd26["fv_hip"] * m["v1"] + dd26["fc_hip"] * np.tanh(m["v1"] / 0.02))
        p += n3 * (dd26["fv_knee"] * m["v2"] + dd26["fc_knee"] * np.tanh(m["v2"] / 0.02))
        p += n3 * (m["gp"] * dd6["d_cpin"] * m["dqpin"] + m["r"] * dd6["d_kneep"] * m["dqk"])
        if _R["sp"] == "calf":
            p += n3 * m["r"] * _R["stiff"] * (m["qk"] - _R["ref"])
        if abs(m["l_i"] - 0.03) < 1e-6:
            p += n3 * _R["pre30"]     # sim ctrl=−(s2+pre) ⇒ −s2 = u+passive+pre
        pred.append(p)
        mv.append(n2 * m["m1"] + n3 * m["m2"])
    pred = np.array(pred)
    mv = np.array(mv)
    c = float(np.corrcoef(pred, mv)[0, 1])
    rmse = float(np.sqrt(np.mean((pred - mv) ** 2)))
    say(f"  (정보) 스탠스 결합토크 예측 vs 측정: corr={c:+.3f}  RMSE={rmse:.2f} Nm "
        f"(구름/무슬립·레일무마찰 가정 + tanh 마찰 근사)")


def fit_directions():
    """fit 파라미터 15개 → 55-dim 회귀자 방향 (물리 단위, per unit param)."""
    import p19_judge as P
    FR = _R["J"]._P["FR"]
    x32 = _R["x32"]
    ref, sp = _R["ref"], _R["sp"]
    mjm = _R["mj"]
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


# ══════════════════ 메인 ══════════════════
def main():
    t00 = time.time()
    np.set_printoptions(precision=4, suppress=True, linewidth=160)
    say("=" * 100)
    say("P22 Phase 1 — 베이스 파라미터 분석 (폐쇄체인+스탠스 투영 회귀자)"
        + ("  [QUICK]" if QUICK else ""))
    say("=" * 100)

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
              A_PAPER=P.A_PAPER, pre30=float(v[2]), stiff=float(v[0]))
    say(f"[0] 후보: {cand['CANDIDATE']}  spring_at={sp} ref={ref:.3f} "
        f"pre30={float(v[2]):.3f}  qoff429=({qoff[0]:.4f},{qoff[1]:.4f})")

    build_par = lambda: P.build_flip(x32, ref, sp)
    build_cvt = lambda li: (lambda: P.build_cvt(x32, ref, sp, li))
    _R["build_cvt"] = build_cvt
    rm_par = RModel(build_par, "par(l_i=30)")
    rm_cvt = RModel(build_cvt(0.02508), "cvt(l_i=25.08)")
    _R["rm_par"] = rm_par
    dpi = float(np.max(np.abs(rm_par.pi0 - rm_cvt.pi0)))
    say(f"    π0 동일성 (par vs cvt): max|Δπ| = {dpi:.1e} → {'PASS' if dpi < 1e-10 else 'FAIL'}")
    say("    body 질량: " + "  ".join(
        f"{b}={rm_par.pi0[10 * k]:.4f}kg" for k, b in enumerate(BODIES))
        + f"  (합 {sum(rm_par.pi0[10 * k] for k in range(5)):.3f})"
        + f"  발반경 rf={rm_par.rf * 1000:.1f}mm")

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

    # ── [2] 구조적 rank (합성) ──
    say(f"\n[2] 구조적 식별성 — 합성 상태 {NSYN}×2 (l_i=30+25.08), 자유/비행/스탠스")
    st_p = sample_syn(0.03, NSYN, rng)
    st_c = sample_syn(0.02508, NSYN, rng)
    syn = build_Y([(rm_par, st_p), (rm_cvt, st_c)], scales, "syn-자유")
    ss_p = sample_syn_stance(rm_par, 0.03, NSYN, rng)
    ss_c = sample_syn_stance(rm_cvt, 0.02508, NSYN, rng)
    syn_st = build_Y([(rm_par, ss_p), (rm_cvt, ss_c)], scales, "syn-스탠스")
    Yfree_sc = syn["Yfree"] * scales
    Yflt_sc = syn["Yflt"] * scales
    Yst_sc = syn_st["Yflt"] * scales
    s_free, Vt_free = spectrum(Yfree_sc)
    s_flt, Vt_flt = spectrum(Yflt_sc)
    s_st, Vt_st = spectrum(Yst_sc)
    r_free = int((s_free > s_free[0] * 1e-7).sum())
    r_flt = int((s_flt > s_flt[0] * 1e-7).sum())
    r_st = int((s_st > s_st[0] * 1e-7).sum())
    s_all, _ = spectrum(np.vstack([Yfree_sc, Yst_sc]))
    r_all = int((s_all > s_all[0] * 1e-7).sum())
    say("  자유기저 σ/σ1: " + " ".join(f"{x:.1e}" for x in (s_free / s_free[0])[:20]))
    say(f"  구조적 rank (tol=σ1·1e-7): 자유 r={r_free} / 비행소거 r={r_flt} / "
        f"스탠스투영 r={r_st} / 자유∪스탠스 r={r_all}")
    cn = np.linalg.norm(Yfree_sc, axis=0)
    cn2 = np.linalg.norm(Yst_sc, axis=0)
    dead = [PNAMES[i] for i in range(NX) if cn[i] < cn.max() * 1e-9
            and cn2[i] < cn2.max() * 1e-9]
    say(f"  구조적 0-열 ({len(dead)}개; 평면기구: hy/Ixx/Izz/Ixy/Ixz/Iyz + base 회전류):")
    say("    " + ", ".join(dead))
    rng2 = np.random.default_rng(SEED + 777)
    st_p2 = sample_syn(0.03, max(NSYN // 2, 200), rng2)
    st_c2 = sample_syn(0.02508, max(NSYN // 2, 200), rng2)
    syn2 = build_Y([(rm_par, st_p2), (rm_cvt, st_c2)], scales, "syn-재시드")
    s2, _ = spectrum(syn2["Yfree"] * scales)
    r2 = int((s2 > s2[0] * 1e-7).sum())
    say(f"  (iii) 재샘플 rank: {r2} vs {r_free} → {'PASS' if r2 == r_free else 'FAIL'}")
    sp_only, _ = spectrum(Yfree_sc[:2 * st_p['N']])
    r_par_only = int((sp_only > sp_only[0] * 1e-7).sum())
    say(f"  l_i=30 단독 rank = {r_par_only} → CVT 스택 +{r_free - r_par_only} (평행사변형 축퇴 해소)")

    Q_, R_, piv = sqr(Yfree_sc, mode="economic", pivoting=True)
    pivots = piv[:r_free]
    deps = piv[r_free:]
    Bmat = np.linalg.lstsq(R_[:r_free, :r_free], R_[:r_free, r_free:], rcond=None)[0]
    say(f"\n  베이스 파라미터 (pivoted QR, {r_free}개) — 물리 단위 재그룹:")
    combos = []
    for k in range(r_free):
        pk = pivots[k]
        terms = [f"{PNAMES[pk]}"]
        for jj, dj in enumerate(deps):
            if abs(Bmat[k, jj]) > 0.02:
                c_phys = Bmat[k, jj] * scales[pk] / scales[dj]
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
            nf = np.linalg.norm(f)
            res = f - P_ @ (P_.T @ f)
            outv.append((fn, float(np.linalg.norm(res) / max(nf, 1e-12))))
        say(f"  {tagn}: " + "  ".join(f"{n}={val:.3f}" for n, val in outv))
        return outv

    fi_syn = fric_indep(np.vstack([Yfree_sc, Yst_sc]), "합성(rich, 자유+스탠스)")

    # ── [4] 실데이터 실용 식별성 ──
    say(f"\n[4] 실데이터 (fit 세션, SG win={SGWIN} poly=3, trial당 ≤{CAP_TRIAL}; 0324 제외)")
    say("  ★ 실측 발견: 전 fit-trial의 xlsx 기록이 이륙 3~9샘플 뒤 종료 — 비행 데이터 전무.")
    say("    → 실용 식별성은 스탠스 투영 행(접촉력 소거 1-DOF)으로 산출. 비행행 수 함께 보고.")
    groups_real, meas, meta, rms_429 = prep_real(SGWIN, CAP_TRIAL)
    for ds in ("jump_position_0421", "jump_0424", "jump_0602", "jump_0429"):
        ms = [m for m in meta if m[0] == ds]
        say(f"  {ds:22s}: trial {sum(1 for m in ms if m[2] > 0)}/{len(ms)} 사용, "
            f"스탠스샘플 {sum(m[2] for m in ms)}, 비행샘플 {sum(m[3] for m in ms)}")
    real = build_Y(groups_real, scales, "real")
    Yr = real["Yflt"]
    Yr_sc = Yr * scales
    s_r, Vt_r = spectrum(Yr_sc)
    kvis = int((s_r > NOISE).sum())
    kgood = int((s_r > 10 * NOISE).sum())
    say("  특이값 σ_i [Nm/스케일]: " + " ".join(f"{x:.2g}" for x in s_r[:min(24, len(s_r))]))
    say(f"  실용 rank: σ>{NOISE}Nm(불확실도<100%) → {kvis}개, σ>{10 * NOISE}Nm(<10%) → {kgood}개 "
        f"[구조 스탠스 r={r_st}, 자유∪스탠스 r={r_all}]")
    say(f"  GAP = 구조적으로 가능(자유∪스탠스 {r_all}) − 실데이터 가시({kvis}) = {r_all - kvis}개")

    say("  구조적(자유∪스탠스 아님, 스탠스투영 기저) 방향별 실데이터 σ:")
    for jj in range(r_st):
        vj = Vt_st[jj]
        lev = float(np.linalg.norm(Yr_sc @ vj))
        say(f"   S{jj + 1:02d} σ_syn={s_st[jj]:9.3g} → 실데이터 {lev:9.3g} Nm "
            f"[{'보임' if lev > NOISE else '노이즈 아래'}]  {pretty_combo(vj, PNAMES, 4)}")

    fi_real = fric_indep(Yr_sc, f"실데이터(관성스팬=σ>{NOISE}Nm)", thr_abs=NOISE)
    corr_check(real, meas)

    say(f"  SG 민감도 (win 7/11/15, cap {CAP_SENS}):")
    sens = {}
    for wn in (7, 11, 15):
        gr, _m2, _meta2, _ = prep_real(wn, CAP_SENS, rms_429)
        rr = build_Y(gr, scales, f"real-w{wn}")
        ss, _ = spectrum(rr["Yflt"] * scales)
        sens[wn] = ss
        say(f"   win={wn:2d}: σ1={ss[0]:.3g} σ5={ss[4]:.3g} σ10={ss[9]:.3g} "
            f"σ>{NOISE} → {int((ss > NOISE).sum())}개")
    d711 = np.abs(sens[7][:10] - sens[11][:10]) / sens[11][:10]
    d1511 = np.abs(sens[15][:10] - sens[11][:10]) / sens[11][:10]
    say(f"   top-10 σ 변화율: win7 max {100 * d711.max():.0f}% / win15 max {100 * d1511.max():.0f}%")

    # ── [5] fit 파라미터 → 식별 부분공간 매핑 ──
    say(f"\n[5] fit 파라미터 방향의 식별성 (실데이터 top-k 부분공간, k={kvis})")
    D = fit_directions()
    Vk = Vt_r[:kvis].T
    Vstruct = Vt_free[:r_free].T
    say(f"  {'param':10s} {'frac_real_topk':>14s} {'frac_struct(자유)':>16s} "
        f"{'leverage[Nm/sweep]':>18s}  판정")
    frac_tab = {}
    for (pn, wsw), dcol in zip(FITP, D.T):
        dth = dcol / scales
        nn = np.linalg.norm(dth)
        if nn < 1e-15:
            say(f"  {pn:10s} {'0 (죽은 나사)':>14s}  — TOTAL_MASS 모드에서 빌더가 "
                f"base 질량을 파생시켜 M_base 스케일은 문자 그대로 no-op")
            frac_tab[pn] = dict(frac_real=0.0, frac_struct=0.0, leverage=0.0, dead=True)
            continue
        dth_h = dth / nn
        fr = float(np.linalg.norm(Vk.T @ dth_h))
        fs = float(np.linalg.norm(Vstruct.T @ dth_h))
        lev = float(np.linalg.norm(Yr @ dcol)) * wsw
        tag = ("STICKER(널스페이스)" if fr < 0.35 else "약함" if fr < 0.7 else "OK")
        frac_tab[pn] = dict(frac_real=fr, frac_struct=fs, leverage=lev)
        say(f"  {pn:10s} {fr:14.3f} {fs:16.3f} {lev:18.3g}  {tag}")

    say("\n[6] fit-파라미터 공간 Fisher (열 = Y·d_p·sweep; σ>0.4Nm = 실데이터가 구분)")
    cols = np.column_stack([np.asarray(Yr @ D[:, i]) * FITP[i][1]
                            for i in range(len(FITP))])
    sf, Vf = np.linalg.svd(cols, full_matrices=False)[1:3]
    nfvis = int((sf > NOISE).sum())
    say("  σ [Nm/sweep]: " + " ".join(f"{x:.2g}" for x in sf))
    say(f"  15개 나사 중 실데이터가 실제로 구분하는 독립 방향: {nfvis}개")
    fitn = [p[0] for p in FITP]
    for jj in range(len(sf)):
        vis = "보임" if sf[jj] > NOISE else "노이즈 아래"
        say(f"   F{jj + 1:02d} σ={sf[jj]:8.3g} [{vis}]  {pretty_combo(Vf[jj], fitn, 4)}")

    res = dict(
        quick=QUICK, nsyn=NSYN, cap=CAP_TRIAL, noise=NOISE,
        pnames=PNAMES, scales=scales.tolist(),
        rank_struct_free=r_free, rank_struct_flight=r_flt,
        rank_struct_stance=r_st, rank_struct_all=r_all, rank_par_only=r_par_only,
        sv_struct_free=s_free.tolist(), sv_struct_stance=s_st.tolist(),
        sv_real=s_r.tolist(), k_vis=kvis, k_good=kgood,
        dead_cols=dead, base_combos=combos,
        fric_indep_syn={n: val for n, val in fi_syn},
        fric_indep_real={n: val for n, val in fi_real},
        fit_fracs=frac_tab, fisher_fit_sv=sf.tolist(),
        fisher_fit_V=[[float(x) for x in row] for row in Vf],
        fit_names=fitn, meta_trials=[list(m) for m in meta],
        sg_sens={str(w): sens[w][:12].tolist() for w in sens},
        report="\n".join(REPORT))
    safe.atomic_json_write(OUT_JSON, res)
    say(f"\n저장: {OUT_JSON}")
    say(f"총 {time.time() - t00:.0f}s")


if __name__ == "__main__":
    main()
