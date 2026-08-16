# -*- coding: utf-8 -*-
"""exp5_video_slip — 26.07.27 7게인 영상 전수 검증: 발 중심 픽셀 추적으로 진짜 슬립 상계 측정.

파이프라인 (250 검증에서 확립):
  ① 프레임 차분으로 점프 순간 탐지 → 스탠스 프레임 구간
  ② 패드 왼쪽 가장자리 x 불변 확인 (카메라·지면 고정 검증)
  ③ 발 중심(볼트홀) 템플릿 매칭: 250 템플릿으로 코스 위치 → 자기 영상 템플릿로 정밀 추적
  ④ 픽셀→mm (0.7~1.2mm/px 범위), 구름 기여 r·Δθ (r=20~25mm, Δθ=인코더 정강이 회전) 차감
산출: _exp5_video_slip.json + graphs/exp5/slip_timeline/video_slip_summary.png
"""
# --- 실험 데이터 경로: 단일 출처 (code/bench/datapaths.py) ---
import os as _o, sys as _s
_d = _o.path.dirname(_o.path.abspath(__file__))
while _d != _o.path.dirname(_d) and not _o.path.isdir(_o.path.join(_d, 'code', 'bench')):
    _d = _o.path.dirname(_d)
if _o.path.join(_d, 'code', 'bench') not in _s.path:
    _s.path.append(_o.path.join(_d, 'code', 'bench'))
from datapaths import DATA_ROOT, CVT_ROOT  # noqa: E402
# ---------------------------------------------------------------
import os, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np, pandas as pd
import imageio.v3 as iio
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
DATA = Path((DATA_ROOT + "/26_07_27"))
OUT = HERE / "graphs" / "exp5" / "slip_timeline"; OUT.mkdir(parents=True, exist_ok=True)
GAINS = sorted([p.name for p in DATA.iterdir() if p.is_dir() and (p/"hip.xlsx").exists()],
               key=lambda s: float(s.split("_")[0]))
SCALE = (0.7, 1.2)          # mm/px 범위 (광학테이블 25mm 피치 + 정강이 250mm 교차 추정)
R_FOOT = (20.0, 25.0)       # 발 휠 반지름 [mm] 범위

def gray(a): return a.mean(axis=2)

def read_frames(mp4):
    return [gray(f) for f in iio.imiter(str(mp4), plugin="FFMPEG")]

def stance_range(frames):
    d = [float(np.abs(frames[i+1]-frames[i]).mean()) for i in range(len(frames)-1)]
    top = np.argsort(d)[-12:]
    j = int(min(top))                       # 점프 클러스터 시작 ≈ 이륙 부근
    return list(range(max(0, j-7), min(len(frames)-1, j+2))), j

def pad_edge(f, y=1210, x0=200, x1=400):
    row = f[y, x0:x1]
    return int(np.argmax(np.abs(np.diff(row)))) + x0

def match(f, T, cy, cx, ry=28, rx=80):
    h = T.shape[0]//2
    best = (1e18, 0, 0)
    for dy in range(-ry, ry+1):
        for dx in range(-rx, rx+1):
            p = f[cy+dy-h:cy+dy+h, cx+dx-h:cx+dx+h]
            if p.shape != T.shape: continue
            s = float(((p-T)**2).mean())
            if s < best[0]: best = (s, dx, dy)
    return best

# ── 250 영상에서 기준 템플릿 확보 (검증 완료된 좌표) ──
mp250 = next((DATA/"250_3_250_3").glob("*.mp4"))
fr250 = read_frames(mp250)
st250, _ = stance_range(fr250)
TY, TX = 1183, 368
T_REF = fr250[st250[2]][TY-18:TY+18, TX-18:TX+18].copy()

RES = {}
for lab in GAINS:
    mp4 = next((DATA/lab).glob("*.mp4"))
    fr = read_frames(mp4)
    st, j = stance_range(fr)
    # 패드 고정 검증 (스탠스 프레임들)
    pe = [pad_edge(fr[i]) for i in st[:6]]
    pad_ok = (max(pe)-min(pe)) <= 2
    # 코스: 250 템플릿으로 이 영상 발 위치 찾기 (정착된 크라우치 프레임 j−5)
    e0, dx0, dy0 = match(fr[j-5], T_REF, TY, TX, ry=40, rx=100)
    cy, cx = TY+dy0, TX+dx0
    # 자기 템플릿 = j−6 (크라우치 정착) → j−6..j+1 절대 탐색 추적
    T_own = fr[j-6][cy-18:cy+18, cx-18:cx+18].copy()
    track = []
    for i in range(j-6, min(j+2, len(fr))):
        e, dx, dy = match(fr[i], T_own, cy, cx)
        track.append((i, e, dx, dy))
    # 컷: 매칭오차 1300 미만(발 온전) + 이웃 중위수 대비 25px 초과 튐 제거 (블러 오매칭)
    good = [x for x in track if x[1] <= 1300]
    dxs0 = [x[2] for x in good]
    dxs = [d for k, d in enumerate(dxs0)
           if abs(d - np.median(dxs0[max(0,k-1):k+2])) <= 25]
    if len(dxs) >= 3:
        disp_px = max(abs(dxs[-1]-dxs[0]), max(abs(d-dxs[0]) for d in dxs))
    else:
        disp_px = np.nan
    # 구름 기여: 인코더 정강이 회전 (onset→liftoff)
    h_ = pd.read_excel(DATA/lab/"hip.xlsx"); k_ = pd.read_excel(DATA/lab/"knee.xlsx"); g_ = pd.read_excel(DATA/lab/"GRF.xlsx")
    n = min(len(h_), len(k_), len(g_)); h_, k_, g_ = h_.iloc[:n], k_.iloc[:n], g_.iloc[:n]
    t = h_["Time"].to_numpy(float)-h_["Time"].iloc[0]
    sh = h_["currentAngle"].to_numpy(float)+k_["currentAngle"].to_numpy(float)   # q1+q2 [rad]
    qd2 = k_["desiredAngle"].to_numpy(float); on = np.where(np.abs(qd2-qd2[0]) > np.radians(0.5))[0]
    t0 = t[on[0]] if len(on) else 0
    gg = g_["Current_GRF"].to_numpy(float); g0 = np.median(gg[-5:]); thr_g = g0+0.06*(np.nanmax(gg)-g0)
    ab = np.where(gg >= thr_g)[0]; tlo = t[min(int(ab[-1])+1, len(t)-1)]
    i0, i1 = np.searchsorted(t, t0), np.searchsorted(t, tlo)-1
    dth = abs(float(sh[i1]-sh[i0]))                        # rad
    disp_mm = (disp_px*SCALE[0], disp_px*SCALE[1])
    roll_mm = (R_FOOT[0]*dth*0.8, R_FOOT[1]*dth)           # 하한: 마지막 프레임 갭 감안 0.8
    true_lo = max(0.0, disp_mm[0]-roll_mm[1]); true_hi = max(0.0, disp_mm[1]-roll_mm[0])
    RES[lab] = dict(hipkp=float(lab.split("_")[0]), n_track=len(good), pad_ok=bool(pad_ok),
                    pad_spread=int(max(pe)-min(pe)), coarse_err=round(e0,0),
                    disp_px=float(disp_px), disp_mm=[round(disp_mm[0],1), round(disp_mm[1],1)],
                    shank_rot_deg=round(np.degrees(dth),1), roll_mm=[round(roll_mm[0],1), round(roll_mm[1],1)],
                    true_slip_mm=[round(true_lo,1), round(true_hi,1)], dxs=dxs)
    print(f"{lab.split('_')[0]:>4}: 패드{'✓' if pad_ok else '✗'}(spread {max(pe)-min(pe)}px) 추적 {len(good)}f "
          f"dx={dxs} → 이동 {disp_px:.0f}px = {disp_mm[0]:.0f}~{disp_mm[1]:.0f}mm | "
          f"정강이 {np.degrees(dth):.0f}° 구름 {roll_mm[0]:.0f}~{roll_mm[1]:.0f}mm | "
          f"진짜슬립 {true_lo:.0f}~{true_hi:.0f}mm", flush=True)

json.dump(RES, open(HERE/"_exp5_video_slip.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ── 종합 그림: 영상 슬립 vs FK 슬립, 효율 재대조 ──
E = json.load(open(HERE/"_exp5_energy.json", encoding="utf-8"))
kp = [RES[g]["hipkp"] for g in GAINS]
fig, ax = plt.subplots(1, 3, figsize=(19, 5.4))
fk_max = [abs(E[g]["slip_absmax"]) for g in GAINS]
fk_net = [abs(E[g]["slip_net"]) for g in GAINS]
v_lo = [RES[g]["true_slip_mm"][0] for g in GAINS]; v_hi = [RES[g]["true_slip_mm"][1] for g in GAINS]
v_mid = [(a+b)/2 for a, b in zip(v_lo, v_hi)]
d_lo = [RES[g]["disp_mm"][0] for g in GAINS]; d_hi = [RES[g]["disp_mm"][1] for g in GAINS]
ax[0].plot(kp, fk_max, "s--", label="FK 최대편위 (과대)")
ax[0].plot(kp, fk_net, "^--", label="FK 순(끝점)")
ax[0].errorbar(kp, [(a+b)/2 for a, b in zip(d_lo, d_hi)], yerr=[[(b-a)/2 for a, b in zip(d_lo, d_hi)]]*2,
               fmt="o-", capsize=4, label="영상 발중심 이동(구름 포함)")
ax[0].errorbar(kp, v_mid, yerr=[[(b-a)/2 for a, b in zip(v_lo, v_hi)]]*2, fmt="D-", capsize=4, label="영상 진짜슬립(구름 차감)")
ax[0].set_title("① 슬립: FK 주장 vs 영상 실측"); ax[0].set_ylabel("[mm]"); ax[0].legend(fontsize=8)
h = [E[g]["h"] for g in GAINS]; W = [E[g]["Wtot"] for g in GAINS]
eff = [hh*100/ww for hh, ww in zip(h, W)]
ax[1].scatter(v_mid, eff)
for i, g in enumerate(GAINS): ax[1].annotate(str(int(kp[i])), (v_mid[i], eff[i]), fontsize=9)
r_eff = np.corrcoef(v_mid, eff)[0, 1]
ax[1].set_title(f"② 효율 vs 영상 진짜슬립 (r={r_eff:.2f})"); ax[1].set_xlabel("진짜슬립 중앙값 [mm]"); ax[1].set_ylabel("효율 [cm/J]")
# ③ 탄성 사이클 에너지 (k_s=150) vs 잉여 일
KS = 150.0
pk_h = {"60_2_250_3":13.25,"80_2_250_3":14.36,"100_1.5_250_3":17.02,"120_2_250_3":19.43,
        "150_2.2_250_3":21.11,"200_2.5_250_3":21.31,"250_3_250_3":21.35}
Ee = [0.5*pk_h[g]**2/KS for g in GAINS]
Wex = [w-min(W) for w in W]
ax[2].plot(kp, Ee, "o-", label="hip 탄성 사이클 ½τ²/k_s [J]")
ax[2].plot(kp, Wex, "s--", label="잉여 총일 (최소 대비) [J]")
ax[2].set_title("③ 직렬탄성 에너지 사이클 vs 잉여 일 (k_s=150)"); ax[2].legend(fontsize=8)
for a_ in ax: a_.grid(alpha=.3)
ax[0].set_xlabel("hip kp"); ax[2].set_xlabel("hip kp")
fig.suptitle("exp5 영상 전수 검증 (7게인) — 진짜 슬립과 효율·에너지 재귀속", fontsize=13)
fig.tight_layout(); fig.savefig(OUT/"video_slip_summary.png", dpi=115); plt.close(fig)
print("done →", OUT/"video_slip_summary.png")
