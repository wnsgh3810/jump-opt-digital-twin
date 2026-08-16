# 무릎 토크 천장을 **속도에 따라 닫히게** 하면 좋아지나 — 모터 전압 한계(역기전력) 축 훑기
#
#   왜 (08-14, 사용자 질문 "모터 모델의 근본적 변화가 같이 들어가야 하지 않나")
#     실측으로 확인한 것: 점프 밀어내기에서 무릎(크랭크) 모터가 매우 빠르게 돈다.
#     명령 토크 상위 10% 순간의 속도가 14.2 rad/s → 모터 128 rad/s → 역기전력 11.6 V.
#     공급 24 V 기준 **절반을 역기전력이 먹는다** (속도 상위 구간은 100% 초과).
#     그런데 그 순간에도 명령 토크는 17.5 N·m 로 전체 중앙값과 같다 — 즉 **빠를 때도 계속
#     크게 요구한다.** 전압이 모자라면 그 명령은 물리적으로 못 나온다.
#     지금 모델의 무릎 천장은 **속도와 무관한 고정값**이라 이 현상을 담을 그릇이 없다.
#
#   여기서 여는 손잡이 (이미 구현돼 있다: FS_TMAP=canon_capv)
#     천장(v) = c0 + c1·|관절 각속도|      · c1 = 0 이면 지금과 **완전히 동일** (회귀 불가)
#     역기전력이 맞다면 c1 은 **음수**여야 한다 (빠를수록 천장이 닫힌다).
#   ※ 과거 기각 #61 은 이 축을 **지금 모델의 실효 천장을 재현하도록** 회귀해 부호가 뒤집혔다.
#     그것은 모델을 모델에 맞춘 것이고, 여기서는 **데이터 성적 위에서 직접** 연다.
import os, sys
os.environ.setdefault("FS_SWEEP_AIR", "0"); os.environ.setdefault("FS_SWEEP_S2S", "1")
from pathlib import Path
GFS = str(Path(__file__).parent)
sys.path.insert(0, GFS); os.chdir(GFS)
import numpy as np
import fs_data as FD, fs_runner as FR, fs_cvt as FC, _GHB_sweep as S

S._ensure()
BASE = np.asarray(S.DEPLOY, float)
# ★ 배포 스택의 무릎·힙 보정 상한 = **마지막 두 칸** (앞에 모터축 관성 2 · 환산 비율 2 가 있다).
#   08-14 여기서 [10],[11] 로 잡았다가 모터축 관성(0.01)을 상한으로 넘겨 판이 무너졌다.
#   c1=0 줄이 지금 모델과 같아야 한다는 회귀 검사가 그 버그를 잡았다 — 그 줄을 지울 것.
C0K, C0H = float(BASE[-2]), float(BASE[-1])
assert 2.0 < C0K < 12.0 and 1.2 < C0H < 10.0, f"보정 상한 자리 확인 실패: {C0K}, {C0H}"


def _one(ft, d, t0, t1):
    t = d["t"]; mm = (t >= t0) & (t <= t1)
    if mm.sum() < 20: return None
    i0 = int(np.argmax(mm)); tg = t[mm] - t[i0]
    L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][mm], d["raw2"][mm],
                           float(d["q1"][i0]), float(d["q2"][i0]),
                           float(d["dq1"][i0]), float(d["dq2"][i0]),
                           float(tg[-1] - 0.004), fade=True)
    if L is None: return None
    gf = lambda k: np.interp(tg, L["t"], L[k])
    sim = [gf("thm1"), gf("q2"), gf("dq1"), gf("dq2")]
    v = [S._r80(tg, d[k][mm], sm, floor=fl) for k, sm, fl in zip(S.CH4, sim, S.AIR_FLOOR)]
    if not all(np.isfinite(v)): return None
    e = np.degrees(np.abs(sim[1] - d["q2"][mm]))
    k = np.where(e > 10.0)[0]
    return float(np.mean([min(x, 10.) for x in v])), (float(tg[k[0]]) if len(k) else float(tg[-1]))


def s2s_all():
    m0 = float(os.environ.get("FS_MASS", "3.30")); keep = os.environ.get("FS_MASS")
    whole, hold = [], []
    try:
        for sub, pay, cvt in FD.S2S_CASES:
            d = FD.load_s2s(sub)
            if d is None: continue
            os.environ["FS_MASS"] = f"{m0+pay:.4f}"
            FR._CACHE.clear(); S._CVT_STAMPED.clear()
            ft = FC.cvt_ft(float(d["l_i"]), ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
            w = _one(ft, d, float(d["t"][0]), float(d["t"][-1]))
            whole.append(w[0] if w else 10.0); hold.append(w[1] if w else 0.0)
    finally:
        if keep is None: os.environ.pop("FS_MASS", None)
        else: os.environ["FS_MASS"] = keep
        FR._CACHE.clear(); S._CVT_STAMPED.clear()
    return float(np.mean(whole)), float(np.mean(hold))


print("무릎 토크 천장을 속도 의존으로: 천장(v) = c0 + c1·|각속도|   (c1=0 이면 지금과 동일)")
print(f"  c0 는 배포 스택 값 고정 — 무릎 {C0K:.3f} · 힙 {C0H:.3f}")
print("  성적 = 창 앞 80% 오차 ÷ 그 신호가 그 구간에서 움직인 폭 (0 이 완벽)")
print("  점프주입 = 점프 세션 측정토크 주입 재생 · 폐루프토크 = PD 흉내 판의 토크 2 채널")
print("  20r/s 천장 = 무릎이 초당 20 라디안일 때 천장이 얼마로 닫히는지 (참고용)")
print()
hdr = (f"{'설정':30s} {'20r/s천장':>9s} {'일어서기':>8s} {'버틴s':>6s} | "
       f"{'점프주입':>8s} {'폐루프토크':>10s} {'점프높이':>8s}")
print(hdr); print("-" * len(hdr))
for c1 in (None, 0.0, -0.05, -0.10, -0.15, -0.25):
    e = S.env_of("canon_cap", BASE)
    if c1 is None:
        tag = "지금 모델 (고정 천장)"
    else:
        tag = f"속도 의존 천장 c1={c1:+.2f}"
        e["FS_TMAP"] = "canon_capv"
        e["FS_TDCAPV"] = f"{C0K:.5f},{c1:.5f},{C0H:.5f},0"
    S._apply(e)
    if c1 is None: os.environ.pop("FS_TDCAPV", None)
    wh, hd = s2s_all()
    S._apply(e)
    if c1 is None: os.environ.pop("FS_TDCAPV", None)
    B = S.board()
    ma = S.absm(B, "ma8", S.FIT, (0, 1, 2, 3))
    clt = S.absm(B, "cl8", S.FIT, (4, 5))
    _hv = []
    for s in S.FIT:
        a = (B.get(s) or {}).get("hr")
        if a is None: continue
        for x in (a if np.ndim(a) else [a]):
            if np.isfinite(x): _hv.append(abs(float(x)))
    h = float(np.mean(_hv)) if _hv else float("nan")
    cap20 = (C0K if c1 is None else max(C0K + c1 * 20.0, 0.0))
    print(f"{tag:30s} {cap20:9.3f} {wh:8.3f} {hd:6.3f} | {ma:8.4f} {clt:10.4f} {h:8.4f}", flush=True)
print("-" * len(hdr))
print("역기전력이 실재하면 c1 은 음수 쪽에서 좋아져야 한다 (빠를수록 천장이 닫힌다).")
print("※ 나머지 축은 배포 스택 그대로 — 공동 재적합 없음.")
