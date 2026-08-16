# -*- coding: utf-8 -*-
"""_G10b_scale — G10 후속: ①힙 채널 음수 회귀 진단 ②채널별 일 분해 ③**유효 동적 척도** 역산.

G10 결과 요약
  · 이지 재검출 후 h_예측/h_실측 = 0.980, ΔE/E_벌크 = 0.977, ∫τ_req·dq ≡ ΔE — 틀 검증됨
  · η(a_hat) 0.975 (11/45 가 **>1** = 에너지 창조 = 불가능) · η(정본) 0.554
  · 무릎 회귀 k2: a_hat 0.672(<1 불가) / 정본 1.084
  · **힙 회귀 k1 이 음수** → 규약 오류인지 실제 현상인지 가려야 한다

여기서 하는 것
  A. **정적 유지 구간(프리홀드) 교차검증** — dq≈0 이라 τ = ∂V/∂q 로 확정된다.
     이건 **접지 상태 그 자리에서의 저속 척도 시험**이라 분동·공중 시험과 완전 독립이다.
     힙 부호 문제도 여기서 바로 드러난다 (정적에서 부호가 맞으면 규약은 정상).
  B. 채널별 일 분해 — 힙이 음의 일을 하고 있다면 총일 해석이 달라진다.
  C. **유효 동적 척도 s** — s·W_정본 = ΔE + 관절마찰 + μ·∫N|ds| 를 μ=0.85 로 풀어 역산.
     s·τ_정본 이 a_hat 대비 몇 배인지가 최종 답.
CLI: python _G10b_scale.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                                    # noqa: E402
import fs_runner as FR                                  # noqa: E402
from _G10_energy import (Reduced, tau_canon, lpf, real_h, G, M_REAL,
                         FC1, FV1, FC2, FV2)            # noqa: E402

MU = 0.85          # 사용자 실측 정지마찰 (정적 홀드 게이트 값)
ARM = (0.010, 0.008)   # 트윈 armature (힙/무릎) — 회전자 반영관성 [kg·m²]


def main():
    R = Reduced(FR.fs_twin())
    ROWS = []
    for sess, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        hr = real_h(p)
        if hr is None:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
        except Exception:
            continue
        t = d["t"]; dt = float(np.median(np.diff(t)))
        q1 = lpf(d["q1"], 30.0); q2 = lpf(d["q2"], 30.0)
        v1 = np.gradient(q1, dt); v2 = np.gradient(q2, dt)
        lo, hi = seg["i_push"], min(seg["i_lo"] + int(0.06 / dt), len(t) - 3)
        zd = np.array([R.MV(q1[i], q2[i])["dzb"] @ np.array([v1[i], v2[i]]) for i in range(lo, hi)])
        i_to = lo + int(np.argmax(zd))
        i0 = seg["i_bot"] if i_to - seg["i_bot"] >= 30 else max(0, i_to - int(0.35 / dt))
        ROWS.append(dict(sess=sess, name=p.name, d=d, seg=seg, dt=dt, hr=hr,
                         q1=q1, q2=q2, v1=v1, v2=v2, i0=i0, i_to=i_to))

    # ────────────────── A. 정적 프리홀드 교차검증 ──────────────────
    print("=" * 126)
    print("Ⓐ ★★ 정적 유지(프리홀드) 교차검증 — dq≈0 이면 τ = ∂V/∂q 로 **확정**된다")
    print("   접지 상태 그 자리에서의 저속 척도 시험 (분동·공중과 완전 독립). 부호 규약도 여기서 판정.")
    print(f"{'세션':<11}{'trial':<19}{'표본':>6}{'|dq|max':>8}"
          f" | {'τ1_필요':>8}{'τ1_a_hat':>9}{'τ1_정본':>8}{'비 a':>6}{'비 c':>6}"
          f" | {'τ2_필요':>8}{'τ2_a_hat':>9}{'τ2_정본':>8}{'비 a':>6}{'비 c':>6}")
    ST = {"a1": [], "c1": [], "a2": [], "c2": []}
    for r in ROWS:
        m = r["seg"]["prehold"].copy()
        m &= (np.abs(r["v1"]) < 0.05) & (np.abs(r["v2"]) < 0.05)
        idx = np.flatnonzero(m)
        if len(idx) < 100:
            continue
        idx = idx[::max(1, len(idx) // 40)]
        gr = np.array([_dV(R, r["q1"][i], r["q2"][i]) for i in idx])
        ma = np.array([[r["d"]["a1"][i], r["d"]["a2"][i]] for i in idx])
        mc = np.array([[tau_canon(r["d"]["raw1"][i]), tau_canon(r["d"]["raw2"][i])] for i in idx])
        out = []
        for ch in range(2):
            q_ = np.mean(gr[:, ch]); a_ = np.mean(ma[:, ch]); c_ = np.mean(mc[:, ch])
            out += [q_, a_, c_, a_ / q_ if abs(q_) > 0.4 else np.nan,
                    c_ / q_ if abs(q_) > 0.4 else np.nan]
            if abs(q_) > 0.4:
                ST[f"a{ch+1}"].append(a_ / q_); ST[f"c{ch+1}"].append(c_ / q_)
        print(f"{r['sess']:<11}{r['name'][:18]:<19}{len(idx):6d}"
              f"{max(np.abs(r['v1'][idx]).max(), np.abs(r['v2'][idx]).max()):8.3f}"
              f" | {out[0]:8.3f}{out[1]:9.3f}{out[2]:8.3f}{out[3]:6.2f}{out[4]:6.2f}"
              f" | {out[5]:8.3f}{out[6]:9.3f}{out[7]:8.3f}{out[8]:6.2f}{out[9]:6.2f}")
    print(f"\n   {'채널':<7}{'환산':<7}{'측정/필요 중앙':>14}{'범위':>20}{'n':>5}")
    for ch, nm in ((1, "힙"), (2, "무릎")):
        for tag, lab in (("a", "a_hat"), ("c", "정본")):
            v = np.array(ST[f"{tag}{ch}"])
            if not len(v):
                continue
            print(f"   {nm:<7}{lab:<7}{np.median(v):14.3f}"
                  f"{f'[{v.min():.2f}, {v.max():.2f}]':>20}{len(v):5d}")
    print("   ※ 이 구간은 raw 가 작아 정본 곡선의 배율이 크다 (raw 5 → ×2.16). 저토크 척도 재확인.")

    # ────────────────── B. 채널별 일 분해 + C. 유효 척도 ──────────────────
    print("\n" + "=" * 126)
    print("Ⓑ 채널별 일 분해 · Ⓒ **유효 동적 척도 s** (s·W_정본 = ΔE + 관절마찰 + μ·∫N|ds|, μ=0.85)")
    print(f"{'세션':<11}{'trial':<19}{'W1_a':>7}{'W2_a':>7}{'W1_c':>7}{'W2_c':>7}"
          f"{'ΔE':>7}{'마찰':>6}{'슬립손':>7}{'필요일':>7}{'s_c':>6}{'s_a':>6}{'s·τc/a_hat':>11}")
    SC = {"a": [], "c": [], "rel": []}
    for r in ROWS:
        i0, i1, dt = r["i0"], r["i_to"], r["dt"]
        sl = slice(i0, i1 + 1)
        v1, v2 = r["v1"], r["v2"]
        s0 = R.MV(r["q1"][i0], r["q2"][i0]); s1 = R.MV(r["q1"][i1], r["q2"][i1])
        A = np.diag(ARM)
        dq0 = np.array([v1[i0], v2[i0]]); dq1 = np.array([v1[i1], v2[i1]])
        dE = (0.5 * dq1 @ (s1["M"] + A) @ dq1 + s1["V"]) - (0.5 * dq0 @ (s0["M"] + A) @ dq0 + s0["V"])
        tc1, tc2 = tau_canon(r["d"]["raw1"]), tau_canon(r["d"]["raw2"])
        W1a = float(np.trapezoid(r["d"]["a1"][sl] * v1[sl], dx=dt))
        W2a = float(np.trapezoid(r["d"]["a2"][sl] * v2[sl], dx=dt))
        W1c = float(np.trapezoid(tc1[sl] * v1[sl], dx=dt))
        W2c = float(np.trapezoid(tc2[sl] * v2[sl], dx=dt))
        Wjf = float(np.trapezoid(FC1 * np.abs(v1[sl]) + FV1 * v1[sl] ** 2
                                 + FC2 * np.abs(v2[sl]) + FV2 * v2[sl] ** 2, dx=dt))
        S = [R.MV(r["q1"][i], r["q2"][i]) for i in range(i0, i1 + 1, 3)]
        vv = np.array([[lpf(v1, 20.0)[i], lpf(v2, 20.0)[i]] for i in range(i0, i1 + 1, 3)])
        vx = np.array([s["dxf"] @ vv[k] for k, s in enumerate(S)])
        vth = np.array([s["dth"] @ vv[k] for k, s in enumerate(S)])
        zc = np.array([s["zc"] for s in S])
        acc = np.gradient(np.gradient(zc, 3 * dt), 3 * dt)
        N = np.maximum(M_REAL * (G + acc), 0.0)
        Wsl = MU * float(np.trapezoid(N * np.abs(vx - R.r * vth), dx=3 * dt))
        need = dE + Wjf + Wsl
        sc = need / max(W1c + W2c, 1e-9); sa = need / max(W1a + W2a, 1e-9)
        # 같은 raw 에서 s·τ_정본 이 a_hat 의 몇 배인가 (푸시 대표 raw = |raw2| 평균)
        rr = float(np.mean(np.abs(r["d"]["raw2"][sl])))
        rel = sc * float(tau_canon(rr)) / max(float(FD.ahat_np(np.array([rr]), np.array([5.0]))[0]), 1e-9)
        SC["c"].append(sc); SC["a"].append(sa); SC["rel"].append(rel)
        print(f"{r['sess']:<11}{r['name'][:18]:<19}{W1a:7.2f}{W2a:7.2f}{W1c:7.2f}{W2c:7.2f}"
              f"{dE:7.2f}{Wjf:6.2f}{Wsl:7.2f}{need:7.2f}{sc:6.2f}{sa:6.2f}{rel:11.2f}")
    for k, lab in (("a", "a_hat"), ("c", "정본")):
        v = np.array(SC[k])
        print(f"   필요 배율 s({lab}) 중앙 {np.median(v):.3f}  범위 [{v.min():.3f}, {v.max():.3f}]"
              f"   — 1.0 이면 그 환산이 맞다는 뜻")
    v = np.array(SC["rel"])
    print(f"   ★ 보정된 푸시 실효토크 / a_hat  중앙 {np.median(v):.3f}  "
          f"범위 [{v.min():.3f}, {v.max():.3f}]")
    json.dump(dict(s_canon=list(map(float, SC["c"])), s_ahat=list(map(float, SC["a"])),
                   rel_ahat=list(map(float, SC["rel"]))),
              io.open(HERE / "_G10b_scale.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장: _G10b_scale.json")


def _dV(R, q1, q2, h=1e-3):
    """∂V/∂q — 정적 유지에 필요한 관절토크 (마찰 제외)."""
    return np.array([(R.MV(q1 + h, q2)["V"] - R.MV(q1 - h, q2)["V"]) / (2 * h),
                     (R.MV(q1, q2 + h)["V"] - R.MV(q1, q2 - h)["V"]) / (2 * h)])


if __name__ == "__main__":
    main()
