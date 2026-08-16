"""P14a — air 'η 사다리' 재검: 필요 토크를 (틀린) serial 계수 대신
(검증된) 4-bar 축소 계수로 재계산하면 저부하 이상 현상이 살아남는가?

매핑 (P1 serial 2R 형식 ↔ 4-bar 축소): A_ser=IΣ1−IΣ2, D_ser=IΣ2, B_ser=K,
E_ser=0, k1_ser=A_4bar, k2_ser=B_4bar.  (air: base 고정 → 사용자 식 2,3행)
η 대신 절대 잔차 τ_meas − τ_req 도 출력 (B≈0이라 req가 미소 → 비율은 폭주).
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import g21_air_regressor as R          # P1 기계 (창, 로더)
from mshoot_s2s_air_holdout import load_air_cycles
from scipy.signal import savgol_filter

G = 9.81
# 4-bar CAD 계수 (P11a userEq check 값)
A4, B4, K4 = 0.128904, -0.003723, 0.002944
IS1, IS2 = 0.033855, 0.003609
# serial 형식으로 매핑
TH = dict(A=IS1 - IS2, D=IS2, B=K4, E=0.0, k1=A4, k2=B4)
# 비교용: P1 당시 serial CAD (air XML 뭉침 — air_regression.json의 xml theta)
SER = json.load(open(REPO / "code/goal21/air_regression.json"))
TH_S = dict(zip(["A", "D", "B", "E", "k1", "k2"],
                [SER["theta_xml"][k] if isinstance(SER.get("theta_xml"), dict) and k in SER["theta_xml"]
                 else None for k in ["A", "D", "B", "E", "k1", "k2"]]))


def req_torque(th, q1, q2, dq1, dq2, ddq1, ddq2):
    """serial-2R 형식 역동역학 (mujoco air frame: q1 수직아래 기준)."""
    c2, s2 = np.cos(q2), np.sin(q2)
    s1, s12 = np.sin(q1), np.sin(q1 + q2)
    M11 = th["A"] + th["D"] + 2 * th["B"] * c2
    M12 = th["D"] + th["B"] * c2
    M22 = th["D"] + th["E"]
    C1 = -th["B"] * s2 * (2 * dq1 * dq2 + dq2**2)
    C2 = th["B"] * s2 * dq1**2
    G1 = G * (th["k1"] * s1 + th["k2"] * s12)
    G2 = G * th["k2"] * s12
    t1 = M11 * ddq1 + M12 * ddq2 + C1 + G1
    t2 = M12 * ddq1 + M22 * ddq2 + C2 + G2
    return t1, t2


def main():
    rows = []
    for c in load_air_cycles():
        t = np.asarray(c["t"])
        k1 = "tau1_real" if "tau1_real" in c else "tau1"
        k2k = "tau2_real" if "tau2_real" in c else "tau2"
        q1 = -np.asarray(c["q1"]) - np.pi / 2
        q2 = -np.asarray(c["q2"])
        dq1 = savgol_filter(-np.asarray(c["dq1"]), 21, 3)
        dq2 = savgol_filter(-np.asarray(c["dq2"]), 21, 3)
        ddq1 = savgol_filter(np.gradient(dq1, t), 21, 3)
        ddq2 = savgol_filter(np.gradient(dq2, t), 21, 3)
        th_m = -np.asarray(c[k1]); tk_m = -np.asarray(c[k2k])
        t1r, t2r = req_torque(TH, q1, q2, dq1, dq2, ddq1, ddq2)
        for i in range(0, len(t), 25):
            rows.append((abs(dq2[i]), tk_m[i], t2r[i], th_m[i], t1r[i], np.sign(dq2[i])))
    rows = np.array(rows)
    print(f"[4-bar 정계수 재검] air 샘플 {len(rows)}개")
    print(f"{'|dq2| bin':>12} {'τ_knee 실측RMS':>14} {'τ_knee 필요RMS':>14} {'잔차RMS':>9} {'잔차·sgn(dq2) 평균':>18}")
    for lo, hi in [(0.05, 0.5), (0.5, 1.5), (1.5, 3.0), (3.0, 8.0)]:
        m = (rows[:, 0] >= lo) & (rows[:, 0] < hi)
        if m.sum() < 20:
            continue
        meas = rows[m, 1]; req = rows[m, 2]
        res = meas - req
        sgn_mean = np.mean(res * rows[m, 5])
        print(f"{f'{lo}-{hi}':>12} {np.sqrt(np.mean(meas**2)):>14.3f} {np.sqrt(np.mean(req**2)):>14.3f} "
              f"{np.sqrt(np.mean(res**2)):>9.3f} {sgn_mean:>18.3f}")
    print("\n[hip 동일]")
    for lo, hi in [(0.05, 0.5), (0.5, 1.5), (1.5, 3.0), (3.0, 8.0)]:
        m = (rows[:, 0] >= lo) & (rows[:, 0] < hi)
        if m.sum() < 20:
            continue
        meas = rows[m, 3]; req = rows[m, 4]
        res = meas - req
        print(f"{f'{lo}-{hi}':>12} {np.sqrt(np.mean(meas**2)):>14.3f} {np.sqrt(np.mean(req**2)):>14.3f} "
              f"{np.sqrt(np.mean(res**2)):>9.3f}")
    # 결론 판별: knee 필요토크가 실측 대비 얼마나 작은가
    m = rows[:, 0] > 0.05
    ratio = np.sqrt(np.mean(rows[m, 2]**2)) / np.sqrt(np.mean(rows[m, 1]**2))
    print(f"\nknee: 필요/실측 RMS 비 = {ratio:.2f}  → {'실측 τ는 대부분 마찰 (η 지표 무의미)' if ratio < 0.5 else 'η 해석 유지'}")


if __name__ == "__main__":
    main()
