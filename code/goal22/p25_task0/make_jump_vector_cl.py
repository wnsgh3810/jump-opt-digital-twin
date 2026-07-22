# -*- coding: utf-8 -*-
"""배포용 jump_vector (순수 PD, CL-CMA) — IK2 접근 + CL 미끼 명령 (07-22).

실기 하드웨어 = 순수 PD (q_des·dq_des만, FF 없음). CL-CMA는 q_des 미끼를 폐루프
PD가 점프로 만드는 최적화라 이 채널에 딱 맞음. 소스 = t0nc_cl_pd15.npz
(★클립 35.5=배포동일 + 15Nm 페널티단독 재최적 → 배포가 진짜 ≤15Nm 재현).

카카오톡 예시 포맷 7열: q_1, q_m, l_1, tau_1, tau_m, q_1_dot, q_m_dot
매핑: q_1=미끼 hip 명령(qd1) · q_m=π+qd2(무변속 TR=1) · l_1=30 · tau=0(순수 PD, FF 없음)
      q_1_dot=dqd1 · q_m_dot=dqd2. 부호 뒤집기 없음.
구조: [홈 hold] + [IK2 관절공간 접근 home→크라우치(=미끼 시작 q0)] + [크라우치 hold] + [CL 점프]
★로봇 게인 = 150/2.2/500/4 (hip_kp/kd, knee_kp/kd) — 파일엔 없음, 로봇에 별도 입력.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
IKDIR = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/FKnIK")
sys.path.insert(0, str(IKDIR))
from IK2 import q2_to_qm, generate_bezier_curve, rot_matrix  # noqa

SRC = "t0nc_cl_pd15.npz"
GAIN_STR = "150 / 2.2 / 500 / 4  (hip_kp/kd, knee_kp/kd)"
DT = 0.002
L, L_O, LI = 0.25, 0.03, 30.0
Q1_HOME_DEG, Q2_HOME_DEG = -45.0, -90.0
HOLD_HOME_S = 1.2
APPROACH_S = 3.2
HOLD_CROUCH_S = 0.6


def foot_z(q1_deg, q2_deg):
    q1r, q2r = np.radians(q1_deg), np.radians(q2_deg)
    p = rot_matrix(q1r) @ np.array([L, 0]) + rot_matrix(q1r + q2r) @ np.array([L, 0])
    return p[1]


def main():
    # ── CL 계획 로드 (미끼 명령 qd + 물리 grf로 이지 검출) ──
    z = np.load(HERE / SRC)
    t = np.asarray(z["t"], float)
    m = t >= 0
    tt = t[m] - t[m][0]
    qd1 = np.asarray(z["qd1"], float)[m]      # 미끼 hip 명령
    qd2 = np.asarray(z["qd2"], float)[m]      # 미끼 knee 명령
    dqd1 = np.asarray(z["dqd1"], float)[m]
    dqd2 = np.asarray(z["dqd2"], float)[m]
    grf = np.asarray(z["grf"], float)[m]
    on = grf > 1.0
    idx = np.where((tt > 0.02) & ~on)[0]
    t_lo = float(tt[idx[0]]) if len(idx) else float(tt[-1])
    js = tt <= (t_lo + 0.01)                  # 스탠스 + 이지 직후 살짝 (비행 미끼 미포함)

    # ── 점프 명령을 DT로 리샘플 ──
    tj = tt[js]
    tj_new = np.arange(0, tj[-1] + DT / 2, DT)

    def rs(a):
        return np.interp(tj_new, tj, a[js])

    j_q1 = rs(qd1)                             # rad (미끼 hip 명령)
    j_qm = np.pi + rs(qd2)                    # rad (q_m = π + qd2, 무변속 TR=1)
    j_q1d = rs(dqd1)                           # rad/s
    j_qmd = rs(dqd2)                           # rad/s
    n_jump = len(tj_new)

    # 크라우치(=미끼 시작 = q0) 정확값
    q1_start_deg = np.degrees(qd1[0])
    q2_start_deg = np.degrees(qd2[0])

    # ── 홈 hold ──
    n_home = int(round(HOLD_HOME_S / DT))
    q1_home_r = np.radians(Q1_HOME_DEG)
    qm_home_r = np.radians(q2_to_qm(Q2_HOME_DEG, L, LI / 1000.0, L_O))   # = π/2

    # ── 접근 (관절공간 베지어: home → 미끼 시작, q_m은 IK2 q2_to_qm) ──
    n_appr = int(round(APPROACH_S / DT))
    s = generate_bezier_curve(0.0, 0.0, 1.0, 1.0, n_appr)
    a_q1 = q1_home_r + (np.radians(q1_start_deg) - q1_home_r) * s
    a_q2 = np.radians(Q2_HOME_DEG) + (np.radians(q2_start_deg) - np.radians(Q2_HOME_DEG)) * s
    a_qm = np.array([np.radians(q2_to_qm(np.degrees(v), L, LI / 1000.0, L_O)) for v in a_q2])
    a_q1[-1] = j_q1[0]                          # 접근 끝 = 정확히 미끼 시작
    a_qm[-1] = j_qm[0]

    # ── 크라우치 hold ──
    n_crh = int(round(HOLD_CROUCH_S / DT))

    def block(n, q1v, qmv, q1d=0.0, qmd=0.0):
        return dict(q_1=np.full(n, q1v), q_m=np.full(n, qmv), l_1=np.full(n, LI),
                    tau_1=np.zeros(n), tau_m=np.zeros(n),
                    q_1_dot=np.full(n, q1d), q_m_dot=np.full(n, qmd))

    segs = []
    segs.append(block(n_home, q1_home_r, qm_home_r))                     # 홈 hold
    segs.append(dict(q_1=a_q1, q_m=a_qm, l_1=np.full(n_appr, LI),        # 접근 (위치만)
                     tau_1=np.zeros(n_appr), tau_m=np.zeros(n_appr),
                     q_1_dot=np.zeros(n_appr), q_m_dot=np.zeros(n_appr)))
    segs.append(block(n_crh, j_q1[0], j_qm[0]))                          # 크라우치 hold
    segs.append(dict(q_1=j_q1, q_m=j_qm, l_1=np.full(n_jump, LI),        # CL 점프 (순수 PD, tau=0)
                     tau_1=np.zeros(n_jump), tau_m=np.zeros(n_jump),
                     q_1_dot=j_q1d, q_m_dot=j_qmd))

    cols = ["q_1", "q_m", "l_1", "tau_1", "tau_m", "q_1_dot", "q_m_dot"]
    df = pd.DataFrame({c: np.concatenate([s[c] for s in segs]) for c in cols})

    out = HERE / "jump_vector_CL_nocvt_pd.xlsx"
    df.to_excel(out, index=False)
    N = len(df)
    print(f"저장: {out}  (총 {N}행, {N * DT:.2f}s @ {DT * 1000:.0f}ms)")
    print(f"  ★ 순수 PD — tau 열 전부 0 (FF 없음). 로봇 게인 = {GAIN_STR}")
    print(f"  ★ q_1/q_m = CL 미끼 명령 (로봇이 PD로 추종 → 점프). 소스 {SRC}")
    print(f"  홈 hold {n_home}행({HOLD_HOME_S}s) + 접근 {n_appr}행({APPROACH_S}s) + "
          f"크라우치 hold {n_crh}행({HOLD_CROUCH_S}s) + 점프 {n_jump}행({n_jump*DT:.3f}s)")
    print(f"  홈: q_1={np.degrees(q1_home_r):+.1f}° q_m={np.degrees(qm_home_r):+.1f}° l_1={LI}")
    print(f"  크라우치(미끼시작): q_1={q1_start_deg:+.1f}° q_m={np.degrees(j_qm[0]):+.1f}°")
    print(f"  점프 끝(이지+): q_1={np.degrees(j_q1[-1]):+.1f}° q_m={np.degrees(j_qm[-1]):+.1f}°")
    print(f"  미끼 q_1 범위: [{np.degrees(j_q1).min():+.1f},{np.degrees(j_q1).max():+.1f}]° "
          f"q_m [{np.degrees(j_qm).min():+.1f},{np.degrees(j_qm).max():+.1f}]°")
    print(f"  속도 범위: q_1_dot [{j_q1d.min():+.1f},{j_q1d.max():+.1f}] q_m_dot [{j_qmd.min():+.1f},{j_qmd.max():+.1f}] rad/s (≤50)")
    print(f"  접근→크라우치 갭: q_1 {abs(a_q1[-1]-j_q1[0])*180/np.pi:.3f}° q_m {abs(a_qm[-1]-j_qm[0])*180/np.pi:.3f}°")


if __name__ == "__main__":
    main()
