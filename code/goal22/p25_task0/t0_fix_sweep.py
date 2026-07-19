# -*- coding: utf-8 -*-
"""t0_fix_sweep — 고정-l_i 전용 PPO 스윕 드라이버 (코디 지시 07-18 밤).

순차 실행: 그리드 {24, 25.08, 26.25, 28, 30}mm 각각
  ① t0_train_long.py fix:<li>  (wc2 레시피: 교사 BC → PPO, 플로어 std≥0.25@예산40%,
     128×128, 24M cap·patience 60, 8워커; 교사 = t0_fix_teachers 생성분/li2508/t0nc_cl)
  ② t0_rollout_long.py fix:<li> (결정론 롤아웃 + t0_spec.audit(cvt=True))
+ 이산화 프로브: fix:26.25:1 / fix:26.25:0.5 (액션 주기 1ms/0.5ms, 물리 0.5ms 불변,
  예산 sim-time 등가 ×2/×4, 교사 = liopt 재샘플 — 1ms 재생 1.106/0.5ms 1.105 검증됨)
→ 최종 그림 graphs/summary/li_ppo_fair_sweep.png (CMA 스윕 곡선 + 조건부 wc2 점 +
  프로브 별도 마커). --resume: 감사 json 있는 점 스킵. --fig-only: 그림만.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import t0_train_long as TL   # parse_fix 재사용 (부작용 없음)

POINTS = ["fix:24", "fix:25.08", "fix:26.25", "fix:28", "fix:30"]
PROBES = ["fix:26.25:1", "fix:26.25:0.5"]
AVT_OPT_MM = 25.161


def run_point(camp):
    _, _, tag = TL.parse_fix(camp)
    aud = HERE / f"t0wc_ppo_audit{tag}.json"
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if (HERE / f"t0wc_ppo_policy{tag}.pt").exists() and not aud.exists():
        env["T0_RESUME"] = "1"     # 외부 킬 잔존 ckpt → 잔여 예산 재개 (코디 07-19)
        print(f"[chain] {camp}: 기존 ckpt 발견 — T0_RESUME=1", flush=True)
    for script in ("t0_train_long.py", "t0_rollout_long.py"):
        print(f"===== {script} {camp} =====", flush=True)
        r = subprocess.run([sys.executable, str(HERE / script), camp],
                           cwd=str(HERE), env=env)
        if r.returncode != 0:
            raise RuntimeError(f"{script} {camp} 실패 (rc={r.returncode})")
    assert aud.exists(), f"수확물 없음: {aud.name}"


def load_results():
    rows = []
    for camp in POINTS + PROBES:
        li, cdt, tag = TL.parse_fix(camp)
        f = HERE / f"t0wc_ppo_audit{tag}.json"
        if not f.exists():
            rows.append(dict(camp=camp, li=li, ctrl_ms=cdt * 1000, missing=True))
            continue
        d = json.load(open(f, encoding="utf-8"))
        rows.append(dict(camp=camp, li=li, ctrl_ms=cdt * 1000, missing=False,
                         h=d["h_plan"], pass_all=bool(d["pass_all"]),
                         ckpt=d["primary_ckpt"],
                         steps=d.get("training", {}).get("steps"),
                         wall_s=d.get("training", {}).get("wall_s"),
                         audit=d["audit_star"]))
    return rows


def make_figure(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    import safe
    fig, ax = plt.subplots(figsize=(9.5, 6))
    # CMA 스윕 곡선 (0.5ms PD 폐루프 기준)
    sw = safe.read_json(HERE / "t0wc_li_sweep.json")["rows"]
    lis = sorted(float(v["l_i_mm"]) for v in sw.values())
    hs = [sw[f"{x:g}"]["h_plan"] for x in lis]
    ax.plot(lis, hs, marker=".", ms=5, alpha=0.8,
            label="CMA 고정-l_i CL 스윕 (0.5ms PD)")
    try:
        d = safe.read_json(HERE / "t0wc_cl_liopt_audit.json")
        ax.plot([d["l_i_mm"]], [d["h_plan"]], marker="*", ms=15, linestyle="none",
                label=f"CMA 자유-l_i 최적 {d['l_i_mm']:.2f}mm: {d['h_plan']:.3f} m")
    except Exception:
        pass
    # 고정-l_i 전용 PPO (2ms)
    fx = [r for r in rows if r["ctrl_ms"] == 2.0 and not r.get("missing")]
    line, = ax.plot([r["li"] for r in fx], [r["h"] for r in fx], marker="o", ms=8,
                    linestyle="--",
                    label="고정-l_i 전용 PPO (2ms 액션, BC+장기예산)")
    bad = [r for r in fx if not r["pass_all"]]
    if bad:
        ax.plot([r["li"] for r in bad], [r["h"] for r in bad], linestyle="none",
                marker="x", ms=11, color=line.get_color())
    # 조건부 wc2 점
    try:
        d = safe.read_json(HERE / "t0wc_ppo_audit_long2.json")
        ax.plot([d["li_star_mm"]], [d["h_plan"]], marker="s", ms=9, linestyle="none",
                label=f"조건부 정책 (wc2) l_i*={d['li_star_mm']:.1f}: {d['h_plan']:.3f} m")
    except Exception:
        pass
    # 이산화 프로브
    for r in rows:
        if r["ctrl_ms"] != 2.0 and not r.get("missing"):
            mk = "^" if r["ctrl_ms"] == 1.0 else "v"
            ax.plot([r["li"]], [r["h"]], marker=mk, ms=11, linestyle="none",
                    label=f"프로브 {r['ctrl_ms']:g}ms @26.25: {r['h']:.3f} m"
                          + ("" if r["pass_all"] else " (감사 FAIL)"))
    ax.axvline(25.08, linestyle="--", alpha=0.6, label="검증앵커 25.08 (0429 CVT)")
    ax.axvline(30.0, linestyle="--", alpha=0.35, label="검증앵커 30 (무변속)")
    ax.axvline(AVT_OPT_MM, linestyle=":", alpha=0.8, label="AVT 해석 최적 25.161")
    ax.axvspan(float(min(lis)), 25.08, alpha=0.08,
               label="외삽 구간 (CVT 층 fit @25.08)")
    ax.set_xlabel("l_i [mm]")
    ax.set_ylabel("h (base-z apex) [m]")
    ax.set_title("task0 with_cvt 공정 비교 — 고정-l_i 전용 PPO vs CMA (x = 감사 FAIL)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower center")
    out = HERE / "graphs" / "summary" / "li_ppo_fair_sweep.png"
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
        for camp in POINTS + PROBES:
            _, _, tag = TL.parse_fix(camp)
            if "--fresh" not in args and (HERE / f"t0wc_ppo_audit{tag}.json").exists():
                print(f"skip (수확 있음): {camp}", flush=True)
                continue
            try:                       # ★ 점 격리 — 한 점이 죽어도 체인 지속 (코디 07-19)
                run_point(camp)
            except Exception as e:
                failures.append((camp, str(e)))
                print(f"[chain] {camp} 실패 — 다음 점 계속: {e}", flush=True)
    rows = load_results()
    for r in rows:
        if r.get("missing"):
            print(f"{r['camp']:16s} MISSING", flush=True)
        else:
            print(f"{r['camp']:16s} h={r['h']:.4f} pass={r['pass_all']} "
                  f"ckpt={r['ckpt']} steps={r['steps']}", flush=True)
    make_figure(rows)
    if failures:
        print(f"FAILURES: {failures}", flush=True)
    print(f"DONE [{(time.time() - t0) / 60:.1f} min]", flush=True)


if __name__ == "__main__":
    main()
