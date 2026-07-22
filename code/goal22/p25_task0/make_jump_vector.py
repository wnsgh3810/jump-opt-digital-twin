# -*- coding: utf-8 -*-
"""배포용 jump_vector — IK2 접근 궤적 + OL 최적화 점프 (사용자 파이프라인, 07-22).

카카오톡 예시 포맷 그대로 (7열): q_1, q_m, l_1, tau_1, tau_m, q_1_dot, q_m_dot
구조: [홈 hold] + [IK2 foot-z 베지어 접근 home→크라우치] + [크라우치 hold(정확한 OL 시작)] + [OL 점프]
매핑 (검증됨): q_1=hip · q_m=π+q2 (무변속 평행사변형 TR=1) · l_1=30 · tau_1=hip토크 · tau_m=knee토크
              q_1_dot=dq_hip · q_m_dot=dq_knee. 부호 뒤집기 없음.
접근구간은 위치만(속도·토크=0, 준정적) — 예시 규약 그대로.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
IKDIR = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/FKnIK")
sys.path.insert(0, str(IKDIR))
from IK2 import inverse_kinematics, q2_to_qm, generate_bezier_curve, rot_matrix  # noqa

DT = 0.002              # 예시와 동일 (500 Hz)
L, L_O, LI = 0.25, 0.03, 30.0   # 무변속 l_1=30mm
Q1_HOME_DEG, Q2_HOME_DEG = -45.0, -90.0    # 예시 홈 (q_1=-45°, q_m=90°)
HOLD_HOME_S = 1.2       # 홈 hold
APPROACH_S = 3.2        # 접근
HOLD_CROUCH_S = 0.6     # 크라우치 hold (OL 시작자세 정착)


def foot_z(q1_deg, q2_deg):
    q1r, q2r = np.radians(q1_deg), np.radians(q2_deg)
    p = rot_matrix(q1r) @ np.array([L, 0]) + rot_matrix(q1r + q2r) @ np.array([L, 0])
    return p[1]


def main():
    # ── OL 점프 계획 로드 (스탠스=이지까지) ──
    z = np.load(HERE / "t0nc_ol.npz")
    t = np.asarray(z["t"], float)
    m = t >= 0
    tt = t[m] - t[m][0]
    q1 = np.asarray(z["q1"], float)[m]
    q2 = np.asarray(z["q2"], float)[m]
    dq1 = np.asarray(z["dq1"], float)[m]
    dq2 = np.asarray(z["dq2"], float)[m]
    tn1 = np.asarray(z["tau1_nm"], float)[m]
    tn2 = np.asarray(z["tau2_nm"], float)[m]
    grf = np.asarray(z["grf"], float)[m]
    on = grf > 1.0
    idx = np.where((tt > 0.02) & ~on)[0]
    t_lo = float(tt[idx[0]]) if len(idx) else float(tt[-1])
    js = tt <= (t_lo + 0.01)          # 스탠스 + 이지 직후 살짝

    # OL 시작자세 (정확값)
    q1_start_deg = np.degrees(q1[0])
    q2_start_deg = np.degrees(q2[0])
    z_home = foot_z(Q1_HOME_DEG, Q2_HOME_DEG)
    z_crouch = foot_z(q1_start_deg, q2_start_deg)

    # ── 점프 계획을 DT로 리샘플 ──
    tj = tt[js]
    tj_new = np.arange(0, tj[-1] + DT / 2, DT)
    def rs(a):
        return np.interp(tj_new, tj, a[js])
    j_q1 = rs(q1)                       # rad (hip)
    j_qm = np.pi + rs(q2)              # rad (q_m = π + q2)
    j_tau1 = rs(tn1)                    # Nm (hip)
    j_taum = rs(tn2)                    # Nm (knee=crank, TR=1)
    j_q1d = rs(dq1)                     # rad/s
    j_qmd = rs(dq2)                     # rad/s (dq_m = dq2)
    n_jump = len(tj_new)

    # ── 홈 hold ──
    n_home = int(round(HOLD_HOME_S / DT))
    q1_home_r = np.radians(Q1_HOME_DEG)
    qm_home_r = np.radians(q2_to_qm(Q2_HOME_DEG, L, LI / 1000.0, L_O))   # = π/2

    # ── 접근 (관절공간 베지어: home → OL 정확 시작, q_m은 IK2 q2_to_qm) ──
    # 발끝-z 방식은 IK2의 x=0 가정 탓에 hip이 0.6° 어긋남(트윈≠IK2 모델차).
    # 관절공간 보간으로 접근 끝을 트윈 최적화 시작자세에 정확히 맞춤 (블렌드 없음).
    n_appr = int(round(APPROACH_S / DT))
    s = generate_bezier_curve(0.0, 0.0, 1.0, 1.0, n_appr)   # 0→1 부드러운 s-커브
    q1_start_rad = np.radians(q1_start_deg)
    q2_start_rad = np.radians(q2_start_deg)
    a_q1 = q1_home_r + (q1_start_rad - q1_home_r) * s
    a_q2 = np.radians(Q2_HOME_DEG) + (q2_start_rad - np.radians(Q2_HOME_DEG)) * s
    a_qm = np.array([np.radians(q2_to_qm(np.degrees(v), L, LI / 1000.0, L_O)) for v in a_q2])
    # 접근 끝 = 정확히 OL 시작 (q_m도 q2_to_qm이 점프 시작 q2를 그대로 변환)
    a_q1[-1] = j_q1[0]
    a_qm[-1] = j_qm[0]

    # ── 크라우치 hold (정확한 OL 시작) ──
    n_crh = int(round(HOLD_CROUCH_S / DT))

    # ── 조립 ──
    def block(n, q1v, qmv, t1=0.0, tm=0.0, q1d=0.0, qmd=0.0):
        return dict(q_1=np.full(n, q1v), q_m=np.full(n, qmv), l_1=np.full(n, LI),
                    tau_1=np.full(n, t1), tau_m=np.full(n, tm),
                    q_1_dot=np.full(n, q1d), q_m_dot=np.full(n, qmd))

    segs = []
    segs.append(block(n_home, q1_home_r, qm_home_r))                        # 홈 hold
    segs.append(dict(q_1=a_q1, q_m=a_qm, l_1=np.full(n_appr, LI),           # 접근 (위치만)
                     tau_1=np.zeros(n_appr), tau_m=np.zeros(n_appr),
                     q_1_dot=np.zeros(n_appr), q_m_dot=np.zeros(n_appr)))
    segs.append(block(n_crh, j_q1[0], j_qm[0]))                             # 크라우치 hold
    segs.append(dict(q_1=j_q1, q_m=j_qm, l_1=np.full(n_jump, LI),           # OL 점프 (FF+PD)
                     tau_1=j_tau1, tau_m=j_taum, q_1_dot=j_q1d, q_m_dot=j_qmd))

    cols = ["q_1", "q_m", "l_1", "tau_1", "tau_m", "q_1_dot", "q_m_dot"]
    df = pd.DataFrame({c: np.concatenate([s[c] for s in segs]) for c in cols})

    out = HERE / "jump_vector_OL_nocvt.xlsx"
    df.to_excel(out, index=False)
    N = len(df)
    print(f"저장: {out}  (총 {N}행, {N * DT:.2f}s @ {DT * 1000:.0f}ms)")
    print(f"  홈 hold {n_home}행({HOLD_HOME_S}s) + 접근 {n_appr}행({APPROACH_S}s) + "
          f"크라우치 hold {n_crh}행({HOLD_CROUCH_S}s) + 점프 {n_jump}행({n_jump*DT:.3f}s)")
    print(f"  홈: q_1={np.degrees(q1_home_r):+.1f}° q_m={np.degrees(qm_home_r):+.1f}° l_1={LI}")
    print(f"  OL 시작: q_1={np.degrees(j_q1[0]):+.1f}° q_m={np.degrees(j_qm[0]):+.1f}°")
    print(f"  점프 끝(이지): q_1={np.degrees(j_q1[-1]):+.1f}° q_m={np.degrees(j_qm[-1]):+.1f}°")
    print(f"  FF 범위: tau_1 [{j_tau1.min():+.2f},{j_tau1.max():+.2f}] tau_m [{j_taum.min():+.2f},{j_taum.max():+.2f}] Nm")
    print(f"  속도 범위: q_1_dot [{j_q1d.min():+.1f},{j_q1d.max():+.1f}] q_m_dot [{j_qmd.min():+.1f},{j_qmd.max():+.1f}] rad/s")
    # 연속성 체크
    print(f"  접근→크라우치 갭: q_1 {abs(a_q1[-1]-j_q1[0])*180/np.pi:.3f}° q_m {abs(a_qm[-1]-j_qm[0])*180/np.pi:.3f}°")


if __name__ == "__main__":
    main()
