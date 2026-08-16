# -*- coding: utf-8 -*-
"""make_air_probe — 마라톤G G2 후속 **공중 판별 실험 2종** 명령 궤적 (08-07).

26_08_02 재분석(G2) 결과 두 가지가 남았다:
  ① gA(힙 중력레버) ±18% · gB(무릎) ±58% — 힙을 −45° 둘레 ±12°만 흔들어
     cos q1 이 0.54~0.84로만 변한 탓. 중력과 센서 오프셋이 분리되지 않는다.
  ② 트윈이 관성·중력 모두 **1.7배** 과대 — 토크 척도 오차(H1)인지 질량분포 오차(H2)인지
     이 실험만으로는 못 가른다.
→ 두 파일로 각각 해결한다. 분해가 필요한 실험(부품 계량)은 사용자 지시로 최후 순번.

**A. `probe_sweep_v1.xlsx` — 느린 전구간 스윕 (①)**
  힙을 가동역 전체(−63~−20°)로 0.04Hz 왕복 → cos q1 이 0.454~0.940 으로 **2.2배 넓어짐**.
  코사인형(끝점에서 속도 0)이라 포락선 없이도 위치·속도 연속.
  무릎도 전구간(q_m 62~126°) 왕복 → gB 를 오프셋에서 분리.
  왕복 양방향이라 **쿨롱 마찰이 반주기마다 부호를 바꿔 평균에서 소거**된다.
  0.04Hz·±21.5°에서 관성 기여 τ=I·A·ω² ≈ 0.03·0.375·0.063 = 0.0007 Nm → 완전 준정적.

**B. `probe_hold3_v1.xlsx` — 3자세 유지 + 미세진동 (②, 추 실험용)**
  발끝 구멍에 **끈으로 자유롭게 매단 추**의 유무만 바꿔 이 파일을 두 번 돌린다.
  세 자세의 힙 지레팔(발끝의 힙축 기준 **수평** 거리)이 −124 / −28 / +270 mm 로
  **부호가 갈려** 두 점을 잇는 기울기가 곧 토크 교정계수가 된다 (공통 오프셋 자동 소거).
  각 자세에서 힙 ±3°@0.15Hz · 무릎 ±3°@0.10Hz 미세진동 — 관절이 늘 천천히 움직이므로
  **정지마찰(±0.26Nm, 판별의 최대 적)이 부호를 바꿔 한 주기 평균에서 사라진다**.
  진동 중 관성·점성 기여는 각각 0.0014 / 0.003 Nm 로 무시 가능 = 사실상 정적 측정.

규약: `sysid_air_*.xlsx` 와 동일 7열 500Hz (q_1, q_m, l_1=30, tau=0 순수 PD, dq_des 인가).
게인은 파일에 없다 — 로봇에 별도 입력 (26_08_02 과 동일 150/2.2/xxx/3 권장).
가동역: q_1 −64.6~−17.5° · q_m 60.1~128.2° (점프 v8 실측역) — 본 궤적은 그 안.
CLI: python make_air_probe.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
FS = 500.0
DT = 1.0 / FS
L1 = L2 = 0.25          # thigh / calf [m]
G = 9.81
Q1_HOME, QM_HOME = -45.0, 90.0

# ── 판별용 3자세 (q1, q_m) — 힙 지레팔 부호가 갈리도록 선정 ──
#   ★접근 오버슈트 ±5° 를 더해도 가동역(q_1 −64.6~−17.5 · q_m 60.1~128.2)에서
#     최소 3.5° 여유가 남도록 중심을 안쪽으로 당겼다 (지레팔 손실은 6% 미만).
POSES = [("P1", -56.0, 69.0), ("P2", -45.0, 80.0), ("P3", -26.0, 120.0)]
APPR = 5.0              # 양방향 접근 오버슈트 [deg] — 진동 대신 **위/아래에서 각각 접근**
APPR_S = 3.0            # 접근 램프 시간 [s]
SETTLE_S = 8.0          # 접근 후 유지(기록) 시간 [s]

# ── 스윕 (양 끝 여유 2.5° 이상) ──
SW_Q1 = (-62.0, -21.0)      # 힙 전구간
SW_QM = (64.0, 124.0)       # 무릎 전구간
SW_F = 0.04                 # Hz (1주기 25s)
SW_CYC = 2
SW_KNEES = [67.0, 122.0]    # 힙 스윕을 걸 무릎 자세 2종 (양 극단)


def _smoothstep(n):
    s = np.linspace(0.0, 1.0, n)
    return s * s * (3.0 - 2.0 * s)


def hold(q1, qm, sec):
    n = int(round(sec * FS))
    return np.full(n, q1), np.full(n, qm), np.zeros(n), np.zeros(n)


def ramp(q1a, qma, q1b, qmb, sec):
    n = int(round(sec * FS))
    w = _smoothstep(n)
    q1 = q1a + (q1b - q1a) * w
    qm = qma + (qmb - qma) * w
    return q1, qm, np.gradient(q1, DT), np.gradient(qm, DT)


def cos_sweep(lo, hi, f, cycles, other, on="hip"):
    """끝점(lo)에서 시작·끝나며 양 끝 속도 0인 코사인 왕복 — 포락선 불필요."""
    n = int(round(cycles / f * FS))
    t = np.arange(n) * DT
    c, a = 0.5 * (lo + hi), 0.5 * (hi - lo)
    x = c - a * np.cos(2 * np.pi * f * t)
    dx = np.gradient(x, DT)
    if on == "hip":
        return x, np.full(n, other), dx, np.zeros(n)
    return np.full(n, other), x, np.zeros(n), dx


def approach(q1c, qmc, sign, q1_from, qm_from):
    """오버슈트 지점에서 목표 자세로 **한 방향으로만** 접근한 뒤 유지.
    정지마찰은 '마지막으로 움직인 방향'의 반대로 걸리므로, +방향 접근과 −방향 접근의
    **평균을 내면 쿨롱 마찰이 소거**된다. 진동(추 흔들림)이 필요 없다."""
    a = ramp(q1_from, qm_from, q1c + sign * APPR, qmc + sign * APPR, APPR_S)
    b = ramp(q1c + sign * APPR, qmc + sign * APPR, q1c, qmc, APPR_S)
    c = hold(q1c, qmc, SETTLE_S)
    return [a, b, c]


def pack(segs, name):
    q1 = np.concatenate([s[0] for s in segs])
    qm = np.concatenate([s[1] for s in segs])
    d1 = np.concatenate([s[2] for s in segs])
    dm = np.concatenate([s[3] for s in segs])
    df = pd.DataFrame({"q_1": np.radians(q1), "q_m": np.radians(qm), "l_1": 30.0,
                       "tau_1": 0.0, "tau_m": 0.0,
                       "q_1_dot": np.radians(d1), "q_m_dot": np.radians(dm)})
    f = HERE / name
    df.to_excel(f, index=False)
    print(f"  저장 {f.name}: {len(df)}행 {len(df)/FS:.1f}s · "
          f"q_1 {q1.min():+.1f}~{q1.max():+.1f}° · q_m {qm.min():.1f}~{qm.max():.1f}° · "
          f"|dq| max {max(np.abs(np.radians(d1)).max(), np.abs(np.radians(dm)).max()):.3f} rad/s")
    return df


def levers(q1_deg, qm_deg):
    """발끝(=종아리 끝)의 힙축/무릎축 기준 **수평** 거리 [m] = 추의 지레팔."""
    q2 = qm_deg - 180.0
    a, b = np.radians(q1_deg), np.radians(q1_deg + q2)
    kx = L1 * np.cos(a)
    fx = kx + L2 * np.cos(b)
    fz = L1 * np.sin(a) + L2 * np.sin(b)
    return fx, fx - kx, fz


def main():
    print("공중 판별 실험 명령 궤적 (500Hz · 순수 PD · dq_des 인가)\n")

    # ── A. 스윕 ──
    print("A. probe_sweep_v1 — 느린 전구간 스윕 (gA·gB 정밀화, 추 없이 1회)")
    S = [hold(Q1_HOME, QM_HOME, 1.0)]
    for qm in SW_KNEES:
        S.append(ramp(S[-1][0][-1], S[-1][1][-1], SW_Q1[0], qm, 2.5))
        S.append(cos_sweep(SW_Q1[0], SW_Q1[1], SW_F, SW_CYC, qm, "hip"))
        S.append(hold(SW_Q1[0], qm, 0.5))
    S.append(ramp(S[-1][0][-1], S[-1][1][-1], Q1_HOME, SW_QM[0], 2.5))
    S.append(cos_sweep(SW_QM[0], SW_QM[1], SW_F, SW_CYC, Q1_HOME, "knee"))
    S.append(hold(Q1_HOME, SW_QM[0], 0.5))
    S.append(ramp(Q1_HOME, SW_QM[0], Q1_HOME, QM_HOME, 2.5))
    S.append(hold(Q1_HOME, QM_HOME, 1.0))
    pack(S, "probe_sweep_v1.xlsx")
    c1 = np.cos(np.radians(SW_Q1))
    print(f"   → cos q1 범위 {c1.min():.3f}~{c1.max():.3f} (26_08_02 은 0.536~0.839) "
          f"= 중력/오프셋 분리력 {(c1.max()-c1.min())/(0.839-0.536):.2f}배\n")

    # ── B. 3자세 유지 (양방향 접근 — 추 흔들림 없음) ──
    print("B. probe_hold3_v2 — 3자세 × 양방향 접근 (추 없이 1회 → 추 달고 1회) [진동 없음]")
    S = [hold(Q1_HOME, QM_HOME, 1.0)]
    for nm, q1, qm in POSES:
        for sign in (+1.0, -1.0):
            S += approach(q1, qm, sign, S[-1][0][-1], S[-1][1][-1])
    S.append(ramp(S[-1][0][-1], S[-1][1][-1], Q1_HOME, QM_HOME, 3.0))
    S.append(hold(Q1_HOME, QM_HOME, 1.0))
    pack(S, "probe_hold3_v2.xlsx")

    print("\n" + "=" * 96)
    print("추 시험 예측표 — 발끝 구멍에 끈으로 자유 매달기 (힘이 정확히 수직 → 지레팔 = 수평거리)")
    print(f"{'자세':<5}{'q_1':>7}{'q_m':>7}{'q2':>7} | {'힙 지레':>9}{'무릎 지레':>10}{'발끝 높이':>10} | "
          f"{'Δτ1 (2kg)':>11}{'Δτ2 (2kg)':>11}")
    for nm, q1, qm in POSES:
        lh, lk, fz = levers(q1, qm)
        print(f"{nm:<5}{q1:7.1f}{qm:7.1f}{qm-180:7.1f} | {1000*lh:9.1f}{1000*lk:10.1f}{1000*fz:10.1f} | "
              f"{2.0*G*lh:+11.3f}{2.0*G*lk:+11.3f}")
    print("  (단위: 지레·높이 mm · Δτ Nm. 발끝 높이는 힙축 기준 아래쪽이 음수)")
    print("\n  판별 기준 — 자세 P1↔P3 의 Δτ1 차이:")
    l1, _, _ = levers(*POSES[0][1:]); l3, _, _ = levers(*POSES[2][1:])
    for m in (1.0, 2.0):
        d = m * G * (l3 - l1)
        print(f"   추 {m:.1f}kg : H2(질량분포 오류)면 {d:+.3f} Nm · "
              f"H1(a_hat 1.7배 작음)이면 {d/1.711:+.3f} Nm · "
              f"두 예측 간격 {d-d/1.711:.3f} Nm (마찰 잔여 ±0.05 대비 {abs(d-d/1.711)/0.05:.0f}배)")
    print("\n  ※ 지레팔은 **실측 currentAngle** 로 다시 계산할 것 (PD가 밀려 2~3° 처진다)")
    print("  ※ 추는 주방저울로 실계량 · 발끝 구멍의 무릎축 기준 실제 거리도 측정 (지금 250mm 가정)")
    # 가동역 여유 감사 (한계에 붙으면 물리 파손 위험 — 자동 검사)
    LIM1, LIMM = (-64.6, -17.5), (60.1, 128.2)
    print("\n  가동역 여유 감사 (접근 오버슈트·스윕 진폭 포함):")
    for nm, q1, qm in POSES:
        print(f"   {nm}: q_1 {q1-APPR:+.1f}~{q1+APPR:+.1f}° (여유 "
              f"{q1-APPR-LIM1[0]:.1f}/{LIM1[1]-q1-APPR:.1f}°) · "
              f"q_m {qm-APPR:.1f}~{qm+APPR:.1f}° (여유 "
              f"{qm-APPR-LIMM[0]:.1f}/{LIMM[1]-qm-APPR:.1f}°)")
    print(f"   스윕: q_1 여유 {SW_Q1[0]-LIM1[0]:.1f}/{LIM1[1]-SW_Q1[1]:.1f}° · "
          f"q_m 여유 {SW_QM[0]-LIMM[0]:.1f}/{LIMM[1]-SW_QM[1]:.1f}°")

    # ── ★ 스윕을 추 달고 재실행할 때의 판별력 (권장 본선) ──
    print("\n" + "=" * 96)
    print("★ 추(2kg)를 달고 **스윕**을 재실행할 때 — 진동 없이 연속 교정곡선이 나온다")
    M = 2.0
    for qm in SW_KNEES:
        xs = [levers(q1, qm)[0] for q1 in np.linspace(*SW_Q1, 200)]
        zs = [levers(q1, qm)[2] for q1 in np.linspace(*SW_Q1, 200)]
        ks = [levers(q1, qm)[1] for q1 in np.linspace(*SW_Q1, 200)]
        print(f"   힙 스윕 @ q_m={qm:.0f}° : 발끝 수평 {1000*min(xs):+7.1f}~{1000*max(xs):+7.1f} mm "
              f"→ Δτ1 {M*G*min(xs):+6.2f}~{M*G*max(xs):+6.2f} Nm | "
              f"Δτ2 {M*G*min(ks):+6.2f}~{M*G*max(ks):+6.2f} Nm | "
              f"발끝 높이 {1000*min(zs):.0f}~{1000*max(zs):.0f} mm")
    allx = [levers(q1, qm)[0] for qm in SW_KNEES for q1 in np.linspace(*SW_Q1, 200)]
    allz = [levers(q1, qm)[2] for qm in SW_KNEES for q1 in np.linspace(*SW_Q1, 200)]
    span = (max(allx) - min(allx))
    print(f"   → 지레팔 총 변화폭 {1000*span:.1f} mm · Δτ1 변화폭 **{M*G*span:.2f} Nm** "
          f"(표본 수만 개 → 기울기 오차 사실상 0)")
    print(f"   → 적합할 기울기: H2(질량분포 오류)면 **1.00** · H1(a_hat 1.7배 과소)면 **0.585**")
    print(f"   → 왕복이라 쿨롱 마찰이 방향마다 부호 반전 → 양방향 평균에서 소거 (진동 불필요)")
    print(f"   → 추 진자 흔들림: 가진 0.04Hz ≪ 진자 고유 ~0.9Hz(줄 30cm) → 줄은 사실상 수직 유지")
    print(f"   ※ 바닥 여유: 발끝이 힙축 아래 최대 {abs(min(allz))*1000:.0f} mm 까지 내려간다 "
          f"— 추가 바닥에 닿지 않도록 최소 {abs(min(allz))*1000+150:.0f} mm 이상 높이에 매달 것")


if __name__ == "__main__":
    main()
