# -*- coding: utf-8 -*-
"""_G2_air_phasor — 26_08_02 **주파수영역(위상자) 재분석** — 최소제곱 회귀의 축퇴를 깬다.

왜 필요한가 (_G2_air_fit 진단):
  시간영역 회귀에서 gA(중력레버)와 off1(토크 센서 오프셋)의 **독립성이 0.005** = 거의 완전 공선.
  힙이 −45° 둘레 ±12°만 흔들리므로 cos q1 이 0.54~0.84로 조금만 변해 둘을 나눌 수 없다.
  게인간 산포(2.7%)는 이 축퇴를 **감지하지 못한다** — 세 부분집합 모두 같은 방향으로 축퇴하므로.
  → 가진 주파수 성분만 뽑으면 **DC 오프셋이 원리적으로 제거**된다. 중력은 강성으로 나타난다.

모형 (q1_0 = −45° 둘레 선형화, δq1 = q1 − q1_0)
  중력토크 gA·cos q1 ≈ gA·cos q1_0 − gA·sin(q1_0)·δq1  → **강성 k_g = −gA·sin(q1_0) = +0.707·gA**
  (2차항은 DC와 2ω로만 가고 ω에는 오지 않는다 — 기본파 추출이 깨끗한 이유)
  임피던스 Z(ω) = τ1(ω)/δq1(ω) = k_g − ω²·I_eff  +  j·ω·b_eq
  b_eq = fv1 + 4·fc1/(π·A·ω)   ← 쿨롱의 기술함수 등가 (진폭 A에 반비례)
  ⇒ 설계된 1Hz **12° vs 6°** 쌍이 쿨롱/점성을 분리한다 (설계 의도, 1차 분석 미사용)

판별
  · I_eff 가 1→3Hz에서 **일정**하면 강체, **감소**하면 모터-링크 사이 직렬 탄성(벨트 SEA)
  · k_g 로부터 gA 를 오프셋 오염 없이 산출
CLI: python _G2_air_phasor.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from _G2_air_fit import prep, FS, DT                      # noqa: E402
from _G2_air_align import trials                          # noqa: E402

# 구간 라벨 → (가진 주파수 Hz, 설계 진폭 deg, 가진 관절)
SEG = {"hip_1Hz_12deg": (1.0, 12.0, 1), "hip_1Hz_6deg": (1.0, 6.0, 1),
       "hip_2Hz_12deg": (2.0, 12.0, 1), "hip_3Hz_8deg": (3.0, 8.0, 1),
       "knee_2Hz_8deg": (2.0, 8.0, 2), "knee_3Hz_5deg": (3.0, 5.0, 2)}


def phasor(x, t, f):
    """기본파 복소진폭 (x ≈ Re{X·e^{jωt}}). DC·타주파수 성분은 직교로 제거된다."""
    w = 2 * np.pi * f
    c, s = np.cos(w * t), np.sin(w * t)
    n = len(t)
    # 최소제곱 (직교성이 완전하지 않은 유한구간 보정)
    A = np.column_stack([c, s, np.ones(n)])
    b, *_ = np.linalg.lstsq(A, np.asarray(x, float), rcond=None)
    return complex(b[0], -b[1])          # x = |X| cos(wt + arg X)


def seg_slices(d, lab, f):
    """가진 구간에서 포락선 램프(각 끝 1주기)를 제외한 정상 구간."""
    idx = np.flatnonzero(d["lab"] == lab)
    if len(idx) == 0:
        return None
    # 연속 덩어리마다
    br = np.flatnonzero(np.diff(idx) > 1)
    chunks = np.split(idx, br + 1)
    out = []
    ramp = int(round(FS / f))
    for c in chunks:
        if len(c) > 2 * ramp + int(0.5 * FS):
            out.append(c[ramp:len(c) - ramp])
    return out


def main():
    T = trials()
    ds = [prep(t, "smooth", 1) for t in T]

    print("=" * 120)
    print("① 구간별 임피던스 Z(ω) = τ/δq  [Nm/rad]  — DC 오프셋이 원리적으로 제거된 값")
    print(f"{'trial':<26}{'구간':<16}{'진폭°':>7}{'f[Hz]':>6}{'Re Z':>9}{'Im Z':>9}"
          f"{'I_eff[kg·m²]':>13}{'b_eq[Nm·s]':>11}{'일관성':>8}")
    rows = []
    for d, t in zip(ds, T):
        for lab, (f, A, j) in SEG.items():
            ch = seg_slices(d, lab, f)
            if not ch:
                continue
            for c in ch:
                tt = np.arange(len(c)) * DT
                q = d["q1"][c] if j == 1 else d["q2"][c]
                tau = d["t1"][c] if j == 1 else d["t2"][c]
                Q = phasor(q - q.mean(), tt, f)
                TAU = phasor(tau - tau.mean(), tt, f)
                # 일관성 = 기본파가 신호를 얼마나 설명하나 (잡음/비선형 지표)
                w = 2 * np.pi * f
                rec = np.real(TAU * np.exp(1j * w * tt))
                coh = 1 - np.var(tau - tau.mean() - rec) / np.var(tau - tau.mean())
                Z = TAU / Q
                amp = np.degrees(np.abs(Q))
                rows.append(dict(trial=f"{t.parent.name[-5:]}/{t.name.split('_')[2]}", lab=lab,
                                 f=f, A=amp, j=j, ReZ=Z.real, ImZ=Z.imag, coh=float(coh),
                                 q2=float(np.degrees(d["q2"][c].mean()))))
    # 요약 출력 (trial×구간 평균)
    for lab in SEG:
        sub = [r for r in rows if r["lab"] == lab]
        if not sub:
            continue
        f = SEG[lab][0]
        w = 2 * np.pi * f
        for r in sub[:0]:
            pass
        A = np.mean([r["A"] for r in sub])
        Re = np.mean([r["ReZ"] for r in sub]); Rs = np.std([r["ReZ"] for r in sub])
        Im = np.mean([r["ImZ"] for r in sub]); Is_ = np.std([r["ImZ"] for r in sub])
        coh = np.mean([r["coh"] for r in sub])
        print(f"{'(9 trial 평균)':<26}{lab:<16}{A:7.2f}{f:6.1f}{Re:9.3f}{Im:9.3f}"
              f"{'':>13}{'':>11}{coh:8.3f}")
        print(f"{'  ± 표본표준편차':<26}{'':<16}{'':>7}{'':>6}{Rs:9.3f}{Is_:9.3f}")

    # ── ② 강체 모형 적합: Re Z = k_g − ω²·I ,  Im Z = ω·fv + 4·fc/(π·A) ──
    print("\n" + "=" * 120)
    print("② 힙 4구간 → 강체 모형 (k_g, I, fv1, fc1) 최소제곱  [1Hz 12°/6° 쌍이 쿨롱/점성 분리]")
    hip = [r for r in rows if r["j"] == 1]
    Xr, yr, Xi, yi = [], [], [], []
    for r in hip:
        w = 2 * np.pi * r["f"]
        Xr.append([1.0, -w ** 2]); yr.append(r["ReZ"])
        Xi.append([w, 4.0 / (np.pi * np.radians(r["A"]))]); yi.append(r["ImZ"])
    kr, *_ = np.linalg.lstsq(np.array(Xr), np.array(yr), rcond=None)
    ki, *_ = np.linalg.lstsq(np.array(Xi), np.array(yi), rcond=None)
    resr = np.array(yr) - np.array(Xr) @ kr
    resi = np.array(yi) - np.array(Xi) @ ki
    q10 = np.radians(-45.2)
    gA = kr[0] / (-np.sin(q10))
    print(f"   중력 강성 k_g = {kr[0]:+.4f} Nm/rad   → gA = k_g / (−sin q1_0) = {gA:+.4f} Nm")
    print(f"   등가 관성 I   = {kr[1]:+.5f} kg·m²      (실수부 잔차 RMS {np.sqrt(np.mean(resr**2)):.4f})")
    print(f"   점성 fv1 = {ki[0]:+.5f} Nm·s/rad · 쿨롱 fc1 = {ki[1]:+.4f} Nm "
          f"(허수부 잔차 RMS {np.sqrt(np.mean(resi**2)):.4f})")

    # ── ③ 주파수별 I_eff — 직렬 탄성 판별 ──
    print("\n" + "=" * 120)
    print("③ 주파수별 등가 관성 I_eff(ω) = (k_g − Re Z)/ω²  — 일정=강체, 감소=직렬 탄성(벨트 SEA)")
    print(f"{'구간':<16}{'f[Hz]':>6}{'진폭°':>7}{'Re Z':>9}{'I_eff':>10}{'±':>9}{'대 1Hz비':>10}{'개수':>6}")
    base = None
    for lab in [l for l in SEG if SEG[l][2] == 1]:
        sub = [r for r in rows if r["lab"] == lab]
        if not sub:
            continue
        f = SEG[lab][0]; w = 2 * np.pi * f
        Ie = np.array([(kr[0] - r["ReZ"]) / w ** 2 for r in sub])
        if base is None:
            base = Ie.mean()
        print(f"{lab:<16}{f:6.1f}{np.mean([r['A'] for r in sub]):7.2f}"
              f"{np.mean([r['ReZ'] for r in sub]):9.3f}{Ie.mean():10.5f}{Ie.std():9.5f}"
              f"{Ie.mean()/base:10.3f}{len(sub):6d}")

    # ── ④ q2 의존성 → Kv (M11 = Is1r + 2·Kv·cos q2) ──
    print("\n" + "=" * 120)
    print("④ 무릎 각도별 등가 관성 (2·3Hz 구간) — M11(q2) = Is1r + 2·Kv·cos q2 회귀")
    hi = [r for r in hip if r["f"] >= 2.0]
    X = np.column_stack([np.ones(len(hi)), 2 * np.cos(np.radians([r["q2"] for r in hi]))])
    yI = np.array([(kr[0] - r["ReZ"]) / (2 * np.pi * r["f"]) ** 2 for r in hi])
    kk, *_ = np.linalg.lstsq(X, yI, rcond=None)
    print(f"   Is1r = {kk[0]:+.5f} kg·m²   Kv = {kk[1]:+.5f} kg·m²")
    for q2t in (-110, -85, -62):
        sub = [v for r, v in zip(hi, yI) if abs(r["q2"] - q2t) < 6]
        pred = kk[0] + 2 * kk[1] * np.cos(np.radians(q2t))
        print(f"   q2={q2t:+5d}° : 실측 I_eff {np.mean(sub):.5f} ± {np.std(sub):.5f} (n={len(sub)}) "
              f"| 회귀 {pred:.5f}")

    # ── ⑤ 무릎 채널 ──
    print("\n" + "=" * 120)
    print("⑤ 무릎 가진 구간 (τ2/δq2) — 무릎쪽 관성·중력·마찰")
    kn = [r for r in rows if r["j"] == 2]
    if kn:
        Xr2 = np.array([[1.0, -(2 * np.pi * r["f"]) ** 2] for r in kn])
        yr2 = np.array([r["ReZ"] for r in kn])
        Xi2 = np.array([[2 * np.pi * r["f"], 4.0 / (np.pi * np.radians(r["A"]))] for r in kn])
        yi2 = np.array([r["ImZ"] for r in kn])
        k2, *_ = np.linalg.lstsq(Xr2, yr2, rcond=None)
        k2i, *_ = np.linalg.lstsq(Xi2, yi2, rcond=None)
        r2r = yr2 - Xr2 @ k2
        print(f"   무릎 중력 강성 k_g2 = {k2[0]:+.4f} Nm/rad · 등가 관성 Is2 = {k2[1]:+.5f} kg·m²")
        print(f"   점성 fv2 = {k2i[0]:+.5f} Nm·s/rad · 쿨롱 fc2 = {k2i[1]:+.4f} Nm")
        print(f"   실수부 잔차 RMS {np.sqrt(np.mean(r2r**2)):.4f} / 신호 std {yr2.std():.4f} "
              f"→ 설명력 {1-np.var(r2r)/np.var(yr2):.3f}")
        print(f"   기본파 일관성 평균 {np.mean([r['coh'] for r in kn]):.3f} "
              f"(힙 {np.mean([r['coh'] for r in hip]):.3f})")

    json.dump(dict(k_g=float(kr[0]), gA=float(gA), I=float(kr[1]), fv1=float(ki[0]),
                   fc1=float(ki[1]), Is1r=float(kk[0]), Kv=float(kk[1]),
                   rows=[{k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                          for k, v in r.items()} for r in rows]),
              io.open(HERE / "_G2_air_phasor.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: _G2_air_phasor.json")


if __name__ == "__main__":
    main()
