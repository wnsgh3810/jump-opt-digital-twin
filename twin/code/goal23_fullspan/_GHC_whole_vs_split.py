# 통짜 판이 **모델 품질을 구분하는 힘**이 있나 — 좋은/지금/나쁜 모델 셋을 통짜와 나눈 것으로 각각 재서
#   "얼마나 벌어지나"를 비교한다. 통짜가 셋을 다 비슷하게 찍으면 그 판은 포화된 것(= 너무 가혹).
import os, sys
os.environ.setdefault("FS_SWEEP_AIR", "0"); os.environ.setdefault("FS_SWEEP_S2S", "1")
from pathlib import Path
GFS = str(Path(__file__).parent)
sys.path.insert(0, GFS); os.chdir(GFS)
import numpy as np
import fs_data as FD, fs_runner as FR, fs_cvt as FC, _GHB_sweep as S
B = np.asarray(S.DEPLOY, float)

def one(ft, d, t0, t1, cap):
    t = d["t"]; mm = (t >= t0) & (t <= t1)
    if mm.sum() < 20: return None
    i0 = int(np.argmax(mm)); tg = t[mm] - t[i0]
    L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][mm], d["raw2"][mm],
                           float(d["q1"][i0]), float(d["q2"][i0]),
                           float(d["dq1"][i0]), float(d["dq2"][i0]),
                           float(tg[-1]-0.004), fade=True)
    if L is None: return None
    gf = lambda k: np.interp(tg, L["t"], L[k])
    sim = [gf("thm1"), gf("q2"), gf("dq1"), gf("dq2")]
    v = [S._r80(tg, d[k][mm], sm, floor=fl) for k, sm, fl in zip(S.CH4, sim, S.AIR_FLOOR)]
    if not all(np.isfinite(v)): return None
    # 오차가 10도 넘을 때까지 버틴 시간 [s] — 발산하는 판에서도 안 포화되는 지표
    e = np.degrees(np.abs(sim[1] - d["q2"][mm]))
    k = np.where(e > 10.0)[0]
    hold = float(tg[k[0]]) if len(k) else float(tg[-1])
    return float(np.mean([min(x, cap) for x in v])), hold

def board(x, mix=None):
    e = S.env_of("canon_cap", np.asarray(x, float))
    if mix: e["FS_TMAP"] = "canon_mix"; e["FS_TMIX"] = mix
    S._apply(e)
    if not mix: os.environ.pop("FS_TMIX", None)
    m0 = float(os.environ.get("FS_MASS", "3.30")); keep = os.environ.get("FS_MASS")
    W, SP, HD = [], [], []
    try:
        for sub, pay, cvt in FD.S2S_CASES:
            d = FD.load_s2s(sub)
            if d is None: continue
            os.environ["FS_MASS"] = f"{m0+pay:.4f}"
            FR._CACHE.clear(); S._CVT_STAMPED.clear()
            ft = FC.cvt_ft(float(d["l_i"]), ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
            w = one(ft, d, float(d["t"][0]), float(d["t"][-1]), 10.0)
            W.append(w[0] if w else 10.0); HD.append(w[1] if w else 0.0)
            per = [one(ft, d, a, b, 10.0) for a, b in FD.air_windows(d, nwin=4, wmax=2.0)]
            per = [p for p in per if p]
            SP.append(float(np.mean([p[0] for p in per])) if per else 3.0)
    finally:
        if keep is None: os.environ.pop("FS_MASS", None)
        else: os.environ["FS_MASS"] = keep
        FR._CACHE.clear(); S._CVT_STAMPED.clear()
    return float(np.mean(W)), float(np.mean(SP)), float(np.mean(HD))

print("일어서기 판 — 세 모델을 세 가지 방식으로 (성적은 0 이 완벽 · 버틴 시간은 길수록 좋다)")
print(f"{'모델':30s} {'통짜 성적':>10s} {'나눈 성적':>10s} {'버틴 시간':>10s}")
print("-"*66)
bad = B.copy(); bad[0] = 0.05          # 무릎 건마찰을 일부러 낮춘 나쁜 모델
good = B.copy()
for tag, x, mix in (("일부러 나쁘게 (무릎마찰 0.05)", bad, None),
                    ("지금 쓰는 모델", B, None),
                    ("좋게 (하중비례 0.30)", good, "0.18,0.30,0,0.3")):
    w, s, h = board(x, mix)
    print(f"{tag:30s} {w:10.3f} {s:10.3f} {h:9.3f}s")
print("-"*66)
print("통짜가 세 모델을 비슷하게 찍으면 = 포화(너무 가혹) · 벌어지면 = 통짜만으로 충분")
