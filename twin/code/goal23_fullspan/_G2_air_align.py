# -*- coding: utf-8 -*-
"""_G2_air_align — 26_08_02 실측을 **설계 궤적에 정렬**해 구간을 정확히 잘라낸다.

왜 필요한가: dqd 부호변화로 자른 1차 시도는 사인 영교차에서 구간이 쪼개져 엉켰다.
설계(make_sysid_air.build)는 결정적이므로, 설계 타임라인을 재생성해 시간축 정렬(t0 추정)
하면 각 표본이 어느 가진 구간인지 **정확히** 알 수 있다.

부가: ① 실측 시간 결손을 균일 500Hz 격자로 보간 복원 ② 이상 trial(명령 대비 폭주) 표식
원본 읽기 전용.
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "goal22" / "p25_task0"))
sys.path.insert(0, str(HERE.parent / "goal22" / "p26_sea"))
from sea_twin2 import ahat_np          # noqa: E402
import fs_data as FD                   # noqa: E402
import make_sysid_air as MK            # noqa: E402

SESS = FD.ROOT / "26_08_02"
FS = 500.0
DT = 1.0 / FS
KNEE_TAG = {"k070": 70.0, "k095": 95.0, "k118": 118.0}


# ── 설계 타임라인 재생성 (make_sysid_air.build 와 동일 순서, 구간 라벨 부착) ──
def design(qm_deg):
    qm = np.radians(qm_deg)
    P, LAB = [], []

    def add(seg, lab):
        P.append(seg); LAB.append((lab, len(seg[0])))

    add(MK.hold(MK.Q1_HOME, MK.QM_HOME, 1.0), "hold_home")
    add(MK.ramp(MK.Q1_HOME, MK.QM_HOME, MK.A1_HOME, qm, 2.0), "ramp_in")
    add(MK.hold(MK.A1_HOME, qm, 1.0), "hold_set")
    for f, a, c in MK.HIP_SEGS:
        add(MK.sine(MK.A1_HOME, qm, f, a, c, "hip"), f"hip_{f:g}Hz_{a:g}deg")
        add(MK.hold(MK.A1_HOME, qm, MK.HOLD), "hold")
    for f, a, c in MK.KNEE_SEGS:
        add(MK.sine(MK.A1_HOME, qm, f, a, c, "knee"), f"knee_{f:g}Hz_{a:g}deg")
        add(MK.hold(MK.A1_HOME, qm, MK.HOLD), "hold")
    add(MK.ramp(MK.A1_HOME, qm, MK.Q1_HOME, MK.QM_HOME, 2.0), "ramp_out")
    add(MK.hold(MK.Q1_HOME, MK.QM_HOME, 1.0), "hold_home")
    q1 = np.concatenate([p[0] for p in P]); qmv = np.concatenate([p[1] for p in P])
    lab = np.concatenate([[n] * c for n, c in LAB])
    return q1, qmv, lab


def trials():
    out = []
    for g in sorted(p for p in SESS.iterdir() if p.is_dir()):
        for t in sorted(p for p in g.iterdir() if p.is_dir()):
            if (t / "hip.xlsx").exists():
                out.append(t)
    return out


def load_uniform(fold):
    """실측을 균일 500Hz 격자로 보간 (시간 결손 복원). 반환 = dict of arrays + t."""
    h = pd.read_excel(fold / "hip.xlsx"); k = pd.read_excel(fold / "knee.xlsx")
    n = min(len(h), len(k))
    t = np.array(h["Time"].to_numpy(float)[:n], dtype=float, copy=True)
    t -= t[0]
    tu = np.arange(0.0, t[-1] + 1e-9, DT)
    d = dict(t=tu, n_raw=n, n_uni=len(tu))
    for tag, s in (("1", h), ("2", k)):
        for src, dst in (("currentAngle", "q"), ("desiredAngle", "qd"),
                         ("currentAngleVelocity", "dq"), ("desiredAngleVelocity", "dqd"),
                         ("currentTorque", "raw")):
            d[dst + tag] = np.interp(tu, t, s[src].to_numpy(float)[:n])
    return d


def align(d, qm_deg):
    """설계 qd1 과 실측 qd1 을 상호상관으로 정렬 → 설계 인덱스 offset."""
    dq1, dqm, lab = design(qm_deg)
    a = d["qd1"] - np.mean(d["qd1"])
    b = dq1 - np.mean(dq1)
    # 실측이 설계보다 길다 (앞뒤 여유). 설계를 실측 안에서 슬라이드.
    best, bi = -np.inf, 0
    lim = len(a) - len(b)
    if lim < 0:
        b = b[:len(a)]; lim = 0
    for i in range(0, lim + 1, 5):
        c = float(np.dot(a[i:i + len(b)], b))
        if c > best:
            best, bi = c, i
    for i in range(max(0, bi - 6), min(lim, bi + 6) + 1):
        c = float(np.dot(a[i:i + len(b)], b))
        if c > best:
            best, bi = c, i
    return bi, lab, dq1, dqm


def main():
    T = trials()
    print("=" * 122)
    print("① 설계-실측 정렬 및 구간별 실제 여기량  (τ = a_hat 변환 축토크 [Nm])")
    for t in T:
        tag = t.name.split("_")[2]
        d = load_uniform(t)
        off, lab, dq1, dqm = align(d, KNEE_TAG[tag])
        lab = lab[:len(d["t"]) - off]          # 기록이 설계보다 짧게 끊긴 trial 방어
        m = slice(off, off + len(lab))
        q1 = d["q1"][m]; q2 = d["q2"][m]
        qd1 = d["qd1"][m]; qd2 = d["qd2"][m]
        v1 = d["dq1"][m]; v2 = d["dq2"][m]
        a1 = ahat_np(d["raw1"][m], v1); a2 = ahat_np(d["raw2"][m], v2)
        # 명령 규약 확인: 설계 q_m 대 실측 qd2
        hh = lab == "hold_set"
        print(f"\n{t.parent.name} / {t.name}   정렬 offset {off} 표본 ({off*DT:.2f}s), "
              f"실측 {d['n_raw']}→균일 {d['n_uni']}표본")
        print(f"   명령 규약 확인: 설계 q_m={KNEE_TAG[tag]:.0f}° → 실측 qd2 (hold_set) "
              f"{np.degrees(qd2[hh]).mean():+.2f}°   [q2 = q_m − 180 예상 "
              f"{KNEE_TAG[tag]-180:+.0f}°]   실측 q2 {np.degrees(q2[hh]).mean():+.2f}°")
        print(f"   {'구간':<18}{'길이s':>6} | {'q1중심°':>8}{'q1진폭°':>8}{'q2중심°':>8}{'q2진폭°':>8}"
              f" | {'|dq1|max':>9}{'|dq2|max':>9} | {'τ1 p-p':>8}{'τ2 p-p':>8}")
        for name in dict.fromkeys(lab):
            s = lab == name
            if name.startswith("hold") or name.startswith("ramp"):
                if name != "hold_set":
                    continue
            print(f"   {name:<18}{s.sum()*DT:6.1f} | "
                  f"{np.degrees(q1[s]).mean():8.2f}{np.ptp(np.degrees(q1[s]))/2:8.2f}"
                  f"{np.degrees(q2[s]).mean():8.2f}{np.ptp(np.degrees(q2[s]))/2:8.2f} | "
                  f"{np.abs(v1[s]).max():9.2f}{np.abs(v2[s]).max():9.2f} | "
                  f"{np.ptp(a1[s]):8.3f}{np.ptp(a2[s]):8.3f}")


if __name__ == "__main__":
    main()
