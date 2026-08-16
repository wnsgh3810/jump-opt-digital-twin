# -*- coding: utf-8 -*-
"""p23_x3_loaders — P23 Phase 3 전용 신규 로더 1종 (p23_loaders 헬퍼 재사용).

load_jump_0319pd(): 26.03.19/position/NO_TR_JUMP — 무변속 점프, '위치(PD) 명령 계열'.
  - 탐사 확정 (p23_survey_unused_assets): 0.32s 창(159샘플, dt 2ms), raw ≤ 27.8, GRF 있음,
    xlsx 직행 청정 (jump_opt_compare csv 사용 금지 규약 동일).
  - 게인: PID.txt 없음, What.txt(세션 루트) = 'No 변속+V_des=0+새 모터' — 게인 미기재.
    Mode A(측정 토크 재생)에는 게인 불필요 → gains=None, 참고용 회귀만 meta에 보존.
  - ★ 주의(정직 노트): desiredTorque가 ±9 캡으로 기록돼 있음 (tau 세션과 동일 캡).
    '위치 세션 = FF 미인가' 가정은 폴더명 기반 — self-test의 cff 회귀로 실제 FF 기여를
    정량 확인해 meta['ff_evidence']에 기록한다 (family 판정의 데이터 근거).
  - l_i=0.030 가정 (Clutch 미기록 — 세션 공통).
원본 읽기 전용. 표준 d-dict 규약은 p23_loaders와 동일.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p23_loaders as L


Q1_ZERO_FIX = np.pi / 4          # ★ 힙 영점 규약 보정 (아래 근거 — 적합 아님, 이산 규약 수정)


def load_jump_0319pd(sub="NO_TR_JUMP"):
    """26.03.19/position/NO_TR_JUMP — 단일 trial (root xlsx 0.32s 창).

    ★ 힙 영점 −π/4 인공물 (2026-07-16 Phase 3 발견): 이 세션만 currentAngle과
    desiredAngle이 **정확히 −π/4** 만큼 이동 (qd1 시작 −1.090 vs 같은 날 tau −0.305,
    Δ=−0.785=−π/4; 타 5세션 전부 크라우치 q1≈−0.29 시작, 이 세션만 −1.09).
    지식 근거: (i) Δ가 π/4로 정확히 양자화 (ii) desired와 current가 동일하게 이동 =
    명령/엔코더 영점 규약 차이 (iii) 무릎 채널·GRF·토크는 전 세션 정합.
    → q1, qd1에 +π/4 가산해 타 세션 규약으로 통일 (dq/토크/GRF 무영향)."""
    root = L.DATA / "26_03_19/position" / sub
    hip = L._read_joint(root / "hip.xlsx")
    knee = L._read_joint(root / "knee.xlsx")
    n = min(len(hip["Time"]), len(knee["Time"]))
    grf = L._read_grf_on(hip["Time"][:n], root)
    d = L._pack(hip, knee, grf, L._parse_h_real(root / "Real Data.txt"))
    d["q1"] = d["q1"] + Q1_ZERO_FIX
    d["qd1"] = d["qd1"] + Q1_ZERO_FIX
    reg_ff = L._regress_gains(d, use_ff=True)     # cff = 기록된 tdes의 raw 기여 (FF 증거)
    reg_pd = L._regress_gains(d, use_ff=False)
    meta = dict(
        ds="jump_0319pd", sub=sub, gains=None,
        gains_source="없음 (PID.txt 부재, What.txt 게인 미기재 — Mode A에 무관)",
        gain_regression=dict(with_ff=reg_ff, no_ff=reg_pd),
        ff_evidence=dict(
            cff_hip=reg_ff["1"]["cff"], cff_knee=reg_ff["2"]["cff"],
            r2_ff=dict(hip=reg_ff["1"]["r2"], knee=reg_ff["2"]["r2"]),
            r2_noff=dict(hip=reg_pd["1"]["r2"], knee=reg_pd["2"]["r2"]),
            note="desiredTorque ±9 기록됨 — cff·R2 비교가 'FF 실인가' 판정 증거"),
        family="PD", ffk=False, dqdes_on=False, is_cvt=False,
        l_i=0.030, l_i_assumed=True, tdes_cap=9.0, heldout_day=False,
        q1_zero_fix=float(Q1_ZERO_FIX),
        q1_zero_fix_evidence=("qd1/q1 모두 정확히 −π/4 이동 (vs 같은 날 0319tau 및 "
                              "0421/0424/0602/0324 전 세션 크라우치 q1≈−0.29); "
                              "무릎·GRF·토크 정합 — 규약 보정이며 적합 아님"))
    return d, meta


def main():
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    d, m = load_jump_0319pd()
    P = L.judge()
    a1 = P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"])
    a2 = P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"])
    print(f"jump_0319pd/NO_TR_JUMP N={len(d['t'])} dur={d['t'][-1]:.3f}s "
          f"h_real={d['h_real']} grf={'Y' if d['grf_real'] is not None else 'N'}")
    print(f"  q1[{d['q1'].min():+.3f},{d['q1'].max():+.3f}] "
          f"q2[{d['q2'].min():+.3f},{d['q2'].max():+.3f}] "
          f"pk|dq|={np.abs(d['dq1']).max():.2f}/{np.abs(d['dq2']).max():.2f}")
    print(f"  raw rng hip[{d['traw1'].min():+.2f},{d['traw1'].max():+.2f}] "
          f"knee[{d['traw2'].min():+.2f},{d['traw2'].max():+.2f}]  "
          f"ahat rms {np.sqrt(np.mean(a1**2)):.2f}/{np.sqrt(np.mean(a2**2)):.2f} Nm")
    if d["grf_real"] is not None:
        g = d["grf_real"]; t = d["t"]
        pk = int(np.argmax(g)); below = np.where(g[pk:] < 0.02 * g[pk])[0]
        toff = t[pk + below[0]] if len(below) else t[-1]
        print(f"  GRF peak {g.max():.1f} @ {t[pk]:.3f}s, toff={toff:.3f}s (기록 끝 {t[-1]:.3f}s)")
    fe = m["ff_evidence"]
    print(f"  FF 증거 회귀: cff hip={fe['cff_hip']:+.3f} knee={fe['cff_knee']:+.3f} | "
          f"R2(ff) hip={fe['r2_ff']['hip']:.3f} knee={fe['r2_ff']['knee']:.3f} | "
          f"R2(no-ff) hip={fe['r2_noff']['hip']:.3f} knee={fe['r2_noff']['knee']:.3f}")
    print("  → cff≈0이면 위치(PD) 세션 판정 유지, cff 큼(≈1)이면 family 재고 필요")
    # 대조: 0319tau의 동일 회귀 (family 콘트라스트의 근거)
    dt_, mt = L.load_jump_0319tau()
    rt = mt["gain_regression"]
    print(f"  [대조 0319tau] cff hip={rt['1']['cff']:+.3f} knee={rt['2']['cff']:+.3f} "
          f"R2 {rt['1']['r2']:.3f}/{rt['2']['r2']:.3f}")


if __name__ == "__main__":
    main()
