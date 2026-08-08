# -*- coding: utf-8 -*-
"""_G52_graphs — **전 trial ModeA 그래프 세트** (q · dq · h), p24 vs 신구성 (마라톤G, 08-08).

산출 구조 (trial 폴더별 정리 — 사용자 요청)
    graphs/G52_modeA/
      README.md
      _ALL_summary.png                     전 세션 한 장 요약
      <세션>/_summary.png                  세션 요약 (trial × 채널 배율)
      <세션>/<trial>/00_overview.png       6패널 통합
      <세션>/<trial>/01_q1.png … 05_h.png  채널별 확대

그리기 규약 (perf_plot_guard 6규칙 준수)
  ① 창 = `fs_data.plot_window` (원본 xlsx 스팬)  ② 통짜 (창 중간 리셋 금지)
  ③ 앵커 = 창 시작 실측 1회 · **thm1(모터측)을 실측 q1 에** 대응
  ④ **α: 해당 없음** — ModeA 는 측정 토크를 직접 주입하므로 PD 게인도 α 도 경로에 없다.
     (정본 `fs_compare_plot.alpha_of` / `alphas_for` 는 CL 전용. 아래 plot() 에서 import 하여
      규약 출처를 공유하되, ModeA 경로에서는 호출되지 않는다 — 호출되면 그게 버그다.)
  ⑤ **색 리터럴 금지** (기본 사이클 + get_color 로 sim/real 매칭)  ⑥ 계획선 미표시

★ 패널 구성이 정본과 다른 이유: 정본 6패널은 `q1·q2·dq1·dq2·τ1·τ2` 인데 **ModeA 는 τ 를
  채점할 수 없다**(측정 τ 가 곧 입력이다). 그 두 칸을 **h(점프높이)** 와 **주입 raw** 로 바꾼다.

★ import 위치 주의 (침묵실패 방역): `fs_compare_plot` 은 모듈 최상단에서 `FS_FIXED=1 ·
  FS_TAUOBS=lpf · FS_TC=0.002 · FS_KNEE_REL=0.1 · FS_KNEE_LOAD=1 · FS_TAULIM=20.5` 를
  `setdefault` 로 심는다. 심판 `_G13_board` 는 이 중 **아무것도 설정하지 않는다.**
  ⇒ 최상단에서 import 하면 p24 기준선과 신구성이 **조용히 둘 다 바뀐다.**
  ⇒ 따라서 **롤아웃하는 `dump()` 에서는 절대 import 하지 않고**, 그림만 그리는 `plot()`
     안에서만 import 한다 (거기선 물리가 돌지 않으므로 무해).

h 패널만 이지 후 **+0.6s 연장** 구간을 그린다 (심판 `_G13_board` 와 동일한 자).

사용법
  python _G52_graphs.py dump p24              # 환경변수 없이 = 구 기준선
  <env 세팅> python _G52_graphs.py dump new
  python _G52_graphs.py --plot
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                                          # noqa: E402
import fs_runner as FR                                        # noqa: E402
from _G13_board import real_h                                 # noqa: E402

OUT = HERE / "graphs" / "G52_modeA"
DUMP = HERE / "_G52_dump"
CH = (("q1", "힙 각도 q1 [°]", True), ("q2", "무릎 각도 q2 [°]", True),
      ("dq1", "힙 각속도 dq1 [rad/s]", False), ("dq2", "무릎 각속도 dq2 [rad/s]", False))


def key(s, n):
    return f"{s}__{n}".replace("/", "_").replace(".", "_")


def dump(tag):
    """두 구성을 **별도 프로세스**로 돌려 궤적을 npz 로 남긴다 (전역 캐시 오염 방지)."""
    DUMP.mkdir(exist_ok=True)
    ft = FR.fs_twin(); SP = FR._sess_params()
    n = 0
    for s, p, g, cvt, ho in FD.registry():
        hv = real_h(p)
        try:
            d = FD.load2(p); pw = FD.plot_window(p, d)
            if pw is None:
                continue
            tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1])
            if m.sum() < 30:
                continue
            i0 = int(np.argmax(m))
            t_end = min(tt[m][-1] + 0.6, tt[-1])
            m2 = (tt >= tt[i0]) & (tt <= t_end)
            t = tt[m2] - tt[i0]
            sp = SP.get(s) or dict(bias1=0.0, knee_deep=None)
            if os.environ.get("FS_NOBIAS") == "1":
                sp = dict(sp, bias1=0.0)
            if os.environ.get("FS_NODEEP") == "1":
                sp = dict(sp, knee_deep=None)
            L = FR.rollout_ol_fs_b(ft, t, d["raw1"][m2], d["raw2"][m2],
                                   float(d["q1"][i0]), float(d["q2"][i0]),
                                   float(d["dq1"][i0]), float(d["dq2"][i0]),
                                   float(t[-1] - 0.004), bias1=sp["bias1"],
                                   knee_deep=sp["knee_deep"], fade=True)
            if L is None:
                continue
            ts = tt[m] - tt[i0]
            gi = lambda k: np.interp(ts, L["t"], L[k])
            np.savez_compressed(
                DUMP / f"{key(s, p.name)}__{tag}.npz",
                ts=ts, q1=gi("thm1"), q2=gi("q2"), dq1=gi("dq1"), dq2=gi("dq2"),
                te=np.asarray(L["t"], float), bz=np.asarray(L["bz"], float),
                # 실측·메타는 두 태그에 동일하지만 그리기 편의상 같이 저장
                m_q1=d["q1"][m], m_q2=d["q2"][m], m_dq1=d["dq1"][m], m_dq2=d["dq2"][m],
                r1=d["raw1"][m], r2=d["raw2"][m],
                hv=np.array([hv if hv else np.nan]),
                cvt=np.array([1.0 if cvt else 0.0]), ho=np.array([1.0 if ho else 0.0]))
            n += 1
            print(f"  {s}/{p.name}", flush=True)
        except Exception as ex:
            print(f"  {s}/{p.name}: ERR {type(ex).__name__} {ex}", flush=True)
    print(f"\n덤프 {n} trial → {DUMP.name}/ (tag={tag})")


def _rmse(a, b, deg):
    e = a - b
    return float(np.sqrt(np.mean((np.degrees(e) if deg else e) ** 2)))


def plot():
    # ★ 정본 규약 모듈은 **여기서만** import (모듈 상단 주석 참조 — dump() 오염 방지).
    #   가져오는 것: Malgun Gothic 폰트·unicode_minus 등 rcParams, 그리고 규약 출처 공유.
    #   `CP.alpha_of` / `CP.alphas_for` 는 CL 전용이며 ModeA 경로에서는 호출되지 않는다.
    import fs_compare_plot as CP                     # noqa: F401  (규약 정본 — 그리기 전용)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    assert CP.alpha_of is not None                   # 규약 출처가 살아있는지 확인용
    OUT.mkdir(parents=True, exist_ok=True)
    NAMES = {key(s, p.name): (s, p.name) for s, p, g, cvt, ho in FD.registry()}
    files = sorted(DUMP.glob("*__p24.npz"))
    if not files:
        print("덤프 없음 — 먼저 `dump p24` / `dump new` 를 실행하라"); return
    SESS = {}
    made = 0
    for f in files:
        k = f.name[:-len("__p24.npz")]
        g = DUMP / f"{k}__new.npz"
        if not g.exists():
            continue
        A = np.load(f); B = np.load(g)
        # ★ 폴더명은 **원본 세션/trial 이름 그대로** 쓴다 (키는 파일명 안전용으로 점을 _ 로 바꾼
        #   상태라 `150_2.2_250_3` 가 `150_2_2_250_3` 로 뭉개진다 → registry 로 역매핑).
        sess, trial = NAMES.get(k, (k.split("__")[0].replace("_", "."), k.split("__", 1)[1]))
        tdir = OUT / sess / trial
        tdir.mkdir(parents=True, exist_ok=True)
        ts = A["ts"]; hv = float(A["hv"][0])
        cvt = bool(A["cvt"][0])

        # ── 채널별 RMSE ──
        rm = {}
        for c, _, deg in CH:
            rm[c] = (_rmse(A[c], A["m_" + c], deg), _rmse(B[c], B["m_" + c], deg))
        h24 = float(A["bz"].max()); hnw = float(B["bz"].max())
        eh24 = abs(h24 / hv - 1) * 100 if np.isfinite(hv) else np.nan
        ehnw = abs(hnw / hv - 1) * 100 if np.isfinite(hv) else np.nan
        # 부호 있는 오차 (과대 +, 과소 −) — 제목에 넣는다 (사용자 요청)
        s24 = (h24 / hv - 1) * 100 if np.isfinite(hv) else np.nan
        snw = (hnw / hv - 1) * 100 if np.isfinite(hv) else np.nan
        HT = (f"점프높이  영상 {hv:.3f} m  ·  p24 {h24:.3f} m ({s24:+.1f}%)"
              f"  →  신구성 {hnw:.3f} m ({snw:+.1f}%)"
              if np.isfinite(hv) else
              f"점프높이  영상 실측 없음  ·  p24 {h24:.3f} m  →  신구성 {hnw:.3f} m")
        SESS.setdefault(sess, []).append((trial, rm, (eh24, ehnw), cvt))

        # ── 개별 채널 그림 ──
        def one(ax, c, lab, deg):
            cv = (lambda x: np.degrees(x)) if deg else (lambda x: x)
            ln, = ax.plot(ts, cv(A["m_" + c]), lw=2.2, label="실측")
            col = ln.get_color()                                   # 규약 ⑤: get_color 매칭
            ax.plot(ts, cv(A[c]), lw=1.3, ls="--", label=f"p24  (RMSE {rm[c][0]:.2f})")
            ax.plot(ts, cv(B[c]), lw=1.6, ls="-", alpha=0.9,
                    label=f"신구성 (RMSE {rm[c][1]:.2f})")
            ax.plot(ts[:1], cv(A["m_" + c][:1]), marker="o", ms=5, color=col)  # 앵커점
            ax.set_xlabel("시간 [s]"); ax.set_ylabel(lab); ax.grid(alpha=0.3)
            ax.legend(fontsize=7, loc="best")

        def hpanel(ax):
            # 규약 ⑤: 색 리터럴 금지. 다른 패널의 배색(실측=1번색 · p24=2번색 · 신구성=3번색)과
            #   맞추기 위해 **사이클에서 1번색을 먼저 소비**해 영상 실측에 쓴다 (get_color 패턴).
            c_meas = ax._get_lines.get_next_color()
            ax.plot(A["te"], A["bz"], lw=1.3, ls="--", label=f"p24  최고 {h24:.3f} m")
            ax.plot(B["te"], B["bz"], lw=1.6, label=f"신구성 최고 {hnw:.3f} m")
            if np.isfinite(hv):
                ax.axhline(hv, lw=2.4, ls=":", color=c_meas,
                           label=f"영상 실측 {hv:.3f} m")
            ax.axvspan(ts[0], ts[-1], alpha=0.08, lw=0)            # 채점 창 음영
            ax.set_xlabel("시간 [s]  (채점 창 = 음영, 이후는 h 판독용 +0.6s 연장)")
            ax.set_ylabel("베이스 높이 bz [m]"); ax.grid(alpha=0.3)
            ax.legend(fontsize=7, loc="best")
            ax.set_title(f"점프 높이 — 오차 p24 {eh24:.2f}% → 신 {ehnw:.2f}%", fontsize=9)

        def rawpanel(ax):
            ax.plot(ts, A["r1"], lw=1.2, label="주입 raw1 (힙)")
            ax.plot(ts, A["r2"], lw=1.2, label="주입 raw2 (무릎)")
            ax.set_xlabel("시간 [s]"); ax.set_ylabel("측정 명령 raw [-]")
            ax.grid(alpha=0.3); ax.legend(fontsize=7)
            ax.set_title("ModeA 입력 — 두 구성에 **동일하게** 주입됨", fontsize=9)

        for i, (c, lab, deg) in enumerate(CH, 1):
            fig, ax = plt.subplots(figsize=(7.6, 4.0))
            one(ax, c, lab, deg)
            ax.set_title(f"{sess} / {trial}{'  [CVT]' if cvt else ''} — {lab}\n{HT}", fontsize=9)
            fig.tight_layout(); fig.savefig(tdir / f"{i:02d}_{c}.png", dpi=110); plt.close(fig)
        fig, ax = plt.subplots(figsize=(7.6, 4.0)); hpanel(ax)
        ax.set_title(f"{sess} / {trial}{'  [CVT]' if cvt else ''}\n{HT}", fontsize=9)
        fig.tight_layout(); fig.savefig(tdir / "05_h.png", dpi=110); plt.close(fig)

        # ── 6패널 통합 ──
        fig, AX = plt.subplots(3, 2, figsize=(13.5, 11.4))
        for ax, (c, lab, deg) in zip(AX.flat, CH):
            one(ax, c, lab, deg)
        hpanel(AX.flat[4]); rawpanel(AX.flat[5])
        d24 = np.mean([rm[c][0] for c, _, _ in CH]); dnw = np.mean([rm[c][1] for c, _, _ in CH])
        fig.suptitle(f"{sess} / {trial}{'   [CVT]' if cvt else ''}   ModeA:  p24  vs  신구성\n"
                     f"{HT}\n"
                     f"4채널 평균 RMSE {d24:.3f} → {dnw:.3f}  ({100*(dnw/d24-1):+.1f}%)",
                     fontsize=11)
        fig.tight_layout(rect=(0, 0, 1, 0.945))
        fig.savefig(tdir / "00_overview.png", dpi=105); plt.close(fig)
        made += 1
        if made % 10 == 0:
            print(f"  … {made} trial", flush=True)

    # ── 세션 요약 ──
    for sess, rows in SESS.items():
        fig, AX = plt.subplots(1, 5, figsize=(19, 4.2))
        lbl = [r[0][:16] for r in rows]; x = np.arange(len(rows))
        for ax, (c, lab, _) in zip(AX[:4], CH):
            ax.bar(x - 0.2, [r[1][c][0] for r in rows], width=0.4, label="p24")
            ax.bar(x + 0.2, [r[1][c][1] for r in rows], width=0.4, label="신구성")
            ax.set_xticks(x); ax.set_xticklabels(lbl, rotation=60, ha="right", fontsize=6)
            ax.set_title(lab, fontsize=9); ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=7)
        ax = AX[4]
        ax.bar(x - 0.2, [r[2][0] for r in rows], width=0.4, label="p24")
        ax.bar(x + 0.2, [r[2][1] for r in rows], width=0.4, label="신구성")
        ax.set_xticks(x); ax.set_xticklabels(lbl, rotation=60, ha="right", fontsize=6)
        ax.set_title("점프높이 오차 [%]", fontsize=9); ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=7)
        _ha = np.nanmean([r[2][0] for r in rows]); _hb = np.nanmean([r[2][1] for r in rows])
        fig.suptitle(f"{sess} — trial 별 ModeA RMSE (낮을수록 좋음)   ·   "
                     f"점프높이 오차 평균 p24 {_ha:.2f}% → 신구성 {_hb:.2f}%", fontsize=12)
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        fig.savefig(OUT / sess / "_summary.png", dpi=105); plt.close(fig)

    # ── 전체 요약 ──
    order_all = sorted(SESS, key=lambda s: (any(r[3] for r in SESS[s]), s))
    order_nc = [s for s in order_all if not any(r[3] for r in SESS[s])]

    def all_fig(order, fname, note):
        fig, AX = plt.subplots(1, 5, figsize=(19, 4.6))
        x = np.arange(len(order))
        for ax, (c, lab, _) in zip(AX[:4], CH):
            p = [np.mean([r[1][c][0] for r in SESS[s]]) for s in order]
            q = [np.mean([r[1][c][1] for r in SESS[s]]) for s in order]
            ax.bar(x - 0.2, p, width=0.4, label="p24")
            ax.bar(x + 0.2, q, width=0.4, label="신구성")
            ax.set_xticks(x); ax.set_xticklabels(order, rotation=60, ha="right", fontsize=7)
            ax.set_title(f"{lab}    {np.mean(p):.2f} → {np.mean(q):.2f}"
                         f" ({100*(np.mean(q)/np.mean(p)-1):+.0f}%)", fontsize=9)
            ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=8)
        ax = AX[4]
        p = [np.nanmean([r[2][0] for r in SESS[s]]) for s in order]
        q = [np.nanmean([r[2][1] for r in SESS[s]]) for s in order]
        ax.bar(x - 0.2, p, width=0.4, label="p24"); ax.bar(x + 0.2, q, width=0.4, label="신구성")
        ax.set_xticks(x); ax.set_xticklabels(order, rotation=60, ha="right", fontsize=7)
        ax.set_title(f"점프높이 오차 [%]    {np.nanmean(p):.2f} → {np.nanmean(q):.2f}"
                     f" ({100*(np.nanmean(q)/np.nanmean(p)-1):+.0f}%)", fontsize=9)
        ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=8)
        a = np.nanmean([r[2][0] for s in order for r in SESS[s]])
        b = np.nanmean([r[2][1] for s in order for r in SESS[s]])
        fig.suptitle(f"전 세션 ModeA 평균 RMSE — p24 vs 신구성   {note}   ·   "
                     f"점프높이 오차 {a:.2f}% → {b:.2f}%", fontsize=13)
        fig.tight_layout(rect=(0, 0, 1, 0.92))
        fig.savefig(OUT / fname, dpi=110); plt.close(fig)

    all_fig(order_all, "_ALL_summary.png", "(맨 오른쪽 26.04.29 = CVT)")
    all_fig(order_nc, "_ALL_summary_noCVT.png",
            "(**CVT 제외** — CVT 가 스케일을 압도해 별도 장으로 분리)")
    order = order_all

    # ── README ──
    tot = sum(len(v) for v in SESS.values())
    md = ["# G52 — 전 trial ModeA 그래프 세트 (q · dq · h)", "",
          "**p24 → 신구성** (`canon_cap 3.8/2.6` · `MASS 3.28` · `PRESLIDE 0.86,0.85,0.02,1.0` · 인공층 전멸)", "",
          f"trial {tot} 개 · PNG {tot*6 + len(SESS) + 1} 장", "",
          "## 폴더 구조", "```", "_ALL_summary.png              전 세션 요약",
          "<세션>/_summary.png           세션 내 trial 별 막대",
          "<세션>/<trial>/00_overview.png  6패널 통합",
          "<세션>/<trial>/01_q1.png … 05_h.png", "```", "",
          "## 읽는 법",
          "- **실측**(굵은 실선) · **p24**(파선) · **신구성**(실선). 시작점의 ● = 창 시작 실측 앵커.",
          "- h 패널만 채점 창(음영) 뒤로 **+0.6s 연장** — 최고점을 직접 읽기 위함 (심판과 동일).",
          "- 6번째 패널 = ModeA 입력(측정 명령 raw). **두 구성에 동일하게 주입**되므로 한 쌍만 표시.", "",
          "## 세션별 평균 (4채널 RMSE 평균 · 점프높이 오차%)", "",
          "| 세션 | trial | p24 4ch | 신 4ch | 변화 | p24 h% | 신 h% |", "|---|---|---|---|---|---|---|"]
    for s in order:
        rs = SESS[s]
        a = np.mean([np.mean([r[1][c][0] for c, _, _ in CH]) for r in rs])
        b = np.mean([np.mean([r[1][c][1] for c, _, _ in CH]) for r in rs])
        ha = np.nanmean([r[2][0] for r in rs]); hb = np.nanmean([r[2][1] for r in rs])
        md.append(f"| {s}{' **(CVT)**' if rs[0][3] else ''} | {len(rs)} | {a:.3f} | {b:.3f} | "
                  f"**{100*(b/a-1):+.1f}%** | {ha:.2f} | {hb:.2f} |")
    (OUT / "README.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\n★ 완료: {made} trial · {OUT}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--plot":
        plot()
    else:
        dump(sys.argv[2] if len(sys.argv) > 2 else "x")
