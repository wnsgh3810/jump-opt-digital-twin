# -*- coding: utf-8 -*-
"""_G80_trend — 전수 슬립 결과에서 **게인·세션·CVT별 경향**을 뽑는다 (마라톤G, 08-09).

무엇을 묻나
  ① 푸시 슬립이 게인(kp)에 따라 어떻게 변하나 — 세게 밀수록 더 미끄러지나?
  ② 세션(=날짜·바닥 상태)별로 다른가 — 같은 게인인데 날짜마다 다르면 바닥/마찰 문제다.
  ③ CVT(0429) 가 무변속과 다른가.
  ④ 구름 대 슬립의 비율 — 발이 "굴러서" 간 건지 "미끄러져서" 간 건지.

QC 경고가 붙은 trial 은 **표시는 하되 회귀에서 뺀다** (버리지 않는다 — 왜 걸렸는지가 정보다).
색은 지정하지 않는다 (프로젝트 규약: matplotlib auto cycle).

※ 성능 그래프 규약(fs_compare_plot / plot_window)은 여기 적용되지 않는다.
   그 규약은 **sim vs real 시계열 비교**(ModeA·CL 보드)를 위한 것이고,
   이 파일은 시계열이 아니라 **측정된 스칼라(구간 슬립)의 산점도·회귀**다.
   창(window) 개념 자체가 없다 — 구간 경계는 이미 fs_slipmeas 가 데이터 세그먼트로 정했다.

CLI: python _G80_trend.py
"""
# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------
import os, sys, io, json, re
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = Path(os.environ.get("G79_OUT",
                          (LEGACY_ROOT + "/G_slip_all_260809"))) / "05_trend"
SEGS = ("하강전반", "하강후반", "바닥유지", "푸시~이륙")
CVT_SESS = {"26.04.29"}

try:
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
except Exception:
    pass


def gains(trial):
    """폴더 라벨 = 실제 커맨드 게인 (데이터 사전 확정). kp1, kd1, kp2, kd2 를 뽑는다."""
    n = [float(x) for x in re.findall(r"[\d.]+", trial.replace("P", "").replace("D", ""))]
    return (n + [np.nan] * 4)[:4]


def load():
    p = HERE / "_G72_slipall.json"
    r = json.load(io.open(p, encoding="utf-8")) if p.exists() else []
    return list(r.values()) if isinstance(r, dict) else r


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = [r for r in load() if r.get("ok")]
    if not res:
        raise SystemExit("측정 결과 없음 — fs_slipmeas 먼저 실행")
    rows = []
    for r in res:
        kp1, kd1, kp2, kd2 = gains(r["trial"])
        rows.append(dict(sess=r["sess"], trial=r["trial"], kp1=kp1, kd1=kd1, kp2=kp2, kd2=kd2,
                         cvt=r["sess"] in CVT_SESS, qc=bool(r.get("qc")),
                         **{s: r["seg"][s]["slip"] for s in SEGS},
                         push_dx=r["seg"]["푸시~이륙"]["dx"],
                         push_roll=r["seg"]["푸시~이륙"]["roll"],
                         tot=r["seg"]["전체"]["slip"], scale=r["scale"]))
    ss = sorted({d["sess"] for d in rows})
    good = [d for d in rows if not d["qc"]]
    print(f"측정 {len(rows)} · QC무경고 {len(good)}")

    # ── 그림1: 세션별 구간 슬립 분포
    fig, ax = plt.subplots(figsize=(13, 5.6))
    w = 0.8 / len(SEGS)
    for i, s in enumerate(SEGS):
        # QC 경고는 **버리지 않고 x 표시**로 남긴다 (왜 걸렸는지가 정보다)
        pos = {True: ([], []), False: ([], [])}
        for j, se in enumerate(ss):
            for d in [d for d in rows if d["sess"] == se]:
                pos[d["qc"]][0].append(j + (i - len(SEGS) / 2 + 0.5) * w)
                pos[d["qc"]][1].append(d[s])
        h = ax.scatter(pos[False][0], pos[False][1], s=28, label=s, alpha=0.9)
        # 같은 구간은 같은 색으로 묶는다 — 색은 지정하지 않고 **방금 그린 것에서 받아온다**
        # (프로젝트 규약: 색 리터럴 금지, get_color 패턴만 허용)
        ax.scatter(pos[True][0], pos[True][1], s=30, marker="x", alpha=0.55,
                   color=h.get_facecolor()[0])
    ax.scatter([], [], marker="x", s=30, label="↑ x 표시 = QC 경고(참고용)")
    ax.axhline(0, lw=0.8)
    ax.set_xticks(range(len(ss))); ax.set_xticklabels(ss, rotation=20)
    ax.set_ylabel("슬립 [mm]  (+ = 화면 오른쪽)")
    ax.set_title("세션·구간별 슬립 — 푸시가 지배하는가")
    ax.legend(ncol=4, fontsize=9); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(OUT / "trend1_세션구간.png", dpi=110); plt.close(fig)

    # ── 그림2: 푸시 슬립 vs kp1 (세션별)
    fig, ax = plt.subplots(figsize=(9, 5.6))
    for se in ss:
        v = [d for d in rows if d["sess"] == se and np.isfinite(d["kp1"])]
        if not v:
            continue
        ax.scatter([d["kp1"] for d in v], [d["푸시~이륙"] for d in v],
                   s=52, label=se, marker="^" if se in CVT_SESS else "o")
    g = [d for d in good if np.isfinite(d["kp1"])]
    if len(g) >= 4:
        a, b = np.polyfit([d["kp1"] for d in g], [d["푸시~이륙"] for d in g], 1)
        xr = np.linspace(min(d["kp1"] for d in g), max(d["kp1"] for d in g), 10)
        rr = np.corrcoef([d["kp1"] for d in g], [d["푸시~이륙"] for d in g])[0, 1]
        ax.plot(xr, a * xr + b, ls="--", lw=1.6,
                label=f"회귀(QC무경고 {len(g)}) {a:+.3f}mm/kp · r={rr:+.2f}")
    ax.axhline(0, lw=0.8); ax.set_xlabel("kp1 (hip 비례게인)")
    ax.set_ylabel("푸시~이륙 슬립 [mm]")
    ax.set_title("게인이 셀수록 더 미끄러지는가 (△=CVT)")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(OUT / "trend2_게인.png", dpi=110); plt.close(fig)

    # ── 그림3: 구름 vs 슬립 (푸시)
    fig, ax = plt.subplots(figsize=(7.4, 6.4))
    for se in ss:
        v = [d for d in rows if d["sess"] == se]
        ax.scatter([d["push_roll"] for d in v], [d["푸시~이륙"] for d in v],
                   s=52, label=se, marker="^" if se in CVT_SESS else "o")
    lim = max(abs(np.array([d["push_roll"] for d in rows] + [d["푸시~이륙"] for d in rows])))
    ax.plot([-lim, lim], [-lim, lim], ls=":", lw=1)
    ax.axhline(0, lw=0.8); ax.axvline(0, lw=0.8)
    ax.set_xlabel("푸시 구름 r·Δθ [mm]"); ax.set_ylabel("푸시 슬립 [mm]")
    ax.set_title("발은 굴러서 갔나 미끄러져서 갔나")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(OUT / "trend3_구름대슬립.png", dpi=110); plt.close(fig)

    # ── 표
    L = ["# 슬립 경향 요약\n"]
    L.append(f"\n측정 {len(rows)} trial · QC 무경고 {len(good)}\n")
    L.append("\n## 세션별 중앙값 [mm]\n\n| 세션 | n | 하강전반 | 하강후반 | 바닥유지 | 푸시~이륙 | 전체 |\n")
    L.append("|---|---|---|---|---|---|---|\n")
    for se in ss:
        v = [d for d in rows if d["sess"] == se]
        L.append(f"| {se} | {len(v)} | " + " | ".join(
            f"{np.median([d[s] for d in v]):+.1f}" for s in SEGS)
            + f" | {np.median([d['tot'] for d in v]):+.1f} |\n")
    tot = [abs(d["tot"]) for d in rows if abs(d["tot"]) > 1e-6]
    frac = [abs(d["푸시~이륙"]) / abs(d["tot"]) for d in rows if abs(d["tot"]) > 1e-6]
    L.append(f"\n## 푸시 지배도\n\n전체 슬립 중 푸시 구간 비중 중앙값 = **{np.median(frac)*100:.0f}%**"
             f" (n={len(frac)})\n")
    io.open(OUT / "요약.md", "w", encoding="utf-8").write("".join(L))
    print(f"저장 → {OUT}")


if __name__ == "__main__":
    main()
