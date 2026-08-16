# -*- coding: utf-8 -*-
"""_G7_pdlaw — 보고 토크가 따르는 **PD 법칙의 실효 게인** 정밀 검증 (사용자 지적 08-07).

배경: 26_08_07 probe(0.04Hz 준정적)에서 kp≈151·kd≈0 이 나왔다. 그러나 사용자 지적 —
  "dq_des=0 제어와 dq_des 정상 인가 제어의 결과가 다르다" → kd 가 0 일 리 없다.
의심되는 결함:
  ① probe 는 **저속**(|dq|≤0.6, 스윕 중엔 0.09 rad/s)이라 kd 항의 신호가 거의 없다
  ② 기록 dq 의 양자화 잡음(계단 0.0244 rad/s)이 회귀자에 실려 **계수를 0으로 끌어내린다**
     (errors-in-variables 감쇠)
→ **26_08_02 공중 사인 가진**으로 검증한다: |dq| 3.3 rad/s (55배), 1~3Hz 로 kd 항이 지배적,
  게다가 **무릎 kp 120/250/500 3종**이라 "실효 kp 가 명령 kp 를 따라가는가"를 직접 볼 수 있다.
CLI: python _G7_pdlaw.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                       # noqa: E402

S02 = FD.ROOT / "26_08_02"
S07 = FD.ROOT / "26_08_07"
Q = 0.008791        # 토크 채널 양자화 계단 [raw]


def rd(fold, f):
    s = pd.read_excel(fold / f)
    return dict(q=s["currentAngle"].to_numpy(float), qd=s["desiredAngle"].to_numpy(float),
                v=s["currentAngleVelocity"].to_numpy(float),
                vd=s["desiredAngleVelocity"].to_numpy(float),
                y=s["currentTorque"].to_numpy(float))


def fit_pd(d, skew, mask=None, cols=("e", "ed", "1")):
    e = np.roll(d["qd"], skew) - d["q"]
    ed = np.roll(d["vd"], skew) - d["v"]
    m = np.zeros(len(e), bool); m[skew + 10:len(e) - 10] = True
    if mask is not None:
        m &= mask
    A = []
    for c in cols:
        A.append({"e": e, "ed": ed, "1": np.ones(len(e))}[c])
    A = np.column_stack(A)[m]
    th, *_ = np.linalg.lstsq(A, d["y"][m], rcond=None)
    r = d["y"][m] - A @ th
    return th, float(np.sqrt(np.mean(r ** 2))), 1 - np.var(r) / np.var(d["y"][m]), int(m.sum()), e, ed, m


def indep(e, ed, m):
    """ed 열이 e 로 설명되지 않는 비율 (1에 가까울수록 독립 = kd 식별 양호)."""
    A = np.column_stack([e[m], np.ones(m.sum())])
    c, *_ = np.linalg.lstsq(A, ed[m], rcond=None)
    r = ed[m] - A @ c
    return float(np.var(r) / max(np.var(ed[m]), 1e-20))


def main():
    print("=" * 118)
    print("① 26_08_02 공중 사인 가진 — 명령 게인 hip 150/2.2 · knee {120,250,500}/3")
    print(f"{'게인폴더':<16}{'trial':<8}{'채널':<6}{'스큐':>5}{'실효kp':>9}{'명령kp':>7}{'α_kp':>7}"
          f"{'실효kd':>9}{'명령kd':>7}{'α_kd':>7}{'잔차':>8}{'R²':>9}{'ed독립성':>9}{'|dq|max':>9}")
    rows = []
    for g in sorted(p for p in S02.iterdir() if p.is_dir()):
        kp1, kd1, kp2, kd2 = (float(x) for x in g.name.split("_"))
        for tr in sorted(p for p in g.iterdir() if p.is_dir()):
            if not (tr / "hip.xlsx").exists():
                continue
            for f, ch, KP, KD in (("hip.xlsx", "힙", kp1, kd1), ("knee.xlsx", "무릎", kp2, kd2)):
                d = rd(tr, f)
                best = None
                for sk in range(0, 5):
                    th, rms, r2, n, e, ed, m = fit_pd(d, sk)
                    if best is None or rms < best[1]:
                        best = (th, rms, r2, n, e, ed, m, sk)
                th, rms, r2, n, e, ed, m, sk = best
                ind = indep(e, ed, m)
                rows.append(dict(gain=g.name, tr=tr.name.split("_")[2], ch=ch, kp=th[0], kd=th[1],
                                 KP=KP, KD=KD, rms=rms, r2=r2, ind=ind, sk=sk))
                print(f"{g.name:<16}{tr.name.split('_')[2]:<8}{ch:<6}{sk:5d}{th[0]:9.2f}{KP:7.0f}"
                      f"{th[0]/KP:7.3f}{th[1]:9.3f}{KD:7.1f}{th[1]/KD:7.3f}{rms:8.4f}{r2:9.5f}"
                      f"{ind:9.3f}{np.abs(d['v']).max():9.2f}")

    print("\n" + "=" * 118)
    print("② 요약 — α_kp 와 α_kd 가 명령 게인에 따라 어떻게 변하나")
    print(f"{'채널':<6}{'명령kp':>8}{'trial수':>8}{'α_kp 평균':>11}{'±':>8}{'α_kd 평균':>11}{'±':>8}"
          f"{'ed독립성':>10}{'R² 평균':>9}")
    for ch in ("힙", "무릎"):
        for KP in sorted({r["KP"] for r in rows if r["ch"] == ch}):
            sub = [r for r in rows if r["ch"] == ch and r["KP"] == KP]
            ak = np.array([r["kp"] / r["KP"] for r in sub])
            ad = np.array([r["kd"] / r["KD"] for r in sub])
            print(f"{ch:<6}{KP:8.0f}{len(sub):8d}{ak.mean():11.3f}{ak.std():8.3f}"
                  f"{ad.mean():11.3f}{ad.std():8.3f}{np.mean([r['ind'] for r in sub]):10.3f}"
                  f"{np.mean([r['r2'] for r in sub]):9.5f}")

    print("\n" + "=" * 118)
    print("③ ★ kd 식별력 진단 — probe(저속) vs 사인가진(고속) 에서 kd 항이 만드는 신호 크기")
    print(f"{'데이터':<28}{'|dq|max':>9}{'kd·ė std [raw]':>16}{'kp·e std [raw]':>16}"
          f"{'ė 잡음 std':>11}{'ė SNR':>8}{'감쇠추정':>9}")
    def diag(lab, d, KP, KD):
        e = np.roll(d["qd"], 2) - d["q"]; ed = np.roll(d["vd"], 2) - d["v"]
        m = np.zeros(len(e), bool); m[20:-20] = True
        # ė 잡음: 정지 구간(|v|<0.05)에서의 ed 산포
        st = np.abs(d["v"]) < 0.05
        nz = float(np.std(ed[st])) if st.sum() > 200 else float("nan")
        sn = float(np.std(ed[m])) / max(nz, 1e-9)
        att = sn ** 2 / (1 + sn ** 2)
        print(f"{lab:<28}{np.abs(d['v']).max():9.2f}{KD*np.std(ed[m]):16.4f}{KP*np.std(e[m]):16.4f}"
              f"{nz:11.4f}{sn:8.2f}{att:9.3f}")
    for g in ("150_2.2_250_3",):
        for tr in ("sysid_air_k095_v1",):
            diag(f"26_08_02 {tr[10:14]} 힙", rd(S02 / g / tr, "hip.xlsx"), 150, 2.2)
            diag(f"26_08_02 {tr[10:14]} 무릎", rd(S02 / g / tr, "knee.xlsx"), 250, 3.0)
    diag("26_08_07 sweep 힙", rd(S07 / "0kg" / "probe_sweep_v1", "hip.xlsx"), 150, 2.2)
    diag("26_08_07 sweep 무릎", rd(S07 / "0kg" / "probe_sweep_v1", "knee.xlsx"), 250, 3.0)
    diag("26_08_07 hold3 힙", rd(S07 / "0kg" / "probe_hold3_v2", "hip.xlsx"), 150, 2.2)
    print("   ※ 감쇠추정 = SNR²/(1+SNR²) — 회귀자 잡음이 계수를 이만큼으로 끌어내린다 (errors-in-variables)")

    # ── ④ 구간별 (가진 주파수별) ──
    print("\n" + "=" * 118)
    print("④ 26_08_02 가진 구간별 실효 게인 — 주파수가 오를수록 kd 신호가 커진다")
    sys.path.insert(0, str(HERE))
    from _G2_air_align import design, load_uniform, align, KNEE_TAG
    tr = S02 / "150_2.2_250_3" / "sysid_air_k095_v1"
    du = load_uniform(tr)
    off, lab, _, _ = align(du, KNEE_TAG["k095"])
    lab = lab[:len(du["t"]) - off]
    sl = slice(off, off + len(lab))
    d = dict(q=du["q1"][sl], qd=du["qd1"][sl], v=du["dq1"][sl], vd=du["dqd1"][sl],
             y=du["raw1"][sl])
    print(f"{'구간':<18}{'표본':>7}{'실효kp':>9}{'α_kp':>7}{'실효kd':>9}{'α_kd':>7}{'ed독립성':>9}{'R²':>9}")
    for nm in dict.fromkeys(lab):
        m0 = lab == nm
        if m0.sum() < 800:
            continue
        th, rms, r2, n, e, ed, m = fit_pd(d, 2, mask=m0)
        print(f"{nm:<18}{n:7d}{th[0]:9.2f}{th[0]/150:7.3f}{th[1]:9.3f}{th[1]/2.2:7.3f}"
              f"{indep(e,ed,m):9.3f}{r2:9.5f}")


if __name__ == "__main__":
    main()
