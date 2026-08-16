# -*- coding: utf-8 -*-
"""_G2_air_ident — 26_08_02 **최종 동정** (위상자 기반 + 부트스트랩 신뢰구간).

_G2_air_phasor 의 1차 위상자 결과를 정밀화한다:
  · 실수부: 무릎 3자세(q2 = −110/−85/−62°)가 **gA 와 gB 를 분리**한다
      Re Z_hip  = (−sin q1₀)·gA + (−sin(q1₀+q2))·gB − ω²·(Is1r + 2·Kv·cos q2)
      Re Z_knee = (−sin(q1₀+q2))·gB − ω²·Is2
    → 미지수 5개(gA, gB, Is1r, Kv, Is2)를 힙 36점 + 무릎 18점 = 54점으로 동시 적합.
    DC 오프셋(off1/off2)은 기본파 추출 단계에서 이미 제거돼 **축퇴가 원리적으로 없다**.
  · 허수부: Im Z = ω·fv + 4·fc/(π·A)  (쿨롱 기술함수) — 힙은 (ω,A) 4조합으로 양호,
    무릎은 2조합뿐이라 조건수가 나쁨 → 조건수도 함께 보고한다.
  · 신뢰구간: **trial 단위 부트스트랩** (표본 자기상관에 오염되지 않는 정직한 오차막대).
CLI: python _G2_air_ident.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from _G2_air_fit import prep, FS, DT                       # noqa: E402
from _G2_air_align import trials                           # noqa: E402
from _G2_air_phasor import SEG, phasor, seg_slices         # noqa: E402

RNG = np.random.default_rng(7)
NB = 2000


def collect():
    """trial × 구간 → 위상자 관측 리스트."""
    obs = []
    for t in trials():
        d = prep(t, "smooth", 1)
        rec = []
        for lab, (f, A, j) in SEG.items():
            for c in (seg_slices(d, lab, f) or []):
                tt = np.arange(len(c)) * DT
                q = d["q1"][c] if j == 1 else d["q2"][c]
                tau = d["t1"][c] if j == 1 else d["t2"][c]
                Q = phasor(q - q.mean(), tt, f)
                TAU = phasor(tau - tau.mean(), tt, f)
                Z = TAU / Q
                rec.append(dict(f=f, j=j, A=float(np.abs(Q)), ReZ=Z.real, ImZ=Z.imag,
                                q1=float(d["q1"][c].mean()), q2=float(d["q2"][c].mean()),
                                lab=lab))
        obs.append(dict(trial=f"{t.parent.name}/{t.name.split('_')[2]}", rec=rec))
    return obs


def fit_real(recs):
    """[gA, gB, Is1r, Kv, Is2] 동시 적합."""
    X, y = [], []
    for r in recs:
        w2 = (2 * np.pi * r["f"]) ** 2
        q1, q2 = r["q1"], r["q2"]
        if r["j"] == 1:
            X.append([-np.sin(q1), -np.sin(q1 + q2), -w2, -2 * w2 * np.cos(q2), 0.0])
        else:
            X.append([0.0, -np.sin(q1 + q2), 0.0, 0.0, -w2])
        y.append(r["ReZ"])
    X = np.array(X); y = np.array(y)
    th, *_ = np.linalg.lstsq(X, y, rcond=None)
    return th, X, y


def fit_imag(recs, j):
    """[fv, fc] — Im Z = ω·fv + 4·fc/(π·A)."""
    X, y = [], []
    for r in recs:
        if r["j"] != j:
            continue
        w = 2 * np.pi * r["f"]
        X.append([w, 4.0 / (np.pi * r["A"])])
        y.append(r["ImZ"])
    X = np.array(X); y = np.array(y)
    th, *_ = np.linalg.lstsq(X, y, rcond=None)
    return th, X, y


def boot(obs, fn):
    """**층화** 부트스트랩: 무릎 자세(k070/k095/k118) 그룹 안에서만 재표본.
    단순 재표본은 자세 다양성을 잃은 표본을 뽑아(예: k095만 3개) gA/gB·Is1r/Kv 축퇴를
    일으켜 표준편차만 비정상적으로 부풀린다 — 설계의 자세 3점을 보존해야 한다."""
    strata = {}
    for i, o in enumerate(obs):
        strata.setdefault(o["trial"].split("/")[1], []).append(i)
    out = []
    for _ in range(NB):
        pick = [g[k] for g in strata.values() for k in RNG.integers(0, len(g), len(g))]
        recs = [r for i in pick for r in obs[i]["rec"]]
        try:
            out.append(fn(recs))
        except Exception:
            pass
    return np.array(out)


def main():
    obs = collect()
    allrec = [r for o in obs for r in o["rec"]]

    th, X, y = fit_real(allrec)
    res = y - X @ th
    B = boot(obs, lambda r: fit_real(r)[0])
    lo, hi = np.percentile(B, [2.5, 97.5], axis=0)
    sd = B.std(axis=0)
    NM = ["gA", "gB", "Is1r", "Kv", "Is2"]
    UN = ["Nm", "Nm", "kg·m²", "kg·m²", "kg·m²"]

    print("=" * 108)
    print("① 실수부 동시 적합 — 중력(gA·gB)과 관성(Is1r·Kv·Is2)  [DC 오프셋 원리적 제거]")
    print(f"   관측 {len(allrec)}점 (힙 {sum(1 for r in allrec if r['j']==1)} + "
          f"무릎 {sum(1 for r in allrec if r['j']==2)}) · 잔차 RMS {np.sqrt(np.mean(res**2)):.4f} "
          f"· 설명력 {1-np.var(res)/np.var(y):.4f}")
    print(f"{'항':<7}{'단위':<8}{'추정값':>12}{'부트 표준편차':>13}{'95% 신뢰구간':>26}{'상대오차%':>10}{'판정':>8}")
    verdict = {}
    for i, n in enumerate(NM):
        rel = 0.5 * (hi[i] - lo[i]) / abs(th[i]) * 100      # 신뢰구간 반폭 기준 (꼬리에 강건)
        v = "신뢰" if rel < 10 else ("주의" if rel < 30 else "미식별")
        verdict[n] = v
        print(f"{n:<7}{UN[i]:<8}{th[i]:+12.5f}{sd[i]:13.5f}"
              f"{f'[{lo[i]:+.5f}, {hi[i]:+.5f}]':>26}{rel:10.1f}{v:>8}")
    # 조건수
    s = np.linalg.svd(X / np.linalg.norm(X, axis=0), compute_uv=False)
    print(f"   설계행렬 조건수 {s[0]/s[-1]:.1f} (작을수록 항끼리 잘 분리됨)")

    print("\n" + "=" * 108)
    print("② 허수부 — 마찰 (Im Z = ω·fv + 4·fc/(π·A), 쿨롱 기술함수)")
    print(f"{'관절':<7}{'fv[Nm·s/rad]':>16}{'±':>10}{'fc[Nm]':>12}{'±':>10}{'조건수':>9}{'설명력':>8}")
    fr = {}
    for j, lab in ((1, "힙"), (2, "무릎")):
        ti, Xi, yi = fit_imag(allrec, j)
        Bi = boot(obs, lambda r, j=j: fit_imag(r, j)[0])
        sdi = Bi.std(axis=0)
        ri = yi - Xi @ ti
        si = np.linalg.svd(Xi / np.linalg.norm(Xi, axis=0), compute_uv=False)
        fr[lab] = (ti, sdi)
        print(f"{lab:<7}{ti[0]:16.5f}{sdi[0]:10.5f}{ti[1]:12.4f}{sdi[1]:10.4f}"
              f"{si[0]/si[-1]:9.1f}{1-np.var(ri)/np.var(yi):8.3f}")

    print("\n" + "=" * 108)
    print("③ 실측 M11(q2) = Is1r + 2·Kv·cos q2  — 트윈 비교용 정본 값")
    Bm = {}
    for q2d in (-110, -85, -62):
        c = np.cos(np.radians(q2d))
        v = th[2] + 2 * th[3] * c
        bv = B[:, 2] + 2 * B[:, 3] * c
        Bm[q2d] = (v, bv.std(), np.percentile(bv, [2.5, 97.5]))
        print(f"   q2 = {q2d:+5d}° : M11 = {v:.5f} ± {bv.std():.5f} kg·m²  "
              f"95%[{Bm[q2d][2][0]:.5f}, {Bm[q2d][2][1]:.5f}]")

    print("\n" + "=" * 108)
    print("④ 주파수 무관성 검사 (직렬 탄성 = 벨트 SEA 유무) — 잔차를 주파수별로 본다")
    print(f"{'가진':<16}{'f[Hz]':>6}{'관측수':>7}{'평균 잔차':>10}{'잔차 std':>10}{'신호 |ReZ|':>11}{'상대%':>8}")
    for lab in SEG:
        idx = [i for i, r in enumerate(allrec) if r["lab"] == lab]
        if not idx:
            continue
        rr = res[idx]
        mag = np.mean([abs(allrec[i]["ReZ"]) for i in idx])
        print(f"{lab:<16}{SEG[lab][0]:6.1f}{len(idx):7d}{rr.mean():10.4f}{rr.std():10.4f}"
              f"{mag:11.3f}{100*abs(rr.mean())/max(mag,1e-9):8.1f}")
    print("   → 잔차 평균이 주파수에 따라 **한 방향으로 커지면** 직렬 탄성 신호,")
    print("      부호가 섞이고 크기가 작으면 강체(현행 트윈 구조) 유지가 옳다.")

    out = dict(names=NM, theta=[float(v) for v in th], sd=[float(v) for v in sd],
               ci_lo=[float(v) for v in lo], ci_hi=[float(v) for v in hi], verdict=verdict,
               M11={str(k): [float(v[0]), float(v[1])] for k, v in Bm.items()},
               fric={k: [[float(x) for x in v[0]], [float(x) for x in v[1]]] for k, v in fr.items()},
               n_obs=len(allrec), resid_rms=float(np.sqrt(np.mean(res ** 2))))
    json.dump(out, io.open(HERE / "_G2_air_ident.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: _G2_air_ident.json")


if __name__ == "__main__":
    main()
