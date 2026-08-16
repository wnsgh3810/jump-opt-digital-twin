# -*- coding: utf-8 -*-
"""_G2_air_fit — 26_08_02 공중 동정 **재분석** (마라톤G 재시작, _G_sysid_air 대체판).

1차 분석(_G_sysid_air.py) 대비 고친 것 — 전부 원본 재판독에서 나온 문제:
  A. 시간 결손(dt 2→최대 88ms, trial당 0~7회)을 균일 500Hz 격자로 보간 복원
  B. 설계 궤적 정렬로 **실험 구간만** 잘라냄 (250_3/k118 의 q1 −100° 폭주는 실험 밖 구간이었다)
  C. a_hat의 sign(v) 항: 정지 근처 v 잡음에 부호가 떨리며 ±0.27Nm 계단을 주입 →
     **평활 속도의 tanh 부호**로 대체 (물리 마찰도 원래 연속). 원본 sign 판과 대조 보고.
  D. 토크↔운동학 **채널 지연 스캔** (1차 분석 미실시). 3Hz에서 4ms = 4.3° 위상 = 관성 편향.
  E. 항별 **실효 기여 토크[Nm]** 와 다중공선성(1−R²ⱼ)로 식별성 판정
     (게인간 산포만으로 판정하던 것을 정량화)
  F. 설계 의도였던 1Hz 12° vs 6° 쌍으로 **쿨롱 vs 점성** 분리 검증

회귀 모형 (직렬 2링크 등가, l_i=30 평행사변형)
  τ1 = Is1·q̈1 + Is2·q̈2 + Kv·[2c2·q̈1 + c2·q̈2 − s2·(2q̇1q̇2+q̇2²)]
       + gA·cos q1 + gB·cos(q1+q2) + fv1·q̇1 + fc1·tanh(q̇1/0.3) + off1
  τ2 = Is2·(q̈1+q̈2) + Kv·[c2·q̈1 + s2·q̇1²] + gB·cos(q1+q2) + fv2·q̇2 + fc2·tanh(q̇2/0.3) + off2
CLI: python _G2_air_fit.py [--sign raw|smooth] [--lag N]
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "goal22" / "p25_task0"))
sys.path.insert(0, str(HERE.parent / "goal22" / "p26_sea"))
import fs_data as FD                       # noqa: E402
from _G2_air_align import (design, trials, load_uniform, align, KNEE_TAG)   # noqa: E402

FS, DT = 500.0, 1.0 / 500.0
NAMES = ["Is1", "Is2", "Kv", "gA", "gB", "fv1", "fv2", "fc1", "fc2", "off1", "off2"]
UNIT = ["kg·m²", "kg·m²", "kg·m²", "Nm", "Nm", "Nm·s", "Nm·s", "Nm", "Nm", "Nm", "Nm"]
# a_hat (Paper) 계수 — p14_judge.A_PAPER 와 동일
KT, GR, CF = 0.091, 9.0, 0.59
A_P = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
VSIGN = 0.05          # 부호 평활 폭 [rad/s] — 엔코더 차분 잡음보다 크고 가진 속도보다 훨씬 작다


def ahat(raw, v, mode="smooth"):
    """raw iTM → 축토크 [Nm]. mode='raw'는 sign(v) 그대로(1차 분석), 'smooth'는 tanh(v/VSIGN)."""
    Iq = (CF / (GR * KT)) * np.asarray(raw, float)
    s = np.sign(v) if mode == "raw" else np.tanh(np.asarray(v, float) / VSIGN)
    return A_P[0] * GR * KT * Iq - A_P[1] * GR * np.abs(Iq) * Iq - A_P[2] * s - A_P[3] * np.abs(Iq) * s


def lpf(x, fc, order=4):
    b, a = butter(order, fc / (FS / 2), btype="low")
    return filtfilt(b, a, np.asarray(x, float))


def prep(fold, mode="smooth", lag=0, fc=12.0):
    """정렬·크롭 후 일관 필터. lag>0 = 토크가 운동학보다 lag 표본 **늦게** 기록됐다고 보고 당김."""
    tag = fold.name.split("_")[2]
    d = load_uniform(fold)
    off, lab, _, _ = align(d, KNEE_TAG[tag])
    lab = lab[:len(d["t"]) - off]
    m = slice(off, off + len(lab))
    q1 = lpf(d["q1"][m], fc); q2 = lpf(d["q2"][m], fc)
    v1 = np.gradient(q1, DT); v2 = np.gradient(q2, DT)
    a1 = np.gradient(v1, DT); a2 = np.gradient(v2, DT)
    a1 = lpf(a1, fc); a2 = lpf(a2, fc)
    vs1 = lpf(d["dq1"][m], fc); vs2 = lpf(d["dq2"][m], fc)      # 부호·마찰용 평활 속도
    t1 = lpf(ahat(d["raw1"][m], vs1, mode), fc)
    t2 = lpf(ahat(d["raw2"][m], vs2, mode), fc)
    if lag:
        t1 = np.roll(t1, -lag); t2 = np.roll(t2, -lag)
    e = 400                                                     # 필터·정렬 경계 제거
    sl = slice(e, len(q1) - e - max(lag, 0))
    return dict(q1=q1[sl], q2=q2[sl], dq1=v1[sl], dq2=v2[sl], ddq1=a1[sl], ddq2=a2[sl],
                t1=t1[sl], t2=t2[sl], lab=lab[sl], gain=fold.parent.name, name=fold.name)


def regressor(d):
    q1, q2, v1, v2, a1, a2 = d["q1"], d["q2"], d["dq1"], d["dq2"], d["ddq1"], d["ddq2"]
    n = len(q1); s2, c2 = np.sin(q2), np.cos(q2)
    Y = np.zeros((2 * n, len(NAMES)))
    Y[:n, 0] = a1
    Y[:n, 1] = a2
    Y[:n, 2] = 2 * c2 * a1 + c2 * a2 - s2 * (2 * v1 * v2 + v2 ** 2)
    Y[:n, 3] = np.cos(q1)
    Y[:n, 4] = np.cos(q1 + q2)
    Y[:n, 5] = v1
    Y[:n, 7] = np.tanh(v1 / 0.3)
    Y[:n, 9] = 1.0
    Y[n:, 1] = a1 + a2
    Y[n:, 2] = c2 * a1 + s2 * v1 ** 2
    Y[n:, 4] = np.cos(q1 + q2)
    Y[n:, 6] = v2
    Y[n:, 8] = np.tanh(v2 / 0.3)
    Y[n:, 10] = 1.0
    return Y, np.concatenate([d["t1"], d["t2"]])


def fit(ds):
    Y = np.vstack([regressor(d)[0] for d in ds])
    T = np.concatenate([regressor(d)[1] for d in ds])
    th, *_ = np.linalg.lstsq(Y, T, rcond=None)
    r = T - Y @ th
    r2 = 1 - r @ r / np.sum((T - T.mean()) ** 2)
    return th, float(r2), float(np.sqrt(np.mean(r ** 2))), Y, T, r


def diagnostics(Y, th, r):
    """항별 실효 기여 토크(std)와 다중공선성 1−R²ⱼ (1에 가까울수록 독립=식별 양호)."""
    contrib = np.array([float(np.std(Y[:, j] * th[j])) for j in range(Y.shape[1])])
    indep = np.zeros(Y.shape[1])
    for j in range(Y.shape[1]):
        A = np.delete(Y, j, axis=1)
        c, *_ = np.linalg.lstsq(A, Y[:, j], rcond=None)
        res = Y[:, j] - A @ c
        v = np.var(Y[:, j])
        indep[j] = float(np.var(res) / v) if v > 1e-20 else 0.0
    # 표준오차 (잔차 자기상관 보정: 유효표본 = N/자기상관 시간)
    ac = np.correlate(r - r.mean(), r - r.mean(), "full")[len(r) - 1:]
    ac /= ac[0]
    tau = 1 + 2 * np.sum(ac[1:min(len(ac), 2000)][ac[1:min(len(ac), 2000)] > 0.05])
    neff = max(len(r) / max(tau, 1.0), Y.shape[1] + 1)
    cov = np.linalg.pinv(Y.T @ Y) * (r @ r / len(r)) * (len(r) / neff)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    return contrib, indep, se, tau


def main():
    mode = "smooth"
    if "--sign" in sys.argv:
        mode = sys.argv[sys.argv.index("--sign") + 1]
    T = trials()

    # ── C. a_hat 부호항의 영향 (정지 구간 잡음의 정체) ──
    print("=" * 116)
    print("① a_hat 부호항 진단 — 정지(hold_set) 구간의 '잡음'이 실제로 무엇인가")
    print(f"{'trial':<38}{'τ1 p-p (sign 원본)':>20}{'τ1 p-p (평활)':>16}{'τ2 p-p (원본)':>16}{'τ2 p-p (평활)':>16}")
    for t in T[:9]:
        r = {}
        for md in ("raw", "smooth"):
            d = prep(t, md)
            h = d["lab"] == "hold_set"
            r[md] = (np.ptp(d["t1"][h]), np.ptp(d["t2"][h]))
        print(f"{t.parent.name+'/'+t.name.split('_')[2]:<38}{r['raw'][0]:20.3f}{r['smooth'][0]:16.3f}"
              f"{r['raw'][1]:16.3f}{r['smooth'][1]:16.3f}")

    # ── D. 채널 지연 스캔 ──
    print("\n" + "=" * 116)
    print("② 토크↔운동학 채널 지연 스캔 (전 trial 통합 잔차 최소점)")
    print(f"{'지연[표본]':>10}{'지연[ms]':>10}{'RMS 잔차[Nm]':>14}{'R²':>10}{'Is1':>10}{'gA':>10}")
    best = (None, np.inf)
    for lag in range(-6, 7):
        ds = [prep(t, mode, lag) for t in T]
        th, r2, rms, *_ = fit(ds)
        mark = ""
        if rms < best[1]:
            best = (lag, rms)
        print(f"{lag:10d}{lag*2:10.0f}{rms:14.4f}{r2:10.4f}{th[0]:10.4f}{th[3]:10.4f}{mark}")
    LAG = best[0]
    print(f"  → 최소 잔차 지연 = {LAG} 표본 ({LAG*2:.0f} ms)")

    # ── 본 적합 ──
    ds = [prep(t, mode, LAG) for t in T]
    th, r2, rms, Y, Tv, r = fit(ds)
    contrib, indep, se, tau = diagnostics(Y, th, r)
    print("\n" + "=" * 116)
    print(f"③ 통합 적합 (9 trial, 부호={mode}, 지연={LAG}표본)   R²={r2:.4f}  RMS 잔차={rms:.4f} Nm")
    print(f"{'항':<6}{'단위':<8}{'추정값':>12}{'표준오차':>11}{'상대오차%':>10}"
          f"{'기여토크[Nm]':>13}{'기여/잔차':>10}{'독립성':>8}{'판정':>8}")
    verdict = {}
    for j, n in enumerate(NAMES):
        rel = abs(se[j] / th[j]) * 100 if abs(th[j]) > 1e-12 else np.inf
        snr = contrib[j] / rms
        ok = "신뢰" if (rel < 25 and snr > 0.3 and indep[j] > 0.02) else (
             "주의" if (rel < 60 and snr > 0.1) else "미식별")
        verdict[n] = ok
        print(f"{n:<6}{UNIT[j]:<8}{th[j]:+12.5f}{se[j]:11.5f}{rel:10.1f}"
              f"{contrib[j]:13.4f}{snr:10.2f}{indep[j]:8.3f}{ok:>8}")
    print(f"  (잔차 자기상관 시간 {tau:.0f} 표본 반영한 유효표본 기준 표준오차)")

    # ── 게인별 자기검증 ──
    print("\n" + "=" * 116)
    print("④ 게인별 독립 적합 — 플랜트 값은 PD 게인과 무관해야 한다")
    print(f"{'게인(무릎kp)':<16}" + "".join(f"{n:>10}" for n in NAMES) + f"{'RMS':>8}")
    TH = {}
    for g in sorted({t.parent.name for t in T}):
        sub = [d for d in ds if d["gain"] == g]
        thg, r2g, rmsg, *_ = fit(sub)
        TH[g] = thg
        print(f"{g:<16}" + "".join(f"{v:10.4f}" for v in thg) + f"{rmsg:8.4f}")
    A = np.array(list(TH.values()))
    var = np.array([A[:, i].std() / max(abs(A[:, i].mean()), 1e-9) * 100 for i in range(A.shape[1])])
    print(f"{'게인간 변동%':<16}" + "".join(f"{v:10.1f}" for v in var))

    # ── F. 쿨롱 vs 점성 분리 (설계 의도) ──
    print("\n" + "=" * 116)
    print("⑤ 구간별 잔차 — 어느 여기에서 모형이 맞고 어디서 틀리나")
    print(f"{'구간':<18}{'표본':>8}{'τ1 RMS잔차':>12}{'τ1 실측 std':>12}{'설명력':>8}"
          f"{'τ2 RMS잔차':>12}{'τ2 실측 std':>12}{'설명력':>8}")
    labs = list(dict.fromkeys(np.concatenate([d["lab"] for d in ds])))
    for L in labs:
        n1 = n2 = 0.0; s1 = s2 = 0.0; cnt = 0
        R1, R2, M1, M2 = [], [], [], []
        for d in ds:
            s = d["lab"] == L
            if not s.any():
                continue
            Yd, Td = regressor(d)
            k = len(d["q1"])
            pr = Yd @ th
            R1.append(Td[:k][s] - pr[:k][s]); R2.append(Td[k:][s] - pr[k:][s])
            M1.append(Td[:k][s]); M2.append(Td[k:][s])
        if not R1:
            continue
        R1 = np.concatenate(R1); R2 = np.concatenate(R2)
        M1 = np.concatenate(M1); M2 = np.concatenate(M2)
        e1 = 1 - np.var(R1) / max(np.var(M1), 1e-12)
        e2 = 1 - np.var(R2) / max(np.var(M2), 1e-12)
        print(f"{L:<18}{len(R1):8d}{np.sqrt(np.mean(R1**2)):12.4f}{M1.std():12.4f}{e1:8.3f}"
              f"{np.sqrt(np.mean(R2**2)):12.4f}{M2.std():12.4f}{e2:8.3f}")

    out = dict(names=NAMES, theta=[float(x) for x in th], se=[float(x) for x in se],
               contrib=[float(x) for x in contrib], indep=[float(x) for x in indep],
               verdict=verdict, r2=r2, rms=rms, lag=int(LAG), sign_mode=mode,
               per_gain={k: [float(x) for x in v] for k, v in TH.items()},
               gain_var_pct=[float(x) for x in var])
    with io.open(HERE / "_G2_air_fit.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\n저장: _G2_air_fit.json")


if __name__ == "__main__":
    main()
