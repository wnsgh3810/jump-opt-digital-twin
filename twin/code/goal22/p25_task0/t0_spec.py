# -*- coding: utf-8 -*-
"""P25-task0 캠페인 공용 제약 스펙 (사용자 지시 07-18: 제약은 AVT LEG task0 스크립트를 따름).

출처: C:/Users/junho/CVT/AVT LEG/optimization_tasks/task0_vertjump_{no,with}_cvt.py
- 토크 제약: |τ_axis| ≤ 15 Nm  → 트윈 raw 도메인 등가 박스 RAW15 = 25.5810
  (a_hat 운동방향 가지 정확히 15.00 Nm — 18Nm→31.1771과 동일 규약, brentq 역산)
- 모터 T-N 포락선: |dq_j| ≤ TN_COEF·|τ̂_j| + TN_OFF   (모터별; CVT는 크랭크측)
- 속도 제약: |dq| ≤ 50 rad/s
- 각도 제약 (측정 규약 = AVT 규약, 수치 그대로):
  q1 ∈ [−72°, −17°] / no_cvt q2(무릎≈크랭크, l_i=30) ∈ [−146°, −36°] / with_cvt qm ∈ [−169°, −2.9°]
- 스탠스 시간 ≤ 0.3 s (감사)
- 시작: 정지 + 정적 웅크림 (q0는 바운드 내 자유 — task0과 동일하게 최적화 대상)
"""
import numpy as np

RAW15 = 25.5810                    # |â_motoring| = 15.00 Nm
TN_COEF, TN_OFF = -0.731019, 48.476878
DQ_LIM = 50.0
Q1_LB, Q1_UB = -1.2566, -0.2967    # [-72°, -17°]
Q2_LB, Q2_UB = -2.5482, -0.6283    # [-146°, -36°]  (no_cvt)
QM_LB, QM_UB = -2.95, -0.05        # [-169°, -2.9°] (with_cvt 크랭크)
T_ST_MAX = 0.3
L1 = L2 = 0.25                     # AVT 링크 길이 (스틱피겨/z_kin 규약)


def tn_gap(dq, ah):
    """T-N 포락선 위반량 [rad/s] (양수 = 위반). 벡터."""
    lim = TN_COEF * np.abs(np.asarray(ah, float)) + TN_OFF
    return np.abs(np.asarray(dq, float)) - lim


def audit(L, t_end=0.6, cvt=False):
    """롤아웃 로그 → 제약 감사 dict (max 위반량; 전부 ≤0이면 통과).
    L 키: t/q1/q2/dq1/dq2/sh1/sh2 (â Nm). 커맨드 창(t≤t_end)만 검사."""
    m = (L["t"] >= 0) & (L["t"] <= t_end)
    q2lb, q2ub = (QM_LB, QM_UB) if cvt else (Q2_LB, Q2_UB)
    out = dict(
        tau_hip=float(np.max(np.abs(L["sh1"][m])) - 15.0),
        tau_knee=float(np.max(np.abs(L["sh2"][m])) - 15.0),
        tn_hip=float(np.max(tn_gap(L["dq1"][m], L["sh1"][m]))),
        tn_knee=float(np.max(tn_gap(L["dq2"][m], L["sh2"][m]))),
        dq_hip=float(np.max(np.abs(L["dq1"][m])) - DQ_LIM),
        dq_knee=float(np.max(np.abs(L["dq2"][m])) - DQ_LIM),
        q1_lo=float(Q1_LB - np.min(L["q1"][m])),
        q1_hi=float(np.max(L["q1"][m]) - Q1_UB),
        q2_lo=float(q2lb - np.min(L["q2"][m])),
        q2_hi=float(np.max(L["q2"][m]) - q2ub),
    )
    out["pass"] = bool(all(v <= 1e-6 for k, v in out.items() if k != "pass"))
    return out


def penalty(L, t_end=0.6, cvt=False, w_tn=50.0, w_dq=50.0, w_q=500.0):
    """최적화용 소프트 페널티 (감사와 같은 정의역, 제곱합)."""
    m = (L["t"] >= 0) & (L["t"] <= t_end)
    q2lb, q2ub = (QM_LB, QM_UB) if cvt else (Q2_LB, Q2_UB)
    p = 0.0
    for dq, ah in ((L["dq1"][m], L["sh1"][m]), (L["dq2"][m], L["sh2"][m])):
        p += w_tn * float(np.sum(np.maximum(0.0, tn_gap(dq, ah)) ** 2)) / max(m.sum(), 1)
        p += w_dq * float(np.sum(np.maximum(0.0, np.abs(dq) - DQ_LIM) ** 2)) / max(m.sum(), 1)
    for q, lb, ub in ((L["q1"][m], Q1_LB, Q1_UB), (L["q2"][m], q2lb, q2ub)):
        p += w_q * float(np.sum(np.maximum(0.0, lb - q) ** 2 + np.maximum(0.0, q - ub) ** 2)) / max(m.sum(), 1)
    return p
