# -*- coding: utf-8 -*-
"""마스터 클래스 시각자료 8종."""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
from pathlib import Path
OUT = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad/p9_explain")

# ── 1. 명시적 스프링 vs 암시적 구속 ─────────────────────────────────────────
m, k, dt, N = 0.1, 1.0e7, 5e-4, 60
x_e, v_e = 0.001, 0.0
xs_e = []
for _ in range(N):
    a = -k * x_e / m
    v_e += a * dt; x_e += v_e * dt
    xs_e.append(x_e)
x_i, v_i = 0.001, 0.0
xs_i = []
for _ in range(N):
    v_i = (v_i - dt * k * x_i / m) / (1 + dt**2 * k / m)
    x_i += v_i * dt
    xs_i.append(x_i)
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.4))
t = np.arange(N) * dt * 1000
ax[0].plot(t, np.array(xs_e) * 1000, label="명시적 스프링 '외력' (explicit)")
ax[0].plot(t, np.array(xs_i) * 1000, label="암시적 구속 (MuJoCo 방식)")
ax[0].set_yscale("symlog", linthresh=1)
ax[0].set_xlabel("t [ms]"); ax[0].set_ylabel("구속 위반 [mm] (symlog)")
ax[0].set_title(f"같은 강성 k=1e7, 같은 dt=0.5ms —\n명시적은 폭발, 암시적은 무조건 안정")
ax[0].legend(fontsize=9); ax[0].grid(alpha=0.3)
ks = np.logspace(3, 9, 100)
ax[1].loglog(ks, 2 / np.sqrt(ks / m) * 1000, label="명시적 안정 한계 dt < 2√(m/k)")
ax[1].axhline(0.5, ls="--", label="우리 시뮬 dt = 0.5 ms")
ax[1].axvline(1e7, ls=":", color="gray")
ax[1].text(1.3e7, 5, "폐루프에 필요한\n강성 영역", fontsize=9)
ax[1].fill_betweenx([1e-3, 1e2], 1e6, 1e9, alpha=0.08)
ax[1].set_xlabel("구속 강성 k [N/m]"); ax[1].set_ylabel("허용 dt [ms]")
ax[1].set_title("명시적 '외력' 방식은 강성↑일수록 dt를 줄여야 함\n(암시적 구속은 이 제한이 없음 → 튜닝 지옥의 정체)")
ax[1].legend(fontsize=9); ax[1].grid(alpha=0.3, which="both")
fig.tight_layout(); fig.savefig(OUT / "m1_implicit.png", dpi=125); plt.close(fig)

# ── 2. 접촉 수식: 임피던스 + 힘-침투 ────────────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.4))
r = np.linspace(0, 1, 200)
for p, mid in [(1, 0.5), (2, 0.5), (5, 0.5)]:
    x = np.clip(r, 0, 1)
    y = np.where(x < mid, 0.5 * (x / mid) ** p, 1 - 0.5 * ((1 - x) / (1 - mid)) ** p)
    d = 0.371 + (0.95 - 0.371) * y
    ax[0].plot(r, d, label=f"power={p}")
ax[0].set_xlabel("침투 / width  (정규화)"); ax[0].set_ylabel("임피던스 d(r)")
ax[0].axhline(0.371, ls=":", color="gray"); ax[0].text(0.02, 0.38, "d0 = imp0 = 0.371 (우리 fit)", fontsize=9)
ax[0].set_title("solimp: 침투가 깊어질수록 구속이 단단해지는 곡선\n(d0→dmax, width 구간에서)")
ax[0].legend(fontsize=9); ax[0].grid(alpha=0.3)
pen = np.linspace(0, 6, 100)
for tc, lab in [(3.0, "3 ms (뻣뻣)"), (6.0, "6.0 ms = 우리 fit"), (12.0, "12 ms (무름)")]:
    ax[1].plot(pen, (1 / (tc * 1e-3) ** 2) * pen * 1e-3 * 3.34, label=f"solref tc={lab}")
ax[1].set_xlabel("침투 깊이 [mm]"); ax[1].set_ylabel("수직력 (개념 스케일) [N]")
ax[1].set_title("solref: k ∝ 1/tc² — 접촉 스프링 강성\n(tc ≥ 2·dt 권장; 작을수록 GRF 채터링 위험)")
ax[1].legend(fontsize=9); ax[1].grid(alpha=0.3)
fig.tight_layout(); fig.savefig(OUT / "m2_contact.png", dpi=125); plt.close(fig)

# ── 3. 마찰 원뿔 ────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 1, figsize=(6.2, 5.6))
th = np.linspace(0, 2 * np.pi, 200)
ax.plot(np.cos(th), np.sin(th), label="elliptic 원뿔 (물리 정확, 방향 무관) — 우리 설정")
sq = np.array([[1, 0], [0, 1], [-1, 0], [0, -1], [1, 0]])
ax.plot(sq[:, 0], sq[:, 1], "--", label="pyramidal 원뿔 (LP 친화, 모서리 왜곡)")
ax.annotate("모서리 방향은 실제보다\n마찰이 √2배 과대", (0.72, 0.72), fontsize=9,
            xytext=(0.95, 1.15), arrowprops=dict(arrowstyle="->"))
ax.set_xlabel("접선력 Fx / (μ·Fn)"); ax.set_ylabel("접선력 Fy / (μ·Fn)")
ax.set_title("마찰 한계면의 단면 (위에서 본 모습)\n안 = 정지 · 경계 = 미끄러짐 시작")
ax.set_aspect("equal"); ax.legend(fontsize=9, loc="lower left"); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(OUT / "m3_cones.png", dpi=125); plt.close(fig)

# ── 4. 접촉 kink와 gradient 세 추정기 ──────────────────────────────────────
th = np.linspace(0, 2, 400)
thc = 1.0
xland = np.where(th < thc, 0.8 * th, 0.8 * thc - 1.6 * (th - thc))   # 접촉 후 기울기 반전
J = (xland - 0.55) ** 2 + 0.02 * th
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.4))
ax[0].plot(th, J, label="진짜 비용 J(θ) — 접촉 전환점에서 꺾임(kink)")
sig = 0.15
Js = np.array([np.mean(np.interp(np.clip(t0 + sig * np.random.default_rng(3).standard_normal(4000), 0, 2), th, J)) for t0 in th])
ax[0].plot(th, Js, label="랜덤 스무딩된 기대 비용 E[J(θ+ε)] — 매끄러움!")
ax[0].axvline(thc, ls=":", color="gray"); ax[0].text(thc + 0.02, max(J) * 0.85, "접촉 발생 경계", fontsize=9)
ax[0].set_xlabel("파라미터 θ (예: 이륙 속도)"); ax[0].set_ylabel("비용 J")
ax[0].set_title("샘플링(0차)이 접촉에 강한 진짜 이유:\n기대값이 불연속을 자동으로 스무딩 (Suh et al. 2022)")
ax[0].legend(fontsize=9); ax[0].grid(alpha=0.3)
rng = np.random.default_rng(5)
pts = np.linspace(0.75, 1.25, 26)
for h_, mk_, lab in [(0.02, "o", "유한차분 h=0.02"), (0.2, "s", "유한차분 h=0.2")]:
    est = [( np.interp(p + h_, th, J) - np.interp(p - h_, th, J)) / (2 * h_) + rng.normal(0, 0.01) for p in pts]
    ax[1].scatter(pts, est, s=18, marker=mk_, label=lab, alpha=0.8)
tg = np.gradient(Js, th)
ax[1].plot(th, tg, lw=2, label="스무딩 비용의 참 기울기 (bundled gradient)")
ax[1].axvline(thc, ls=":", color="gray")
ax[1].set_xlim(0.7, 1.3); ax[1].set_xlabel("θ"); ax[1].set_ylabel("dJ/dθ 추정")
ax[1].set_title("kink 근처의 유한차분: 스텝이 작으면 한쪽 기울기만,\n크면 편향 — 어느 쪽도 '진짜 개선 방향'이 아님")
ax[1].legend(fontsize=8.5); ax[1].grid(alpha=0.3)
fig.tight_layout(); fig.savefig(OUT / "m4_kink.png", dpi=125); plt.close(fig)

# ── 5. 카오스: 이중진자 민감도 지수 성장 ────────────────────────────────────
def dp_deriv(s):
    t1, t2, w1, w2 = s
    d = t2 - t1
    den = 3 - np.cos(2 * d)
    a1 = (w1**2 * np.sin(2 * d) + 2 * w2**2 * np.sin(d) + 3 * 9.81 * np.sin(t1) * 2 - 9.81 * (np.sin(t1 + 2 * d) + np.sin(t1))) / -den
    a2 = (2 * w2**2 * np.sin(2 * d) / 2 + 4 * w1**2 * np.sin(d) + 2 * 9.81 * (np.sin(t2 - 2 * d) * 0 + np.sin(t1) * np.cos(d) - np.sin(t2))) / den
    return np.array([w1, w2, a1, a2])

def rk4(s, dt):
    k1 = dp_deriv(s); k2 = dp_deriv(s + dt / 2 * k1)
    k3 = dp_deriv(s + dt / 2 * k2); k4 = dp_deriv(s + dt * k3)
    return s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)

dt2 = 1e-3; T = 4.0; n = int(T / dt2)
s0 = np.array([1.8, 2.2, 0.0, 0.0]); eps = 1e-8
sa, sb = s0.copy(), s0 + np.array([eps, 0, 0, 0])
sens = []
for i in range(n):
    sa = rk4(sa, dt2); sb = rk4(sb, dt2)
    sens.append(np.linalg.norm(sb - sa) / eps)
fig, ax = plt.subplots(figsize=(8.2, 4.6))
tt = np.arange(n) * dt2
ax.semilogy(tt, sens)
lam = np.polyfit(tt[200:2500], np.log(np.array(sens)[200:2500]), 1)[0]
ax.semilogy(tt, np.exp(lam * tt) * sens[0], "--", label=f"e^(λt), λ ≈ {lam:.1f}/s")
ax.set_xlabel("시간 [s]"); ax.set_ylabel("|∂상태(t)/∂초기조건|  (민감도)")
ax.set_title("카오스의 gradient: 이중진자에서 초기조건 민감도가 지수 폭발\n→ 긴 horizon을 통과한 미분은 쓸 수 없는 숫자가 됨 (우리 full-replay 발산과 동일 물리)")
ax.legend(fontsize=10); ax.grid(alpha=0.3, which="both")
fig.tight_layout(); fig.savefig(OUT / "m5_chaos.png", dpi=125); plt.close(fig)

# ── 6. MPPI 한 사이클 ──────────────────────────────────────────────────────
rng = np.random.default_rng(11)
Nst, Ns, lam_ = 40, 64, 0.15
dtm = 1 / Nst
u_nom = np.zeros(Nst)
target = 1.0

def roll(u):
    x = v = 0.0
    xs = [0.0]
    for ui in u:
        v += ui * dtm; x += v * dtm
        xs.append(x)
    return np.array(xs)

du = rng.normal(0, 3.0, (Ns, Nst))
costs = []
trajs = []
for i in range(Ns):
    xs = roll(u_nom + du[i])
    trajs.append(xs)
    costs.append(50 * (xs[-1] - target) ** 2 + 0.01 * np.sum((u_nom + du[i]) ** 2))
costs = np.array(costs)
w = np.exp(-(costs - costs.min()) / lam_ / costs.std())
w /= w.sum()
u_new = u_nom + (w[:, None] * du).sum(0)
fig, ax = plt.subplots(figsize=(8.6, 4.8))
tt = np.linspace(0, 1, Nst + 1)
for i in range(Ns):
    ax.plot(tt, trajs[i], color="C0", alpha=float(min(0.85, 0.03 + 8 * w[i])), lw=1)
ax.plot(tt, roll(u_new), color="C1", lw=3, label="가중 평균으로 갱신된 궤적 (한 사이클 결과)")
ax.scatter([1], [target], marker="*", s=220, color="C3", zorder=5, label="목표")
ax.set_xlabel("t [s]"); ax.set_ylabel("위치 x")
ax.set_title("MPPI 한 사이클: 노이즈 궤적 64개를 굴려 비용 낮은 것에 큰 가중치\nu ← u + Σ wᵢ·δᵢ,  wᵢ ∝ exp(−Jᵢ/λ)  (진한 파랑 = 좋은 샘플)")
ax.legend(fontsize=9); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(OUT / "m6_mppi.png", dpi=125); plt.close(fig)

# ── 7. 4족 MPC 아키텍처 ────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 5.4)); ax.axis("off")
def box(x, y, w, h, t, fs=9.5):
    ax.add_patch(plt.Rectangle((x, y), w, h, fill=False, lw=1.5))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs)
box(0.02, 0.66, 0.16, 0.24, "상태 추정\n(칼만: IMU+엔코더\n→ CoM 위치·속도)")
box(0.21, 0.66, 0.15, 0.24, "게이트 스케줄러\n(어느 발이 언제\n닿을지 '미리' 결정)")
box(0.39, 0.60, 0.24, 0.34, "Convex MPC (25~100 Hz)\n단일강체(SRB) 모델 + 접촉스케줄 고정\n→ 선형화 → QP → 지면반력 계획\n(horizon ~0.5 s)", 9)
box(0.66, 0.66, 0.15, 0.24, "WBC (0.5~1 kHz)\n반력→관절토크\n+ 스윙발 PD")
box(0.84, 0.66, 0.14, 0.24, "로봇 / 시뮬\n(MuJoCo는 플랜트,\nMPC 모델 아님)")
for x0, x1 in [(0.18, 0.21), (0.36, 0.39), (0.63, 0.66), (0.81, 0.84)]:
    ax.annotate("", (x1, 0.78), (x0, 0.78), arrowprops=dict(arrowstyle="->", lw=1.4))
ax.annotate("", (0.10, 0.66), (0.88, 0.60), arrowprops=dict(arrowstyle="->", lw=1.2, connectionstyle="arc3,rad=0.25"))
ax.text(0.47, 0.47, "센서 피드백 (매 스텝 재계획 = 모델 오차를 피드백이 흡수)", fontsize=9, ha="center")
box(0.02, 0.06, 0.44, 0.26, "우리 프로젝트 대응:\nMPC의 SRB 축소모델 ↔ 우리 CasADi 4-bar 해석식 (훨씬 정밀)\n접촉스케줄 고정 ↔ 우리 phase 분할(스탠스→비행)", 9)
box(0.52, 0.06, 0.46, 0.26, "차이: 그들은 온라인 재계획(피드백으로 오차 흡수)\n우리는 오프라인 최적화 + open-loop 배포(트윈 정밀도가 전부)\n→ 우리가 트윈에 이토록 공을 들이는 이유", 9)
ax.set_title("4족 보행 MPC의 표준 구조 (MIT Cheetah 계열, Di Carlo et al. 2018)")
fig.tight_layout(); fig.savefig(OUT / "m7_mpc.png", dpi=125); plt.close(fig)

# ── 8. 방법 지도 ───────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9.6, 6.2))
pts = [
    ("CasADi NLP (우리 궤적최적화)", 2.9, 0.6, "C0"),
    ("iLQG/DDP (MJPC, 유한차분)", 2.0, 2.6, "C1"),
    ("MJX/Brax 미분가능 시뮬", 3.0, 1.9, "C2"),
    ("MPPI", 0.9, 2.9, "C3"),
    ("Predictive Sampling (MJPC)", 0.6, 2.7, "C4"),
    ("CMA-ES (우리 파라미터 식별)", 0.5, 0.9, "C5"),
    ("CEM", 0.8, 2.0, "C6"),
    ("RL 정책기울기 (PPO 등)", 0.3, 1.4, "C7"),
]
for name, x, y, c in pts:
    ax.scatter(x, y, s=140, color=c, zorder=3)
    ax.annotate(name, (x, y), textcoords="offset points", xytext=(9, 5), fontsize=9.5)
ax.set_xlim(-0.2, 3.6); ax.set_ylim(0, 3.4)
ax.set_xlabel("← 미분 정보 사용 안 함 (0차)                          해석적 미분 사용 →")
ax.set_ylabel("← 오프라인 (한 번 계산)              온라인/실시간 재계획 →")
ax.set_title("최적 제어·정책 방법 지도 — 접촉이 많고 horizon이 길수록 왼쪽이 유리해진다")
ax.grid(alpha=0.3)
ax.axvspan(-0.2, 1.3, alpha=0.05, color="C3")
ax.text(0.5, 0.15, "접촉-강건 지대", fontsize=9, color="C3")
fig.tight_layout(); fig.savefig(OUT / "m8_map.png", dpi=125); plt.close(fig)

print("8 figures saved:", len(list(OUT.glob("m*_*.png"))))
