# 하중(토크)에 비례하는 무릎 손실을 넣으면 일어서기가 좋아지나 — 방향과 **한계**를 본다 (읽기 전용)
#   모델에 이미 있는 항: canon_mix 의 무릎 손실 = (fc0 + fc1·|명령|)·tanh(속도/v0)
#   fc1 이 "하중에 비례" 성분이다. 08-14 측정은 짐 1kg당 0.39 N·m 였다.
#
#   ★ 08-14 확장 — 사용자 질문 "일어서기가 확실하게 좋아질 수 있나?" 에 답하기 위해:
#     ① fc1 을 0.30 에서 멈추지 않고 0.80 까지 훑는다 (바닥이 어디인지 몰랐다).
#     ② 조각으로 나눈 성적뿐 아니라 **통짜 성적**과 **버틴 시간**도 같이 잰다
#        (6 회차 판이 통짜로 바뀌므로, 이 축이 통짜에서도 듣는지 확인해야 한다).
#     성적 = 창 앞 80% 오차 ÷ 그 신호가 그 구간에서 움직인 폭 · 채널당 상한 10 · **0 이 완벽**.
#     버틴 시간 = 무릎 각도 오차가 10 도를 넘을 때까지 걸린 시간 [s] · **길수록 좋다**.
import os, sys, collections
os.environ.setdefault("FS_SWEEP_AIR", "0"); os.environ.setdefault("FS_SWEEP_S2S", "1")
from pathlib import Path
GFS = str(Path(__file__).parent)
sys.path.insert(0, GFS); os.chdir(GFS)
import numpy as np
import fs_data as FD, fs_runner as FR, fs_cvt as FC, _GHB_sweep as S

S._ensure()          # 판을 먼저 읽어 둔다 (board() 가 이걸 쓴다)
BASE = np.asarray(S.DEPLOY, float)


def _one(ft, d, t0, t1):
    """한 창을 통짜 개루프로 재생하고 (성적, 버틴 시간) 을 돌려준다."""
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
    hold = float(tg[k[0]]) if len(k) else float(tg[-1])
    return float(np.mean([min(x, 10.) for x in v])), hold


def board_s2s():
    """일어서기 4 경우를 재고, 경우별 (나눈 성적) 과 전체 (통짜, 버틴 시간) 을 함께 돌려준다."""
    m0 = float(os.environ.get("FS_MASS", "3.30")); keep = os.environ.get("FS_MASS")
    out, whole, hold = {}, [], []
    try:
        for sub, pay, cvt in FD.S2S_CASES:
            d = FD.load_s2s(sub)
            if d is None: continue
            os.environ["FS_MASS"] = f"{m0+pay:.4f}"
            FR._CACHE.clear(); S._CVT_STAMPED.clear()
            ft = FC.cvt_ft(float(d["l_i"]), ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
            per = [_one(ft, d, a, b) for a, b in FD.air_windows(d, nwin=4, wmax=2.0)]
            per = [p for p in per if p]
            out[sub] = float(np.mean([p[0] for p in per])) if per else 3.0
            w = _one(ft, d, float(d["t"][0]), float(d["t"][-1]))
            whole.append(w[0] if w else 10.0); hold.append(w[1] if w else 0.0)
    finally:
        if keep is None: os.environ.pop("FS_MASS", None)
        else: os.environ["FS_MASS"] = keep
        FR._CACHE.clear(); S._CVT_STAMPED.clear()
    return out, float(np.mean(whole)), float(np.mean(hold))


print("무릎 손실 (fc0 + fc1·|명령|)·tanh(속도/v0) 를 넣었을 때")
print("  성적 = 창 앞 80% 오차 ÷ 그 신호가 그 구간에서 움직인 폭 (0 이 완벽 · 채널당 상한 10)")
print("  버틴 시간 = 무릎 각도 오차가 10 도를 넘기까지 [s] (길수록 좋다)")
print("  합격선 참고: 0.43 이하면 '쓸 만하다', 그 위는 '못 쓴다'")
print()
hdr = (f"{'설정':22s} {'나눈평균':>9s} {'변속0':>7s} {'변속2.5':>8s} {'변속5':>7s} {'무변속':>7s}"
       f" | {'통짜':>7s} {'버틴s':>7s} | {'점프주입':>9s}")
print(hdr); print("-" * len(hdr))
ROWS = [("지금 (canon_cap)", "canon_cap", None)] + [
    (f"하중비례 fc1={f:.2f}", "canon_mix", f"0.18,{f:.2f},0,0.3")
    for f in (0.00, 0.08, 0.16, 0.30, 0.40, 0.50, 0.65, 0.80)]
for tag, mode, mix in ROWS:
    e = S.env_of("canon_cap", BASE)
    e["FS_TMAP"] = mode
    if mix: e["FS_TMIX"] = mix
    else: e.pop("FS_TMIX", None)
    S._apply(e)
    if not mix: os.environ.pop("FS_TMIX", None)
    s, wh, hd = board_s2s()
    S._apply(e)
    if not mix: os.environ.pop("FS_TMIX", None)
    B = S.board()
    ma = S.absm(B, "ma8", S.FIT, (0, 1, 2, 3))
    m = float(np.mean(list(s.values())))
    print(f"{tag:22s} {m:9.3f} {s.get('cvt/no_load',float('nan')):7.3f} "
          f"{s.get('cvt/load_2.5',float('nan')):8.3f} {s.get('cvt/load_5',float('nan')):7.3f} "
          f"{s.get('no_cvt/no_load',float('nan')):7.3f} | {wh:7.3f} {hd:7.3f} | {ma:9.4f}", flush=True)
print("-" * len(hdr))
print("점프주입 = 점프 8 세션 측정토크 주입 재생 (0 이 완벽, 지금 0.1747). 이게 나빠지면 대가가 있는 것.")
print("※ 나머지 16 축은 배포 스택 그대로다 — 공동 재적합을 안 한 값이므로 대가는 과대평가다.")
