# -*- coding: utf-8 -*-
"""_GH6_jointfit — 축들이 **서로 얽혀 있는가**를 먼저 잰다 (마라톤H, 2026-08-11).

왜 이걸 먼저 하나 (사용자 지시 "따로 잰 값이니 같이 다시 고려해야 하지 않나")
  지금까지 축을 하나씩 맞췄고, 각 축의 기준선은 **다른 축이 예전 값일 때** 잰 것이다.
  축끼리 상호작용이 있으면 그 조합은 최적이 아니다 — 공동 적합이 필요하다.
  그런데 공동 적합(13축 NSGA-II)은 몇 시간짜리다. **정말 필요한지부터 재는 게 싸다.**

  실제로 08-11 에 붙잡는세기 × 무릎필터는 **완전 독립**이었다 (무릎필터 효과가
  붙잡는세기 100/50/20/10 어디서나 −1.3/−2.6/−4.3% 로 동일). 전부 그렇다면
  한 축씩 맞춘 현행 조합이 이미 최적이고 공동 적합은 시간만 쓴다.

재는 법 — 상호작용 = |같이 넣은 효과 − 따로 넣은 효과의 합|
  두 축 A,B 에 대해 f(A), f(B), f(A+B) 를 재고
      상호작용 = f(A+B) − [f(A) + f(B)]
  이 값이 0 에 가까우면 **분리 가능**(따로 맞춰도 된다), 크면 **공동 적합 필요**.

CLI: python _GH6_jointfit.py
"""
import os, sys, io, json, time, itertools
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GH6_interact.json"
CH = ("q1", "q2", "dq1", "dq2", "a1", "a2")
SUB = os.environ.get("GH6_SESS", "26.04.21,26.04.24,26.06.02,26.07.27").split(",")

# 시험할 축 = 스크리닝에서 효과가 있었던 것들. 값은 **실측·공차 안**에서 한 걸음.
#   (경계 밖으로 나가야 이득이 나는 축은 08-11 에 이미 과적합으로 판명 — 여기 안 넣는다)
MOVES = {
    "질량 3.30":      {"FS_MASS": "3.30"},
    "허벅지질량 0.87": {"FS_MBODY": "thigh=0.87"},
    "힙탄성 170":     {"FS_KS_HIP": "170"},
    "마찰 0.78":      {"FS_PRESLIDE": "0.78,0.77,0.02,1.0"},
    "붙잡는세기 20":   {"FS_IMPRATIO": "20"},
    "무릎필터 0.0025": {"FS_CMD_LPF": "0.002,0.0025"},
    "토크캡 3.4,2.3":  {"FS_TDCAP": "3.4,2.3"},
}


def board():
    import fs_data as FD, fs_compare_plot as CP
    F = []
    for s, p, g, cvt, ho in FD.registry():
        if cvt or not g or s not in SUB:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            d["_sess"] = s; d["_fold"] = p
            r = CP.cl_pair(d, seg, g, s)
        except Exception:
            continue
        if r is None:
            continue
        t, (mo, mf), old, fs, m, cmd, _ = r
        e = lambda a, b, k: float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2))) * \
            (180 / np.pi if k in ("q1", "q2") else 1)
        F.append([e(fs[i], mf[k], k) for i, k in enumerate(CH)])
    F = np.array(F)
    return F if len(F) and np.all(np.isfinite(F)) else None


def main():
    import fs_runner as FR
    keys = sorted({k for v in MOVES.values() for k in v})
    saved = {k: os.environ.get(k) for k in keys}

    def restore():
        for k, v in saved.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        FR._S2S = None

    restore(); b = board()
    if b is None:
        raise SystemExit("기준선 실패")
    b = b.mean(0)
    score = lambda f: 100 * (np.mean(f / b) - 1)

    def run(cfgs):
        restore()
        for c in cfgs:
            for k, v in c.items():
                os.environ[k] = v
        FR._S2S = None
        f = board()
        return None if f is None else score(f.mean(0))

    print(f"부분집합 {SUB} · 폐루프 6채널 정규화 점수 [%]\n")
    single = {}
    for nm, cfg in MOVES.items():
        single[nm] = run([cfg])
        print(f"  단독  {nm:16s} {single[nm]:+6.2f}%", flush=True)
    print(f"\n{'조합':36s} {'같이':>7s} {'따로합':>7s} {'상호작용':>8s}  판정")
    res = {}
    for a, c in itertools.combinations(MOVES, 2):
        if single[a] is None or single[c] is None:
            continue
        j = run([MOVES[a], MOVES[c]])
        if j is None:
            print(f"  {a} + {c}: 발산"); continue
        s = single[a] + single[c]
        d = j - s
        res[f"{a}+{c}"] = dict(joint=j, sum=s, inter=d)
        tag = "얽힘" if abs(d) > 0.30 else ("약간" if abs(d) > 0.10 else "독립")
        print(f"{a+' + '+c:36s} {j:+7.2f} {s:+7.2f} {d:+8.2f}  {tag}", flush=True)
    restore()
    import safe
    safe.atomic_json_write(OUT, {"single": single, "pairs": res, "sess": SUB})
    if res:
        v = np.array([abs(r["inter"]) for r in res.values()])
        print(f"\n상호작용 크기: 중앙 {np.median(v):.2f}%p · 최대 {v.max():.2f}%p")
        print("  → 최대가 0.3%p 미만이면 **분리 가능** = 공동 적합 불필요 (한 축씩 맞춘 게 이미 최적)")
        print(f"  저장 → {OUT}")


if __name__ == "__main__":
    main()
