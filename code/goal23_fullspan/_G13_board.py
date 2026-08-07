# -*- coding: utf-8 -*-
"""_G13_board — 마라톤 G 심판 보드 (지표 선고정, 이후 불변).

═══════════════════ 지표 정의 (2026-08-08 고정 — 마라톤 종료까지 변경 금지) ═══════════════════
  J_G = 0.50·Ê_MA + 0.30·Ê_h + 0.20·Ê_slip        (p24 기준 정규화 → p24 = 1.000, **낮을수록 좋음**)

  Ê_MA   = mean_세션 [ mean_채널 ( RMSE_ch,세션 / RMSE_ch,세션(p24) ) ],  채널 = q1(thm1)·q2·dq1·dq2
           ※ τ 는 ModeA 에서 **주입값**이라 채점 제외 (자기채점 금지)
           ※ q1 은 반드시 thm1(모터측)로 채점 — 사지각 비교는 직렬 처짐이 유령 오차 (PLAYBOOK §7)
  Ê_h    = mean_trial |h_sim/h_영상 − 1|            / 같은 값(p24)
           ※ h_영상 = Real Data.txt "실제 점프 높이" (**영상 실측 = A급**, 사용자 확정 08-07)
  Ê_slip = mean_trial |slip_sim − slip_기하|        / mean_trial |slip_기하|,  다시 p24 로 정규화
           ※ slip = Δx_foot − r·Δθ_foot (r=21mm).  기하 요구량 = 측정 (q1,q2) 강제값 (_G12)
           ※ 발 롤러는 **종아리와 한 덩어리 금속** (사용자 확정 08-08) → 구름분이 관절각으로 확정

  창 = fs_data.plot_window (원본 xlsx 스팬, PLAYBOOK §11) · 푸시 창 = [max(i0,i_push), i_lo]
  게이트(하드): held-out 0324 · gate 0421 의 MA q1·q2 악화 ≤ max(5%, 0.05)
════════════════════════════════════════════════════════════════════════════════════════════

CLI: python _G13_board.py <tag>        # tag=p24 로 첫 실행하면 기준 저장
"""
import os, sys, io, json, re
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                                          # noqa: E402
import fs_runner as FR                                        # noqa: E402
from _G10_energy import Reduced, lpf, real_h                  # noqa: E402

CH = ("q1", "q2", "dq1", "dq2")
W = dict(MA=0.50, h=0.30, slip=0.20)
REF = HERE / "_G13_ref_p24.json"


def slip_of(x, th, r):
    """Δx − r·Δθ (부호 있는 순수 미끄럼)."""
    return float((x[-1] - x[0]) - r * (th[-1] - th[0])) * 1000.0


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "x"
    R = Reduced(FR.fs_twin())
    ft = FR.fs_twin(); SP = FR._sess_params()
    rows = []
    print(f"보드 실행: tag={tag}")
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        hv = real_h(p)
        try:
            d = FD.load2(p); seg = FD.segment(d)
            pw = FD.plot_window(p, d)
            if pw is None:
                continue
            tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1])
            if m.sum() < 30:
                continue
            i0 = int(np.argmax(m))
            t_end = min(tt[m][-1] + 0.6, tt[-1])          # h 판독용 연장 (이지 후 +0.6s)
            m2 = (tt >= tt[i0]) & (tt <= t_end)
            t = tt[m2] - tt[i0]
            sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
            L = FR.rollout_ol_fs_b(ft, t, d["raw1"][m2], d["raw2"][m2],
                                   float(d["q1"][i0]), float(d["q2"][i0]),
                                   float(d["dq1"][i0]), float(d["dq2"][i0]),
                                   float(t[-1] - 0.004), bias1=sp["bias1"],
                                   knee_deep=sp["knee_deep"], fade=True)
            if L is None:
                continue
            # ── MA RMSE (채점 창 = plot_window 만) ──
            ts = tt[m] - tt[i0]
            gm = lambda k: np.interp(ts, L["t"], L[k])
            e = dict(q1=np.sqrt(np.mean((np.degrees(gm("thm1") - d["q1"][m])) ** 2)),
                     q2=np.sqrt(np.mean((np.degrees(gm("q2") - d["q2"][m])) ** 2)),
                     dq1=np.sqrt(np.mean((gm("dq1") - d["dq1"][m]) ** 2)),
                     dq2=np.sqrt(np.mean((gm("dq2") - d["dq2"][m]) ** 2)))
            # ── h ──
            hs = float(np.asarray(L["bz"], float).max())
            eh = abs(hs / hv - 1.0) if hv else np.nan
            # ── slip (push 창) ──
            a = max(i0, seg["i_push"]); b = seg["i_lo"]
            es = np.nan; sl_s = sl_g = np.nan
            if b - a > 5:
                ta, tb = tt[a] - tt[i0], tt[b] - tt[i0]
                sel = (L["t"] >= ta) & (L["t"] <= tb)
                if sel.sum() > 5:
                    sl_s = slip_of(np.asarray(L["xf"])[sel], np.asarray(L["thf"])[sel], R.r)
                dt = float(np.median(np.diff(tt)))
                q1f = lpf(d["q1"], 30.0); q2f = lpf(d["q2"], 30.0)
                v1 = np.gradient(q1f, dt); v2 = np.gradient(q2f, dt)
                idx = np.arange(a, b + 1, 2)
                S = [R.MV(q1f[i], q2f[i]) for i in idx]
                xg = np.array([x["xf"] for x in S])
                vth = np.array([x["dth"] @ np.array([v1[i], v2[i]]) for x, i in zip(S, idx)])
                sl_g = (float(xg[-1] - xg[0]) - R.r * float(np.trapezoid(vth, dx=2 * dt))) * 1000
                es = abs(sl_s - sl_g)
            rows.append(dict(s=s, name=p.name, ho=ho, e=e, eh=eh, es=es,
                             sl_s=sl_s, sl_g=sl_g, hs=hs, hv=hv))
            print(f"  {s}/{p.name}: q1 {e['q1']:.3f} q2 {e['q2']:.3f} "
                  f"h {hs:.3f}/{hv} slip {sl_s:.1f}/{sl_g:.1f}", flush=True)
        except Exception as ex:
            print(f"  {s}/{p.name}: ERR {type(ex).__name__} {ex}", flush=True)

    # ── 집계 ──
    S = sorted({r["s"] for r in rows})
    per = {s: {c: float(np.mean([r["e"][c] for r in rows if r["s"] == s])) for c in CH} for s in S}
    agg = dict(per=per,
               eh=float(np.nanmean([r["eh"] for r in rows])),
               es=float(np.nanmean([r["es"] for r in rows])),
               sg=float(np.nanmean([abs(r["sl_g"]) for r in rows])),
               tag=tag)
    print("\n" + "=" * 108)
    print(f"{'세션':<12}{'n':>3}{'q1[°]':>9}{'q2[°]':>9}{'dq1':>9}{'dq2':>9}"
          f"{'|h/h_v−1|':>11}{'slip_sim':>10}{'slip_기하':>10}")
    for s in S:
        sub = [r for r in rows if r["s"] == s]
        print(f"{s:<12}{len(sub):3d}" + "".join(f"{per[s][c]:9.3f}" for c in CH)
              + f"{np.nanmean([r['eh'] for r in sub]):11.3f}"
              + f"{np.nanmean([r['sl_s'] for r in sub]):10.1f}"
              + f"{np.nanmean([r['sl_g'] for r in sub]):10.1f}"
              + ("   ← held-out/gate" if sub[0]["ho"] else ""))
    print(f"{'전체':<12}{len(rows):3d}" + "".join(
        f"{float(np.mean([per[s][c] for s in S])):9.3f}" for c in CH)
        + f"{agg['eh']:11.3f}{'':10}{agg['sg']:10.1f}")

    if not REF.exists() or tag == "p24":
        json.dump(agg, io.open(REF, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n★ 기준(p24) 저장: {REF.name}  →  J_G(p24) ≡ 1.000")
        print(f"   Ê_h(p24) = {agg['eh']:.4f} · Ê_slip 원단위(p24) = {agg['es']:.2f} mm "
              f"(기하 평균 {agg['sg']:.1f} mm)")
        return
    ref = json.load(io.open(REF, encoding="utf-8"))
    ema = float(np.mean([np.mean([per[s][c] / max(ref["per"][s][c], 1e-9) for c in CH])
                         for s in S if s in ref["per"]]))
    eh = agg["eh"] / max(ref["eh"], 1e-9)
    es = (agg["es"] / max(agg["sg"], 1e-9)) / max(ref["es"] / max(ref["sg"], 1e-9), 1e-9)
    J = W["MA"] * ema + W["h"] * eh + W["slip"] * es
    print("\n" + "=" * 108)
    print(f"  Ê_MA {ema:.4f} · Ê_h {eh:.4f} · Ê_slip {es:.4f}   →   **J_G = {J:.4f}**  (p24 = 1.0000)")
    bad = []
    for s in ("26.03.24", "26.04.21"):
        if s not in ref["per"] or s not in per:
            continue
        for c in ("q1", "q2"):
            tol = max(ref["per"][s][c] * 0.05, 0.05)
            if per[s][c] - ref["per"][s][c] > tol:
                bad.append(f"{s}/{c}: {ref['per'][s][c]:.3f}→{per[s][c]:.3f}")
    print("  게이트(0324·0421 MA q1·q2): " + ("PASS" if not bad else "FAIL — " + " · ".join(bad)))
    json.dump(dict(agg, J=J, ema=ema, eh_n=eh, es_n=es, gate_fail=bad),
              io.open(HERE / f"_G13_board_{tag}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
