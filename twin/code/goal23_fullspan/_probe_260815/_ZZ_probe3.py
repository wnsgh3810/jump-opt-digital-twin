# -*- coding: utf-8 -*-
"""원자료만으로 각 게이트가 어디서 켜지는지 계량 (MuJoCo 미사용)."""
import os, sys
os.environ["PYTHONIOENCODING"] = "utf-8"
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import numpy as np
import fs_data as FD

LAW_V0_KNEE = 7.296751871368546     # supp 속도 게이트 v0 (무릎)
V01_HIP = 6.3999970141423645        # hip_supp 속도 게이트 v0
KNEE_DEEP_TH = np.degrees(-2.2706733568446227)   # knee_deep 결합각 (0424/0602/0421)


def gate_v(v, v0):
    return 1.0 / (1.0 + (np.abs(v) / v0) ** 2)


def stat(tag, t, q1, q2, dq1, dq2, r1, r2):
    n = len(t)
    dur = float(t[-1] - t[0])
    f_slow2 = float(np.mean(np.abs(dq2) < 1.0))
    f_slow1 = float(np.mean(np.abs(dq1) < 1.0))
    print(f"\n■ {tag}  (길이 {dur:.2f}s, {n} 샘플)")
    print(f"   무릎축속도 |dq2|: 중앙 {np.median(np.abs(dq2)):5.2f} p90 {np.percentile(np.abs(dq2),90):6.2f} "
          f"최대 {np.abs(dq2).max():6.2f} rad/s | 1 rad/s 미만 시간 {f_slow2*100:4.1f}%")
    print(f"   힙속도  |dq1|: 중앙 {np.median(np.abs(dq1)):5.2f} p90 {np.percentile(np.abs(dq1),90):6.2f} "
          f"최대 {np.abs(dq1).max():6.2f} rad/s | 1 rad/s 미만 시간 {f_slow1*100:4.1f}%")
    print(f"   무릎각 q2: 중앙 {np.degrees(np.median(q2)):7.1f}° 최소 {np.degrees(q2.min()):7.1f}° "
          f"최대 {np.degrees(q2.max()):7.1f}° | {KNEE_DEEP_TH:.0f}° 보다 깊은 시간 {np.mean(np.degrees(q2)<KNEE_DEEP_TH)*100:4.1f}%")
    print(f"   명령토크 |raw|: 힙 중앙 {np.median(np.abs(r1)):5.2f} p90 {np.percentile(np.abs(r1),90):6.2f} | "
          f"무릎 중앙 {np.median(np.abs(r2)):5.2f} p90 {np.percentile(np.abs(r2),90):6.2f} N·m")
    print(f"   [지지층 게이트] 무릎 gate_v(v0={LAW_V0_KNEE:.2f}) 평균 {np.mean(gate_v(dq2,LAW_V0_KNEE)):.3f} "
          f"| 힙 gate_v(v0={V01_HIP:.2f}) 평균 {np.mean(gate_v(dq1,V01_HIP)):.3f}  (1=완전작동, 0=소멸)")
    print(f"   [상승항 rise] (1-gate) 평균 무릎 {np.mean(1-gate_v(dq2,LAW_V0_KNEE)):.3f} "
          f"| k_rise·dq2·(1-g) 평균크기 {np.mean(np.abs(0.2656*dq2*(1-gate_v(dq2,LAW_V0_KNEE)))):.3f} N·m")
    print(f"   [fade(|dq1|>1 에서 감쇠)] 유효 bias 배수 평균 "
          f"{np.mean(np.clip(1-(np.abs(dq1)-1)/2,0,1)):.3f}")


print("=== 짐 지고 일어서기 26.06.04 (S2S_CASES) ===")
for sub, pay, cvt in FD.S2S_CASES:
    try:
        d = FD.load_s2s(sub)
    except Exception as ex:
        print(f"{sub}: 적재 실패 {ex}")
        continue
    t, q1, q2 = d["t"], d["q1"], d["q2"]
    stat(f"{sub}  짐 {pay}kg  변속기 {'O' if cvt else 'X'}  l_i={d['l_i']*1000:.2f}mm",
         t, q1, q2, d["dq1"], d["dq2"], d["raw1"], d["raw2"])

print("\n\n=== 점프 (fit 세션 각 1 trial) ===")
seen = set()
for s, p, g, cvt, ho in FD.registry():
    if s in seen or cvt or ho or not g:
        continue
    seen.add(s)
    if len(seen) > 3:
        break
    try:
        d = FD.load2(p); seg = FD.segment(d)
        m = seg["score"]
        stat(f"{s}/{p.name} (채점창)", d["t"][m], d["q1"][m], d["q2"][m],
             d["dq1"][m], d["dq2"][m], d["raw1"][m], d["raw2"][m])
    except Exception as ex:
        print(f"{s}/{p.name}: {type(ex).__name__} {ex}")
