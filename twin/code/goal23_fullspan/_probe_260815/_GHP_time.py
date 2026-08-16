# -*- coding: utf-8 -*-
"""_GHP_time — 창 1개 Δ 되찾기 비용 측정 (무거운 탐색과 겹치므로 먼저 잰다)."""
import os, sys, time
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("FS_SWEEP_AIR", "0")
os.environ.setdefault("FS_SWEEP_S2S", "1")
os.environ["FS_CVT_XML"] = "0"
from pathlib import Path
HERE = str(Path(__file__).parent)
sys.path.insert(0, HERE); os.chdir(HERE)
import numpy as np
import fs_data as FD, fs_runner as FR, fs_cvt as FC, _GHB_sweep as S
import _GHC_s2s_missing as MS

t0 = time.time()
S._apply(S.env_of("canon_cap", np.asarray(S.DEPLOY, float)))
m0 = float(os.environ.get("FS_MASS", "3.30"))
print("env:", {k: os.environ.get(k) for k in ("FS_TMAP", "FS_TDCAP", "FS_MASS", "FS_KNEEM_FL", "FS_CVT_DISS_SCALE")})
sub, pay, cvt = FD.S2S_CASES[0]
d = FD.load_s2s(sub)
os.environ["FS_MASS"] = f"{m0 + pay:.4f}"
FR._CACHE.clear(); S._CVT_STAMPED.clear()
t1 = time.time()
ft = FC.cvt_ft(float(d["l_i"]), ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
t2 = time.time()
print(f"모델 빌드 {t2-t1:.1f}s (적재 포함 {t2-t0:.1f}s)")
t = d["t"]
mm = (t >= 0.30) & (t <= 0.45)
t3 = time.time()
e = MS.err_of(ft, d, mm, 0.0)
t4 = time.time()
print(f"재생 1회 {t4-t3:.3f}s  (Δ=0 에서 창끝 오차 {e:+.3f}도)")
dl = MS.solve_delta(ft, d, mm)
t5 = time.time()
print(f"Δ 되찾기 1창 {t5-t4:.2f}s → Δ={dl}")
