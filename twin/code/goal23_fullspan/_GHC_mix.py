# -*- coding: utf-8 -*-
"""_GHC_mix — **채널별 혼합 변환식** 선별 (마라톤H 추가작업, 2026-08-12).

왜 (08-11~12 에 쌓인 근거가 전부 이 형태를 가리킨다)
  무게추 왕복 실측(`26_08_07/{0,2,4}kg`, 상행−하행 절반차 = 마찰):
    무릎 0.135 + **0.1197**·|명령| → 전달효율 **88%** (4절링크+벨트를 거친다)
    힙   0.278 + 0.0029·|명령|    → 효율 **≈100%** (모터가 허벅지를 거의 직접 돌린다)
  즉 **힘비례 손실은 무릎에만 있다.**
  그런데 기각 #82(canon_fric)는 양 채널에 같은 형태를 강제해, 힙이 실측(0.004)과 충돌하는
  0.259 를 떠안고 졌다. **무릎 쪽 값은 오히려 실측과 맞았다** (속도비례 0.012 vs 실측 0.016).
  ⇒ 형태가 틀린 게 아니라 **적용 범위**가 틀렸다. 힙은 상한형, 무릎만 하중비례형.

무엇을 재나 (전부 H3 = 방금 승격한 현행 스택을 1.0000 으로 놓고, 낮을수록 좋음)
  · 측정 토크 주입 재생 : 측정 토크를 그대로 넣고 돌린 뒤 관절각·각속도 4채널 오차.
    PD 가 없어 오차를 못 감춘다 — 물리의 1급 심판.
  · 폐루프           : 실제 게인으로 PD 제어한 뒤 각도·속도·토크 6채널 오차.
  · 점프 높이        : 영상 실측 대비 오차.
  종합 = 0.40×주입재생 + 0.40×폐루프 + 0.20×점프높이 (채널별 정규화).
  게이트 5종(0324·0421 주입재생, 0421·0429 폐루프, 0429 주입재생)은 목적에서 제외·감시만.

★ 무릎 건마찰은 **관절 마찰(FS_KNEEM_FL)에 이미 있다.** 변환식의 일정몫(fc0)을 또 넣으면
  이중 차감이므로 여기서는 **fc0=0** 으로 두고 하중기울기(fc1)와 속도문턱(v0)만 본다.

CLI: python _GHC_mix.py
"""
import os, sys, io, json, itertools
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GHC_mix.json"

# 방금 승격한 현행 스택 (CURRENT_STACK.md H3_260812)
H3 = dict(x.split("=", 1) for x in
          io.open(HERE / "_GHB_winner_env.txt", encoding="utf-8").read().split(";"))

# 무릎 하중기울기 — 하한은 준정적 실측 0.156, 상한은 열어둔다 (고속 손실은 이 채널로 관측 불가)
FC1 = (0.156, 0.22, 0.30, 0.38, 0.46)
V0 = (0.10, 0.30, 1.00)


def main():
    import _GHB_sweep as S
    S._ensure()

    def score(env):
        S._apply(env)
        B = S.board()
        if not B:
            return None
        ma = S.ratio(B, "ma", S.FIT); cl = S.ratio(B, "cl", S.FIT)
        hs = [B[s]["h"] / S._BASE[s]["h"] for s in S.FIT
              if s in B and B[s].get("h") and S._BASE.get(s, {}).get("h")]
        h = float(np.mean(hs)) if hs else np.nan
        g = {}
        for s in S.GATE_MA:
            g[f"{s}MA"] = S.ratio(B, "ma", (s,))
        for s in S.GATE_CL:
            g[f"{s}CL"] = S.ratio(B, "cl", (s,))
        return dict(ma=ma, cl=cl, h=h, gate=g)

    # ① 기준선을 H3 로 다시 잡는다 (_GHB_sweep._BASE 는 H2 이므로 비율을 H3 기준으로 환산)
    b3 = score(dict(H3))
    if b3 is None:
        raise SystemExit("H3 기준선 실패")
    norm = lambda r, k: r[k] / b3[k]
    print("채널별 혼합 변환식 선별 — 힙 = 상한형(H3 그대로) · 무릎 = 하중비례형")
    print(f"기준선 = H3 (방금 승격). 아래는 전부 H3 대비 [%], 음수가 개선.\n")
    print(f"{'무릎 기울기':>10s} {'속도문턱':>8s} | {'주입재생':>9s} {'폐루프':>8s} {'점프높이':>9s} "
          f"{'종합':>8s} | 게이트")
    R = {}
    best = None
    for fc1, v0 in itertools.product(FC1, V0):
        e = dict(H3); e["FS_TMAP"] = "canon_mix"; e["FS_TMIX"] = f"0,{fc1:.4f},0,{v0:.3f}"
        r = score(e)
        if r is None:
            print(f"{fc1:10.3f} {v0:8.2f} | 실패"); continue
        ma, cl, h = norm(r, "ma"), norm(r, "cl"), norm(r, "h")
        tot = 0.40 * ma + 0.40 * cl + 0.20 * h
        bad = [f"{k} {100*(x/b3['gate'][k]-1):+.1f}%" for k, x in r["gate"].items()
               if np.isfinite(x) and x / b3["gate"][k] > 1.02]
        R[f"{fc1}_{v0}"] = dict(fc1=fc1, v0=v0, ma=ma, cl=cl, h=h, tot=tot, bad=bad)
        f = lambda z: f"{100*(z-1):+.2f}%"
        print(f"{fc1:10.3f} {v0:8.2f} | {f(ma):>9s} {f(cl):>8s} {f(h):>9s} {f(tot):>8s} | "
              f"{'통과' if not bad else ' · '.join(bad)}", flush=True)
        if not bad and (best is None or tot < best[1]):
            best = (f"{fc1}_{v0}", tot)
    S._apply(dict(H3))
    import safe
    safe.atomic_json_write(OUT, dict(res=R, best=best))
    print(f"\n최고: {best}" if best else "\n게이트를 통과하는 후보 없음")
    print("※ 실측 준정적 값 = 0.156 (하한). 그보다 커야 하면 고속 손실이 더해진다는 뜻.")


if __name__ == "__main__":
    main()
