# -*- coding: utf-8 -*-
"""t0_05ms_sweep — 0.5ms 액션 주기 PPO 전면 비교 드라이버 (사용자 확정 07-19).

런 4개 (26.25@0.5ms는 프로브 기확보 1.0978 — 스킵):
  fix:24:0.5 / fix:25.08:0.5 / fix:28:0.5 (CVT, 자기 점 CMA 교사 0.5ms 재샘플 BC)
  nc05 (no_cvt 플랜트 @0.5ms, 교사 t0nc_cl.npz — 감사 cvt=False 규약은 t0nc_rollout이 담당)
레시피 = 0.5ms 프로브판 그대로 (96M cap sim-time 등가, patience 120, 플로어 std≥0.25
@예산40%, 128넷, T0_RESUME ckpt 재개, 점별 subprocess 격리).
교사 0.5ms 재생 검증 (07-19): 24=1.0705 / 25.08=1.0826 / 28=1.0938 / nc30=0.9818 완주.
최종 그림: graphs/summary/li_ppo_05ms.png (2ms vs 0.5ms vs CMA + no_cvt(30) 짝 강조)
— 그림 단계는 json 표준 모듈만 사용 (safe/bench 의존 제거 — 프로브 체인 사인 재발 방지).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "bench"))   # 하위 스크립트 안전망
import t0_train_long as TL

POINTS = ["fix:24:0.5", "fix:25.08:0.5", "fix:28:0.5", "nc05"]
LI_2MS = [("24", 24.0), ("25p08", 25.08), ("26p25", 26.25), ("28", 28.0), ("30", 30.0)]
LI_05MS = [("24", 24.0), ("25p08", 25.08), ("26p25", 26.25), ("28", 28.0)]


def names_of(camp):
    if camp == "nc05":
        return "t0nc", "_long_05ms"
    _, _, tag = TL.parse_fix(camp)
    return "t0wc", tag


def run_point(camp):
    prefix, tag = names_of(camp)
    aud = HERE / f"{prefix}_ppo_audit{tag}.json"
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if (HERE / f"{prefix}_ppo_policy{tag}.pt").exists() and not aud.exists():
        env["T0_RESUME"] = "1"     # 외부 킬 잔존 ckpt → 잔여 예산 재개
        print(f"[chain] {camp}: 기존 ckpt 발견 — T0_RESUME=1", flush=True)
    for script in ("t0_train_long.py", "t0_rollout_long.py"):
        print(f"===== {script} {camp} =====", flush=True)
        r = subprocess.run([sys.executable, str(HERE / script), camp],
                           cwd=str(HERE), env=env)
        if r.returncode != 0:
            raise RuntimeError(f"{script} {camp} 실패 (rc={r.returncode})")
    assert aud.exists(), f"수확물 없음: {aud.name}"


def _jload(name):
    f = HERE / name
    if not f.exists():
        return None
    return json.load(open(f, encoding="utf-8"))


def _nc_point(name):
    """nc 감사 json → (h, pass) — best ckpt 우선 (통과 시)."""
    d = _jload(name)
    if d is None:
        return None
    if d.get("pass_best"):
        return float(d["h_plan_best_ckpt"]), True
    return float(d["h_plan"]), bool(d.get("pass_final"))


def make_figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(9.5, 6))
    # CMA 스윕 곡선 (0.5ms PD CL 기준)
    sw = _jload("t0wc_li_sweep.json")["rows"]
    lis = sorted(float(v["l_i_mm"]) for v in sw.values())
    ax.plot(lis, [sw[f"{x:g}"]["h_plan"] for x in lis], marker=".", ms=5, alpha=0.8,
            label="CMA 고정-l_i CL 스윕 (0.5ms PD)")
    d = _jload("t0wc_cl_liopt_audit.json")
    if d:
        ax.plot([d["l_i_mm"]], [d["h_plan"]], marker="*", ms=15, linestyle="none",
                label=f"CMA 자유-l_i 최적 {d['l_i_mm']:.2f}mm: {d['h_plan']:.3f} m")
    # 고정-l_i PPO 곡선 — 2ms / 0.5ms
    for suf, pts, lab, ls in (("_long", LI_2MS, "고정-l_i PPO (2ms 액션)", "--"),
                              ("_long_05ms", LI_05MS, "고정-l_i PPO (0.5ms 액션)", "-")):
        xs, ys, bad = [], [], []
        for li_s, li in pts:
            d = _jload(f"t0wc_ppo_audit_lifix{li_s}{suf}.json")
            if d is None:
                continue
            xs.append(li); ys.append(d["h_plan"])
            if not d["pass_all"]:
                bad.append((li, d["h_plan"]))
        if xs:
            line, = ax.plot(xs, ys, marker="o", ms=8, linestyle=ls, label=lab)
            if bad:
                ax.plot([b[0] for b in bad], [b[1] for b in bad], linestyle="none",
                        marker="x", ms=11, color=line.get_color())
    # no_cvt(30) 짝 강조 — 플립 플랜트, Q2 바운드 감사 (cvt=False)
    nc2 = _nc_point("t0nc_ppo_audit_long.json")
    nc5 = _nc_point("t0nc_ppo_audit_long_05ms.json")
    for pt, lab, mk in ((nc2, "no_cvt PPO 2ms", "s"), (nc5, "no_cvt PPO 0.5ms", "D")):
        if pt:
            ax.plot([30.0], [pt[0]], marker=mk, ms=10, linestyle="none",
                    label=f"{lab}: {pt[0]:.3f} m" + ("" if pt[1] else " (감사 FAIL)"))
    if nc2 and nc5:
        ax.annotate("", xy=(30.0, nc5[0]), xytext=(30.0, nc2[0]),
                    arrowprops=dict(arrowstyle="->", alpha=0.6))
    ax.axvline(25.08, linestyle="--", alpha=0.6, label="검증앵커 25.08 (0429 CVT)")
    ax.axvline(30.0, linestyle="--", alpha=0.35, label="검증앵커 30 (무변속)")
    ax.axvspan(float(min(lis)), 25.08, alpha=0.08, label="외삽 구간 (CVT fit @25.08)")
    ax.set_xlabel("l_i [mm]")
    ax.set_ylabel("h (base-z apex) [m]")
    ax.set_title("task0 — 액션 주기 비교: PPO 2ms vs 0.5ms vs CMA (x = 감사 FAIL)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower center")
    out = HERE / "graphs" / "summary" / "li_ppo_05ms.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"figure saved: {out}", flush=True)


def main():
    t0 = time.time()
    args = sys.argv[1:]
    failures = []
    if "--fig-only" not in args:
        for camp in POINTS:
            prefix, tag = names_of(camp)
            if "--fresh" not in args and (HERE / f"{prefix}_ppo_audit{tag}.json").exists():
                print(f"skip (수확 있음): {camp}", flush=True)
                continue
            try:                       # 점 격리 — 한 점이 죽어도 체인 지속
                run_point(camp)
            except Exception as e:
                failures.append((camp, str(e)))
                print(f"[chain] {camp} 실패 — 다음 점 계속: {e}", flush=True)
    for camp in POINTS:
        prefix, tag = names_of(camp)
        d = _jload(f"{prefix}_ppo_audit{tag}.json")
        if d is None:
            print(f"{camp:16s} MISSING", flush=True)
        elif prefix == "t0nc":
            h, ok = _nc_point(f"{prefix}_ppo_audit{tag}.json")
            print(f"{camp:16s} h={h:.4f} pass={ok} steps={d.get('training', {}).get('steps')}",
                  flush=True)
        else:
            print(f"{camp:16s} h={d['h_plan']:.4f} pass={d['pass_all']} "
                  f"steps={d.get('training', {}).get('steps')}", flush=True)
    make_figure()
    if failures:
        print(f"FAILURES: {failures}", flush=True)
    print(f"DONE [{(time.time() - t0) / 60:.1f} min]", flush=True)


if __name__ == "__main__":
    main()
