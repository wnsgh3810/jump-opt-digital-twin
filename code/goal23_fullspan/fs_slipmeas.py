# -*- coding: utf-8 -*-
"""fs_slipmeas — **슬립·구름 판정의 정본 절차** (마라톤G G72, 08-08 확립).

한 줄: 슬립 = (영상으로 잰 발의 실제 이동) − (엔코더로 계산한 굴러간 거리).

왜 둘이 다 필요한가
  | 측정 | 얻는 것 | 못 얻는 것 |
  |---|---|---|
  | 엔코더 q1,q2 | **Δθ_발** — 4절 폐쇄로 결정, **베이스 위치와 무관** | Δx_발 |
  | 영상(롤러 중심) | **Δx_발** — 세계 좌표 실측 | Δθ_발 (롤러에 마커 없음) |
  비유: 바퀴가 "몇 바퀴 돌았나"는 엔코더가, "실제로 몇 cm 갔나"는 자가 안다.
  둘의 차이가 **미끄러짐**이다. 하나만으로는 절대 분해되지 않는다.

━━ 절차 5단계 (전부 자동, 각 단계에 QC 플래그) ━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ① **자 교정**   그 영상에서 발 금속판(30.0mm) 지름을 재서 mm/px 확정 (`fs_vidscale`).
                 ★ 다른 영상 값 재사용 금지 — 카메라 거리·줌이 세션마다 다르다.
  ② **동기**     영상 이륙 프레임(프레임차분 급증 시작) ↔ 데이터 `segment().t_lo`.
  ③ **발 탐색**  스쿼트 바닥에서 전역 원 탐색 → 각 후보를 이륙까지 추적 →
                 **이륙 때 가장 크게 움직인 원 = 발** (볼트 구멍·나사는 0px 움직인다).
  ④ **추적**     등속 예측 + 적응창 + 수직 구속 (`fs_vidscale.track_roller`).
  ⑤ **융합**     slip(t) = Δx_영상 − r·Δθ_엔코더,  r = 20.0 mm.

━━ 하지 말 것 (전부 실제 사고, REJECTED #73~#77) ━━━━━━━━━━━━━━━━━━━━━━━━━
  ✗ 발판 플레이트 120mm 자 (0.7453) — 금속판을 24.1mm 로 봄, ×1.239 오차
  ✗ 링크 연결부 추적 — 종아리 회전에 따라 궤도운동, 병진 변위가 아님
  ✗ 고정 ±5px 탐색창 — 푸시(프레임당 20~30px)에서 발을 놓치고 배경에 락온
  ✗ 세로 창까지 넓히기 — 흰 플랫폼 **볼트 구멍**이 더 높은 점수로 이김
  ✗ 이동중앙값 평활 — 푸시 급변을 뭉갬 (−56.5 → −38.5mm)
  ✗ 모델 Δx 로 만든 '기하 슬립' — |모델Δx|/|구름| 중앙 3.23, 증언과 부호 반대

정본 검증 trial: 26.07.23/150_2.2_250_3 →
  하강전반 −0.6 · 하강후반 −6.8 · 바닥유지 −0.6 · **푸시~이륙 −42.0** · 전체 −49.9 mm
  (사용자 육안 3건 전부 재현: 깊게앉기 −10~15 · 6.67~8.17s 이동 8.xx · 푸시 −60=플레이트 절반)

CLI:  python fs_slipmeas.py <세션> <trial>      # 한 trial
      python fs_slipmeas.py --all               # 전수 (오래 걸림 → .bat 로)
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("P25_CLIP_RAW", "35.5")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_vidscale as VS                                       # noqa: E402

OUT_JSON = HERE / "_G72_slipall.json"
FPS_DEFAULT = 24.0


# ── ② 동기 ────────────────────────────────────────────────────────────────────
def motion_profile(mp4, step=4):
    """프레임차분(움직임) 시계열. 이륙은 여기서 폭발적으로 튄다."""
    import imageio.v3 as iio
    prof = []; prev = None
    for f in iio.imiter(Path(mp4)):
        g = np.asarray(f, float)[..., :3].mean(axis=2)[::step, ::step]
        prof.append(0.0 if prev is None else float(np.abs(g - prev).mean()))
        prev = g
    return np.asarray(prof)


def liftoff_frame(prof, *, lo=0.25, hi=0.50, min_run=3):
    """이륙 프레임 검출.

    ★ 단발 스파이크를 버려야 한다 — 카카오톡 mp4 는 **1초(24프레임) 간격 키프레임**에서
      프레임차분이 혼자 튄다 (실측: f24·f48·f72·f120·f144·f168·f192 에 3~5 크기 스파이크).
      "임계 첫 교차" 로 잡으면 f24 를 이륙으로 오인한다.
    절차: prof > lo·max 인 **연속 런** 중 길이 ≥ min_run 인 **최장 런** = 점프 구간.
          그 안에서 prof > hi·max 를 처음 넘는 프레임 = 이륙.
    반환: (f_lo, run_start, run_end)  — 불확도 ±1~2프레임(±42~83ms).
    """
    m = float(prof.max())
    idx = np.where(prof > lo * m)[0]
    if not len(idx):
        return None, None, None
    runs = [r for r in np.split(idx, np.where(np.diff(idx) > 3)[0] + 1) if len(r) >= min_run]
    if not runs:
        return None, None, None
    run = max(runs, key=len)
    inside = run[prof[run] > hi * m]
    f = int(inside[0]) if len(inside) else int(run[0])
    return f, int(run[0]), int(run[-1])


# ── ③ 발 탐색 ────────────────────────────────────────────────────────────────
def _scan_circles(g, ys, xs, *, rrange=(11.0, 24.0, 0.5), topn=40):
    """거친 격자 전역 탐색 → 상위 후보 [(score,cx,cy,r)]."""
    ang = np.deg2rad(np.arange(*VS.SECTOR, 6.0)); ca = np.cos(ang); sa = -np.sin(ang)
    rs = np.arange(*rrange); out = []
    for cy in ys:
        for cx in xs:
            ri = (rs[:, None] - VS.EDGE_D) * ca[None, :]; si = (rs[:, None] - VS.EDGE_D) * sa[None, :]
            ro = (rs[:, None] + VS.EDGE_D) * ca[None, :]; so = (rs[:, None] + VS.EDGE_D) * sa[None, :]
            sc = (VS._samp(g, cx + ri, cy + si) - VS._samp(g, cx + ro, cy + so)).mean(axis=1)
            j = int(np.argmax(sc)); out.append((float(sc[j]), float(cx), float(cy), float(rs[j])))
    out.sort(key=lambda t: -t[0])
    # 근접 후보 병합
    keep = []
    for c in out:
        if all(np.hypot(c[1] - k[1], c[2] - k[2]) > 14 for k in keep):
            keep.append(c)
        if len(keep) >= topn:
            break
    return keep


def find_foot(mp4, f_lo, *, band=(0.60, 0.99), back=14, topn=8):
    """**이륙 순간 크게 움직이는 원 = 발**.

    판별 원리 (이게 결정적이다):
      바닥유지 구간에는 발도 배경 볼트 구멍도 거의 안 움직인다 → 구별 불가.
      그런데 **이륙 순간(2~3프레임)엔 발만 20~40px 튄다.** 배경은 0이다.
      그래서 스쿼트 바닥 프레임에서 후보를 뽑고, 각 후보를 이륙까지 따라가
      **변위가 가장 큰 것**을 발로 판정한다. (반지름이 무너지는 후보는 탈락.)
    반환: (score, cx, cy, r, moved_px) — cx,cy 는 **스쿼트 바닥 프레임** 기준 시드.
    """
    import imageio.v3 as iio
    f_sit = max(4, f_lo - back)
    want = set(range(f_sit, f_lo + 2)); F = {}
    for i, f in enumerate(iio.imiter(Path(mp4))):
        if i in want:
            F[i] = np.asarray(f, float)[..., :3].mean(axis=2)
        if i > max(want):
            break
    if f_sit not in F or f_lo not in F:
        return None
    H, W = F[f_sit].shape
    ys = np.arange(int(H * band[0]), int(H * band[1]), 6.0)
    xs = np.arange(int(W * 0.10), int(W * 0.94), 6.0)
    cands = _scan_circles(F[f_sit], ys, xs, topn=topn)
    best = None
    for s0, cx, cy, r0 in cands:
        c = np.array([cx, cy], float); v = np.zeros(2); rr = [r0]; okk = True
        for i in range(f_sit + 1, f_lo + 1):
            if i not in F:
                okk = False; break
            pred = c + v
            w = float(np.clip(2.5 * np.hypot(*v) + 6.0, 6.0, 60.0))
            sc, nx, ny, nr = VS.fit_roller(F[i], pred[0], pred[1], win=w, win_y=7.0)
            v = np.array([nx, ny]) - c; c = np.array([nx, ny]); rr.append(nr)
        if not okk:
            continue
        rr = np.array(rr)
        if rr.std() / max(rr.mean(), 1e-9) > 0.20:          # 반지름 붕괴 → 발이 아님
            continue
        moved = float(abs(c[0] - cx))
        if best is None or moved > best[4]:
            best = (s0, float(cx), float(cy), float(np.median(rr)), moved)
    return best


# ── ⑤ 융합 ───────────────────────────────────────────────────────────────────
def measure(sess, trial, *, verbose=True):
    """한 trial 의 슬립·구름 분해. 실패 시 reason 을 담은 dict 반환."""
    import fs_data as FD, fs_runner as FR
    from _G10_energy import Reduced
    from _G13_board import lpf

    hit = [q for s, q, g, c, h in FD.registry() if s == sess and q.name == trial]
    if not hit:
        return dict(sess=sess, trial=trial, ok=False, reason="registry 없음")
    p = hit[0]
    vids = sorted(Path(p).glob("*.mp4"))
    vids = [v for v in vids if "online-video-cutter" not in v.name]
    if not vids:
        return dict(sess=sess, trial=trial, ok=False, reason="mp4 없음")
    mp4 = vids[0]

    d = FD.load2(p); t = d["t"]; seg = FD.segment(d)
    if seg is None or seg.get("t_lo") is None:
        return dict(sess=sess, trial=trial, ok=False, reason="segment/t_lo 없음")
    t_lo = float(seg["t_lo"])

    prof = motion_profile(mp4)
    f_lo, r0f, r1f = liftoff_frame(prof)
    if f_lo is None or f_lo < 40:
        return dict(sess=sess, trial=trial, ok=False, reason=f"이륙 프레임 검출 실패 (f_lo={f_lo})",
                    mp4=mp4.name)
    fps = FPS_DEFAULT
    shift = t_lo - f_lo / fps                      # 데이터시각 = 영상시각 + shift

    f0 = max(2, f_lo - 110)                        # 하강 시작 부근
    fd = find_foot(mp4, f_lo)
    if fd is None:
        return dict(sess=sess, trial=trial, ok=False, reason="발 자동 탐색 실패", mp4=mp4.name)
    sc0, cx0, cy0, r0, moved = fd

    # 시드는 **스쿼트 바닥(f_lo-14)** 기준 → 거기서 앞뒤로 나눠 추적
    f_sit = max(4, f_lo - 14)
    tb = VS.track_roller(mp4, f0, f_sit, (cx0, cy0))          # 뒤로(=시간 역순 아님, f0→f_sit)
    tf = VS.track_roller(mp4, f_sit, max(f_sit, f_lo - 1), (tb[f_sit]["cx"], tb[f_sit]["cy"]))
    tr = {**tb, **tf}
    R = np.array([v["r"] for v in tr.values()]); S = np.array([v["score"] for v in tr.values()])
    ok = S > np.percentile(S, 25)
    dia = float(2 * np.median(R[ok]))
    s_mm = VS.METAL_DIA_MM / dia
    rel = float((2 * np.percentile(R[ok], 75) - 2 * np.percentile(R[ok], 25)) / 2 / dia)

    # ★ 접지 유효 구간 절단 — 이륙 다음 프레임부터 발이 화면에서 사라져 추적이 튄다.
    #   (실측: f200 에서 −148mm 로 폭주). 지면 높이에서 벗어나거나 점수가 무너지면 자른다.
    ks = sorted(tr)
    cys = np.array([tr[k]["cy"] for k in ks]); scs = np.array([tr[k]["score"] for k in ks])
    y0 = float(np.median(cys[: max(3, len(ks) // 2)])); s0 = float(np.median(scs))
    cxs = np.array([tr[k]["cx"] for k in ks])
    last = len(ks) - 1
    for j in range(3, len(ks)):
        if (abs(cys[j] - y0) > 8.0 or scs[j] < 0.5 * s0
                or abs(cxs[j] - cxs[j - 1]) > 60.0):        # 1프레임 60px 초과 = 물리적 불가
            last = j - 1; break
    ks = ks[: last + 1]
    f_end = ks[-1]
    fi = np.array(ks, float)
    xpx = np.array([tr[int(k)]["cx"] for k in fi])          # ★ 평활 금지

    # ★★ 동기 재확정: **마지막 접지 프레임 ↔ 데이터 t_lo** ★★
    #   24fps 에서 푸시는 5프레임뿐인데 구름이 마지막 프레임에 15mm 급변한다 —
    #   동기 1프레임(42ms) 오차가 **푸시 슬립을 11mm** 흔든다.
    #   프레임차분으로 잡은 f_lo 는 ±1프레임 불확도가 있으므로, 물리적으로 확실한
    #   "발이 지면에 있던 마지막 프레임 = 이륙 직전" 을 t_lo 에 맞춘다.
    shift = t_lo - f_end / fps
    t_vid = fi / fps
    t_dat = t_vid + shift

    Rd = Reduced(FR.fs_twin()); rfoot = VS.FOOT_R_M
    q1f = lpf(d["q1"], 30.0); q2f = lpf(d["q2"], 30.0)
    th = np.array([Rd.state(q1f[i], q2f[i])[2] for i in range(0, len(t), 2)])
    th_v = np.interp(t_dat, t[::2], th)

    x_mm = (xpx - xpx[0]) * s_mm
    roll = rfoot * (th_v - th_v[0]) * 1000.0
    slip = x_mm - roll

    # 구간 경계는 **데이터 세그먼트**에서 (프레임 비율 추정 금지)
    t_bot = float(t[seg["i_bot"]]); t_push = float(seg["t_push"]); t_desc = float(seg["t_desc"])
    jf = lambda td: int(np.argmin(np.abs(t_dat[: len(fi)] - td)))
    n = len(fi)
    i_d, i_b, i_p = jf(t_desc), jf(t_bot), jf(t_push)
    i_m = (i_d + i_b) // 2
    B = {"하강전반": (i_d, i_m), "하강후반": (i_m, i_b),
         "바닥유지": (i_b, i_p), "푸시~이륙": (i_p, n - 1), "전체": (i_d, n - 1)}
    segs = {k: dict(dx=float(x_mm[b] - x_mm[a]), roll=float(roll[b] - roll[a]),
                    slip=float(slip[b] - slip[a]), t=(float(t_vid[a]), float(t_vid[b])))
            for k, (a, b) in B.items()}

    # 동기 민감도: shift 를 ±1프레임 흔들었을 때 푸시 슬립이 얼마나 변하나
    def push_slip(sh):
        tv = fi / fps + sh
        th2 = np.interp(tv, t[::2], th)
        rl = rfoot * (th2 - th2[0]) * 1000.0
        a, b = B["푸시~이륙"]
        return float((x_mm[b] - x_mm[a]) - (rl[b] - rl[a]))
    sens = float(max(abs(push_slip(shift + 1 / fps) - segs["푸시~이륙"]["slip"]),
                     abs(push_slip(shift - 1 / fps) - segs["푸시~이륙"]["slip"])))

    qc = []
    if sens > 8.0:
        qc.append(f"동기 ±1프레임 → 푸시슬립 ±{sens:.0f}mm")
    if rel > 0.10:
        qc.append(f"지름 산포 {rel*100:.0f}% (>10%)")
    if float(np.min(S)) < 40:
        qc.append(f"최저 추적점수 {np.min(S):.0f} (<40)")
    if moved < 15:
        qc.append(f"이륙 변위 {moved:.0f}px (<15 — 발 오탐 가능)")
    if abs(shift) > 20:
        qc.append(f"동기 shift {shift:+.1f}s (비정상)")
    if f_end < f_lo - 2:
        qc.append(f"접지 절단 f{f_end} (이륙 f{f_lo} 보다 {f_lo-f_end}프레임 이름 — 동기 의심)")
    if B["푸시~이륙"][1] - B["푸시~이륙"][0] < 2:
        qc.append("푸시 구간 프레임 <2 (분해능 부족)")

    res = dict(sess=sess, trial=trial, ok=True, mp4=mp4.name, fps=fps,
               f_lo=f_lo, f_end=f_end, jump_run=[r0f, r1f], t_lo=t_lo, shift=shift, f0=f0,
               seed=[cx0, cy0], seed_r=r0, seed_moved=moved,
               dia_px=dia, scale=s_mm, rel_sd=rel,
               score_min=float(np.min(S)), score_med=float(np.median(S)),
               r_foot_mm=rfoot * 1000, seg=segs, sync_sens_mm=sens, qc=qc,
               series=dict(f=fi.tolist(), x=x_mm.tolist(), roll=roll.tolist(), slip=slip.tolist()))
    if verbose:
        _pr(res)
    return res


def _pr(r):
    if not r["ok"]:
        print(f"  ✗ {r['sess']}/{r['trial']}: {r['reason']}")
        return
    print(f"  {r['sess']}/{r['trial']:<20s} 자 {r['scale']:.4f} mm/px (지름 {r['dia_px']:.1f}px "
          f"±{r['rel_sd']*100:.0f}%) · 이륙 f{r['f_lo']} · shift {r['shift']:+.2f}s"
          + ("   ⚠ " + " / ".join(r["qc"]) if r["qc"] else ""))
    g = r["seg"]
    print(f"      {'구간':<10}{'Δx':>9}{'구름':>9}{'슬립':>9}")
    for k in ("하강전반", "하강후반", "바닥유지", "푸시~이륙", "전체"):
        v = g[k]
        print(f"      {k:<10}{v['dx']:9.2f}{v['roll']:9.2f}{v['slip']:9.2f}")


def main():
    import fs_data as FD
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--all" in sys.argv:
        reg = [(s, q.name) for s, q, g, c, h in FD.registry()]
    elif len(args) >= 2:
        reg = [(args[0], args[1])]
    else:
        reg = [("26.07.23", "150_2.2_250_3")]
    print("=" * 104)
    print(f"★ 슬립·구름 전수 판정 — 자=발 금속판 {VS.METAL_DIA_MM:.0f}mm · r={VS.FOOT_R_M*1000:.0f}mm "
          f"· + = 화면 오른쪽 = 모델 +x")
    OUT = {}
    if OUT_JSON.exists():
        try:
            OUT = json.load(io.open(OUT_JSON, encoding="utf-8"))
        except Exception:
            OUT = {}
    for s, q in reg:
        try:
            r = measure(s, q)
        except Exception as ex:
            r = dict(sess=s, trial=q, ok=False, reason=f"{type(ex).__name__}: {str(ex)[:70]}")
            print(f"  ✗ {s}/{q}: {r['reason']}")
        OUT[f"{s}/{q}"] = r
        json.dump(OUT, io.open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    good = [v for v in OUT.values() if v.get("ok")]
    print(f"\n성공 {len(good)}/{len(OUT)} · 저장: {OUT_JSON.name}")


if __name__ == "__main__":
    main()
