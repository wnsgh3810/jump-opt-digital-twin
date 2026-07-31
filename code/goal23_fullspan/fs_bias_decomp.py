# -*- coding: utf-8 -*-
"""fs_bias_decomp — bias의 물리 분해 파일럿 (사용자 가설: 인코더 영점 Δθ + 발 접촉점 δx).

원리: 하강 스윕의 잔차 프로파일 r1(q),r2(q)를 민감도 기저 3개로 최소자승 분해.
  r1_i ≈ Δθ1·∂s1/∂q1 + Δθ2·∂s1/∂q2 + δx·∂s1/∂x_f   (r2_i 동형 — 양 채널 공동 적합)
민감도: 각 표본 자세에서 트윈 settle 유지토크를 (q1+0.5°), (q2+0.5°), (발 geom x+2mm 모델)로
재계산해 수치 미분. 기저가 자세 의존이므로 상수 bias와 구별 가능 (상수-only 대비 R² 비교).
판정: R² 대폭 상승 + Δθ(°)·δx(mm)가 실물 척도(≲2°, ≲5mm)면 성립 → bias 은퇴 경로.
파일럿 trial: 무슬립 영상 확인분 위주 (0602/150_2.2_250_3 · 25일/150_2.2_250_3 · 27일/250_3_250_3).
CLI: python fs_bias_decomp.py
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import fs_calib as FC          # tw0/MODEL/hold_torque 재사용 (감사와 동일 기계)
import fs_model as FM
import safe
import mujoco as mjm

DQ = np.radians(0.5)           # 각도 섭동
DX = 0.002                     # 발 접촉점 섭동 [m]
PILOT = [("26.06.02", "150_2.2_250_3"), ("26.07.25", "150_2.2_250_3"), ("26.07.27", "250_3_250_3")]


def build_footshift_model():
    base_xml, _ = FM.capture_base_xml()
    old = '<geom name="foot" class="foot" type="cylinder" size="0.0210 0.0065" pos="0 0 -0.25" euler="90 0 0"/>'
    new = f'<geom name="foot" class="foot" type="cylinder" size="0.0210 0.0065" pos="{DX} 0 -0.25" euler="90 0 0"/>'
    xml = safe.xml_patch(base_xml, old, new, count=1)
    return mjm.MjModel.from_xml_string(xml)


def hold_on(model, q1_0, q2_0):
    """fs_calib.hold_torque 문자 미러 — 임의 모델 위에서."""
    M0 = FC.MODEL
    FC.MODEL = model
    try:
        return FC.hold_torque(q1_0, q2_0)
    finally:
        FC.MODEL = M0


def main():
    st = json.load(open(HERE / "_fs_static_audit.json", encoding="utf-8"))
    m_shift = build_footshift_model()
    for s, tr in PILOT:
        rows = [r for r in st[s][tr]["rows"] if r["ok"]][::3]      # stride 3
        if len(rows) < 6:
            print(f"{s}/{tr}: 표본 부족", flush=True)
            continue
        A, y = [], []
        for r in rows:
            q1, q2 = float(r["q1"]), float(r["q2"])
            s1_0, s2_0 = float(r["s1"]), float(r["s2"])           # 기준 유지토크 (감사 저장분)
            s1_a, s2_a, ok1 = hold_on(FC.MODEL, q1 + DQ, q2)
            s1_b, s2_b, ok2 = hold_on(FC.MODEL, q1, q2 + DQ)
            s1_c, s2_c, ok3 = hold_on(m_shift, q1, q2)
            if not (ok1 and ok2 and ok3):
                continue
            G = np.array([
                [(s1_a - s1_0) / DQ, (s1_b - s1_0) / DQ, (s1_c - s1_0) / DX],
                [(s2_a - s2_0) / DQ, (s2_b - s2_0) / DQ, (s2_c - s2_0) / DX],
            ])
            A.append(G[0]); y.append(r["a1"] - s1_0)
            A.append(G[1]); y.append(r["a2"] - s2_0)
        A = np.array(A); y = np.array(y)
        # 3파라미터 물리 적합
        p, res, *_ = np.linalg.lstsq(A, y, rcond=None)
        yhat = A @ p
        ss = 1 - np.sum((y - yhat) ** 2) / np.sum((y - y.mean()) ** 2)
        # 대조: 상수-only (채널별 상수 2개 = 현행 bias 방식)
        C = np.zeros((len(y), 2)); C[0::2, 0] = 1; C[1::2, 1] = 1
        pc, *_ = np.linalg.lstsq(C, y, rcond=None)
        ssc = 1 - np.sum((y - C @ pc) ** 2) / np.sum((y - y.mean()) ** 2)
        # 혼합: 상수2 + 물리3
        M = np.hstack([A, C])
        pm, *_ = np.linalg.lstsq(M, y, rcond=None)
        ssm = 1 - np.sum((y - M @ pm) ** 2) / np.sum((y - y.mean()) ** 2)
        print(f"{s}/{tr} (표본 {len(rows)}):", flush=True)
        print(f"  물리3: Δθ1 {np.degrees(p[0]):+.2f}° · Δθ2 {np.degrees(p[1]):+.2f}° · δx {p[2]*1000:+.1f}mm | R² {ss:.3f}", flush=True)
        print(f"  대조 — 상수-only(현행 bias) R² {ssc:.3f} | 상수2+물리3 R² {ssm:.3f}", flush=True)


if __name__ == "__main__":
    main()
