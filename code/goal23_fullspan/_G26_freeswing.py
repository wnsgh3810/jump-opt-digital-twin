# -*- coding: utf-8 -*-
"""_G26_freeswing — **토크 센서를 전혀 쓰지 않는** 관절 마찰 측정 (무동력 자유진동 감쇠, 08-08).

왜 이게 중요한가
  지금까지 관절 마찰(쿨롱 fc, 점성 b)은 **공중 가진 회귀**로 얻었는데, 그건 `a_hat` 으로 변환한
  토크를 썼다 → **토크 척도 오차가 그대로 실린다**. G19 에서 마찰이 J_G 에 가장 민감한 축으로
  드러났으므로, **척도와 무관한 마찰 측정**이 있어야 판이 열린다.

원리 (고등학교 물리 수준)
  모터를 끄고 다리를 흔들면 진폭이 점점 줄어든다. **줄어드는 모양**이 마찰의 종류를 말해준다.
  · **쿨롱(마른 마찰)**: 매 반주기마다 진폭이 **같은 양만큼** 줄어든다 → 직선
      Δθ(반주기) = 2·fc / gA        (fc: 쿨롱 토크, gA: 중력 복원계수)
  · **점성(끈적한 마찰)**: 매 반주기마다 진폭이 **같은 비율로** 줄어든다 → 지수
      θ_{n+1} / θ_n = exp(−b·T/(2·I))
  ⇒ 진폭 수열을 (반주기 번호 vs 진폭)으로 놓고 **직선/지수** 어느 쪽인지 보면 분리된다.
  ⇒ gA(=1.48~1.62, 분동 교정, 척도 무관) 와 I(=자유진동 주기, 척도 무관) 만 있으면
    **fc 와 b 가 Nm 단위로 확정**된다. **토크 센서 불개입.**

데이터: `26_08_07/no_current` (모터 전원 OFF, 무릎 각도 3종 × 힙 놓기) — G3-F/G5-C 와 동일 원본,
        단 그때는 **정지점(평형각)과 주기**만 썼고 **감쇠(진폭 수열)는 미사용**이었다.
CLI: python _G26_freeswing.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                                          # noqa: E402

SESS = FD.ROOT / "26_08_07" / "no_current"
GA = 1.5410            # 힙 중력 복원계수 [Nm] — 분동 교정 (G3-C/G8-D, 척도 무관)
I_HIP = 0.0530         # 힙축 총관성 [kg·m²] — 자유진동 주기 (G5-C, 척도 무관)


def load(fold):
    h = pd.read_excel(fold / "hip.xlsx"); k = pd.read_excel(fold / "knee.xlsx")
    n = min(len(h), len(k))
    t = np.array(h["Time"].to_numpy(float)[:n], float, copy=True); t -= t[0]
    return dict(t=t, q1=h["currentAngle"].to_numpy(float)[:n],
                q2=k["currentAngle"].to_numpy(float)[:n],
                v1=h["currentAngleVelocity"].to_numpy(float)[:n], n=n)


def turns(t, q, v, vth=0.30):
    """방향 전환점(반주기 경계) 인덱스 — 속도 부호 반전 (양자화 잡음 문턱 vth)."""
    s = np.sign(v); s[np.abs(v) < vth] = 0
    out, last = [], 0
    for i in range(len(s)):
        if s[i] != 0:
            if last != 0 and s[i] != last:
                out.append(i)
            last = s[i]
    return out


def main():
    if not SESS.exists():
        print(f"데이터 없음: {SESS}")
        return
    # no_current 는 하위폴더 없이 xlsx 가 바로 있다 (실측 구조 확인 08-08)
    folds = [SESS] if (SESS / "hip.xlsx").exists() else sorted(p for p in SESS.iterdir() if p.is_dir())
    print("=" * 112)
    print("① 무동력 자유진동 구간 탐색 (모터 OFF · 토크 센서 불개입)")
    print(f"   앵커: gA = {GA} Nm (분동 교정) · I = {I_HIP} kg·m² (자유진동 주기) — 둘 다 척도 무관")
    print(f"{'trial':<26}{'표본':>7}{'길이s':>7}{'q2[°]':>8}{'반주기수':>9}{'진폭 초/말[°]':>15}")
    ALL = []
    for f in folds:
        try:
            d = load(f)
        except Exception:
            continue
        tr = turns(d["t"], d["q1"], d["v1"])
        if len(tr) < 4:
            continue
        # ★ 08-08 정정: no_current 는 **여러 번의 개별 놓기 실험**이 한 파일에 이어져 있다.
        #   통짜로 진폭 수열을 만들면 놓기마다 진폭이 리셋돼 감쇠 적합이 무의미해진다
        #   (1차 시도: 진폭 29.06 → 32.67 로 **증가**, R² 0.12/0.14 = 실패).
        #   ⇒ **연속 반주기 묶음(burst)** 으로 먼저 분할한 뒤 묶음 안에서만 감쇠를 본다.
        segs, cur = [], []
        for i in range(len(tr) - 1):
            a, b = tr[i], tr[i + 1]
            dt_ = d["t"][b] - d["t"][a]
            if 0.20 < dt_ < 1.6:
                cur.append((abs(np.degrees(d["q1"][b] - d["q1"][a])) / 2, dt_))
            else:
                if len(cur) >= 3:
                    segs.append(cur)
                cur = []
        if len(cur) >= 3:
            segs.append(cur)
        q2m = float(np.degrees(np.median(d["q2"])))
        for j, sg in enumerate(segs):
            amp = np.array([x[0] for x in sg]); half = np.array([x[1] for x in sg])
            ALL.append(dict(name=f"{f.name}#{j+1}", amp=amp, half=half, q2=q2m))
            print(f"{(f.name+'#'+str(j+1))[:25]:<26}{d['n']:7d}{d['t'][-1]:7.1f}{q2m:8.1f}"
                  f"{len(amp):9d}{amp[0]:8.2f}/{amp[-1]:6.2f}")

    if not ALL:
        print("   자유진동 구간 미검출")
        return

    # ── ② 감쇠 모양 판별 ──
    print("\n" + "=" * 112)
    print("② ★ 감쇠 모양 판별 — 직선(쿨롱) vs 지수(점성)")
    print("   쿨롱이면 진폭이 매 반주기 **같은 양** 감소 · 점성이면 **같은 비율** 감소")
    print(f"{'trial':<26}{'n':>4}{'직선 R²':>9}{'지수 R²':>9}{'판정':>10}"
          f"{'Δ진폭/반주기[°]':>16}{'감쇠비 r':>10}")
    FC, BV = [], []
    for r in ALL:
        a = r["amp"]; k = np.arange(len(a))
        # 직선 적합 a = a0 − s·k
        A1 = np.column_stack([k, np.ones(len(k))])
        c1, *_ = np.linalg.lstsq(A1, a, rcond=None)
        r1 = 1 - np.var(a - A1 @ c1) / max(np.var(a), 1e-12)
        # 지수 적합 log a = log a0 − λ·k
        m = a > 0.05
        if m.sum() < 3:
            continue
        A2 = np.column_stack([k[m], np.ones(m.sum())])
        c2, *_ = np.linalg.lstsq(A2, np.log(a[m]), rcond=None)
        r2 = 1 - np.var(np.log(a[m]) - A2 @ c2) / max(np.var(np.log(a[m])), 1e-12)
        s_lin = -c1[0]                                  # 반주기당 진폭 감소 [deg]
        ratio = float(np.exp(c2[0]))                    # 반주기당 진폭 비
        # 물리 환산
        fc = GA * np.radians(s_lin) / 2.0               # 쿨롱 [Nm]  (Δθ = 2 fc / gA)
        Th = float(np.median(r["half"])) * 2.0          # 전주기 [s]
        b = -2.0 * I_HIP * np.log(max(ratio, 1e-6)) / max(Th / 2, 1e-6)   # 점성 [Nm·s/rad]
        FC.append(fc); BV.append(b)
        print(f"{r['name'][:25]:<26}{len(a):4d}{r1:9.4f}{r2:9.4f}"
              f"{'쿨롱' if r1 > r2 else '점성':>10}{s_lin:16.3f}{ratio:10.4f}")

    print("\n" + "=" * 112)
    print("③ ★★ 척도 무관 마찰 추정치 (토크 센서 전혀 안 씀)")
    fc = np.array(FC); bv = np.array(BV)
    f = lambda x: f"{np.median(x):.4f} [{np.percentile(x,10):.4f}, {np.percentile(x,90):.4f}]"
    print(f"   쿨롱 fc  (전부 쿨롱 가정)  {f(fc)} Nm")
    print(f"   점성 b   (전부 점성 가정)  {f(bv)} Nm·s/rad")
    print()
    print(f"   {'':<28}{'본 측정(척도무관)':>20}{'트윈 현행':>12}{'공중동정(a_hat)':>18}")
    print(f"   {'힙 쿨롱 [Nm]':<28}{np.median(fc):20.4f}{0.2383:12.4f}{0.187:18.3f}")
    print(f"   {'힙 점성 [Nm·s/rad]':<28}{np.median(bv):20.4f}{0.3121:12.4f}{0.0594:18.4f}")
    print()
    print("   ※ 두 값은 **상한**이다 (한 종류가 전부라고 가정했으므로).")
    print("     실제는 둘의 혼합이며, 직선/지수 R² 비교가 어느 쪽이 지배적인지 말해준다.")
    json.dump(dict(fc=list(map(float, fc)), b=list(map(float, bv)),
                   gA=GA, I=I_HIP), io.open(HERE / "_G26_freeswing.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: _G26_freeswing.json")


if __name__ == "__main__":
    main()
