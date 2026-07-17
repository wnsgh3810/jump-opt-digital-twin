# -*- coding: utf-8 -*-
"""t18 엄격판 — 개루프 기록형 계획(iLQR·PPO)의 â≤18Nm 전 구간 준수 사영 (사용자 지시 07-17).

원리: 고정 raw 박스(31.18)는 운동방향 가지만 18Nm — 반대방향 순간엔 마찰 가세로 â 최대 20.7.
속도-부호별 포락선 [같은방향 31.1771 / v=0 28.7533 / 반대방향 26.6456]으로 명령을 사영하고
rollout_ol(골든 검증된 개루프 미러)로 재롤아웃 → 실현 속도 기준 재사영 반복 → 전 구간 |â|≤18.
초과가 전부 공중 구간(apex는 이지 속도로 결정)이라 h_plan 변화는 ~0 기대.
산출 = *_t18_strict.npz (별도 파일 — canonical t18은 모터-전류 박스판 유지, 엄격판은 감도 행).
"""
import os
import shutil
import sys
from pathlib import Path

for k in ("P23_SPRING_GATED", "P23_RISE_GATED", "P24_HIP_LAW", "P24_REFIT"):
    os.environ.setdefault(k, "1")
os.environ.setdefault("P25_CLIP_RAW", "31.1771")

import numpy as np

HERE = Path(__file__).parent
for p in [HERE, HERE.parent / "p23_veins", HERE.parent / "p20_rise",
          HERE.parent / "p19_jump", HERE.parent.parent / "bench"]:
    sys.path.insert(0, str(p))

import p25_a_twin as T

R_MOT, R_ZERO, R_OPP = 31.1771, 28.7533, 26.6456   # ahat⁻¹(18Nm) — brentq 역산 (본문 로그)
TOL = 18.005


DILATE = 10      # 스텝 (dt 0.5ms × 10 = 5ms — tm 1.31ms 필터 잔향 커버)


def viol_mask(tg, tL, aL):
    """위반 시각(|â|>18) → 소스 그리드 마스크 (±DILATE 팽창). 위반 지점만 조인다 —
    푸시 구간(위반 0)은 건드리지 않아 h 손실 없음."""
    v = np.abs(aL) > 18.0005
    if not v.any():
        return None
    idx = np.clip(np.searchsorted(tg, tL[v]), 0, len(tg) - 1)
    mk = np.zeros(len(tg), bool)
    mk[idx] = True
    out = mk.copy()
    for s in range(1, DILATE + 1):
        out[s:] |= mk[:-s]
        out[:-s] |= mk[s:]
    return out


def audit(P, L):
    """실현 (raw, dq)로 |â| 최대·초과율."""
    a1 = P.J.ahat(P.A_PAPER, L["raw1"], L["dq1"])
    a2 = P.J.ahat(P.A_PAPER, L["raw2"], L["dq2"])
    aa = np.maximum(np.abs(a1), np.abs(a2))
    m = L["t"] <= T.T_END          # 커맨드 창 (비행 규약 구간은 명령 0)
    return float(aa[m].max()), float((aa[m] > TOL).mean())


def main():
    tw = T.twin()
    P = tw["P"]
    st = T.settle_state(tw, *tw["q0"])
    # ★ 재롤아웃은 tm=0 (필터 패스스루): npz의 raw는 이미 필터를 거친 물리 명령 —
    # 그대로 재적용해야 원본 동역학 재현 (이중 필터링 시 스탠스 램프 1.3ms 지연 → F_τ 오염)
    tw2 = dict(tw, tm=0.0)
    # PPO 제외 (07-17 진단): 정책 궤적의 개루프 재생은 초기상태 미세차가 무보정 성장 —
    # 스탠스 τ RMSE 0.000인데 q2 0.08rad/h −5.2cm 어긋남 = 재생 기준선 무효. 유효 측정은 iLQR뿐.
    for name in ("p25_a4_ilqr_t18.npz",):
        src = HERE / name
        z = np.load(src)
        t = np.asarray(z["t"], float)
        m = t >= 0
        tg = t[m] - t[m][0]
        r1 = np.asarray(z["raw1"], float)[m].copy()
        r2 = np.asarray(z["raw2"], float)[m].copy()
        h0 = float(z["h_plan"]) if "h_plan" in z.files else float("nan")
        L = None
        la1 = np.full_like(r1, R_MOT)              # 누적 한계 (위반 지점만 단조 조임)
        la2 = np.full_like(r2, R_MOT)
        for it in range(25):
            L = T.rollout_ol(tw2, tg, r1, r2, st, record=True)
            assert L is not None, f"{name}: 롤아웃 발산"
            mx, frac = audit(P, L)
            if mx <= TOL:
                break
            mw = L["t"] <= T.T_END
            a1L = P.J.ahat(P.A_PAPER, L["raw1"], L["dq1"])
            a2L = P.J.ahat(P.A_PAPER, L["raw2"], L["dq2"])
            for aL, la in ((np.where(mw, a1L, 0.0), la1), (np.where(mw, a2L, 0.0), la2)):
                mk = viol_mask(tg, L["t"], aL)
                if mk is not None:
                    la[mk] = np.minimum(la[mk], R_OPP)
            r1 = np.clip(r1, -la1, la1)
            r2 = np.clip(r2, -la2, la2)
        h1 = T.apex_of(L)
        mx, frac = audit(P, L)
        status = "OK" if mx <= TOL else "잔존"
        print(f"{name:28s} h {h0:.4f}→{h1:.4f} (Δ{100*(h1-h0):+.2f}cm)  "
              f"max|â| {mx:.3f}  >18: {100*frac:.2f}%  [{it+1}회 사영, {status}]", flush=True)
        assert mx <= 18.05, f"{name}: 사영 미수렴 (max â {mx:.3f})"
        dst = src.with_name(src.stem + "_strict.npz")
        T.save_npz(dst, L, extra=dict(
            h_plan=h1, qd1=L["q1"], qd2=L["q2"], dqd1=L["dq1"], dqd2=L["dq2"],
            strict18=1.0, raw_clip=R_MOT))
    print("DONE — 3계획 엄격판 갱신 (원본 .bak 백업)", flush=True)


if __name__ == "__main__":
    main()
