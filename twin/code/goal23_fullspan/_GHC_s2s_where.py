# "오차가 어디서 **생기나**" — 짧은 창을 자세마다 새로 앵커해서 국소 발산 속도를 잰다.
#   앞 판의 결함: 통짜 재생은 오차가 시간에 따라 쌓여서, 늦게 지나는 자세일수록 무조건
#   커 보인다 (자세 탓인지 누적 탓인지 구분 불가).
#   고침: 0.15초짜리 창을 0.05초 간격으로 밀며 **매번 그 순간의 실측 상태로 다시 시작**한다.
#         그러면 각 창의 오차는 그 구간에서 **새로 생긴 것**만 담는다.
import os, sys, collections
os.environ.setdefault("FS_SWEEP_AIR", "0"); os.environ.setdefault("FS_SWEEP_S2S", "1")
from pathlib import Path
GFS = str(Path(__file__).parent)
sys.path.insert(0, GFS); os.chdir(GFS)
import numpy as np
import fs_data as FD, fs_runner as FR, fs_cvt as FC, _GHB_sweep as S

S._apply(S.env_of("canon_cap", np.asarray(S.DEPLOY, float)))
m0 = float(os.environ.get("FS_MASS", "3.30"))
WIN, STEP = 0.15, 0.05
BINS = [(-180, -170), (-170, -160), (-160, -140), (-140, -120), (-120, -90), (-90, -60), (-60, 0)]

print(f"0.15초 창을 매번 실측 상태로 새로 시작 → 그 창에서 **새로 생긴** 무릎각 오차 [도]")
print(f"{'경우':16s} " + " ".join(f"{a}~{b}".rjust(11) for a, b in BINS))
print("-" * 100)
res = {}
for sub, pay, cvt in FD.S2S_CASES:
    d = FD.load_s2s(sub)
    if d is None:
        continue
    W = FD.air_windows(d, nwin=4, wmax=2.0)
    os.environ["FS_MASS"] = f"{m0 + pay:.4f}"
    FR._CACHE.clear(); S._CVT_STAMPED.clear()
    ft = FC.cvt_ft(float(d["l_i"]), ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
    t = d["t"]
    acc = collections.defaultdict(list)
    for w0, w1 in W:
        a = w0
        while a + WIN <= w1:
            mm = (t >= a) & (t <= a + WIN)
            if mm.sum() >= 20:
                i0 = int(np.argmax(mm)); tg = t[mm] - t[i0]
                L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][mm], d["raw2"][mm],
                                       float(d["q1"][i0]), float(d["q2"][i0]),
                                       float(d["dq1"][i0]), float(d["dq2"][i0]),
                                       float(tg[-1] - 0.004), fade=True)
                if L is not None:
                    sim = np.interp(tg, L["t"], L["q2"])
                    e = float(np.degrees(np.abs(sim - d["q2"][mm])[-1]))   # 창 끝의 어긋남
                    cr = float(np.degrees(np.mean(d["q2"][mm])))
                    sp = float(np.mean(np.abs(d["dq2"][mm])))
                    for b in BINS:
                        if b[0] <= cr < b[1]:
                            acc[b].append((e, sp)); break
            a += STEP
    res[sub] = acc
    row = []
    for b in BINS:
        if acc[b]:
            row.append(f"{np.mean([x[0] for x in acc[b]]):7.2f}({len(acc[b]):3d})")
        else:
            row.append(" " * 11)
    print(f"{sub:16s} " + " ".join(row))
print("-" * 100)
print("괄호 = 창 개수. 변속기 사점 = 크랭크 -176.5° · 전달비 0.19 = -170° · 무변속은 전 각도 1.0")
print()
print("같은 창들의 평균 크랭크 속도 [rad/s] — 오차가 속도 탓인지 자세 탓인지 가르는 대조")
print(f"{'경우':16s} " + " ".join(f"{a}~{b}".rjust(11) for a, b in BINS))
for sub, acc in res.items():
    row = []
    for b in BINS:
        row.append(f"{np.mean([x[1] for x in acc[b]]):11.2f}" if acc[b] else " " * 11)
    print(f"{sub:16s} " + " ".join(row))
