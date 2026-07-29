# -*- coding: utf-8 -*-
"""fs_calib_all — 세션 캘리브 전자동화 원패스 (Day1 #6, 졸업 기준 4 재현성).

새 세션 데이터가 오면 이 한 번으로 fs7 세션층 전체가 재생산된다:
  ① fs_calib audit      → _fs_static_audit.json  (하강 정적 잔차)
  ② fs_calib updown     → _fs_updown.json        (복귀 창 → 마찰/바이어스 분리)
  ③ fs_runner kneedeep  → _fs_knee_deep.json     (무릎 딥플렉션 간섭 세션 적합)
  ④ fs_calib_cvt        → _fs_cvt_audit.json     (0429 CVT 크랭크 감사)
  ⑤ fs_runner tauobs2   → _fs_tauobs_w.json      (관측 w 세션 상수)
순서 고정 (⑤는 ①~③ 산출물을 소비). 전 단계 하강/복귀 창만 사용 — 점프 창 무접촉 (규칙 4).
CLI: python fs_calib_all.py [--dry]  (--dry: 실행 없이 단계·산출물 나열)
"""
import os, sys, subprocess
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path

HERE = Path(__file__).parent
STEPS = [
    ("정적 감사 (하강)", [sys.executable, "fs_calib.py", "audit"], "_fs_static_audit.json"),
    ("복귀 창 분리", [sys.executable, "fs_calib.py", "updown"], "_fs_updown.json"),
    ("무릎 간섭 적합", [sys.executable, "fs_runner.py", "kneedeep"], "_fs_knee_deep.json"),
    ("CVT 감사 (0429)", [sys.executable, "fs_calib_cvt.py", "audit"], "_fs_cvt_audit.json"),
    ("관측 w 상수화", [sys.executable, "fs_runner.py", "tauobs2"], "_fs_tauobs_w.json"),
]


def main():
    dry = "--dry" in sys.argv
    env = dict(os.environ, PYTHONIOENCODING="utf-8", FS_KNEE_REL="0.1")
    for name, cmd, out in STEPS:
        print(f"[{name}] → {out}" + (" (dry)" if dry else ""), flush=True)
        if dry:
            continue
        r = subprocess.run(cmd, cwd=HERE, env=env, capture_output=True, text=True, encoding="utf-8")
        tail = "\n".join((r.stdout or "").strip().splitlines()[-3:])
        print(tail, flush=True)
        if r.returncode != 0 or not (HERE / out).exists():
            print(f"FAIL: {name} (rc {r.returncode})\n{(r.stderr or '')[-800:]}", flush=True)
            sys.exit(1)
    print("전 단계 완료 — _sess_params()가 소비하는 5개 산출물 최신화됨", flush=True)


if __name__ == "__main__":
    main()
