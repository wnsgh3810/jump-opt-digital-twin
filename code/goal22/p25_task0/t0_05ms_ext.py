# -*- coding: utf-8 -*-
"""t0_05ms_ext — 0.5ms 4점 연장 재개 드라이버 (사용자 승인 07-20).

배경: 0.5ms 4점(24/25.08/28/nc30)이 24M 부근 일제 조기종료 — patience를 min(120)으로
캡해 sim-시간 창이 2ms 대비 절반이 된 예산버그 (t0_train_long에 픽스 완료: eval 주기
×ratio 스케일 + patience 60 = sim-시간 등가; 96M cap 자체는 유효했음).

동작: 4점 전부 기존 ckpt에서 T0_RESUME 재개 (스텝 오프셋은 train log 폴백으로 복원,
엔트로피 플로어 잔여구간 = 절대스텝 38.4M 기준 자동 재산정) → 재수확 → li_ppo_05ms.png
갱신. nc05는 q1 마진 소프트 페널티 (T0_W_Q1MARGIN=50, 바운드 안쪽 0.01 rad부터) 활성
— 감사 경계 스침/비행 이탈로 audit-PASS best가 안 잡히는 문제 방지.
재클릭 재개 가능: 감사 training.steps ≥ 30M 인 점은 완료로 간주하고 스킵.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "bench"))
import t0_05ms_sweep as S5   # names_of/_jload/_nc_point/make_figure 재사용

POINTS = ["fix:24:0.5", "fix:25.08:0.5", "fix:28:0.5", "nc05"]
DONE_STEPS = 30_000_000      # 연장 완료 판정 (기존 조기종료분은 24.0~29.3M)


def run_point(camp):
    prefix, tag = S5.names_of(camp)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", T0_RESUME="1")
    if camp == "nc05":
        env["T0_W_Q1MARGIN"] = "50"   # q1 마진 완만 벌점 (코디 07-20 처방)
    for script in ("t0_train_long.py", "t0_rollout_long.py"):
        print(f"===== {script} {camp} (ext) =====", flush=True)
        r = subprocess.run([sys.executable, str(HERE / script), camp],
                           cwd=str(HERE), env=env)
        if r.returncode != 0:
            raise RuntimeError(f"{script} {camp} 실패 (rc={r.returncode})")
    assert (HERE / f"{prefix}_ppo_audit{tag}.json").exists(), f"수확물 없음: {camp}"


def steps_of(camp):
    prefix, tag = S5.names_of(camp)
    d = S5._jload(f"{prefix}_ppo_audit{tag}.json")
    if d is None:
        return 0
    return int(d.get("training", {}).get("steps") or 0)


def main():
    t0 = time.time()
    args = sys.argv[1:]
    failures = []
    if "--fig-only" not in args:
        for camp in POINTS:
            if steps_of(camp) >= DONE_STEPS and "--fresh" not in args:
                print(f"skip (연장 완료 {steps_of(camp)} steps): {camp}", flush=True)
                continue
            try:                       # 점 격리 — 한 점이 죽어도 체인 지속
                run_point(camp)
            except Exception as e:
                failures.append((camp, str(e)))
                print(f"[chain] {camp} 실패 — 다음 점 계속: {e}", flush=True)
    for camp in POINTS:
        prefix, tag = S5.names_of(camp)
        d = S5._jload(f"{prefix}_ppo_audit{tag}.json")
        if d is None:
            print(f"{camp:16s} MISSING", flush=True)
        elif prefix == "t0nc":
            h, ok = S5._nc_point(f"{prefix}_ppo_audit{tag}.json")
            print(f"{camp:16s} h={h:.4f} pass={ok} steps={steps_of(camp)}", flush=True)
        else:
            print(f"{camp:16s} h={d['h_plan']:.4f} pass={d['pass_all']} "
                  f"steps={steps_of(camp)}", flush=True)
    S5.make_figure()
    if failures:
        print(f"FAILURES: {failures}", flush=True)
    print(f"DONE [{(time.time() - t0) / 60:.1f} min]", flush=True)


if __name__ == "__main__":
    main()
