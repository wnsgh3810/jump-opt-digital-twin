# -*- coding: utf-8 -*-
"""s2s_video_static v3 — H3 영상측: 0604 페이로드 s2s 정적 유지 구간 링크각 정밀 측정.

목적: 인코더 각도와 영상(진짜 사지) 각도의 차이 = 구동계 비틀림(직렬탄성)을 페이로드별로 측정.
  기립(q1≈−16°)에서 τ1: 0kg −1.20 / 5kg −2.39 / 7.5kg −2.62 Nm → SEA(k_s≈170)라면 ~0.4−0.5° 추가 처짐.
  크라우치(τ1≈0)는 대조군. 0kg ext(τ1≈−0.14)도 대조군.

측정 방법 진화 (v1/v2 교훈):
  · v1: 힙 디스크 = 크랭크 허브 확인 (자세 간 disc-knee 363/358/296px 불일치, 겉보기 회전이 q2 차이 추종)
    → 디스크 기반 절대각 오염. 자동 트러스 소패치는 자기유사+반사 변화로 오정합.
  · v2: 36px 소패치 Kabsch — 영상 간 스케일 1~3% 차이를 강체 모델이 흡수 못해 바이어스/기각 붕괴.
  · v3 (최종): ★밀집 마스크 NCC 정합 — 링크 전체 금속 픽셀(수천 점)을 상관계수(밝기 불변)로,
    (회전 dφ, 스케일 s, 병진 t) 완전 탐색+파라볼라. 크랭크 디스크/베어링/발 휠(구름) 제외 마스크.
    프레임별 미소 정합으로 떨림 [°] 직접 산출. 레일 좌에지 직선으로 카메라 롤 보정(영상 간).
    절대각 앵커: θ_thigh(0kg crouch) ≡ q1_enc(0kg crouch) (τ1=−0.03≈0 캘리브).

각도 규약: θ = degrees(atan2(-(dy), dx)) — 이미지 y 아래+. 픽셀 회전 dφ(x→y+)에 대해 Δθ = −dφ.
"""
import os, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd
import imageio.v3 as iio
from scipy import ndimage
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data/26.06.04/no_cvt")

KT, GR, CF = 0.091, 9.0, 0.59
A = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
def ahat(raw, v):
    Iq = (CF/(GR*KT))*np.asarray(raw, float); s = np.sign(v)
    return A[0]*GR*KT*Iq - A[1]*GR*np.abs(Iq)*Iq - A[2]*s - A[3]*np.abs(Iq)*s

FPS = 24.0
CFG = {
    "0kg": dict(
        mp4=ROOT/"no_load/KakaoTalk_20260604_170859513.mp4", raw=ROOT/"no_load/raw_unwrap",
        payload=0.0, crouch_end_data=48.306,
        holds={"crouch": (4, 44), "stand": (134, 166), "ext": (196, 226)},
        segs={"crouch": (0.0, 48.306), "stand": (51.142, 53.218), "ext": (54.218, 68.216)}),
    "5kg": dict(
        mp4=ROOT/"load_5/KakaoTalk_20260604_170309383.mp4", raw=ROOT/"load_5/raw_unwrap",
        payload=5.0, crouch_end_data=47.486,
        holds={"crouch": (4, 64), "stand": (167, 191), "settle": (232, 254)},
        segs={"crouch": (18.058, 47.486), "stand": (51.25, 52.716)}),
    "7.5kg": dict(
        mp4=ROOT/"load_7.5/KakaoTalk_20260604_170101423.mp4", raw=ROOT/"load_7.5/raw_unwrap",
        payload=7.5, crouch_end_data=53.35,
        holds={"crouch": (4, 84), "stand": (179, 195)},
        segs={"crouch": (36.408, 53.35), "stand": (56.57, 58.414)}),
}
REF0 = {  # 0kg 평균영상 근사 좌표 (암흑 중심공 정련 전)
    "crouch": dict(knee=(577, 937), foot=(350, 1155), disc=(286, 723)),
    "stand":  dict(knee=(662, 1054), foot=(307, 1148), disc=(310, 1005)),
    "ext":    dict(knee=(460, 858), foot=(318, 1152), disc=(352, 585)),
}
TSZ = 36

def gray(a): return a.mean(axis=2).astype(np.float32)

def stream_video(cfg):
    prev, diffs, n = None, [], 0
    frames = {k: [] for k in cfg["holds"]}
    mean_rgb = {k: None for k in cfg["holds"]}
    for i, fr in enumerate(iio.imiter(str(cfg["mp4"]), plugin="FFMPEG")):
        g = gray(fr)
        if prev is not None:
            diffs.append(float(np.abs(g - prev).mean()))
        prev = g; n += 1
        for k, (a, b) in cfg["holds"].items():
            if a <= i < b:
                frames[k].append(g)
                f64 = fr.astype(np.float64)
                mean_rgb[k] = f64 if mean_rgb[k] is None else mean_rgb[k] + f64
    for k in cfg["holds"]:
        mean_rgb[k] = mean_rgb[k] / len(frames[k])
    return np.array(diffs), frames, mean_rgb, n

def motion_onset(diffs, t_from=0.8):
    d = diffs.copy(); d[np.arange(len(d)) % 24 == 23] = 0.0
    for i in range(int(t_from*FPS), len(d)-2):
        if d[i] > 1.0 and d[i+1] > 1.0 and d[i+2] > 1.0:
            return i / FPS
    return None

def cut(img, cx, cy, half):
    return img[int(round(cy))-half:int(round(cy))+half, int(round(cx))-half:int(round(cx))+half]

def ssd_match(img, T, cx, cy, r):
    h = T.shape[0] // 2
    E = np.full((2*r+1, 2*r+1), np.inf, np.float64)
    H, W = img.shape
    icx, icy = int(round(cx)), int(round(cy))
    for iy, dy in enumerate(range(-r, r+1)):
        y0 = icy + dy - h
        if y0 < 0 or y0 + 2*h > H: continue
        for ix, dx in enumerate(range(-r, r+1)):
            x0 = icx + dx - h
            if x0 < 0 or x0 + 2*h > W: continue
            p = img[y0:y0+2*h, x0:x0+2*h]
            E[iy, ix] = float(((p - T)**2).mean())
    iy, ix = np.unravel_index(np.argmin(E), E.shape)
    return icx + (ix - r), icy + (iy - r), E[iy, ix]

def refine_dark_center(img, cx, cy, r=13):
    reg = img[int(cy)-r:int(cy)+r+1, int(cx)-r:int(cx)+r+1]
    thr = reg.min() + 0.35*(reg.max() - reg.min())
    yy, xx = np.mgrid[-r:r+1, -r:r+1]
    m = ((reg < thr) & (xx**2 + yy**2 <= r*r)).astype(np.float64)
    if m.sum() < 4: return float(cx), float(cy)
    w = (thr - reg).clip(0) * m
    return float(cx + (xx*w).sum()/w.sum()), float(cy + (yy*w).sum()/w.sum())

# ── 레일 롤 ──
def rail_roll(meanimg):
    g = meanimg
    prof = ndimage.uniform_filter1d(g[498:503].mean(axis=0), 3)
    gr = np.diff(prof)
    x_guess = int(np.argmin(gr[160:280]) + 160)
    xs, ys = [], []
    for y in range(420, 1081, 2):
        p = ndimage.uniform_filter1d(g[y-1:y+2].mean(axis=0), 3)
        d = np.diff(p)
        lo = x_guess - 16
        seg = d[lo:x_guess + 16]
        i = int(np.argmin(seg))
        if seg[i] > -12: continue
        s = 0.0
        if 0 < i < len(seg)-1:
            d2 = seg[i-1] - 2*seg[i] + seg[i+1]
            if d2 > 1e-9: s = float(np.clip(0.5*(seg[i-1]-seg[i+1])/d2, -1, 1))
        xs.append(lo + i + 0.5 + s); ys.append(y)
    xs, ys = np.array(xs, float), np.array(ys, float)
    for _ in range(4):
        b = np.polyfit(ys, xs, 1)
        res = xs - np.polyval(b, ys)
        mad = np.median(np.abs(res)) + 1e-9
        keep = np.abs(res) < 3*mad*1.4826 + 0.2
        if keep.sum() < 40: break
        xs, ys = xs[keep], ys[keep]
    b = np.polyfit(ys, xs, 1)
    res = xs - np.polyval(b, ys)
    se_slope = res.std() / np.sqrt(((ys - ys.mean())**2).sum())
    return float(np.degrees(np.arctan(b[0]))), float(np.degrees(se_slope)), len(xs)

# ── 인코더 ──
_ENC_CACHE = {}
def enc_arrays(cfg):
    key = str(cfg["raw"])
    if key not in _ENC_CACHE:
        hip = pd.read_excel(cfg["raw"]/"hip.xlsx"); knee = pd.read_excel(cfg["raw"]/"knee.xlsx")
        n = min(len(hip), len(knee)); hip, knee = hip.iloc[:n], knee.iloc[:n]
        t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
        _ENC_CACHE[key] = dict(
            t=t,
            q1=np.degrees(hip["currentAngle"].to_numpy(float)),
            q2=np.degrees(knee["currentAngle"].to_numpy(float)),
            a1=ahat(hip["currentTorque"].to_numpy(float), hip["currentAngleVelocity"].to_numpy(float)),
            a2=ahat(knee["currentTorque"].to_numpy(float), knee["currentAngleVelocity"].to_numpy(float)))
    return _ENC_CACHE[key]

def encoder_window(cfg, t0, t1):
    E = enc_arrays(cfg)
    m = (E["t"] >= t0) & (E["t"] <= t1)
    if m.sum() < 3: return None
    return dict(q1=float(E["q1"][m].mean()), q1_std=float(E["q1"][m].std()),
                q2=float(E["q2"][m].mean()), q2_std=float(E["q2"][m].std()),
                tau1=float(E["a1"][m].mean()), tau2=float(E["a2"][m].mean()),
                n=int(m.sum()), t0=round(t0, 3), t1=round(t1, 3))

# ═══════════ 밀집 마스크 NCC 정합 (그래디언트 크기 영상 — 조명/반사 불변) ═══════════
def grad_mag(img):
    g = ndimage.gaussian_filter(img.astype(np.float64), 1.2)
    gx = ndimage.sobel(g, axis=1); gy = ndimage.sobel(g, axis=0)
    return np.hypot(gx, gy).astype(np.float32)

def build_mask_pts(img_int, img_g, p_from, p_to, half_w, frac_lo, frac_hi, excl=(), step=2, min_int=85):
    """p_from→p_to 코리도 안 금속 픽셀 좌표 (x,y) + 그래디언트 값. 필터는 강도 영상, 값은 그래디언트."""
    p_from, p_to = np.array(p_from, float), np.array(p_to, float)
    d = p_to - p_from; L = np.linalg.norm(d); u = d / L; nv = np.array([-u[1], u[0]])
    x0 = int(min(p_from[0], p_to[0]) - half_w - 5); x1 = int(max(p_from[0], p_to[0]) + half_w + 5)
    y0 = int(min(p_from[1], p_to[1]) - half_w - 5); y1 = int(max(p_from[1], p_to[1]) + half_w + 5)
    xs = np.arange(max(x0, 0), min(x1, img_int.shape[1]), step)
    ys = np.arange(max(y0, 0), min(y1, img_int.shape[0]), step)
    XX, YY = np.meshgrid(xs, ys)
    P = np.stack([XX.ravel(), YY.ravel()], axis=1).astype(float)
    rel = P - p_from
    along = rel @ u / L; perp = rel @ nv
    m = (along >= frac_lo) & (along <= frac_hi) & (np.abs(perp) <= half_w)
    vals_i = img_int[P[:, 1].astype(int), P[:, 0].astype(int)]
    m &= vals_i > min_int
    for (cx, cy, r) in excl:
        m &= np.hypot(P[:, 0]-cx, P[:, 1]-cy) > r
    valg = img_g[P[:, 1].astype(int), P[:, 0].astype(int)]
    return P[m], valg[m].astype(np.float64)

def ncc_cost(valsA, valsB, ok):
    a = valsA[ok]; b = valsB[ok]
    if len(a) < 50: return 2.0
    a = a - a.mean(); b = b - b.mean()
    den = np.sqrt((a*a).sum()*(b*b).sum())
    if den < 1e-9: return 2.0
    return 1.0 - float((a*b).sum()/den)

def sample(img, pts):
    v = ndimage.map_coordinates(img, [pts[:, 1], pts[:, 0]], order=1, mode="constant", cval=-1e4)
    return v, v > -1e3

def register(imgA, imgB, ptsA, valsA, anchorA, anchorB,
             dphi_list, s_list, t_r=6, t_step=2, refine=True):
    """B ≈ transform(A): p_B = cB + s·R(dφ)·(p_A − anchorA). return best dict."""
    relA = ptsA - anchorA
    best = None
    tgrid = np.arange(-t_r, t_r+1e-9, t_step)
    for dphi in dphi_list:
        a = np.radians(dphi); c, s_ = np.cos(a), np.sin(a)
        Rm = np.array([[c, -s_], [s_, c]])
        for s in s_list:
            rot = relA @ (s*Rm).T
            for tx in tgrid:
                for ty in tgrid:
                    pB = rot + anchorB + (tx, ty)
                    vB, ok = sample(imgB, pB)
                    cost = ncc_cost(valsA, vB, ok)
                    if best is None or cost < best["cost"]:
                        best = dict(cost=cost, dphi=float(dphi), s=float(s), tx=float(tx), ty=float(ty))
    if refine:
        for _ in range(2):
            b2 = None
            for dphi in best["dphi"] + np.arange(-0.5, 0.51, 0.1):
                a = np.radians(dphi); c, s_ = np.cos(a), np.sin(a)
                Rm = np.array([[c, -s_], [s_, c]])
                for s in best["s"] + np.array([-0.005, -0.0025, 0, 0.0025, 0.005]):
                    rot = relA @ (s*Rm).T
                    for tx in best["tx"] + np.arange(-1.0, 1.01, 0.5):
                        for ty in best["ty"] + np.arange(-1.0, 1.01, 0.5):
                            pB = rot + anchorB + (tx, ty)
                            vB, ok = sample(imgB, pB)
                            cost = ncc_cost(valsA, vB, ok)
                            if b2 is None or cost < b2["cost"]:
                                b2 = dict(cost=cost, dphi=float(dphi), s=float(s), tx=float(tx), ty=float(ty))
            best = b2
    # dφ 파라볼라 정련 + 곡률
    dgrid = np.arange(-0.4, 0.41, 0.08)
    costs = []
    for dd in dgrid:
        a = np.radians(best["dphi"]+dd); c, s_ = np.cos(a), np.sin(a)
        Rm = np.array([[c, -s_], [s_, c]])
        pB = relA @ (best["s"]*Rm).T + anchorB + (best["tx"], best["ty"])
        vB, ok = sample(imgB, pB)
        costs.append(ncc_cost(valsA, vB, ok))
    costs = np.array(costs)
    i = int(np.argmin(costs))
    dsub = 0.0
    if 0 < i < len(dgrid)-1:
        d2 = costs[i-1] - 2*costs[i] + costs[i+1]
        if d2 > 1e-12: dsub = float(np.clip(0.5*(costs[i-1]-costs[i+1])/d2, -1, 1))*0.08
    best["dphi"] = best["dphi"] + dgrid[i] + dsub
    # 서브셋 산포 (6분할 dφ 재적합)
    rng = np.random.default_rng(0)
    idx = rng.permutation(len(ptsA))
    subs = []
    for kpart in range(6):
        sel = idx[kpart::6]
        if len(sel) < 60: continue
        cc = []
        for dd in np.arange(-0.6, 0.61, 0.12):
            a = np.radians(best["dphi"]+dd); c, s_ = np.cos(a), np.sin(a)
            Rm = np.array([[c, -s_], [s_, c]])
            pB = (ptsA[sel]-anchorA) @ (best["s"]*Rm).T + anchorB + (best["tx"], best["ty"])
            vB, ok = sample(imgB, pB)
            cc.append(ncc_cost(valsA[sel], vB, ok))
        cc = np.array(cc); j = int(np.argmin(cc)); ss = 0.0
        if 0 < j < len(cc)-1:
            d2 = cc[j-1] - 2*cc[j] + cc[j+1]
            if d2 > 1e-12: ss = float(np.clip(0.5*(cc[j-1]-cc[j+1])/d2, -1, 1))*0.12
        subs.append(best["dphi"] + np.arange(-0.6, 0.61, 0.12)[j] + ss)
    best["dphi_se"] = float(np.std(subs)/np.sqrt(max(len(subs), 1))) if len(subs) >= 3 else 0.3
    best["n_pts"] = len(ptsA)
    return best

# ═══════════ 실행 ═══════════
print("=== 1) 스트리밍 ===")
V = {}
for lab, cfg in CFG.items():
    diffs, frames, mean_rgb, n = stream_video(cfg)
    means = {k: mean_rgb[k].mean(axis=2).astype(np.float32) for k in cfg["holds"]}
    grads = {k: grad_mag(means[k]) for k in means}
    onset = motion_onset(diffs)
    off = cfg["crouch_end_data"] - onset
    V[lab] = dict(frames=frames, mean_rgb=mean_rgb, means=means, grad=grads, onset=onset, off=off)
    print(f"{lab}: {n}f, 온셋 {onset:.2f}s → 오프셋 {off:+.2f}s | " +
          " ".join(f"{k}:{len(frames[k])}f" for k in frames))

print("\n=== 2) 레일 롤 ===")
for lab in V:
    roll, se, npts = rail_roll(V[lab]["means"]["crouch"])
    V[lab]["roll"], V[lab]["roll_se"] = roll, se
    print(f"{lab}: roll {roll:+.3f}° ± {se:.3f} (n={npts})")

print("\n=== 3) 인코더 창 평균 (±0.3s 감도) ===")
ENC = {}
for lab, cfg in CFG.items():
    ENC[lab] = {}
    for post, (fa, fb) in cfg["holds"].items():
        if post not in cfg["segs"]:
            ENC[lab][post] = None; continue
        e = {}
        for dt, tag in ((0.0, "mid"), (-0.3, "lo"), (0.3, "hi")):
            t0 = max(fa/FPS + V[lab]["off"] + dt, cfg["segs"][post][0])
            t1 = min(fb/FPS + V[lab]["off"] + dt, cfg["segs"][post][1])
            e[tag] = encoder_window(cfg, t0, t1) if t1 > t0 else None
        e["mid"]["q1_offsens"] = round(max(abs(e[t]["q1"] - e["mid"]["q1"]) for t in ("lo", "hi") if e[t]), 3)
        ENC[lab][post] = e["mid"]
        print(f"{lab} {post}: q1 {e['mid']['q1']:+.2f}±{e['mid']['q1_std']:.2f} (감도 {e['mid']['q1_offsens']}) "
              f"q2 {e['mid']['q2']:+.2f} τ1 {e['mid']['tau1']:+.2f} τ2 {e['mid']['tau2']:+.2f}")

print("\n=== 4) 특징점 ===")
feat = {lab: {} for lab in V}
for post in ("crouch", "stand", "ext"):
    feat["0kg"][post] = {}
    for f in ("knee", "foot", "disc"):
        feat["0kg"][post][f] = refine_dark_center(V["0kg"]["means"][post], *REF0[post][f])
for lab in ("5kg", "7.5kg"):
    for post in CFG[lab]["holds"]:
        tpost = "stand" if post == "settle" else post
        feat[lab][post] = {}
        for f in ("knee", "foot", "disc"):
            T = cut(V["0kg"]["means"][tpost], *feat["0kg"][tpost][f], TSZ//2)
            x0, y0 = feat["0kg"][tpost][f]
            mx, my, me = ssd_match(V[lab]["means"][post], T, x0, y0, 95)
            if f in ("knee", "foot"):
                mx, my = refine_dark_center(V[lab]["means"][post], mx, my)
            feat[lab][post][f] = (float(mx), float(my))
for lab in V:
    for post in feat[lab]:
        k = feat[lab][post]
        print(f"{lab} {post}: knee ({k['knee'][0]:.1f},{k['knee'][1]:.1f}) foot ({k['foot'][0]:.1f},{k['foot'][1]:.1f}) "
              f"disc ({k['disc'][0]:.1f},{k['disc'][1]:.1f})")

def masks_for(lab, post, seg=None):
    """seg=None: 전체. seg=(lo,hi): 코리도 along-분수 구간 (세그먼트 축선법용)."""
    img = V[lab]["means"][post]; img_g = V[lab]["grad"][post]
    k = feat[lab][post]
    tl, th_ = (0.20, 0.97) if seg is None else seg
    thigh = build_mask_pts(img, img_g, k["disc"], k["knee"], half_w=46, frac_lo=tl, frac_hi=th_,
                           excl=[(k["disc"][0], k["disc"][1], 80), (k["knee"][0], k["knee"][1], 48)])
    sl, sh_ = (0.10, 0.95) if seg is None else seg
    shank = build_mask_pts(img, img_g, k["knee"], k["foot"], half_w=40, frac_lo=sl, frac_hi=sh_,
                           excl=[(k["knee"][0], k["knee"][1], 48), (k["foot"][0], k["foot"][1], 34)])
    return thigh, shank

print("\n=== 5) 영상 내 자세 간 정합 (진단용 — 인코더 캘리브 잔차 포함 주의) ===")
within = {lab: {} for lab in V}
for lab in V:
    imgCg = V[lab]["grad"]["crouch"]
    (ptsT, valT), (ptsS, valS) = masks_for(lab, "crouch")
    kC = np.array(feat[lab]["crouch"]["knee"])
    q1c = ENC[lab]["crouch"]["q1"]
    for post in CFG[lab]["holds"]:
        if post == "crouch": continue
        imgPg = V[lab]["grad"][post]
        kP = np.array(feat[lab][post]["knee"])
        e = ENC[lab].get(post)
        if e: dlist = -(e["q1"]-q1c) + np.arange(-4, 4.1, 0.8)
        else: dlist = np.arange(-15, 60.1, 2.5)
        w = register(imgCg, imgPg, ptsT, valT, kC, kP, dlist, np.arange(0.96, 1.041, 0.02))
        w["dtheta"] = -w["dphi"]
        if e: dlist2 = -((e["q1"]+e["q2"])-(q1c+ENC[lab]["crouch"]["q2"])) + np.arange(-4, 4.1, 0.8)
        else: dlist2 = np.arange(-40, 20.1, 2.5)
        ws = register(imgCg, imgPg, ptsS, valS, kC, kP, dlist2, np.arange(0.96, 1.041, 0.02))
        ws["dtheta"] = -ws["dphi"]
        within[lab][post] = dict(thigh=w, shank=ws)
        dq1 = (e["q1"]-q1c) if e else None
        dq12 = ((e["q1"]+e["q2"])-(q1c+ENC[lab]["crouch"]["q2"])) if e else None
        print(f"{lab} crouch→{post}: 허벅지 Δθ {w['dtheta']:+.3f}°±{w['dphi_se']:.3f} (cost {w['cost']:.3f}, s {w['s']:.3f})"
              + (f" | Δq1 {dq1:+.3f}° → 차이 {w['dtheta']-dq1:+.3f}°" if dq1 is not None else " | 인코더 없음"))
        print(f"              정강이 Δθ {ws['dtheta']:+.3f}°±{ws['dphi_se']:.3f} (cost {ws['cost']:.3f})"
              + (f" | Δ(q1+q2) {dq12:+.3f}° → 차이 {ws['dtheta']-dq12:+.3f}°" if dq12 is not None else ""))

print("\n=== 6) 영상 간 같은 자세 정합 (0kg → lab) — 방법 A: 밀집 NCC 유사변환 ===")
S_LIST_X = np.arange(0.94, 1.081, 0.01)
cross = {}
for lab in ("5kg", "7.5kg"):
    cross[lab] = {}
    for post in ("crouch", "stand"):
        img0g = V["0kg"]["grad"][post]; imgTg = V[lab]["grad"][post]
        (ptsT0, valT0), (ptsS0, valS0) = masks_for("0kg", post)
        k0 = np.array(feat["0kg"][post]["knee"]); kT = np.array(feat[lab][post]["knee"])
        droll = V[lab]["roll"] - V["0kg"]["roll"]
        out = {}
        for body, (pts, vals) in dict(thigh=(ptsT0, valT0), shank=(ptsS0, valS0)).items():
            c = register(img0g, imgTg, pts, vals, k0, kT, np.arange(-4, 4.1, 0.8), S_LIST_X)
            c["dtheta"] = -c["dphi"]
            c["dtheta_corr"] = c["dtheta"] - droll
            out[body] = c
            print(f"0kg→{lab} @{post} [{body}]: Δθ {c['dtheta']:+.3f}°±{c['dphi_se']:.3f} "
                  f"(롤보정 {c['dtheta_corr']:+.3f}°) s {c['s']:.3f} cost {c['cost']:.3f} n {c['n_pts']}")
        cross[lab][post] = out

print("\n=== 6b) 방법 B: 3세그먼트 축선법 (병진 전용 매칭 → 축 방향 회전; 스케일/전단 면역) ===")
SEGS = {"thigh": [(0.20, 0.46), (0.46, 0.72), (0.72, 0.97)],
        "shank": [(0.10, 0.39), (0.39, 0.67), (0.67, 0.95)]}
def segment_axis_rot(lab, post):
    """0kg→lab: 세그먼트별 병진 정합 → 매칭점 축선 방향 변화 [°] + 세그먼트 잔차."""
    img0g = V["0kg"]["grad"][post]; imgTg = V[lab]["grad"][post]
    k0 = np.array(feat["0kg"][post]["knee"]); kT = np.array(feat[lab][post]["knee"])
    out = {}
    for body in ("thigh", "shank"):
        c0, cT, costs, ns = [], [], [], []
        for seg in SEGS[body]:
            th_m, sh_m = masks_for("0kg", post, seg=seg)
            pts, vals = th_m if body == "thigh" else sh_m
            if len(pts) < 150:
                continue
            b = register(img0g, imgTg, pts, vals, k0, kT, [0.0], [1.0], t_r=10, t_step=2)
            cen = pts.mean(axis=0)
            c0.append(cen); cT.append(cen - k0 + kT + (b["tx"], b["ty"]))
            costs.append(b["cost"]); ns.append(len(pts))
        c0, cT = np.array(c0), np.array(cT)
        if len(c0) < 2:
            out[body] = None; continue
        # 방향: 끝-끝 벡터 (3점이면 중간점 잔차 = 휨/오정합 지표)
        v0 = c0[-1] - c0[0]; vT = cT[-1] - cT[0]
        a0_ = np.degrees(np.arctan2(-v0[1], v0[0])); aT_ = np.degrees(np.arctan2(-vT[1], vT[0]))
        dth = aT_ - a0_
        bend = np.nan
        if len(c0) == 3:
            u = v0/np.linalg.norm(v0); nv = np.array([-u[1], u[0]])
            bend = float((cT[1]-cT[0]-(c0[1]-c0[0])) @ nv)  # 중간 세그 횡 잔차 [px]
        out[body] = dict(dtheta=float(dth), dtheta_corr=float(dth - (V[lab]["roll"] - V["0kg"]["roll"])),
                         costs=[round(c_, 3) for c_ in costs], mid_resid_px=round(bend, 2) if bend == bend else None,
                         n_pts=ns, seg_c0=c0.tolist(), seg_cT=cT.tolist())
    return out

crossB = {}
for lab in ("5kg", "7.5kg"):
    crossB[lab] = {}
    for post in ("crouch", "stand"):
        r = segment_axis_rot(lab, post)
        crossB[lab][post] = r
        for body in ("thigh", "shank"):
            if r[body]:
                print(f"0kg→{lab} @{post} [{body}] 축선법: Δθ {r[body]['dtheta']:+.3f}° "
                      f"(롤보정 {r[body]['dtheta_corr']:+.3f}°) 중간잔차 {r[body]['mid_resid_px']}px cost {r[body]['costs']}")

print("\n=== 7) 프레임별 떨림 (자체 평균 대비 미소 정합, 강도 영상) ===")
scatter = {}
for lab in V:
    scatter[lab] = {}
    for post in CFG[lab]["holds"]:
        img = V[lab]["means"][post]
        k = feat[lab][post]
        ptsT, valT = build_mask_pts(img, img, k["disc"], k["knee"], half_w=46, frac_lo=0.20, frac_hi=0.97,
                                    excl=[(k["disc"][0], k["disc"][1], 80), (k["knee"][0], k["knee"][1], 48)])
        sel = np.random.default_rng(1).permutation(len(ptsT))[:1200]
        pts, vals = ptsT[sel], valT[sel]
        ka = np.array(k["knee"])
        rots = []
        for g in V[lab]["frames"][post]:
            b = register(img, g, pts, vals, ka, ka,
                         np.arange(-0.6, 0.61, 0.3), [1.0], t_r=2, t_step=1, refine=False)
            rots.append(-b["dphi"])
        rots = np.array(rots)
        scatter[lab][post] = dict(std=float(rots.std()), sem=float(rots.std()/np.sqrt(len(rots))), n=len(rots))
        print(f"{lab} {post}: 떨림 std {rots.std():.3f}° SEM {scatter[lab][post]['sem']:.3f}° (n={len(rots)})")

print("\n=== 8) 절대각 (자세별 0kg 인코더 앵커) + 핵심 비교 ===")
K_S = 170.0
# 앵커: 각 자세에서 θ(0kg) ≡ q1_enc(0kg) — 0kg 자체의 처짐(τ1: crouch −0.03 / stand −1.20)은 앵커에 흡수됨.
TH = {"0kg": {}, "5kg": {}, "7.5kg": {}}
SH = {"0kg": {}, "5kg": {}, "7.5kg": {}}
for post in ("crouch", "stand", "ext"):
    TH["0kg"][post] = ENC["0kg"][post]["q1"]
    SH["0kg"][post] = ENC["0kg"][post]["q1"] + ENC["0kg"][post]["q2"]
for lab in ("5kg", "7.5kg"):
    for post in ("crouch", "stand"):
        TH[lab][post] = TH["0kg"][post] + cross[lab][post]["thigh"]["dtheta_corr"]
        SH[lab][post] = SH["0kg"][post] + cross[lab][post]["shank"]["dtheta_corr"]
TH["5kg"]["settle"] = None  # 자세 간 정합 신뢰 불가 (cost>0.8, 외관 급변) — 원시 라인각만 보고
SH["5kg"]["settle"] = None

print("\n★ 핵심: 페이로드 비교 (0kg 기준 Δ, 같은 자세, 롤보정) — 방법 A(밀집 NCC)·B(축선법) 병기")
comp = {}
for post in ("stand", "crouch"):
    comp[post] = {}
    b_e = ENC["0kg"][post]
    for lab in ("5kg", "7.5kg"):
        e = ENC[lab][post]
        cth = cross[lab][post]["thigh"]; csh = cross[lab][post]["shank"]
        bth = crossB[lab][post]["thigh"]; bsh = crossB[lab][post]["shank"]
        dv, dvs = cth["dtheta_corr"], csh["dtheta_corr"]
        dvB = bth["dtheta_corr"] if bth else None
        dvsB = bsh["dtheta_corr"] if bsh else None
        de = e["q1"] - b_e["q1"]; des = (e["q1"]+e["q2"]) - (b_e["q1"]+b_e["q2"])
        dtau = e["tau1"] - b_e["tau1"]
        pred = de + np.degrees(dtau / K_S)
        methodAB = abs(dv - dvB) if dvB is not None else 0.3
        u = float(np.sqrt(cth["dphi_se"]**2 + V[lab]["roll_se"]**2 + V["0kg"]["roll_se"]**2 +
                          scatter[lab][post]["sem"]**2 + scatter["0kg"][post]["sem"]**2 + (0.5*methodAB)**2 + 0.1**2))
        comp[post][lab] = dict(
            d_video=round(dv, 3), d_videoB=round(dvB, 3) if dvB is not None else None,
            d_enc=round(de, 3), d_tau1=round(dtau, 3),
            d_pred_sea=round(pred, 3), excess=round(dv - de, 3),
            excessB=round(dvB - de, 3) if dvB is not None else None, unc=round(u, 3),
            d_shank_video=round(dvs, 3), d_shank_videoB=round(dvsB, 3) if dvsB is not None else None,
            d_shank_enc=round(des, 3),
            shank_excess=round(dvs - des, 3), d_tau2=round(e["tau2"] - b_e["tau2"], 3))
        c = comp[post][lab]
        print(f"{post} {lab}: 허벅지 Δ영상 A {c['d_video']:+.3f}° / B {c['d_videoB']:+.3f}° (±{c['unc']:.3f}) | "
              f"Δq1 {c['d_enc']:+.3f}° | SEA예측 {c['d_pred_sea']:+.3f}° | 초과 A {c['excess']:+.3f}° B {c['excessB']:+.3f}° "
              f"(Δτ1 {c['d_tau1']:+.2f}Nm)")
        print(f"          정강이 Δ영상 A {c['d_shank_video']:+.3f}° / B {c['d_shank_videoB']:+.3f}° | "
              f"Δ(q1+q2) {c['d_shank_enc']:+.3f}° | 초과 {c['shank_excess']:+.3f}° (Δτ2 {c['d_tau2']:+.2f}Nm) | "
              f"무릎사슬 δ2 {c['shank_excess']-c['excess']:+.3f}°")

# ── 산출물 ──
RES = {}
for lab in V:
    cfg = CFG[lab]
    RES[lab] = dict(payload=cfg["payload"], roll_deg=round(V[lab]["roll"], 3), roll_se=round(V[lab]["roll_se"], 3),
                    offset_video_to_data_s=round(V[lab]["off"], 3), holds={})
    for post in cfg["holds"]:
        k = feat[lab][post]
        e = ENC[lab].get(post)
        th_raw = float(np.degrees(np.arctan2(-(k["knee"][1]-k["disc"][1]), k["knee"][0]-k["disc"][0])))
        sh_raw = float(np.degrees(np.arctan2(-(k["foot"][1]-k["knee"][1]), k["foot"][0]-k["knee"][0])))
        RES[lab]["holds"][post] = dict(
            posture={"crouch": "크라우치(τ1~0)", "stand": "기립(q1~-16°)", "ext": "직립 신전(τ1~0)",
                     "settle": "최종 착좌(인코더 기록 종료 후)"}[post],
            n_frames=len(V[lab]["frames"][post]),
            thigh_abs_deg=round(TH[lab][post], 3) if TH[lab][post] is not None else None,
            shank_abs_deg=round(SH[lab][post], 3) if SH[lab][post] is not None else None,
            thigh_line_raw_deg=round(th_raw, 3),   # 모터면(구 disc)→무릎 원시 atan2 (크랭크 오염 참고용)
            shank_line_raw_deg=round(sh_raw, 3),   # 무릎→발 원시 atan2 (롤 미보정)
            thigh_wobble_std_deg=round(scatter[lab][post]["std"], 3),
            thigh_sem_deg=round(scatter[lab][post]["sem"], 3),
            knee_px=[round(v, 2) for v in k["knee"]], foot_px=[round(v, 2) for v in k["foot"]],
            motorface_px=[round(v, 2) for v in k["disc"]],
            motorface_knee_len_px=round(float(np.hypot(k["knee"][0]-k["disc"][0], k["knee"][1]-k["disc"][1])), 1),
            knee_foot_len_px=round(float(np.hypot(k["foot"][0]-k["knee"][0], k["foot"][1]-k["knee"][1])), 1),
            encoder=e)

def _r(d, nd=4):
    return {k: (round(v, nd) if isinstance(v, float) else v) for k, v in d.items()}
OUT = dict(
    note="v3 그래디언트 NCC 정합 (방법 A=유사변환, 방법 B=3세그먼트 축선법). "
         "절대각 앵커: 자세별 θ(0kg) ≡ q1_enc(0kg) — 0kg 자체 처짐은 앵커에 흡수 (stand τ1=-1.2Nm ~ -0.4°). "
         "disc=크랭크 허브(힙축 아님, v1 확인: 자세별 disc-knee 363/358/296px) — 마스크 제외. "
         "cross(영상간)는 레일 롤 차이 보정. 각 규약 θ=atan2(-(dy),dx). "
         "settle/within은 저신뢰 진단용 (자세 간 외관변화+인코더 캘리브 잔차 얽힘).",
    k_s_ref=K_S,
    within_video={lab: {p: {b: _r(w[b]) for b in w} for p, w in within[lab].items()} for lab in within},
    cross_video_A={lab: {p: {b: _r(c[b]) for b in c} for p, c in cross[lab].items()} for lab in cross},
    cross_video_B={lab: {p: {b: (_r(c[b]) if c[b] else None) for b in c} for p, c in crossB[lab].items()}
                   for lab in crossB},
    trials=RES, compare=comp)
json.dump(OUT, open(HERE/"_s2s_video_static.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 플롯
fig, axs = plt.subplots(1, 2, figsize=(12.5, 5))
pay = [0, 5, 7.5]
for i, post in enumerate(("stand", "crouch")):
    a = axs[i]
    dv = [0] + [comp[post][l]["d_video"] for l in ("5kg", "7.5kg")]
    dvB = [0] + [comp[post][l]["d_videoB"] for l in ("5kg", "7.5kg")]
    de = [0] + [comp[post][l]["d_enc"] for l in ("5kg", "7.5kg")]
    ds = [0] + [comp[post][l]["d_pred_sea"] for l in ("5kg", "7.5kg")]
    unc = [scatter["0kg"][post]["sem"]] + [comp[post][l]["unc"] for l in ("5kg", "7.5kg")]
    a.errorbar(pay, dv, yerr=unc, marker="o", capsize=3, label="영상 A: 밀집 NCC (롤보정)")
    a.plot(pay, dvB, marker="s", ls="--", label="영상 B: 3세그먼트 축선법")
    a.plot(pay, de, marker="^", ls=":", label="인코더 q1 (강체 가정)")
    a.plot(pay, ds, marker="v", ls="-.", label="인코더+SEA 예측 (k_s=170)")
    tt = {"stand": "기립 (q1~-16°, τ1 -1.2→-2.6Nm)", "crouch": "크라우치 (τ1~0, 대조군)"}[post]
    a.set_title(tt); a.set_xlabel("페이로드 [kg]"); a.set_ylabel("허벅지 절대각 Δ vs 0kg [°]")
    a.grid(alpha=.3); a.legend(fontsize=8)
fig.suptitle("0604 s2s 정적 홀드 — 영상 허벅지각 페이로드 트렌드 (직렬탄성 검증)", fontsize=12)
fig.tight_layout(); fig.savefig(HERE/"s2s_video_static.png", dpi=115)
plt.close(fig)

# 오버레이 (마스크 + 특징점 + 링크선)
for lab in V:
    posts = list(CFG[lab]["holds"])
    fig, axs2 = plt.subplots(1, len(posts), figsize=(5.2*len(posts), 8.2))
    if len(posts) == 1: axs2 = [axs2]
    for a, post in zip(axs2, posts):
        img = V[lab]["mean_rgb"][post].round().astype(np.uint8)
        a.imshow(img[400:1280])
        k = feat[lab][post]
        (ptsT, _), (ptsS, _) = masks_for(lab, post)
        a.plot(ptsT[::9, 0], ptsT[::9, 1]-400, ls="none", marker=".", ms=1.5, alpha=.5, label="thigh mask")
        a.plot(ptsS[::9, 0], ptsS[::9, 1]-400, ls="none", marker=".", ms=1.5, alpha=.5, label="shank mask")
        for f, mk in (("knee", "o"), ("foot", "s"), ("disc", "D")):
            a.plot(k[f][0], k[f][1]-400, marker=mk, ms=10, mfc="none", mew=1.5, label=f)
        h = RES[lab]["holds"][post]
        tt = (f"허벅지 {h['thigh_abs_deg']:+.2f}° 정강이 {h['shank_abs_deg']:+.2f}°"
              if h["thigh_abs_deg"] is not None else
              f"원시 라인각 허벅지 {h['thigh_line_raw_deg']:+.2f}° 정강이 {h['shank_line_raw_deg']:+.2f}° (저신뢰)")
        a.set_title(f"{lab} {post}\n{tt}", fontsize=9)
        a.axis("off"); a.legend(fontsize=6, loc="lower right")
    fig.tight_layout()
    fig.savefig(HERE/f"s2s_video_marks_{lab.replace('.', 'p')}.png", dpi=110)
    plt.close(fig)

# 정합 검증 이미지: 0kg 평균을 적합 변환으로 워프 → 대상과 비교 (핵심 비교의 시각 증거)
def warp_check(lab, post, body="thigh"):
    c = cross[lab][post][body]
    k0 = np.array(feat["0kg"][post]["knee"]); kT = np.array(feat[lab][post]["knee"])
    img0 = V["0kg"]["means"][post]; imgT = V[lab]["means"][post]
    p0 = np.array(feat["0kg"][post]["disc" if body == "thigh" else "foot"])
    x0 = int(min(k0[0], p0[0]) - 60); x1 = int(max(k0[0], p0[0]) + 60)
    y0 = int(min(k0[1], p0[1]) - 60); y1 = int(max(k0[1], p0[1]) + 60)
    a = np.radians(c["dphi"]); s = c["s"]
    Rm = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    XX, YY = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1))
    PT = np.stack([XX.ravel(), YY.ravel()], 1).astype(float)
    # 대상 좌표 → 0kg 좌표 (역변환)
    P0 = (PT - kT - (c["tx"], c["ty"])) @ np.linalg.inv((s*Rm)).T + k0
    W = ndimage.map_coordinates(img0, [P0[:, 1], P0[:, 0]], order=1, cval=0).reshape(XX.shape)
    Tgt_pT = PT.reshape(*XX.shape, 2)
    Tgt = ndimage.map_coordinates(imgT, [Tgt_pT[..., 1].ravel(), Tgt_pT[..., 0].ravel()],
                                  order=1, cval=0).reshape(XX.shape)
    return W, Tgt

combos = [(lab, post) for lab in ("5kg", "7.5kg") for post in ("crouch", "stand")]
fig, axs3 = plt.subplots(len(combos), 3, figsize=(13, 4.2*len(combos)))
for r, (lab, post) in enumerate(combos):
    W, Tgt = warp_check(lab, post, "thigh")
    d = np.abs(W - Tgt); d[(W == 0) | (Tgt == 0)] = 0
    axs3[r][0].imshow(W, cmap="gray"); axs3[r][0].set_title(f"0kg 워프 → {lab} {post}", fontsize=9)
    axs3[r][1].imshow(Tgt, cmap="gray"); axs3[r][1].set_title(f"{lab} {post} 실제", fontsize=9)
    axs3[r][2].imshow(d, cmap="magma")
    axs3[r][2].set_title(f"|차| (Δθ보정 {cross[lab][post]['thigh']['dtheta_corr']:+.2f}°, cost {cross[lab][post]['thigh']['cost']:.2f})", fontsize=9)
    for cc in range(3): axs3[r][cc].axis("off")
fig.suptitle("정합 검증: 0kg 평균영상을 적합 변환으로 워프 vs 대상 (허벅지 영역)", fontsize=11)
fig.tight_layout(); fig.savefig(HERE/"s2s_video_aligncheck.png", dpi=100)
plt.close(fig)
print("\ndone → _s2s_video_static.json / s2s_video_static.png / s2s_video_marks_*.png / s2s_video_aligncheck.png")
