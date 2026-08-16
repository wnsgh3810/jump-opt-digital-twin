# 하중 비례 무릎 손실을 넣으면 **최종 지표**(계획 토크 vs 측정 토크)가 버티나?
#   일어서기는 3.163 -> 1.542 로 절반이 됐는데, 최종 목표까지 상하면 그 축은 쓸 수 없다.
import os, sys, json
os.environ.setdefault("FS_SWEEP_AIR", "0"); os.environ.setdefault("FS_SWEEP_S2S", "0")
from pathlib import Path
GFS = str(Path(__file__).parent)
sys.path.insert(0, GFS); os.chdir(GFS)
import numpy as np
import fs_data as FD, fs_compare_plot as CP, _GHB_sweep as S

def rel(plan, meas):
    p = np.asarray(plan, float); m = np.asarray(meas, float)
    e = float(np.sqrt(np.mean((p-m)**2))); r = float(np.sqrt(np.mean(p**2)))
    return e/r, float(np.corrcoef(p, m)[0,1])

def taufid(tag):
    base = FD.SESS_FIT["26.07.27"]
    acc = []
    for fold in FD.trials_of(base):
        d = FD.load2(fold); d["_sess"] = "26.07.27"; d["_fold"] = fold
        g = FD.gains_of(fold.name); seg = FD.segment(d)
        r = CP.cl_pair(d, seg, g, "26.07.27", show_old=False, cmd_tau=True)
        if r is None: continue
        t, (mo, mf), old, fs, m, cmd, pl = r
        k = t <= t[0] + 0.8*(t[-1]-t[0])
        c1, c2 = np.asarray(cmd[4]), np.asarray(cmd[5])
        mm = (d["t"] >= t[0]) & (d["t"] <= t[-1])
        r1, r2 = d["raw1"][mm], d["raw2"][mm]
        n = min(len(k), len(c1), len(r1)); k = k[:n]
        acc.append((rel(c1[:n][k], r1[:n][k])[0], rel(c2[:n][k], r2[:n][k])[0]))
    a = np.array(acc)
    print(f"{tag:28s} 힙 {a[:,0].mean():.3f}   무릎 {a[:,1].mean():.3f}   ({len(acc)} 시행)")
    return a.mean(axis=0)

X = np.asarray(S.DEPLOY, float)
print("최종 지표 = (트윈 명령 − 실기 명령) ÷ 트윈 명령, 26.07.27 평균. 0 이 완벽\n")
e = S.env_of("canon_cap", X); S._apply(e); os.environ.pop("FS_TMIX", None)
d0 = taufid("지금 (canon_cap)")
for fc1 in (0.16, 0.30):
    e = S.env_of("canon_cap", X); e["FS_TMAP"] = "canon_mix"; e["FS_TMIX"] = f"0.18,{fc1:.2f},0,0.3"
    S._apply(e)
    d = taufid(f"하중비례 fc1={fc1}")
    print(f"     → 힙 {100*(d[0]-d0[0])/d0[0]:+.1f}% · 무릎 {100*(d[1]-d0[1])/d0[1]:+.1f}%\n")
print("[참고] 일어서기 판: 지금 3.163 · fc1=0.16 3.082 · fc1=0.30 1.542 (0 이 완벽)")
print("[참고] 탐색 중간 승자는 힙 +5.8% · 무릎 +14.7% 로 악화했다")
