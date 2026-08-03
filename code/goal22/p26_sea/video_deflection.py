# -*- coding: utf-8 -*-
"""video_deflection — H4/H9: 영상에서 변형 위치 직접 특정 (exp5 250 게인).

측정:
  · 정강이 절대각 θ_vid = atan2(무릎휠중심 − 발볼트중심)  [영상, 사지의 진짜 각도]
  · 인코더 절대각 θ_enc = q1_enc + q2_enc + const          [모터측]
  · 예측: θ_enc − θ_vid ≈ τ1/k1 (+τ2/k2) — 토크 파형 모양, 피크 ~7°
  · H9: 몸통 2점 라인 각도 변화 (베이스 피치) — ~0°면 베이스 무죄
정렬: 각도 곡선 자체의 시간 이동 최적화 (±0.1s), 기준선 = 푸시 전 프레임 (토크≈0).
"""
import os, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np, pandas as pd
import imageio.v3 as iio
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
DATA = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data/26_07_27/250_3_250_3")
KT, GR, CF = 0.091, 9.0, 0.59
A = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
def ahat(raw, v):
    Iq = (CF/(GR*KT))*np.asarray(raw, float); s = np.sign(v)
    return A[0]*GR*KT*Iq - A[1]*GR*np.abs(Iq)*Iq - A[2]*s - A[3]*np.abs(Iq)*s
def gray(a): return a.mean(axis=2)

def match(f, T, cy, cx, ry=35, rx=55):
    h = T.shape[0]//2; best = (1e18, 0, 0)
    for dy in range(-ry, ry+1):
        for dx in range(-rx, rx+1):
            p = f[cy+dy-h:cy+dy+h, cx+dx-h:cx+dx+h]
            if p.shape != T.shape: continue
            s = float(((p-T)**2).mean())
            if s < best[0]: best = (s, dx, dy)
    return best

mp4 = next(DATA.glob("*.mp4"))
fr = [gray(f) for f in iio.imiter(str(mp4), plugin="FFMPEG")]
d = [float(np.abs(fr[i+1]-fr[i]).mean()) for i in range(len(fr)-1)]
j = int(min(np.argsort(d)[-12:]))            # 점프 클러스터 시작
REF = j - 5                                   # 정착 크라우치 프레임 (템플릿 기준)
# 특징점 (f125 격자 판독): 무릎휠 (610,1065), 발볼트 (368,1183), 몸통=흰 캐리지 브래킷 좌(212,665)·우(502,660)
PTS = {"knee": (1065, 610), "foot": (1183, 368), "bodyL": (665, 212), "bodyR": (660, 502)}
T = {k: fr[REF][y-20:y+20, x-20:x+20].copy() for k, (y, x) in PTS.items()}
FR = list(range(j-6, min(j+2, len(fr))))
trk = {k: [] for k in PTS}
for i in FR:
    for k, (y, x) in PTS.items():
        e, dx, dy = match(fr[i], T[k], y, x)
        trk[k].append((i, e, x+dx, y+dy))
# 유효 프레임: knee·foot 매칭 오차 한계 내
rows = []
for idx, i in enumerate(FR):
    ek, ef = trk["knee"][idx][1], trk["foot"][idx][1]
    if ek > 1500 or ef > 1500:               # 블러 파탄 프레임 제외
        continue
    kx, ky = trk["knee"][idx][2], trk["knee"][idx][3]
    fx, fy = trk["foot"][idx][2], trk["foot"][idx][3]
    th_vid = np.degrees(np.arctan2(-(ky-fy), kx-fx))      # 영상 y는 아래+ → 부호 반전
    bl = trk["bodyL"][idx]; br = trk["bodyR"][idx]
    body_ang = np.degrees(np.arctan2(-(br[3]-bl[3]), br[2]-bl[2])) if (bl[1] < 4000 and br[1] < 4000) else np.nan
    rows.append(dict(fr=i, t_vid=i/24.0, th_vid=th_vid, body=body_ang,
                     err=(round(ek), round(ef), round(bl[1]), round(br[1]))))
    print(f"f{i}: θ_vid={th_vid:.2f}° body={body_ang:.2f}° 매칭오차 knee/foot/bL/bR={rows[-1]['err']}")

# ── 인코더 절대각 + 토크 ──
hip = pd.read_excel(DATA/"hip.xlsx"); knee = pd.read_excel(DATA/"knee.xlsx")
n = min(len(hip), len(knee)); hip, knee = hip.iloc[:n], knee.iloc[:n]
t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
q1 = hip["currentAngle"].to_numpy(float); q2 = knee["currentAngle"].to_numpy(float)
v1 = hip["currentAngleVelocity"].to_numpy(float); v2 = knee["currentAngleVelocity"].to_numpy(float)
a1 = ahat(hip["currentTorque"].to_numpy(float), v1); a2 = ahat(knee["currentTorque"].to_numpy(float), v2)
th_enc = np.degrees(q1 + q2)                              # 절대각 (상수차는 기준선 차감으로 소거)

tv = np.array([r["t_vid"] for r in rows]); thv = np.array([r["th_vid"] for r in rows])
# ★정렬 = 독립 사건 앵커 (자유 정합 금지 — 신호를 시프트로 흡수함):
#   영상 이륙 = 발 템플릿 파탄 직전.후 사이 (f_lo+0.5) ↔ GRF 이륙 t_lo. ±0.5프레임 감도 병기.
grf = pd.read_excel(DATA/"GRF.xlsx").iloc[:n]
g = grf["Current_GRF"].to_numpy(float); g0 = np.median(g[-5:]); thr_g = g0 + 0.06*(np.nanmax(g)-g0)
ab = np.where(g >= thr_g)[0]; T_LO = t[min(int(ab[-1])+1, len(t)-1)]
f_lo = None
for idx0 in range(len(FR)):
    e_f = trk["foot"][idx0][1]
    if e_f > 1500:
        f_lo = FR[idx0] - 0.5; break
if f_lo is None: f_lo = FR[-1] + 0.5
def defl_at(halfshift):
    SH = T_LO - (f_lo + halfshift)/24.0
    the_al = np.interp(tv + SH - tv[0]*0, t, th_enc)  # placeholder
    return SH
SH = T_LO - f_lo/24.0
tmap = tv + SH                                             # 각 프레임의 인코더 로컬시각
the_al = np.interp(tmap, t, th_enc)
C0 = float(np.mean(thv[:3] - the_al[:3]))                  # 상수 오프셋 = 크라우치(저토크) 캘리브
defl = (the_al + C0) - thv                                 # 인코더 − 영상 = 사슬 비틀림
tau1 = np.interp(tmap, t, a1); tau2 = np.interp(tmap, t, a2)
pred_h = np.degrees(-(tau1 - tau1[:3].mean()) / 170.0)     # hip만 (k1=170) — 부호: 굴곡 토크(−)가 인코더를 더 굽힘(−)쪽으로
pred_hk = pred_h + np.degrees(-(tau2 - tau2[:3].mean()) / 600.0)
# 감도: 이륙 앵커 ±0.5프레임
sens = {}
for hs, tag in [(-0.5, "early"), (0.5, "late")]:
    tm2 = tv + (T_LO - (f_lo + hs)/24.0)
    th2 = np.interp(tm2, t, th_enc); c2 = float(np.mean(thv[:3] - th2[:3]))
    sens[tag] = ((th2 + c2) - thv).round(2).tolist()
print(f"\n앵커: 영상이륙 f{f_lo} ↔ GRF 이륙 {T_LO:.3f}s → shift={SH*1e3:.0f}ms | 감도 ±0.5프레임 병기")
for i, r in enumerate(rows):
    print(f"f{r['fr']}: 비틀림(인코더−영상)={defl[i]:+.2f}° [감도 {sens['early'][i]:+.2f}~{sens['late'][i]:+.2f}]  "
          f"예측 hip만={pred_h[i]:+.2f}°  hip+knee={pred_hk[i]:+.2f}°  τ1={tau1[i]:+.1f} τ2={tau2[i]:+.1f}  body={r['body']:.2f}°")
body = np.array([r["body"] for r in rows])
print(f"\n몸통 피치 변화 (H9): {np.nanmax(body)-np.nanmin(body):.2f}° (전 프레임 범위)")

fig, ax = plt.subplots(1, 2, figsize=(15, 5.4))
ax[0].plot(tv - tv[0], defl, "o-", label="측정: 인코더 절대각 − 영상 절대각 [°]")
ax[0].plot(tv - tv[0], -pred_h, "s--", label="예측: τ1/k1 (k1=170, hip만)")
ax[0].plot(tv - tv[0], -pred_hk, "^:", label="예측: +knee 직렬(600) 포함")
ax[0].set_title("H4: 사슬 비틀림 직접 측정 vs 스프링 예측 (250 게인)")
ax[0].set_xlabel("t [s] (첫 추적 프레임 기준)"); ax[0].set_ylabel("각도 [°]"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)
ax[1].plot(tv - tv[0], body - np.nanmean(body[:2]), "o-")
ax[1].axhline(0, color="gray", lw=0.8)
ax[1].set_title(f"H9: 몸통 피치 변화 — 범위 {np.nanmax(body)-np.nanmin(body):.2f}° (0에 가까우면 베이스 무죄)")
ax[1].set_xlabel("t [s]"); ax[1].set_ylabel("몸통 라인 각도 변화 [°]"); ax[1].grid(alpha=.3)
fig.suptitle("영상 직접 측정 — 변형은 어디에 있나 (H4/H9)", fontsize=13)
fig.tight_layout(); fig.savefig(HERE/"video_deflection.png", dpi=115)
json.dump(dict(shift_ms=SH*1e3, rows=[dict(r, defl=float(defl[i]), tau1=float(tau1[i]), tau2=float(tau2[i]))
          for i, r in enumerate(rows)]), open(HERE/"_video_deflection.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done → video_deflection.png")
