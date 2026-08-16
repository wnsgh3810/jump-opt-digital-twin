"""GOAL22 P12 — hip↔knee 토크 트레이드오프 분석 (사용자 관찰 07-09 검증).

가설: 스탠스(발 고정 + base 레일)에서 시스템은 1-DOF → 운동은 a(q)·τ 한 조합만 결정,
직교(널) 방향 n(q)의 토크 재분배는 q/dq에 불가시. fit(게인 재적합)이 이 널 방향으로
hip↔knee 분배를 옮겼는지 정량화:
  (1) Δτ = fit − label 의 hip/knee 상관 + TLS 기울기
  (2) 기하 예측 널 기울기 −a2/a1 (발-고정 자코비안, J·a=(0,-1))과 비교
  (3) Δτ 에너지 중 널 방향 비율 [%]
  (4) 잔차 e = label − real 의 상관 (참고)
"""
import sys, json
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
import mujoco

sys.path.insert(0, str(Path(__file__).parent))
from g22_p10_anim import build_fourbar_model
from g22_p10_cl import load_trial_xlsx, SD
from g22_p10_pdlaw import SETS

TRAJ = Path(__file__).parent / "p10_cl_traj"
OUT = Path(__file__).parent / "p12_tradeoff.json"
SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad/g22_cl_gallery")


def make_jac(model):
    data = mujoco.MjData(model)
    fg = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "foot")

    def fk(q1c, q2c):
        q1m = -q1c - np.pi / 2; q2m = -q2c
        data.qpos[:] = [1.0, q1m, q2m, -q2m, q2m]
        data.qvel[:] = 0
        mujoco.mj_forward(model, data)
        p = data.geom_xpos[fg]
        return np.array([p[0], p[2]])

    def a_vec(q1c, q2c, eps=1e-5):
        """a = dq/dz (발 고정, base 수직 이동): J·a = (0,-1). canonical 좌표."""
        p0 = fk(q1c, q2c)
        J = np.column_stack([(fk(q1c + eps, q2c) - p0) / eps,
                             (fk(q1c, q2c + eps) - p0) / eps])
        try:
            a = np.linalg.solve(J, np.array([0.0, -1.0]))
        except np.linalg.LinAlgError:
            return None
        return a
    return a_vec


def tls_slope(x, y):
    """총최소자승 기울기 (y = m x): 공분산 주축."""
    X = np.column_stack([x - x.mean(), y - y.mean()])
    _, _, Vt = np.linalg.svd(X, full_matrices=False)
    vx, vy = Vt[0]
    return vy / vx if abs(vx) > 1e-12 else np.inf


def main():
    model = build_fourbar_model()
    a_vec = make_jac(model)
    rows = {}
    for ds, (root, subs) in SETS.items():
        for sub in subs:
            fL = TRAJ / f"{ds}__{sub}__label.npz"
            fF = TRAJ / f"{ds}__{sub}__fit.npz"
            if not (fL.exists() and fF.exists()):
                continue
            d = load_trial_xlsx(ds, root, sub)
            t = d["t"]
            zL = np.load(fL); zF = np.load(fF)
            g = lambda z, k: np.interp(t, z["t"], z[k])
            # 스탠스: label GRF>5 (t>=0, 실측 구간)
            grfL = g(zL, "grf")
            st = grfL > 5.0
            if st.sum() < 20:
                continue
            s1L, s2L = g(zL, "sh1")[st], g(zL, "sh2")[st]
            s1F, s2F = g(zF, "sh1")[st], g(zF, "sh2")[st]
            tp1 = np.interp(t - SD, t, d["tau1_paper"])[st]
            tp2 = np.interp(t - SD, t, d["tau2_paper"])[st]
            d1, d2 = s1F - s1L, s2F - s2L                    # fit − label
            e1, e2 = s1L - tp1, s2L - tp2                    # label − real
            # 기하 널 기울기 (실측 자세 기준, 스탠스 평균)
            q1r, q2r = np.asarray(d["q1"])[st], np.asarray(d["q2"])[st]
            slopes_pred, null_fr = [], []
            for i in range(0, len(q1r), max(1, len(q1r) // 25)):
                a = a_vec(q1r[i], q2r[i])
                if a is None or not np.isfinite(a).all():
                    continue
                slopes_pred.append(-a[1] / a[0] if abs(a[0]) > 1e-9 else np.nan)
                n = np.array([-a[1], a[0]]); n /= np.linalg.norm(n)
                # 이 샘플 근방 Δτ의 널 성분 비율은 전체로 계산 (아래)
            # Δτ 에너지 널 비율: 각 샘플의 a(q)로 분해
            num = den = 0.0
            for i in range(len(q1r)):
                a = a_vec(q1r[i], q2r[i]) if i % max(1, len(q1r) // 50) == 0 else a
                if a is None:
                    continue
                ah = a / np.linalg.norm(a)
                nh = np.array([-ah[1], ah[0]])
                v = np.array([d1[i], d2[i]])
                num += (v @ nh) ** 2
                den += v @ v
            frac_null = 100.0 * num / max(den, 1e-12)
            c_d = float(np.corrcoef(d1, d2)[0, 1]) if d1.std() > 1e-6 and d2.std() > 1e-6 else np.nan
            c_e = float(np.corrcoef(e1, e2)[0, 1]) if e1.std() > 1e-6 and e2.std() > 1e-6 else np.nan
            m_d = float(tls_slope(d2, d1))                   # Δτ1 = m·Δτ2
            rows[f"{ds}/{sub}"] = dict(
                corr_fitlabel=c_d, slope_fitlabel=m_d,
                slope_pred=float(np.nanmean(slopes_pred)),
                frac_null=float(frac_null), corr_resid=c_e,
                rms_d1=float(np.sqrt(np.mean(d1 ** 2))), rms_d2=float(np.sqrt(np.mean(d2 ** 2))))
            r = rows[f"{ds}/{sub}"]
            print(f"{ds}/{sub}: corr(Δτ1,Δτ2)={c_d:+.2f} 기울기 {m_d:+.2f} "
                  f"(예측 {r['slope_pred']:+.2f})  널비율 {frac_null:5.1f}%  corr(e1,e2)={c_e:+.2f}",
                  flush=True)
    json.dump(rows, open(OUT, "w"), indent=1)
    # 데이터셋 요약
    print("\n=== 데이터셋 중앙값 ===")
    for ds in SETS:
        ks = [k for k in rows if k.startswith(ds + "/")]
        if not ks:
            continue
        med = lambda f: float(np.nanmedian([rows[k][f] for k in ks]))
        print(f"{ds:22s} corr_Δ {med('corr_fitlabel'):+.2f}  기울기 {med('slope_fitlabel'):+.2f} "
              f"(예측 {med('slope_pred'):+.2f})  널비율 {med('frac_null'):5.1f}%  corr_e {med('corr_resid'):+.2f}",
              flush=True)

    # 대표 그림: 사용자 지목 trial 산점 + 널 방향선
    key = "jump_0602/90_0.75_90_2"
    ds, sub = key.split("/")
    d = load_trial_xlsx(ds, SETS[ds][0], sub)
    t = d["t"]
    zL = np.load(TRAJ / f"{ds}__{sub}__label.npz"); zF = np.load(TRAJ / f"{ds}__{sub}__fit.npz")
    g = lambda z, k: np.interp(t, z["t"], z[k])
    st = g(zL, "grf") > 5.0
    d1 = (g(zF, "sh1") - g(zL, "sh1"))[st]; d2 = (g(zF, "sh2") - g(zL, "sh2"))[st]
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.6))
    ax[0].scatter(d2, d1, s=10)
    m = rows[key]["slope_pred"]
    xx = np.linspace(d2.min(), d2.max(), 10)
    ax[0].plot(xx, m * xx, "C1", lw=1.5, label=f"기하 예측 널 방향 (기울기 {m:+.2f})")
    ax[0].set_xlabel("Δτ knee [Nm] (fit − label)"); ax[0].set_ylabel("Δτ hip [Nm]")
    ax[0].set_title(f"{key} — 스탠스 토크 재분배"); ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    ax[1].plot(t[st] * 1e3, d1, lw=1.2, label="Δτ hip")
    ax[1].plot(t[st] * 1e3, d2, lw=1.2, label="Δτ knee")
    ax[1].set_xlabel("t [ms]"); ax[1].set_ylabel("Δτ [Nm]")
    ax[1].set_title("시간 파형 (반대 부호 = 트레이드)"); ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(SCR / "p12_tradeoff_example.png", dpi=115)
    print("saved p12_tradeoff.json + p12_tradeoff_example.png", flush=True)


if __name__ == "__main__":
    main()
