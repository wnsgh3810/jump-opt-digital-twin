# -*- coding: utf-8 -*-
"""
p26 ruler_offset.py — 영상 눈금자(자)로 base 절대높이를 읽어 (delta1, delta2) 능선 비식별을 깨는 분석.

영상: 26.06.04/no_cvt/no_load/KakaoTalk_20260604_170859513.mp4 (9.46s, 24fps 컨테이너, 720x1280)
데이터: 같은 폴더 raw_unwrap/hip.xlsx, knee.xlsx

핵심 발견 (2026-07-29 서브에이전트):
 1. 영상 정적 3구간 (프레임차분): A=프레임 0-23(시작 정지), B=148-166(중간 짧은 정지), C=196-226(끝 정지).
    지시서의 인코더 각도(A: -49.6/-100.7)는 0~48.3s 전체 평균(초기 -63/-132 혼입 오염)이었음.
    실제 플래토 값 사용: A(-45.01,-91.23) B(-16.49,-147.07) C(-71.95,-36.57) [deg].
 2. 영상 시간축은 VFR/재인코딩 왜곡 — 시간 매칭 대신 "정지 구간 패턴" 매칭이 유일하게 유효.
 3. B(깊은 크라우치) 영상 프레임은 이 trial 인코더와 불일치: 영상 대퇴각 -9.7 deg(이미지)인데
    인코더 q1은 trial 전체에서 -16.36 deg를 넘은 적 없음. 눈금자도 인코더-FK 대비 -1.8~-2.5cm 낮음.
    플래토 토크 ~0.7Nm뿐이라 처짐(compliance)으로 설명 불가 → B 프레임은 플래토와 비동시(다른 순간/반복) 판정.
    ⇒ B는 방정식에서 제외(진단 전용), A·C 눈금 방정식 + 능선 관계(delta2=-2.06*delta1+7.2)로 3미지수 완결.
 4. 구조적 통찰: 정적 자세는 모두 발이 힙 바로 아래(bx~0) → d bz/d delta1 ∝ (cos q1 + cos(q1+q2)) ~ 0.
    즉 눈금자 방정식은 사실상 delta2만 구속(자세별 감도차)하고, 능선과의 교차로 delta1이 결정된다.
 5. 깊이 시차(parallax): 링크 0.25m가 다리 평면에서 ~12.3px/cm인데 배너 눈금은 ~10.4-11.1px/cm →
    다리 평면은 카메라에 ~15% 더 가깝다. 마스트(캐리지 중앙 기둥)는 배너와 유사 심도(마스트 변위/힙 변위
    비 1.17 ≈ 스케일비) → 마스트-눈금자 조합은 유효, 단 gamma2(심도비) ±3%를 계통 불확도로 전파.

출력: _ruler_offset.json, ruler_offset_marks.png (같은 폴더)
실행: PYTHONIOENCODING=utf-8 python ruler_offset.py
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
import json
import os
import numpy as np

D = np.pi / 180.0
HERE = os.path.dirname(os.path.abspath(__file__))
VID = (DATA_ROOT + "/26_06_04/no_cvt/no_load/KakaoTalk_20260604_170859513.mp4")

# ---------------------------------------------------------------------------
# 1) 정적 구간 대표 프레임 평균 (프레임차분 quiet run에서 선정, 각 10장)
#    A: 5-14 (video 0.21-0.58s), B: 153-162 (6.38-6.75s), C: 217-226 (9.04-9.42s)
# ---------------------------------------------------------------------------
WINS = {"A": list(range(5, 15)), "B": list(range(153, 163)), "C": list(range(217, 227))}

def load_avg_frames():
    import imageio.v3 as iio
    need = set(sum(WINS.values(), []))
    acc = {k: None for k in WINS}
    for i, fr in enumerate(iio.imiter(VID, plugin="FFMPEG")):
        if i in need:
            for k, idxs in WINS.items():
                if i in idxs:
                    acc[k] = fr.astype(np.float64) if acc[k] is None else acc[k] + fr
    return {k: acc[k] / len(WINS[k]) for k in WINS}

# ---------------------------------------------------------------------------
# 2) 눈금자 앵커: 10cm 큰 눈금(숫자 10..70) tick 중심 y (frame A에서 검출·수동 검증됨)
#    검출법: 배너 우측 에지 적합(x=-0.0275y+174.1, 롤 -1.57deg) 후 에지 좌측 44..4px 밴드의
#    어두움 프로파일 피크. 숫자 크롭과 대조 검증(70/60/50/20/10), 간격 105->116px 단조 증가(원근) 확인.
# ---------------------------------------------------------------------------
ANCH_Y = np.array([375.44, 480.51, 586.50, 693.50, 803.13, 915.72, 1031.47])
ANCH_CM = np.array([70.0, 60.0, 50.0, 40.0, 30.0, 20.0, 10.0])
CF = np.polyfit(ANCH_Y, ANCH_CM, 2)  # cm(y) 2차: 앵커 잔차 ±0.07cm

def cm_of_y(y):
    return float(np.polyval(CF, y))

def px_per_cm_local(y):
    return float(-1.0 / (2 * CF[0] * y + CF[1]))

# ---------------------------------------------------------------------------
# 3) 캐리지 특징 = 마스트(검은 원기둥) 상단 패치, frame A (356,559) 중심 41x41 템플릿.
#    NCC 정합: B (354.96, 803.50) ncc 0.77 / C (356.00, 429.91) ncc 0.92. 특징-상단에지 상수차는 c로 흡수.
#    (에지 50% 교차법은 대비 3-7레벨로 불가 판정 — 흑기둥 vs 흑배경.)
# ---------------------------------------------------------------------------
MAST_A = (356.0, 559.0)

def ncc_match(ref, pos, tgt, guess, half=20, srch=30):
    x0, y0 = int(round(pos[0])), int(round(pos[1]))
    T = ref[y0 - half:y0 + half + 1, x0 - half:x0 + half + 1]
    Tm = T - T.mean()
    gx, gy = int(round(guess[0])), int(round(guess[1]))
    scores = {}
    best = (-2, 0, 0)
    for dy in range(-srch, srch + 1):
        for dx in range(-srch, srch + 1):
            cx, cy = gx + dx, gy + dy
            P = tgt[cy - half:cy + half + 1, cx - half:cx + half + 1]
            if P.shape != T.shape:
                continue
            Pm = P - P.mean()
            den = np.sqrt((Tm ** 2).sum() * (Pm ** 2).sum())
            s = (Tm * Pm).sum() / den if den > 0 else -1
            scores[(dx, dy)] = s
            if s > best[0]:
                best = (s, cx, cy)
    s, cx, cy = best
    dx0, dy0 = cx - gx, cy - gy
    try:
        sxm, sxp = scores[(dx0 - 1, dy0)], scores[(dx0 + 1, dy0)]
        sym, syp = scores[(dx0, dy0 - 1)], scores[(dx0, dy0 + 1)]
        cx += 0.5 * (sxm - sxp) / (sxm - 2 * s + sxp)
        cy += 0.5 * (sym - syp) / (sym - 2 * s + syp)
    except (KeyError, ZeroDivisionError):
        pass
    return cx, cy, s

# ---------------------------------------------------------------------------
# 4) 인코더 플래토 (raw_unwrap xlsx, 영상 매칭 창 평균) [deg]
#    A: t 46.3-47.0 (플래토 40-48.3 안정 ±0.01), B: t 52.4-53.2 (±0.2), C: t 54.5-56.0 (±0.03)
# ---------------------------------------------------------------------------
Q1 = {"A": -45.01, "B": -16.49, "C": -71.95}
Q2 = {"A": -91.23, "B": -147.07, "C": -36.57}
RIDGE_A, RIDGE_B = -2.06, 7.2  # delta2 = a*delta1 + b (인코더-FK 발끝 폐쇄 능선)

def bz_cm(k, d1, d2):
    a = (Q1[k] + d1) * D
    s = (Q1[k] + Q2[k] + d1 + d2) * D
    return -25.0 * (np.sin(a) + np.sin(s))


def solve_V1(h):
    """(참고) 3자세 LSQ — B 오염 포함, 지시서 원안."""
    from scipy.optimize import least_squares
    def res(p):
        d1, d2, c = p
        return np.array([bz_cm(k, d1, d2) + c - h[k] for k in "ABC"])
    best = None
    for d1 in np.arange(-12, 12.1, 1.0):
        for d2 in np.arange(-12, 12.1, 1.0):
            c = np.mean([h[k] - bz_cm(k, d1, d2) for k in "ABC"])
            sse = float((res([d1, d2, c]) ** 2).sum())
            if best is None or sse < best[0]:
                best = (sse, [d1, d2, c])
    sol = least_squares(res, best[1], method="lm")
    d1, d2, c = sol.x
    return d1, d2, c, res(sol.x)


def solve_V2(hA, hC, q1=Q1, q2=Q2, rb=RIDGE_B):
    """주해: A,C 눈금 방정식 + 능선 → (d1,d2,c) 완결."""
    from scipy.optimize import brentq
    def bzc(k, d1, d2):
        a = (q1[k] + d1) * D
        s = (q1[k] + q2[k] + d1 + d2) * D
        return -25.0 * (np.sin(a) + np.sin(s))
    tgt = hC - hA
    def f(d1):
        d2 = RIDGE_A * d1 + rb
        return (bzc("C", d1, d2) - bzc("A", d1, d2)) - tgt
    xs = np.linspace(-12, 12, 481)
    fs = [f(x) for x in xs]
    for i in range(len(xs) - 1):
        if fs[i] * fs[i + 1] < 0:
            d1 = brentq(f, xs[i], xs[i + 1])
            d2 = RIDGE_A * d1 + rb
            c = hA - bzc("A", d1, d2)
            return d1, d2, c
    return None


def main():
    frames = load_avg_frames()
    gray = {k: frames[k].mean(axis=2) for k in frames}

    ymast = {"A": MAST_A[1]}
    ncc = {"A": 1.0}
    guesses = {"B": (356, 801), "C": (356, 431)}
    for k in "BC":
        x, y, s = ncc_match(gray["A"], MAST_A, gray[k], guesses[k])
        ymast[k] = y
        ncc[k] = s
        print(f"mast {k}: y={y:.2f} (x={x:.2f}) ncc={s:.3f}")

    h = {k: cm_of_y(ymast[k]) for k in "ABC"}
    for k in "ABC":
        print(f"h_{k} = {h[k]:.3f} cm (y={ymast[k]:.2f}, local {px_per_cm_local(ymast[k]):.2f} px/cm)")

    d1_v1, d2_v1, c_v1, r_v1 = solve_V1(h)
    print(f"V1(3자세, B오염 참고): d1={d1_v1:+.2f} d2={d2_v1:+.2f} c={c_v1:.2f} res={np.round(r_v1,3)}")

    d1, d2, c = solve_V2(h["A"], h["C"])
    rB = bz_cm("B", d1, d2) + c - h["B"]
    print(f"V2(A,C+능선, 주해): d1={d1:+.3f} d2={d2:+.3f} c={c:.3f} | B 진단잔차 {rB:+.2f} cm")

    # --- MC 불확도: 읽기 ±0.22cm, gamma2 ±3%(A-C 스팬), 인코더창 ±0.15deg, 능선절편 ±0.5deg
    rng = np.random.default_rng(0)
    R1, R2, RC = [], [], []
    for _ in range(4000):
        hA = h["A"] + rng.normal(0, 0.22)
        hC = hA + (h["C"] + rng.normal(0, 0.22) - hA) * (1 + rng.normal(0, 0.03))
        qb = rng.normal(0, 0.15, 4)
        q1s = {"A": Q1["A"] + qb[0], "C": Q1["C"] + qb[2], "B": Q1["B"]}
        q2s = {"A": Q2["A"] + qb[1], "C": Q2["C"] + qb[3], "B": Q2["B"]}
        out = solve_V2(hA, hC, q1=q1s, q2=q2s, rb=7.2 + rng.normal(0, 0.5))
        if out:
            R1.append(out[0]); R2.append(out[1]); RC.append(out[2])
    R1, R2, RC = map(np.array, (R1, R2, RC))
    print(f"MC: d1 {R1.mean():+.2f}±{R1.std():.2f}, d2 {R2.mean():+.2f}±{R2.std():.2f}, c {RC.mean():.2f}±{RC.std():.2f}")

    # --- 능선 교차 판정: A,C 눈금 패밀리(능선 없이)와 능선의 교차각/위치
    fam = []
    from scipy.optimize import brentq
    for d1f in np.arange(-4, 8.01, 2.0):
        def g(d2f, d1f=d1f):
            return (bz_cm("C", d1f, d2f) - bz_cm("A", d1f, d2f)) - (h["C"] - h["A"])
        try:
            fam.append((d1f, brentq(g, -12, 12)))
        except ValueError:
            pass

    # --- 검증 이미지
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(15, 9))
    K_pts = {"A": (580.5, 935.5), "B": (666.0, 1062.1), "C": (456.8, 860.7)}
    F_pts = {"A": (360.3, 1153.5), "B": (367.4, 1153.8), "C": (346.4, 1154.4)}
    for ax, k in zip(axes, "ABC"):
        ax.imshow(frames[k].astype(np.uint8))
        for yc, cmv in zip(ANCH_Y, ANCH_CM):
            ln, = ax.plot([95, 150], [yc, yc], lw=1.2)
            ax.text(60, yc + 4, f"{int(cmv)}", fontsize=7, color=ln.get_color())
        ym = ymast[k]
        ln2, = ax.plot([120, 420], [ym, ym], lw=1.5, ls="--")
        ax.plot([MAST_A[0]], [ym], marker="+", ms=14, mew=2, color=ln2.get_color())
        ax.text(160, ym - 8, f"h_{k}={h[k]:.2f}cm", fontsize=9, color=ln2.get_color())
        ln3, = ax.plot([K_pts[k][0]], [K_pts[k][1]], marker="x", ms=10, mew=2)
        ax.plot([F_pts[k][0]], [F_pts[k][1]], marker="x", ms=10, mew=2, color=ln3.get_color())
        ttl = f"{k}: q1={Q1[k]:.2f} q2={Q2[k]:.2f}"
        if k == "B":
            ttl += " [EXCLUDED]"
        ax.set_title(ttl, fontsize=10)
        ax.set_xlim(0, 720); ax.set_ylim(1280, 0); ax.axis("off")
    fig.suptitle(f"ruler offset break: V2(A,C+ridge) d1={d1:+.2f}\u00b1{R1.std():.2f} d2={d2:+.2f}\u00b1{R2.std():.2f} c={c:.2f}cm | B diag residual {rB:+.2f}cm", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "ruler_offset_marks.png"), dpi=110)
    print("saved ruler_offset_marks.png")

    out = {
        "note": "눈금자 base 절대높이로 (d1,d2) 능선 붕괴. A/C 눈금 방정식 + 능선(d2=-2.06d1+7.2) 교차 = 주해(V2). "
                "B(크라우치) 영상 프레임은 이 trial 인코더와 비동시(영상 대퇴 -9.7deg vs 인코더 최대 -16.36deg, "
                "눈금 -1.8cm) → 제외. 지시서의 A 각도(-49.6/-100.7)는 0-48.3s 전체평균 오염 — 실제 플래토 "
                "(-45.01/-91.23) 사용. 정적자세 bx~0이라 눈금 방정식은 delta1에 1차 둔감(delta2 위주 구속) → "
                "능선과 잘 조건화된 교차. 시차: 다리평면 12.3px/cm vs 배너 10.4-11.1px/cm(15%) — 마스트는 배너 "
                "유사심도(변위비 1.17=스케일비 검증), gamma2=1±0.03 계통 반영.",
        "video": os.path.basename(VID),
        "frames": {k: [WINS[k][0], WINS[k][-1]] for k in WINS},
        "encoder_windows_s": {"A": [46.3, 47.0], "B": [52.4, 53.2], "C": [54.5, 56.0]},
        "q_deg": {k: [Q1[k], Q2[k]] for k in "ABC"},
        "y_mast_px": {k: round(float(ymast[k]), 2) for k in "ABC"},
        "ncc": {k: round(float(ncc[k]), 3) for k in "ABC"},
        "h_A_cm": round(h["A"], 3), "h_B_cm": round(h["B"], 3), "h_C_cm": round(h["C"], 3),
        "px_per_cm": {"banner_local_at_mast": {k: round(px_per_cm_local(ymast[k]), 3) for k in "ABC"},
                       "leg_plane_from_links": 12.3,
                       "anchors_y_px": ANCH_Y.tolist(), "anchors_cm": ANCH_CM.tolist()},
        "delta1_deg": round(float(d1), 2),
        "delta2_deg": round(float(d2), 2),
        "c_cm": round(float(c), 2),
        "uncertainty_1sigma": {"delta1_deg": round(float(R1.std()), 2),
                                "delta2_deg": round(float(R2.std()), 2),
                                "c_cm": round(float(RC.std()), 2),
                                "budget": "읽기±0.22cm, gamma2±3%, 인코더±0.15deg, 능선절편±0.5deg; "
                                          "미포함: 원근 각왜곡~1deg급, A/C 미소 하중처짐"},
        "ridge_cross": {"intersects": True,
                         "family_AC_only": [[round(a, 2), round(b, 2)] for a, b in fam],
                         "comment": "A,C 패밀리는 d2~+1.0~+1.3(거의 수평)로 능선(기울기 -2.06)과 d1=2.97에서 "
                                    "교차. 능선 후보역 d1 3~9 중 상단(6~9)은 d2<=-5 필요 -> 눈금 d2와 >5sigma "
                                    "배치, 강기각. d1~3 저단부 채택."},
        "V1_reference_3pose": {"delta1": round(float(d1_v1), 2), "delta2": round(float(d2_v1), 2),
                                "c": round(float(c_v1), 2), "residuals_cm": [round(float(x), 2) for x in r_v1],
                                "warning": "B 오염 포함 — 사용 금지, 지시서 원안 재현용"},
        "B_diagnostic_residual_cm": round(float(rB), 2),
        "crosschecks": {"calf_angle_delta12_deg": {"A": 1.2, "B": 0.9, "C": -1.8},
                         "comment": "다리평면 무릎베어링-발휠 각 직접측정(롤 -0.24 보정). V2의 d1+d2=4.05와 "
                                    "1~3deg 긴장 — 원근/특징픽 계통 한계. 능선 교차 판정에는 영향 없음."},
    }
    with open(os.path.join(HERE, "_ruler_offset.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("saved _ruler_offset.json")


if __name__ == "__main__":
    main()
