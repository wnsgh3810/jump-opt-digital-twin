# 예측 시험: 하중 비례 손실을 넣으면 **무릎 속도비례 마찰이 실측(≈0.034) 쪽으로 내려가고 싶어지나?**
#   지금 그 값은 0.228 로 실측의 6.7배다. 그 축이 하중 비례 손실을 대신 떠맡고 있었다면,
#   진짜 항이 들어온 뒤에는 낮은 값이 더 좋아져야 한다. 아니면 내 해석이 틀린 것이다.
import os, sys
os.environ.setdefault("FS_SWEEP_AIR", "0"); os.environ.setdefault("FS_SWEEP_S2S", "1")
from pathlib import Path
GFS = str(Path(__file__).parent)
sys.path.insert(0, GFS); os.chdir(GFS)
import numpy as np
import fs_data as FD, fs_runner as FR, fs_cvt as FC, _GHB_sweep as S
S._ensure()
BASE = np.asarray(S.DEPLOY, float)

def s2s_score():
    m0 = float(os.environ.get("FS_MASS", "3.30")); keep = os.environ.get("FS_MASS")
    out = []
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
                i0 = int(np.argmax(mm)); tg = t[mm]-t[i0]
                L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][mm], d["raw2"][mm],
                                       float(d["q1"][i0]), float(d["q2"][i0]),
                                       float(d["dq1"][i0]), float(d["dq2"][i0]),
                                       float(tg[-1]-0.004), fade=True)
                if L is None: continue
                gf = lambda k: np.interp(tg, L["t"], L[k])
                sim = [gf("thm1"), gf("q2"), gf("dq1"), gf("dq2")]
                v = [S._r80(tg, d[k][mm], sm, floor=fl) for k, sm, fl in zip(S.CH4, sim, S.AIR_FLOOR)]
                if all(np.isfinite(v)): per.append(float(np.mean([min(x,10.) for x in v])))
            out.append(float(np.mean(per)) if per else 3.0)
    finally:
        if keep is None: os.environ.pop("FS_MASS", None)
        else: os.environ["FS_MASS"] = keep
        FR._CACHE.clear(); S._CVT_STAMPED.clear()
    return float(np.mean(out))

print("무릎 속도비례 마찰을 바꿔 가며 — **건마찰은 실측 0.423 으로 올려놓고** (지금 모델은 0.118)")
print(f"{'무릎 속도비례':>14s} {'천장 그대로':>14s} {'하중비례 0.30':>16s}")
print("-"*50)
for damp in (0.00, 0.034, 0.08, 0.15, 0.228):
    row = []
    for mode, mix in (("canon_cap", None), ("canon_mix", "0.18,0.30,0,0.3")):
        x = BASE.copy(); x[2] = damp; x[0] = 0.423
        e = S.env_of("canon_cap", x); e["FS_TMAP"] = mode
        if mix: e["FS_TMIX"] = mix
        S._apply(e)
        if not mix: os.environ.pop("FS_TMIX", None)
        row.append(s2s_score())
    print(f"{damp:14.3f} {row[0]:14.3f} {row[1]:16.3f}")
print("-"*50)
print("값은 짐 지고 일어서기 판 (0 이 완벽). 하중비례를 넣었을 때 낮은 마찰이 더 좋아지면 예측 적중.")
