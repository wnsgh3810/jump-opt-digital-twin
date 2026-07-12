# -*- coding: utf-8 -*-
"""render_kit — GIF 텍스트 오버레이 정본 (모든 렌더러가 이걸 사용해야 함).

표준 필드/순서/색 (g22_cl_results 렌더러 = 사실상 표준을 정본화, 2026-07-13):
  trial(백) → t[ms] → base_z[cm](시안) → hip[deg](초록) → knee[deg](주황)
  → h_sim[m](노랑) → h_real[m](분홍) → [CVT면] l_i[mm](주황) → [있으면] extra
누락 이력: g22_p19_results/gif (hip/knee/h_sim/h_real 없음), gif_v2 (hip/knee 없음)
— 렌더러마다 오버레이를 손으로 다시 쓰다 생긴 드리프트. 이 모듈이 단일 출처다.
lint_footguns 훅이 _draw_text_outlined 직접 사용을 경고한다.
"""

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
