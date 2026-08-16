# 개선된 트윈이 "최종 지표"까지 좋아지게 하나 — 계획 토크 vs 측정 토크 (26.07.27)
#   비교: 지금 쓰는 모델 vs 탐색 중간 승자. 둘 다 같은 목표각을 폐루프로 돌려
#   그 트윈이 만든 명령 토크를 실기가 실제로 낸 명령 토크와 비교한다 (환산식 통과 전).
import os, sys, json
os.environ.setdefault("FS_SWEEP_AIR", "0"); os.environ.setdefault("FS_SWEEP_S2S", "0")
from pathlib import Path
GFS = str(Path(__file__).parent)
sys.path.insert(0, GFS); os.chdir(GFS)
import numpy as np
import fs_data as FD, fs_compare_plot as CP, _GHB_sweep as S

# ★ 08-16 재적용 — **최종 승자 파일**을 읽는다 (구조 이름도 같이).
_TAG = os.environ.get("FS_CMP_FROM", "_GHB_sweep8.json")
_J = json.load(open(_TAG, encoding="utf-8"))["res"]
MODE = sorted(_J, key=lambda m: _J[m]["score"])[0]
best = {"x": _J[MODE]["x"], "v": _J[MODE]["score"], "t": _J[MODE]["minutes"] * 60}
print("승자: %s · 구조 %s · 축 %d 개 · 점수 %.5f" % (_TAG, MODE, len(best["x"]), best["v"]))

def rel(plan, meas):
    p = np.asarray(plan, float); m = np.asarray(meas, float)
    e = float(np.sqrt(np.mean((p-m)**2))); r = float(np.sqrt(np.mean(p**2)))
    return e/r, float(np.corrcoef(p, m)[0,1]), float(np.max(np.abs(m)))/max(float(np.max(np.abs(p))),1e-9)

def run(x, tag, mode="canon_cap"):
    S._apply(S.env_of(mode, np.asarray(x, float)))
    base = FD.SESS_FIT["26.07.27"]
    print(f"== {tag} ==")
    print(f"{'시행':18s} {'힙 상대':>8s} {'힙 상관':>8s} {'힙 피크비':>9s} {'무릎 상대':>9s} {'무릎 상관':>9s} {'무릎 피크비':>10s}")
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
        h = rel(c1[:n][k], r1[:n][k]); kn = rel(c2[:n][k], r2[:n][k])
        acc.append((h[0], kn[0]))
        print(f"{fold.name:18s} {h[0]:8.3f} {h[1]:8.3f} {h[2]:9.2f} {kn[0]:9.3f} {kn[1]:9.3f} {kn[2]:10.2f}")
    a = np.array(acc)
    print(f"{'평균':18s} {a[:,0].mean():8.3f} {'':8s} {'':9s} {a[:,1].mean():9.3f}\n")
    return a.mean(axis=0)

d0 = run(np.asarray(S.DEPLOY, float), "지금 쓰는 모델")
d1 = run(np.asarray(best["x"], float), "8회차 승자", MODE)
print(f"힙  {d0[0]:.3f} → {d1[0]:.3f}  ({100*(d1[0]-d0[0])/d0[0]:+.1f}%)")
print(f"무릎 {d0[1]:.3f} → {d1[1]:.3f}  ({100*(d1[1]-d0[1])/d0[1]:+.1f}%)")
print("\n상대 = (트윈 명령 − 실기 명령)의 제곱평균 ÷ 트윈 명령의 제곱평균. 0 이 완벽.")
print("[대조] 실제 배포된 계획(07-25 트윈)의 같은 값: 힙 0.461 · 무릎 0.276")
