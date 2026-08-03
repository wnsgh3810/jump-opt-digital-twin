# -*- coding: utf-8 -*-
"""P18 — l_i 가변 4-bar (CVT) 코어: 빌더 + 폐쇄 솔버 + 데이터 로더.

26.04.29 세션: l_i = 25.08mm (점프 창 내 상수, Clutch.xlsx 실측), l_o = 30mm 유지
→ 비평행사변형: crank각 ≠ calf각 (비선형 전달비). 엔코더/모터/토크 = crank 쪽 (기존과 동일).
루프 폐쇄: site-site connect (qpos0 폐쇄 불필요) + 해석적 폐쇄 솔버로 IC/FK 처리.
"""
import sys, json
import numpy as np
import pandas as pd
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
import p14_judge as J
import g21_p13_linkage as P13
import g21_p13e_honest as PH

L1 = 0.25          # thigh = coupler length
L2 = 0.25          # calf
LO = 0.03          # rocker (calf 쪽) — 세션 불변
DATA429 = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data/26_04_29")
SUBS429 = ["60_0.75_60_2", "60_1.5_60_1.5", "90_0.75_90_2", "90_1.5_90_2.5",
           "120_2_120_2", "120_2.2_150_2.5", "120_2.2_200_2.8",
           "150_2.2_250_3", "150_2.2_350_3.5", "150_2.2_500_4"]


# ── 빌더: flip XML에서 커플러 부착점만 l_i로 이동 + site-site connect ──
def build_cvt(x32, ref, l_i, A=None):
    S = J._P["S"]; FR = J._P["FR"]; FL = J._P["FL"]; mj = J._P["mj"]
    dd = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = ref
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, np.asarray(x32)[26:32])))
    # 1) crank geom 끝 + coupler 부착 높이를 l_i로 (기본 0.03)
    xml = xml.replace('fromto="0 0 0 0 0 0.03"', f'fromto="0 0 0 0 0 {l_i:.5f}"')
    xml = xml.replace('<body name="coupler" pos="0 0 0.03">',
                      f'<body name="coupler" pos="0 0 {l_i:.5f}">')
    # 2) 기존 body-anchor connect 제거 → site-site connect
    import re
    xml = re.sub(r'<connect body1="coupler" body2="calf"[^/]*/>', '', xml)
    xml = xml.replace('</body>\n        </body>', '</body>\n        </body>')  # no-op 안전
    # coupler에 tip site, calf에 rocker site 삽입
    xml = xml.replace('<joint name="cpin" type="hinge"/>',
                      '<joint name="cpin" type="hinge"/><site name="ctip" pos="0 0 -0.25" size="0.003"/>')
    xml = xml.replace('<joint name="cpin" type="hinge" damping=',
                      '<site name="ctip" pos="0 0 -0.25" size="0.003"/><joint name="cpin" type="hinge" damping=')
    xml = xml.replace('<joint name="knee" type="hinge" damping=',
                      '<site name="rocker" pos="0 0 0.03" size="0.003"/><joint name="knee" type="hinge" damping=')
    xml = xml.replace('<equality>', '<equality>\n  <connect site1="ctip" site2="rocker" solref="0.0008 1"/>')
    model = mj.MjModel.from_xml_string(xml)
    return model, dd


# ── 폐쇄 솔버: crank 각(mj) -> calf 각(mj), cpin 각, 전달비 ──
def closure(qc, l_i, qk0=None):
    """thigh 프레임. C = l_i(sin,cos qc), K=(0,-L1), R(qk)=K+LO(sin,cos qk), |C-R|=L1."""
    K = np.array([0.0, -L1])
    C = l_i * np.array([np.sin(qc), np.cos(qc)])
    qk = qc if qk0 is None else qk0
    for _ in range(40):
        R = K + LO * np.array([np.sin(qk), np.cos(qk)])
        d = C - R
        f = d @ d - L1 * L1
        Rp = LO * np.array([np.cos(qk), -np.sin(qk)])
        df = -2.0 * (d @ Rp)
        if abs(df) < 1e-12:
            break
        step = f / df
        qk -= np.clip(step, -0.3, 0.3)
        if abs(f) < 1e-14:
            break
    R = K + LO * np.array([np.sin(qk), np.cos(qk)])
    u = (R - C) / L1
    theta_p = np.arctan2(-u[0], -u[1])
    qpin = theta_p - qc
    # 전달비 r = dqk/dqc
    Cp = l_i * np.array([np.cos(qc), -np.sin(qc)])
    Rp = LO * np.array([np.cos(qk), -np.sin(qk)])
    d = C - R
    r = (d @ Cp) / (d @ Rp) if abs(d @ Rp) > 1e-12 else 1.0
    return float(qk), float(((qpin + np.pi) % (2 * np.pi)) - np.pi), float(r)


def qpos_from_crank(bz, q1m, qc, l_i, qk_prev=None):
    qk, qpin, r = closure(qc, l_i, qk_prev)
    return [bz, q1m, qc, qpin, qk], qk, r


# ── 26.04.29 로더 (기존 규격 + Clutch) ──
def load_0429(sub):
    def rd(fn):
        df = pd.read_excel(DATA429 / sub / fn)
        return {c: df[c].values.astype(float) for c in df.columns}
    hip = rd("hip.xlsx"); knee = rd("knee.xlsx")
    n = min(len(hip["Time"]), len(knee["Time"]))
    t = hip["Time"][:n] - hip["Time"][0]
    d = dict(t=t)
    for nm, src in [("1", hip), ("2", knee)]:
        d["q" + nm] = src["currentAngle"][:n]; d["qd" + nm] = src["desiredAngle"][:n]
        d["dq" + nm] = src["currentAngleVelocity"][:n]; d["dqd" + nm] = src["desiredAngleVelocity"][:n]
        d["traw" + nm] = src["currentTorque"][:n]; d["tdes" + nm] = src["desiredTorque"][:n]
    try:
        grf = pd.read_excel(DATA429 / sub / "GRF.xlsx")["Current_GRF"].values.astype(float)
        d["grf_real"] = grf[:n] if len(grf) >= n else None
    except Exception:
        d["grf_real"] = None
    cl = pd.read_excel(DATA429 / sub / "Clutch.xlsx")
    m = (cl["Time"].values >= hip["Time"][0]) & (cl["Time"].values <= hip["Time"][n - 1])
    d["l_i"] = float(np.median(cl["Current Link Length [mm]"].values[m])) / 1000.0
    # h_real
    d["h_real"] = float("nan")
    try:
        sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal12/data_loaders")
        from load_combined_15trial import parse_h_real
        d["h_real"] = float(parse_h_real(DATA429 / sub / "Real Data.txt"))
        if d["h_real"] > 3.0:
            d["h_real"] /= 100.0
    except Exception:
        pass
    return d


def label_gains_429(sub):
    p = [float(v) for v in sub.split("_")]
    return p[0], p[1], p[2], p[3]


if __name__ == "__main__":
    # sanity 1: 폐쇄 솔버 — l_i=0.03이면 qk=qc, r=1
    for qc in [0.3, 1.0, 2.0, 2.6]:
        qk, qp, r = closure(qc, 0.03)
        assert abs(qk - qc) < 1e-9 and abs(r - 1) < 1e-9, (qc, qk, r)
    print("sanity1 OK: l_i=30mm -> qk=qc, r=1 (평행사변형)")
    # l_i=25.08mm 전달비 프로파일
    for qc in [0.3, 1.0, 1.5, 2.0, 2.6]:
        qk, qp, r = closure(qc, 0.02508)
        print(f"  qc={qc:.2f}: qk={qk:.4f} (qk-qc={np.degrees(qk-qc):+.2f}deg)  r=dqk/dqc={r:.4f}")
    # sanity 2: 모델 빌드 + 폐쇄 잔차
    J.winit()
    C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
    X = np.array(C16["x"])
    model, dd = build_cvt(X[:32], float(X[36]), 0.02508)
    mj = J._P["mj"]
    dta = mj.MjData(model)
    qc = 2.0
    qp5, qk, r = qpos_from_crank(1.0, -1.2, qc, 0.02508)
    dta.qpos[:] = qp5
    mj.mj_forward(model, dta)
    res = float(np.max(np.abs(dta.efc_pos))) if dta.nefc else 0.0
    print(f"sanity2: site-connect 폐쇄 잔차 = {res:.2e} m")
    # sanity 3: l_i=0.03 CVT 빌드 == 기존 flip과 질량행렬 일치?
    model30, _ = build_cvt(X[:32], float(X[36]), 0.03)
    qp5b, _, _ = qpos_from_crank(1.0, -1.2, qc, 0.03)
    d30 = mj.MjData(model30)
    d30.qpos[:] = qp5b
    mj.mj_forward(model30, d30)
    res30 = float(np.max(np.abs(d30.efc_pos))) if d30.nefc else 0.0
    print(f"sanity3: l_i=30mm CVT 폐쇄 잔차 = {res30:.2e} m")
