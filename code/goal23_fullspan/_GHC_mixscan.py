# 하중(토크)에 비례하는 무릎 손실을 넣으면 일어서기가 좋아지나 — 방향만 본다 (읽기 전용)
#   모델에 이미 있는 항: canon_mix 의 무릎 손실 = (fc0 + fc1·|명령|)·tanh(속도/v0)
#   fc1 이 "하중에 비례" 성분이다. 08-14 측정은 짐 1kg당 0.39 N·m 였다.
import os, sys, collections
os.environ.setdefault("FS_SWEEP_AIR", "0"); os.environ.setdefault("FS_SWEEP_S2S", "1")
from pathlib import Path
GFS = str(Path(__file__).parent)
sys.path.insert(0, GFS); os.chdir(GFS)
import numpy as np
import fs_data as FD, fs_runner as FR, fs_cvt as FC, _GHB_sweep as S

S._ensure()          # 판을 먼저 읽어 둔다 (board() 가 이걸 쓴다)
BASE = np.asarray(S.DEPLOY, float)

def board_s2s():
    import fs_runner as FR
    m0 = float(os.environ.get("FS_MASS", "3.30")); keep = os.environ.get("FS_MASS")
    out = {}
    try:
        for sub, pay, cvt in FD.S2S_CASES:
            d = FD.load_s2s(sub)
            if d is None: continue
            W = FD.air_windows(d, nwin=4, wmax=2.0)
            os.environ["FS_MASS"] = f"{m0+pay:.4f}"
            FR._CACHE.clear(); S._CVT_STAMPED.clear()
            ft = FC.cvt_ft(float(d["l_i"]), ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
            t = d["t"]; per = []
            for w0, w1 in W:
                mm = (t >= w0) & (t <= w1)
                if mm.sum() < 20: continue
                i0 = int(np.argmax(mm)); tg = t[mm] - t[i0]
                L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][mm], d["raw2"][mm],
                                       float(d["q1"][i0]), float(d["q2"][i0]),
                                       float(d["dq1"][i0]), float(d["dq2"][i0]),
                                       float(tg[-1]-0.004), fade=True)
                if L is None: continue
                gf = lambda k: np.interp(tg, L["t"], L[k])
                sim = [gf("thm1"), gf("q2"), gf("dq1"), gf("dq2")]
                v = [S._r80(tg, d[k][mm], sm, floor=fl) for k, sm, fl in zip(S.CH4, sim, S.AIR_FLOOR)]
                if all(np.isfinite(v)): per.append(float(np.mean([min(x,10.) for x in v])))
            out[sub] = float(np.mean(per)) if per else 3.0
    finally:
        if keep is None: os.environ.pop("FS_MASS", None)
        else: os.environ["FS_MASS"] = keep
        FR._CACHE.clear(); S._CVT_STAMPED.clear()
    return out

print("무릎 손실 (fc0 + fc1·|명령|)·tanh(속도/v0) 를 넣었을 때 (0 이 완벽)")
print(f"{'설정':30s} {'일어서기 평균':>12s} {'변속0':>7s} {'변속2.5':>8s} {'변속5':>7s} {'무변속':>7s} {'점프 주입':>9s}")
print("-"*100)
for tag, mode, mix in (("지금 (canon_cap)", "canon_cap", None),
                       ("canon_mix fc1=0",  "canon_mix", "0.18,0.00,0,0.3"),
                       ("canon_mix fc1=0.08","canon_mix","0.18,0.08,0,0.3"),
                       ("canon_mix fc1=0.16","canon_mix","0.18,0.16,0,0.3"),
                       ("canon_mix fc1=0.30","canon_mix","0.18,0.30,0,0.3")):
    e = S.env_of("canon_cap", BASE)
    e["FS_TMAP"] = mode
    if mix: e["FS_TMIX"] = mix
    else: e.pop("FS_TMIX", None)
    S._apply(e)
    if not mix: os.environ.pop("FS_TMIX", None)
    s = board_s2s()
    S._apply(e)
    B = S.board()
    ma = S.absm(B, "ma8", S.FIT, (0,1,2,3))
    m = float(np.mean(list(s.values())))
    print(f"{tag:30s} {m:12.3f} {s.get('cvt/no_load',float('nan')):7.3f} "
          f"{s.get('cvt/load_2.5',float('nan')):8.3f} {s.get('cvt/load_5',float('nan')):7.3f} "
          f"{s.get('no_cvt/no_load',float('nan')):7.3f} {ma:9.4f}")
print("-"*100)
print("점프 주입 = 점프 8세션 측정토크 주입 재생 (0 이 완벽, 지금 0.1747). 이게 나빠지면 대가가 있는 것.")
