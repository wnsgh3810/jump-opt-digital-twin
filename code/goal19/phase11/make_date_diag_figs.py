# -*- coding: utf-8 -*-
"""Figures for the per-date accuracy explainer Notion page (default color cycle)."""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot as MS
import mshoot_fourbar_refit as FR
from load_31exp import list_experiments

OUT = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad/date_diag")
OUT.mkdir(exist_ok=True)
g18 = sys.modules[S.load_jump_0602.__module__]
D = {
    "0324": (Path("C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data/26.03.24/Jump/Jump_No_Tr"), "P60_D1.5", True),
    "0421": (Path("C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data/26.04.21/Position Control"), "P100_D0.75_P100_D2", True),
    "0424": (Path(g18.DATA_0424), "90_0.75_90_2", False),
    "0602": (Path(g18.DATA_0602), "60_0.75_60_2", False),
}
viz = json.load(open(REPO / "code/goal19/phase11/viz_final/viz_index.json"))
vr = {(r["ds"], r["sub"]): r["h_sim"] / r["h_real"] for r in viz}

# ---- fig1: 지령 무릎 궤적 4날짜 -------------------------------------------------
fig, ax = plt.subplots(figsize=(7.5, 4))
for ds, (base, sub, bug) in D.items():
    knee = pd.read_excel(base / sub / "knee.xlsx")
    t = knee["Time"].values - knee["Time"].values[0]
    qd = np.rad2deg(knee["desiredAngle"].values)
    mv = np.where(np.abs(np.diff(qd)) > 1e-4)[0]
    s0, s1 = max(mv[0] - 25, 0), min(mv[-1] + 40, len(t) - 1)
    ax.plot(t[s0:s1] - t[mv[0]], qd[s0:s1], lw=2, label=f"{ds}  (목표 {qd.max():.0f}°)")
ax.set_xlabel("시간 [s]"); ax.set_ylabel("무릎 지령 각도 q2_des [deg]")
ax.set_title("① 날짜마다 로봇에게 시킨 '안무'(지령 궤적)가 다르다")
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(OUT / "fig1_references.png", dpi=115); plt.close(fig)

# ---- fig2: 지령 vs 실측 (관통/미달) ---------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(10, 6.5), sharex=False)
notes = {"0324": "버그: 지령을 23° 지나쳐 관통", "0421": "버그: 목표 미달",
         "0424": "정상: 지령에 근접", "0602": "정상: 부드러운 게인 → 미달(중간영역 체류)"}
for ax, (ds, (base, sub, bug)) in zip(axes.flat, D.items()):
    knee = pd.read_excel(base / sub / "knee.xlsx")
    t = knee["Time"].values - knee["Time"].values[0]
    qd = np.rad2deg(knee["desiredAngle"].values); qm = np.rad2deg(knee["currentAngle"].values)
    mv = np.where(np.abs(np.diff(qd)) > 1e-4)[0]
    s0, s1 = max(mv[0] - 25, 0), min(mv[-1] + 60, len(t) - 1)
    tt = t[s0:s1] - t[mv[0]]
    ax.plot(tt, qm[s0:s1], lw=2, label="실측 각도")
    ax.plot(tt, qd[s0:s1], "--", lw=2, label="지령 각도")
    ax.set_title(f"{ds} {sub}\n{notes[ds]}", fontsize=10)
    ax.set_xlabel("시간 [s]"); ax.set_ylabel("무릎각 [deg]"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
fig.suptitle("② 지령 vs 실측 — dq_des 버그 날짜는 실행이 계획에서 크게 벗어남", y=1.0)
fig.tight_layout(); fig.savefig(OUT / "fig2_cmd_vs_actual.png", dpi=115); plt.close(fig)

# ---- 데이터 수집 (fig3,4,5) ------------------------------------------------------
groups = [(ds, [s for d2, s, isj in list_experiments() if d2 == ds], MS.LOADERS[ds]) for ds in MS.LOADERS]
for ds, tdir, subs in MS.MARCH:
    groups.append((ds, subs, lambda s, _t=tdir: MS.load_march(_t, s)))
rows = []
for ds, subs, loader in groups:
    for sub in subs:
        td = loader(sub)
        rows.append(dict(ds=ds.replace("jump_", "").replace("position_", ""), sub=sub,
                         q2e=np.rad2deg(np.mean(td["q2"][-10:])), r=vr.get((ds, sub), np.nan)))

# fig3: 신전 깊이 vs h_ratio
fig, ax = plt.subplots(figsize=(7.5, 4.6))
for ds in ["0324", "0421", "0424", "0602"]:
    xs = [r["q2e"] for r in rows if r["ds"] == ds]; ys = [r["r"] for r in rows if r["ds"] == ds]
    ax.plot(xs, ys, "o" if ds != "0421" else "X", ms=9, ls="", label=ds + (" (별개 모드)" if ds == "0421" else ""))
ax.axhline(1.0, ls=":", lw=1)
ax.set_xlabel("이륙 시 무릎각 q2 [deg]  (0에 가까울수록 = 다리를 더 폄)")
ax.set_ylabel("full-replay h_ratio (sim/실측)")
ax.set_title("③ 다리를 깊이 펼수록 재현이 어려움 (상관 −0.39, 0421 제외)\n단, 0602는 깊이와 무관(0.02) → 신전은 '증폭기'일 뿐")
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(OUT / "fig3_extension_vs_ratio.png", dpi=115); plt.close(fig)

# fig4: 0424 세션 순서
order = [("60_0.75_60_2", "17:31"), ("60_1.5_60_1.5", "17:57"), ("90_0.75_90_2", "18:17"),
         ("120_2.2_150_2.5", "18:40"), ("120_2.2_200_2.8", "19:46"), ("120_2_120_2", "20:12"),
         ("150_2.2_250_3", "20:32"), ("150_2.2_350_3.5", "20:57"), ("150_2.2_500_4", "21:17")]
ys = [vr[("jump_0424", s)] for s, _ in order]
fig, ax = plt.subplots(figsize=(8.5, 4.2))
ax.plot(range(1, 10), ys, "o-", lw=2, ms=8)
for i, (s, tm) in enumerate(order):
    ax.annotate(tm, (i + 1, ys[i]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
ax.axvspan(3.5, 9.5, alpha=0.08)
ax.set_xlabel("0424 세션 실험 순서 (파일 기록시각 복원)"); ax.set_ylabel("h_ratio")
ax.set_title("④ 4월 세션(4시간) 안에서 뭔가가 변했다 — 순서 상관 −0.63, 3→4번째 사이 계단\n(원인 미확정 · 6월 세션은 같은 게인 구성에서 산포 ±0.014)")
ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(OUT / "fig4_session_order.png", dpi=115); plt.close(fig)

# fig5: 피드백 함량
def kd_of(sub):
    return float(sub.split("_")[-1].lstrip("DP"))
fb = {}
for ds, (base, _, bug) in D.items():
    subs = [p.name for p in base.iterdir() if (p / "knee.xlsx").exists()]
    vals = []
    for sub in subs:
        knee = pd.read_excel(base / sub / "knee.xlsx")
        dq = knee["currentAngleVelocity"].values
        dqd = np.zeros_like(dq) if bug else knee["desiredAngleVelocity"].values
        tau = knee["currentTorque"].values
        m = np.abs(dq) > 1.0
        vals.append(100 * np.abs(kd_of(sub) * (dqd - dq))[m].mean() / max(np.abs(tau)[m].mean(), 1e-6))
    fb[ds] = vals
fig, ax = plt.subplots(figsize=(8, 4.2))
pos = 0; ticks = []; lab = []
for ds in ["0324", "0421", "0424", "0602"]:
    v = fb[ds]; xs = np.arange(pos, pos + len(v))
    tag = " (버그)" if ds in ("0324", "0421") else " (정상)"
    ax.bar(xs, v, label=f"{ds}{tag}  평균 {np.mean(v):.0f}%")
    ticks.append(np.mean(xs)); lab.append(ds + tag); pos += len(v) + 1.2
ax.axhline(100, ls="--", lw=1)
ax.text(0.1, 103, "100% = 토크가 상쇄하는 두 피드백 항의 '작은 차이'로 만들어짐", fontsize=8)
ax.set_xticks(ticks); ax.set_xticklabels(lab)
ax.set_ylabel("무릎 τ 중 속도-피드백 성분 비율 [%]")
ax.set_title("⑤ 버그 날짜의 토크는 '피드백 덩어리' — 얼려서 재생하면 취약")
ax.legend(fontsize=8); ax.grid(alpha=0.3, axis="y")
fig.tight_layout(); fig.savefig(OUT / "fig5_feedback_fraction.png", dpi=115); plt.close(fig)

# fig6: 창 점수(균일) vs full-replay(벌어짐)
best = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
_, per = FR.evaluate(np.array(best["x"]))
name_map = {"jump_0324": "0324", "jump_position_0421": "0421", "jump_0424": "0424", "jump_0602": "0602"}
win = {name_map[k]: np.rad2deg(v["mean"][1]) for k, v in per.items() if k in name_map}
full = {}
for ds in ["0324", "0421", "0424", "0602"]:
    full[ds] = np.mean([abs(1 - r["r"]) * 100 for r in rows if r["ds"] == ds])
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
ks = ["0324", "0421", "0424", "0602"]
axes[0].bar(ks, [win[k] for k in ks])
axes[0].set_title("시험 A: 0.1초 창 (fit 잣대)\n→ 4개 날짜 균일 = 모델은 날짜를 안 가림")
axes[0].set_ylabel("창 무릎각 오차 [deg]")
axes[1].bar(ks, [full[k] for k in ks])
axes[1].set_title("시험 B: 전체 궤적 눈감고 재생 (갤러리 잣대)\n→ 날짜별로 벌어짐 = 데이터 성질의 차이")
axes[1].set_ylabel("full-replay |1 − h_ratio| [%]")
for ax in axes:
    ax.grid(alpha=0.3, axis="y")
fig.tight_layout(); fig.savefig(OUT / "fig6_window_vs_full.png", dpi=115); plt.close(fig)

# fig7: 다리 기하 개념도 (특이점)
fig, axes = plt.subplots(1, 2, figsize=(9, 4.4))
L = 0.25
def draw(ax, q1, q2, dashed=False, note=None):
    h = np.array([0, 0])
    k = h + L * np.array([np.sin(q1), -np.cos(q1)])
    f = k + L * np.array([np.sin(q1 + q2), -np.cos(q1 + q2)])
    st = "--" if dashed else "-"
    ax.plot([h[0], k[0]], [h[1], k[1]], st, lw=3)
    ax.plot([k[0], f[0]], [k[1], f[1]], st, lw=3)
    ax.plot(*f, "o", ms=9)
    return f
for ax, (q2d, title) in zip(axes, [(-95, "굽힌 다리 (중간 영역)\n1° 오차 → 영향 작음"),
                                   (-18, "거의 편 다리 (특이점 근처)\n관절속도→수직속도 변환이 퇴화\n→ 이륙속도가 오차·타이밍에 극도로 민감")]):
    q1 = np.deg2rad(-40 if q2d == -95 else -12)
    f1 = draw(ax, q1, np.deg2rad(q2d))
    f2 = draw(ax, q1, np.deg2rad(q2d + 6), dashed=True)
    ax.annotate("", xy=f2, xytext=f1, arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal"); ax.set_xlim(-0.25, 0.4); ax.set_ylim(-0.55, 0.08)
    ax.grid(alpha=0.25); ax.set_xticklabels([]); ax.set_yticklabels([])
fig.suptitle("③의 원리: 무릎각 +6°(점선)가 만드는 차이 — 편 다리에서 훨씬 민감한 건 '속도 전달'")
fig.tight_layout(); fig.savefig(OUT / "fig7_leg_geometry.png", dpi=115); plt.close(fig)

print("figures ->", OUT)
for f in sorted(OUT.glob("*.png")):
    print("  ", f.name)
