# -*- coding: utf-8 -*-
"""render_kit — 시각화 정본 (GIF 오버레이 + 트라이얼 비교 그래프).

① GIF 텍스트 오버레이 표준 (g22_cl_results 렌더러 정본화, 2026-07-13):
  trial(백) → t[ms] → base_z[cm](시안) → hip[deg](초록) → knee[deg](주황)
  → h_sim[m](노랑) → h_real[m](분홍) → [CVT면] l_i[mm](주황) → [있으면] extra
누락 이력: g22_p19_results/gif (hip/knee/h_sim/h_real 없음), gif_v2 (hip/knee 없음)
— 렌더러마다 오버레이를 손으로 다시 쓰다 생긴 드리프트. 이 모듈이 단일 출처다.

② 트라이얼 비교 그래프 표준 = fig_trial_std (2026-07-13 사용자 지시):
  출처: cvt_results_v2.fig_trial (0429 png_v2, 사용자 승인 규격) — 2×3 패널
  [q(deg)+q_des | dq1 hip | dq2 crank / hip τ | knee(crank) τ | GRF].
  새 그래프 포맷 발명 금지 — sim vs real 트라이얼 그림은 전부 이 함수로.
lint_footguns 훅이 _draw_text_outlined / 자체 fig 직접 작성을 경고한다.
"""
import numpy as np

Y0, DY, X0 = 10, 30, 10


def draw_overlay(dr, MA, label, t_ms, bz_cm=None, hip_deg=None, knee_deg=None,
                 h_sim=None, h_real=None, l_i_mm=None, extra=None):
    """표준 오버레이. dr=ImageDraw, MA=goal18_CANONICAL make_anim 모듈.

    필드가 None이면 그 줄은 생략하되, 표준 7필드(hip/knee/h_sim/h_real 포함)를
    가진 렌더가 정본이다 — 생략은 데이터가 정말 없을 때만.
    """
    y = Y0

    def line(txt, fill="white"):
        nonlocal y
        MA._draw_text_outlined(dr, (X0, y), txt, MA.FONT, fill=fill)
        y += DY

    line(f"trial = {label}", "white")
    line(f"t = {t_ms:>6.0f} ms")
    if bz_cm is not None:
        line(f"base_z = {bz_cm:>5.1f} cm", "#00ffff")
    if hip_deg is not None:
        line(f"hip  = {hip_deg:+6.1f}", "#00ff00")
    if knee_deg is not None:
        line(f"knee = {knee_deg:+6.1f}", "#ff8800")
    if h_sim is not None:
        line(f"h_sim  = {h_sim:.3f} m", "#ffff00")
    if h_real is not None and h_real == h_real:
        line(f"h_real = {h_real:.3f} m", "#ff66ff")
    if l_i_mm is not None:
        line(f"l_i = {l_i_mm:.1f} mm", "#ffaa00")
    if extra:
        line(extra, "#cccccc")


def fig_trial_std(out, name, d, L, m, tag, l_i, tp1, tp2, o1q=0.0, o2q=0.0,
                  model_tag="", cl_note=" · 실효게인 α+클립 반영"):
    """트라이얼 비교 그래프 표준 — cvt_results_v2.fig_trial(png_v2 규격) 이식본.

    d: 실측 dict (t/q1/q2/dq1/dq2[/qd1/qd2/grf_real]) · L: sim 로그 (t/q1/q2/dq1/dq2/
    sh1/sh2/grf) · m: metrics2 dict (q2/dq2/h/h_real) · tp1/tp2: 실측 축토크 (a_hat 변환,
    SD 시프트 적용본 — 호출측 계산) · o1q/o2q: sim에 가산된 q 오프셋 (표시 시 제거).
    레이아웃/라벨/색은 원본 그대로 유지할 것 (사용자 승인 규격 — 변경 금지).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    t = d["t"]
    mk = (L["t"] >= -0.02) & (L["t"] <= t[-1] + 0.01)
    fig, ax = plt.subplots(2, 3, figsize=(14.5, 7))
    ax[0, 0].plot(L["t"][mk], np.degrees(L["q1"][mk] - o1q), "C0", lw=1.3, label="q1 sim")
    ax[0, 0].plot(t, np.degrees(d["q1"]), "C1", lw=1.3, label="q1 real")
    ax[0, 0].plot(L["t"][mk], np.degrees(L["q2"][mk] - o2q), "C0", lw=1.3, label="q2(crank) sim")
    ax[0, 0].plot(t, np.degrees(d["q2"]), "C1", lw=1.3, label="q2 real")
    if tag == "CL" and "qd1" in d:
        ax[0, 0].plot(t, np.degrees(d["qd1"]), "C2--", lw=1.1, label="q_des")
        ax[0, 0].plot(t, np.degrees(d["qd2"]), "C2--", lw=1.1, label="_nolegend_")
    ax[0, 0].set_ylabel("q [deg]")
    ax[0, 1].plot(L["t"][mk], L["dq1"][mk], lw=1.3, label="sim")
    ax[0, 1].plot(t, d["dq1"], lw=1.3, label="real")
    ax[0, 1].set_ylabel("dq1 hip [rad/s]")
    ax[0, 2].plot(L["t"][mk], L["dq2"][mk], lw=1.3, label="sim")
    ax[0, 2].plot(t, d["dq2"], lw=1.3, label="real")
    ax[0, 2].set_ylabel("dq2 crank [rad/s]")
    ax[1, 0].plot(L["t"][mk], L["sh1"][mk], lw=1.3, label="sim shaft tau")
    ax[1, 0].plot(t, tp1, lw=1.3, label="real tau (a_hat)")
    ax[1, 0].set_ylabel("hip tau [Nm]")
    ax[1, 1].plot(L["t"][mk], L["sh2"][mk], lw=1.3, label="sim shaft tau")
    ax[1, 1].plot(t, tp2, lw=1.3, label="real tau (a_hat)")
    ax[1, 1].set_ylabel("knee(crank) tau [Nm]")
    ax[1, 2].plot(L["t"][mk], L["grf"][mk], lw=1.3, label="sim")
    if d.get("grf_real") is not None:
        ax[1, 2].plot(t, d["grf_real"], lw=1.3, label="real")
    ax[1, 2].set_ylabel("GRF z [N]")
    for a_ in ax.flat:
        a_.grid(alpha=0.3); a_.legend(fontsize=7); a_.set_xlabel("t [s]")
    extra = cl_note if tag == "CL" else ""
    h_txt = ""
    if np.isfinite(m.get("h", float("nan"))) and np.isfinite(m.get("h_real", float("nan"))):
        h_txt = f" · h_sim {m['h']:.2f} / h_real {m['h_real']:.2f} m"
    fig.suptitle(f"{name} [{tag} {model_tag}, l_i={l_i*1000:.1f}mm{extra}] — "
                 f"q2 RMSE {m['q2']:.3f} rad · dq2 {m['dq2']:.2f}{h_txt}")
    fig.tight_layout()
    fig.savefig(out, dpi=100)
    plt.close(fig)
