# 중간 승자가 "물리를 고쳤나" 확인 — 국소 오차(재앵커 짧은 창)와 모자란 토크를 다시 잰다.
#   점수만 좋아지고 국소가 그대로면 발산 시점만 미룬 것이다.
import os, sys, json, collections
os.environ.setdefault("FS_SWEEP_AIR", "0"); os.environ.setdefault("FS_SWEEP_S2S", "1")
from pathlib import Path
GFS = str(Path(__file__).parent)
sys.path.insert(0, GFS); os.chdir(GFS)
import numpy as np
import fs_data as FD, fs_runner as FR, fs_cvt as FC, _GHB_sweep as S
from _GHC_s2s_missing import solve_delta

rows = [json.loads(l) for l in open("_GHB_sweep5_trials.jsonl", encoding="utf-8")]
best = min(rows, key=lambda r: r["v"])
XW = np.asarray(best["x"], float)
print(f"중간 승자: {best['t']/60:.1f}분 지점 · 점수 {best['v']:.5f}")

WIN, STEP = 0.15, 0.05
BINS = [(-180,-160), (-160,-140), (-140,-120), (-120,-90), (-90,-60), (-60,0)]

def run(x, tag):
    S._apply(S.env_of("canon_cap", np.asarray(x, float)))
    m0 = float(os.environ.get("FS_MASS", "3.30")); keep = os.environ.get("FS_MASS")
    print(f"\n== {tag} ==")
    print(f"{'경우':16s} " + " ".join(f"{a}~{b}".rjust(11) for a,b in BINS) + "   | 모자란 토크 깊은접힘")
    try:
        for sub, pay, cvt in FD.S2S_CASES:
            d = FD.load_s2s(sub)
            if d is None: continue
            W = FD.air_windows(d, nwin=4, wmax=2.0)
            os.environ["FS_MASS"] = f"{m0+pay:.4f}"
            FR._CACHE.clear(); S._CVT_STAMPED.clear()
            ft = FC.cvt_ft(float(d["l_i"]), ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
            t = d["t"]; acc = collections.defaultdict(list); dl_deep = []
            for w0, w1 in W:
                a = w0
                while a + WIN <= w1:
                    mm = (t >= a) & (t <= a + WIN)
                    if mm.sum() >= 20:
                        i0 = int(np.argmax(mm)); tg = t[mm]-t[i0]
                        L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][mm], d["raw2"][mm],
                                               float(d["q1"][i0]), float(d["q2"][i0]),
                                               float(d["dq1"][i0]), float(d["dq2"][i0]),
                                               float(tg[-1]-0.004), fade=True)
                        cr = float(np.degrees(np.mean(d["q2"][mm])))
                        if L is not None:
                            sim = np.interp(tg, L["t"], L["q2"])
                            e = float(np.degrees(np.abs(sim - d["q2"][mm])[-1]))
                            for b in BINS:
                                if b[0] <= cr < b[1]: acc[b].append(e); break
                        if cr < -155:
                            v = solve_delta(ft, d, mm)
                            if v is not None: dl_deep.append(v)
                    a += STEP
            row = [f"{np.mean(acc[b]):7.2f}({len(acc[b]):2d})" if acc[b] else " "*11 for b in BINS]
            dd = f"{np.mean(dl_deep):+7.2f}({len(dl_deep):2d})" if dl_deep else "   —   "
            print(f"{sub:16s} " + " ".join(row) + f"   | {dd}")
    finally:
        if keep is None: os.environ.pop("FS_MASS", None)
        else: os.environ["FS_MASS"] = keep
        FR._CACHE.clear(); S._CVT_STAMPED.clear()

run(np.asarray(S.DEPLOY, float), "지금 쓰는 모델 (출발점)")
run(XW, "탐색 중간 승자")
print("\n왼쪽 = 그 자세에서 새로 생긴 무릎각 오차 [도] (0이 완벽)")
print("오른쪽 = 깊은 접힘에서 모자란 무릎 명령 토크 [N·m] (0이 완벽, −는 모델이 너무 많이 민다는 뜻)")
