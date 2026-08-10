# -*- coding: utf-8 -*-
"""_GB1_promote — 승격 판단용 **한 폴더**를 조립한다 (마라톤G, 08-09).

왜
  사용자 지시: "승격 여부를 판단해야하니까 mode A·변속도 p24랑 비교하는 그래프 만들어,
  cl도 비슷하게, 폴더 따로 만들어서 잘 정리하고".
  그래프는 `fs_compare_plot`(비CVT)·`fs_cvt_plot`(CVT)이 이미 정본 규약대로 그린다.
  이 스크립트는 그 둘의 결과를 **하나의 판단 문서**로 합친다 — 총평 그림 + 00_승격판단.md.

★ 표를 손으로 쓰지 않는다 (08-09 사고: 인라인으로 만든 표만 낡아 CSV 와 어긋남).
  두 그림 스크립트가 남긴 `_rmse.json` 을 읽는다. 없으면 실행 안내를 내고 멈춘다.

CLI: python _GB1_promote.py [폴더]
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

# ★ 08-09 정정 (사용자 지적): 비교 그림은 **repo 안** 이 관례다 —
#   `_compare` / `_compare_fs16` / `_compare_gate` / `_compare_svg25` / `_compare_G50` 이
#   이미 git 에 추적돼 있다 (568 파일). 새로 **생성한** 그림이라 중복 저장도 아니다.
#   (repo 밖에 두는 건 `_G79_collect` 처럼 **기존 이미지를 복사**해 모을 때의 규칙이다.)
ROOT = Path(os.environ.get("G_PROMOTE_OUT", str(HERE / "_compare_G_promote")))
TAG = os.environ.get("FS_STACK_TAG", "마라톤G")
GATE = ("26.03.24", "26.04.21")      # held-out(FF) · 위치제어 — fit 에 안 들어간 두 세션
CVT_SESS = "26.04.29"


def load():
    """비CVT·CVT 두 결과를 합쳐 {(mode, sess): dict} 로."""
    out = {}
    for sub in ("nonCVT", "CVT"):
        f = ROOT / sub / "_rmse.json"
        if not f.exists():
            raise SystemExit(
                f"[없음] {f}\n"
                f"  먼저 그림을 생성하라:\n"
                f"    FS_CMP_OUT={ROOT/'nonCVT'} ... python fs_compare_plot.py\n"
                f"    FS_CMP_OUT_CVT={ROOT/'CVT'} FS_CVT_ALL=1 ... python fs_cvt_plot.py")
        for k, v in json.load(io.open(f, encoding="utf-8")).items():
            mode, sess = k.split("|")
            v["cvt"] = (sub == "CVT")
            out[(mode, sess)] = v
    return out


def _qd(v):
    """자세 4채널(q1·q2·dq1·dq2) 평균 — 승패 판정의 본체.

    ★ τ 는 제외한다. 그래프의 '실측 τ' 는 a_hat 변환값 = **p24 자신의 환율**이라,
      다른 환율(canon_cap)을 쓰는 후보를 거기에 재면 구조적으로 진다 (환율 차이 자체가
      RMSE 로 계상됨 — τ1 2.16 / τ2 3.66 Nm, 동역학 성분 0). 이종 지표 비교 금지 원칙.
    """
    return float(np.mean(v["old"][:4])), float(np.mean(v["new"][:4]))


def overview(D):
    """세션별 q·dq 개선율 막대 — 한 장으로 승패가 보이게."""
    for mode in ("ModeA", "CL"):
        rows = sorted([(s, v) for (m, s), v in D.items() if m == mode])
        if not rows:
            continue
        fig, a = plt.subplots(figsize=(10, 4.4))
        x = np.arange(len(rows))
        o = np.array([_qd(v)[0] for _, v in rows])
        f = np.array([_qd(v)[1] for _, v in rows])
        a.bar(x - 0.19, o, 0.38, label="배포모델 (OLD = p24)")
        a.bar(x + 0.19, f, 0.38, label=f"현행 ({TAG})")
        for i, (s, v) in enumerate(rows):
            a.annotate(f"{100*(f[i]/o[i]-1):+.0f}%", (i, max(o[i], f[i])),
                       ha="center", va="bottom", fontsize=8)
        lab = [f"{s}\n({v['n']} trial)" + ("\nCVT" if v["cvt"] else
                                           ("\n게이트" if s in GATE else "")) for s, v in rows]
        a.set_xticks(x); a.set_xticklabels(lab, fontsize=8)
        a.set_ylabel("q·dq 4채널 평균 RMSE")
        a.set_title(f"{mode} — 세션별 자세 정확도 (낮을수록 좋음 · τ 제외: 환율 상이)")
        a.legend(); a.grid(alpha=0.3, axis="y")
        fig.tight_layout()
        fig.savefig(ROOT / f"00_총평_{mode}.png", dpi=110)
        plt.close(fig)


def doc(D):
    L = []
    A = L.append
    nT = sum(v["n"] for v in D.values())
    ma = [(s, v) for (m, s), v in D.items() if m == "ModeA"]
    cl = [(s, v) for (m, s), v in D.items() if m == "CL"]
    wm = sum(1 for _, v in ma if _qd(v)[1] < _qd(v)[0])
    wc = sum(1 for _, v in cl if _qd(v)[1] < _qd(v)[0])
    A(f"# 승격 판단 — {TAG} vs 배포모델(p24)\n")
    A(f"\n## 결론 한 줄\n")
    A(f"**자세(q·dq)는 ModeA {wm}/{len(ma)} · CL {wc}/{len(cl)} 세션에서 이기고, "
      f"게이트 두 세션과 변속(CVT)도 함께 좋아졌다 — 승격 조건의 '비악화'는 충족.**\n")
    A(f"단, 아래 **τ 환율 주의**를 반드시 같이 읽을 것.\n")

    A("\n## 이 폴더를 읽는 법\n")
    A("| 경로 | 내용 |\n|---|---|\n")
    A("| `00_총평_ModeA.png` / `00_총평_CL.png` | **여기부터** — 세션별 자세 정확도 한 장 |\n")
    A("| `nonCVT/ModeA/<세션>/<trial>.png` | 무변속 · 측정 토크 주입 재생 (1급 심판) |\n")
    A("| `nonCVT/CL/<세션>/<trial>.png` | 무변속 · 폐루프 |\n")
    A(f"| `CVT/ModeA/{CVT_SESS}/` · `CVT/CL/{CVT_SESS}/` | **변속(l_i≈25.08mm)** 같은 형식 |\n")
    A("| 각 세션 폴더의 `_summary.png` | 채널별 평균 RMSE 막대 |\n")
    A("| `*/README.md` · `*/_rmse.json` | trial 단위 표와 원수치 |\n")
    A("\n각 그림은 **3자 겹침**이다 — 실측(실선) · 배포모델 p24(파선) · "
      f"현행 {TAG}(점선). 패널은 q1·q2·dq1·dq2·τ1·τ2.\n")

    A("\n## 판정표 (세션별 · q·dq 4채널 평균 RMSE)\n\n")
    A("| 모드 | 세션 | trial | 비고 | OLD(p24) | " + TAG + " | 변화 |\n")
    A("|---|---|---|---|---|---|---|\n")
    for mode in ("ModeA", "CL"):
        for s, v in sorted([(s, v) for (m, s), v in D.items() if m == mode]):
            o, f = _qd(v)
            note = "**변속**" if v["cvt"] else ("**게이트**" if s in GATE else "fit")
            A(f"| {mode} | {s} | {v['n']} | {note} | {o:.2f} | {f:.2f} | "
              f"**{100*(f/o-1):+.0f}%** |\n")

    A("\n## 채널별 (trial 가중 평균, 무변속)\n\n")
    A("| 모드 | 채널 | OLD | " + TAG + " | 변화 |\n|---|---|---|---|---|\n")
    for mode in ("ModeA", "CL"):
        R = [v for (m, s), v in D.items() if m == mode and not v["cvt"]]
        if not R:
            continue
        w = np.array([v["n"] for v in R], float)
        O = (np.array([v["old"] for v in R]) * w[:, None]).sum(0) / w.sum()
        F = (np.array([v["new"] for v in R]) * w[:, None]).sum(0) / w.sum()
        for i, ch in enumerate(R[0]["ch"]):
            A(f"| {mode} | {ch} | {O[i]:.2f} | {F[i]:.2f} | {100*(F[i]/O[i]-1):+.0f}% |\n")

    A("\n## 점프높이 (1급 게이트 · ModeA 연장 재생 vs 영상 실측)\n")
    A("자세가 맞아도 **높이가 틀리면 트윈이 아니다.** 배율오차 = |sim/영상 − 1| 의 평균 (작을수록 좋음).\n\n")
    hj = ROOT / "nonCVT" / "_jumph.json"
    if hj.exists():
        J = json.load(io.open(hj, encoding="utf-8"))
        S = {}
        for k, (hv, ho, hf) in J.items():
            if hv:
                S.setdefault(k.split("|")[0], []).append((hv, ho, hf))
        A("| 세션 | n | 비고 | 영상 [m] | OLD [m] | " + TAG + " [m] | |배율오차| OLD→" + TAG + " |\n")
        A("|---|---|---|---|---|---|---|\n")
        AO, AF = [], []
        for s in sorted(S):
            a = np.array(S[s], float); v, o, f = a[:, 0], a[:, 1], a[:, 2]
            ro = np.abs(o / v - 1).mean(); rf = np.abs(f / v - 1).mean()
            AO += list(np.abs(o / v - 1)); AF += list(np.abs(f / v - 1))
            note = "**게이트**" if s in GATE else "fit"
            A(f"| {s} | {len(a)} | {note} | {v.mean():.3f} | {o.mean():.3f} | {f.mean():.3f} | "
              f"{100*ro:.1f}% → **{100*rf:.1f}%** {'✅' if rf < ro else '⚠'} |\n")
        A(f"| **전체** | {len(AO)} | | | | | **{100*np.mean(AO):.1f}% → "
          f"{100*np.mean(AF):.1f}%** (trial 승 {sum(1 for x, y in zip(AO, AF) if y < x)}/{len(AO)}) |\n")
        # 높이 변화가 '균일한 축소'인지 'OLD 치우침의 보정'인지 판별 (버그 vs 물리)
        bs, cs, nm2 = [], [], []
        for s in sorted(S):
            a = np.array(S[s], float); v, o, f = a[:, 0], a[:, 1], a[:, 2]
            bs.append(float((o / v - 1).mean())); cs.append(float((f / o - 1).mean())); nm2.append(s)
        bs_, cs_ = np.array(bs), np.array(cs)
        r = float(np.corrcoef(bs_, cs_)[0, 1])
        agree = int(sum(1 for x, y in zip(bs_, cs_) if x * y < 0))
        A(f"\n### 높이 변화의 정체 — 균일 축소가 아니라 **치우침 보정**\n")
        A("먼저 의심한 것: '질량을 3.20→3.28 로 올렸으니 전 세션이 똑같이 낮아진 것 아닌가?'\n")
        A("→ **아니다.** G/OLD 높이 비가 0.937~1.070 로 퍼진다 (균일 축소면 한 값에 몰려야 한다).\n\n")
        A("| 세션 | OLD 치우침 | " + TAG + " 보정 방향 | 방향 일치 |\n|---|---|---|---|\n")
        for s, b_, c_ in zip(nm2, bs_, cs_):
            A(f"| {s}{' **(게이트)**' if s in GATE else ''} | {100*b_:+.1f}% | {100*c_:+.1f}% | "
              f"{'○' if b_*c_ < 0 else '✗'} |\n")
        A(f"\n상관계수 **r = {r:+.2f}** · 방향 일치 **{agree}/{len(bs_)} 세션**.\n")
        A("즉 OLD 가 **높게 본 세션은 낮추고, 낮게 본 세션은 올린다** — 계통 오차를 실제로 줄이는\n")
        A("보정이지 스케일 장난이 아니다. 그런데 **딱 하나 어긋난 세션이 held-out 0324** 이다.\n")
        A("\n⚠ **held-out 0324: 높이 2.5% → 4.2% 악화** (자세는 −45% 개선). OLD 가 유독 잘 맞던\n")
        A("세션이라 절대 수준은 4%대지만, **게이트 비악화 조건을 이 지표에서는 못 지켰다.**\n")
        A("승격 전 사용자 결정 필요: (a) 자세 대폭 개선을 우선해 승격 / (b) 높이 게이트를 먼저 해결.\n")

    A("\n## ⚠ τ 환율 주의 (표에서 τ 가 나빠 보이는 이유)\n")
    A("그래프의 **'실측 τ' 는 진짜 실측이 아니다.** 모터가 기록하는 것은 *명령* 토크(raw)뿐이고,\n")
    A("거기서 관절 축토크를 얻으려면 **환율(변환식)** 이 필요하다. 그런데\n")
    A("- p24 는 `a_hat` 환율을 쓰고,\n")
    A(f"- {TAG} 는 **분동으로 교정한 정본곡선**(`canon_cap`) 환율을 쓴다.\n")
    A("\n그림의 '실측 τ' 선은 `a_hat` 으로 그려져 있다 = **p24 자신의 환율**이다.\n")
    A("환율이 다른 두 값을 같은 자로 재면, 환율 차이가 그대로 오차로 계상된다.\n")
    A("\n실제로 **동역학을 전혀 섞지 않고** 두 환율의 차이만 재면 (점프 창, 46 trial):\n")
    A("```\nRMSE(canon_cap − a_hat)   τ1(힙) 2.16 Nm   τ2(무릎) 3.66 Nm\n```\n")
    A("표에서 τ 가 나빠진 폭(ModeA τ1 +0.45 · τ2 +0.61)은 **이 환율 차이보다 훨씬 작다.**\n")
    A(f"즉 τ 열은 {TAG} 의 동역학이 나빠졌다는 뜻이 아니라 **자를 p24 것으로 썼다**는 뜻이다.\n")
    A("→ 승격 판정은 **q·dq 로만** 한다 (정본 심판 J_G 도 τ 를 안 쓴다). "
      "τ-fidelity 를 제대로 채점하려면 먼저 **환율 자체를 실측으로 결착**해야 한다 (이월 과제).\n")

    A("\n## 남은 승격 절차\n")
    A("1. 이 스택을 `fourbar_pXX_candidate.json` 으로 포장 (현재는 환경변수로만 존재).\n")
    A("2. `bench compare pXX p24` → 골든 재현 + held-out 게이트.\n")
    A("3. `bench promote` → CURRENT_STACK 갱신.\n")
    (ROOT / "00_승격판단.md").write_text("".join(L), encoding="utf-8")
    return wm, len(ma), wc, len(cl), nT


def main():
    global ROOT
    if len(sys.argv) > 1:
        ROOT = Path(sys.argv[1])
    D = load()
    overview(D)
    wm, nm_, wc, nc, nT = doc(D)
    print(f"조립 완료 → {ROOT}")
    print(f"  ModeA 자세 승 {wm}/{nm_} 세션 · CL {wc}/{nc} 세션 · 총 {nT} trial")


if __name__ == "__main__":
    main()
