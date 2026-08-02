# -*- coding: utf-8 -*-
"""make_sysid_air — 마라톤G Phase1: **공중 시스템 동정용 명령 궤적** 생성.

목적: 발을 지면에서 뗀(매달린) 상태에서 힙/무릎을 사인 가진해
      **M(관성)·C·G(중력 레버)·관절 마찰**을 한 번에 실측 식별한다.

왜 이 형태인가 (마라톤G 발견 반영)
  - G1-F2: 정적 공중 데이터는 신호 0.34Nm < 잡음 0.4Nm 로 **판별력 0**.
           동적 가진은 τ_inertia = I·q̈ 가 진동수의 **제곱**으로 커진다 (3Hz·12°에서 ≈3Nm) → SNR 해결.
  - 사용자 지적: 무동력 매달림은 backdrivability로 **무릎이 풀리고** 정지각이 매번 다르다.
           → 모터를 켜고 가진하면 무릎은 PD가 붙잡고, 관절이 계속 움직여 **정지마찰이 걸릴 틈이 없다**.
  - 관성은 정적 데이터로 원리상 식별 불가 (멈춘 물체는 관성을 드러내지 않음) → 동적 가진이 유일한 길.

파일 규약 (`jump_vector_CL_nocvt_pd_v8.xlsx` 미러, 500Hz)
  q_1 [rad] 힙 목표각 (기립 −0.785398 = −45°) · q_m [rad] 모터측 목표각 = **−q2** (기립 +1.570796)
  l_1 [mm] CVT 링크 길이 (무변속 30) · tau_1/tau_m 피드포워드 토크 (0 = 순수 PD)
  q_1_dot / q_m_dot [rad/s] 목표 속도 (dq_des 인가 — 0424 이후 세션과 동일 규약)

안전 범위 (점프 궤적 v8 실측 가동역 안에서만 설계)
  q_m 60.1~128.2° (=q2 −60~−128°) · q_1 −64.6~−17.5°  → 본 궤적은 q_m 62~126°, q_1 −57~−33°.
CLI: python make_sysid_air.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
FS = 500.0
DT = 1.0 / FS
Q1_HOME = np.radians(-45.0)          # 기립 자세 (파일 규약 시작점)
QM_HOME = np.radians(90.0)
A1_HOME = np.radians(-45.0)          # 힙 가진 중심 = 기립 각도

# 무릎 시험 각도 (모터측 q_m). q2 = −q_m. 판별력은 펼수록 커짐(70°) → 3점으로 스팬.
# 무릎 가진 진폭(±8°)까지 더해도 점프 가동역(60.1~128.2°) 안에 들도록 중심을 잡았다.
KNEES = [("k070", 70.0), ("k095", 95.0), ("k118", 118.0)]

# 힙 가진: (진동수 Hz, 진폭 deg, 사이클 수).
#   1Hz에서 진폭 2종 = **쿨롱 마찰(진폭 무관) vs 점성(진폭 비례)** 분리용.
#   3Hz = 관성 항 최대화 (τ_I = I·A·(2πf)² → 진동수 제곱).
HIP_SEGS = [(1.0, 12.0, 4), (1.0, 6.0, 4), (2.0, 12.0, 6), (3.0, 8.0, 9)]
# 무릎 가진 (힙 고정): 종아리·크랭크쪽 관성 분리용
KNEE_SEGS = [(2.0, 8.0, 6), (3.0, 5.0, 9)]
HOLD = 0.3             # 구간 사이 정지 (구간 경계 식별용 마커 겸용)


def _smoothstep(n):
    """0→1 최소저크형 (양 끝 속도 0) — 구간 이음매에서 속도 불연속 방지."""
    s = np.linspace(0.0, 1.0, n)
    return s * s * (3.0 - 2.0 * s)


def hold(q1, qm, sec):
    n = int(round(sec * FS))
    return (np.full(n, q1), np.full(n, qm), np.zeros(n), np.zeros(n))


def ramp(q1a, qma, q1b, qmb, sec):
    n = int(round(sec * FS))
    w = _smoothstep(n)
    q1 = q1a + (q1b - q1a) * w
    qm = qma + (qmb - qma) * w
    return (q1, qm, np.gradient(q1, DT), np.gradient(qm, DT))


def sine(center1, centerm, f, amp_deg, cycles, on="hip"):
    """양 끝 1사이클에 레이즈드코사인 포락선 → 위치·속도 모두 연속. 해석은 실측 q,dq,ddq로 하므로
    포락선이 있어도 식별에 지장 없다 (안전을 위한 처리)."""
    n = int(round(cycles / f * FS))
    t = np.arange(n) * DT
    A = np.radians(amp_deg)
    ramp_n = int(round(1.0 / f * FS))
    env = np.ones(n)
    r = 0.5 * (1 - np.cos(np.pi * np.linspace(0, 1, ramp_n)))
    env[:ramp_n] = r
    env[-ramp_n:] = r[::-1]
    x = A * env * np.sin(2 * np.pi * f * t)
    dx = np.gradient(x, DT)
    if on == "hip":
        return (center1 + x, np.full(n, centerm), dx, np.zeros(n))
    return (np.full(n, center1), centerm + x, np.zeros(n), dx)


def build(qm_deg):
    qm = np.radians(qm_deg)
    P = [hold(Q1_HOME, QM_HOME, 1.0),
         ramp(Q1_HOME, QM_HOME, A1_HOME, qm, 2.0),
         hold(A1_HOME, qm, 1.0)]
    for f, a, c in HIP_SEGS:
        P.append(sine(A1_HOME, qm, f, a, c, "hip"))
        P.append(hold(A1_HOME, qm, HOLD))
    for f, a, c in KNEE_SEGS:
        P.append(sine(A1_HOME, qm, f, a, c, "knee"))
        P.append(hold(A1_HOME, qm, HOLD))
    P.append(ramp(A1_HOME, qm, Q1_HOME, QM_HOME, 2.0))
    P.append(hold(Q1_HOME, QM_HOME, 1.0))
    q1 = np.concatenate([p[0] for p in P]); qmv = np.concatenate([p[1] for p in P])
    d1 = np.concatenate([p[2] for p in P]); dm = np.concatenate([p[3] for p in P])
    return pd.DataFrame({"q_1": q1, "q_m": qmv, "l_1": 30, "tau_1": 0, "tau_m": 0,
                         "q_1_dot": d1, "q_m_dot": dm})


def main():
    print("공중 시스템 동정 명령 궤적 (500Hz, dq_des 인가, tau_ff=0)\n")
    print(f"{'파일':<34} {'행':>7} {'길이[s]':>8} {'q_1[°]':>16} {'q_m[°]':>16} "
          f"{'|dq1|max':>9} {'|dqm|max':>9}")
    for tag, qm_deg in KNEES:
        df = build(qm_deg)
        f = HERE / f"sysid_air_{tag}_v1.xlsx"
        df.to_excel(f, index=False)
        q1d = np.degrees(df["q_1"].values); qmd = np.degrees(df["q_m"].values)
        print(f"{f.name:<34} {len(df):7d} {len(df)/FS:8.2f} "
              f"{f'{q1d.min():.1f}~{q1d.max():.1f}':>16} {f'{qmd.min():.1f}~{qmd.max():.1f}':>16} "
              f"{np.abs(df['q_1_dot']).max():9.2f} {np.abs(df['q_m_dot']).max():9.2f}")
    print("\n안전 확인: 점프 궤적 v8 가동역 = q_1 −64.6~−17.5° / q_m 60.1~128.2°")


if __name__ == "__main__":
    main()
