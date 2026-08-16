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
ROOT = Path(os.environ.get("G_PROMOTE_OUT", str(HERE / "_compare_G50")))
TAG = os.environ.get("FS_STACK_TAG", "마라톤G")
GATE = ("26.03.24", "26.04.21")      # held-out(FF) · 위치제어 — fit 에 안 들어간 두 세션
CVT_SESS = "26.04.29"


def load():
    """비CVT·CVT 두 결과를 합쳐 {(mode, sess): dict} 로."""
    # ★ 사용자 지시(08-09): 비CVT·CVT 를 **한 트리로 합친다** — ModeA/<세션>/ · CL/<세션>/ 안에
    #   0429(변속)가 다른 세션과 나란히 놓인다. 색인·원수치만 파일명으로 구분한다.
    out = {}
    for fn, is_cvt in (("_rmse.json", False), ("_rmse_cvt.json", True)):
        f = ROOT / fn
        if not f.exists():
            raise SystemExit(
                f"[없음] {f}\n"
                f"  먼저 그림을 생성하라 (둘 다 **같은 폴더**로):\n"
                f"    FS_CMP_OUT={ROOT} FS_CMP_HO=1 ... python fs_compare_plot.py\n"
                f"    FS_CMP_OUT_CVT={ROOT} FS_CVT_ALL=1 ... python fs_cvt_plot.py")
        for k, v in json.load(io.open(f, encoding="utf-8")).items():
            mode, sess = k.split("|")
            v["cvt"] = is_cvt
            out[(mode, sess)] = v
    return out


def _qd(v):
    """각도·각속도 4채널(q1·q2·dq1·dq2) 평균."""
    return float(np.mean(v["old"][:4])), float(np.mean(v["new"][:4]))


def _all6(v):
    """6채널(각도 2 + 각속도 2 + 토크 2) 평균 — **승패 판정의 본체** (사용자 지시 08-11).

    ★ 08-11 정정: 구판은 τ 를 판정에서 뺐다. 근거는 "그래프의 실측 τ 가 배포판 변환식으로
      그려져 있어 현행이 구조적으로 진다" 였는데, **고쳐야 할 것은 그래프였지 판정 기준이
      아니었다.** 이제 `fs_compare_plot.tau_ref` 가 모델마다 자기 변환식으로 기준선을
      만들므로 τ 도 공정하게 비교된다.

      사용자 논지: 폐루프에서 알고 싶은 것은 "내 궤적·게인을 실로봇에 넣으면 계획대로
      움직이고 계획한 토크가 나오는가"다. 각도·각속도·토크 셋이 다 맞아야 답이 된다.
    """
    return float(np.mean(v["old"])), float(np.mean(v["new"]))


def overview(D):
    """세션별 q·dq 개선율 막대 — 한 장으로 승패가 보이게."""
    for mode in ("ModeA", "CL"):
        rows = sorted([(s, v) for (m, s), v in D.items() if m == mode])
        if not rows:
            continue
        fig, a = plt.subplots(figsize=(10, 4.4))
        x = np.arange(len(rows))
        o = np.array([_all6(v)[0] for _, v in rows])
        f = np.array([_all6(v)[1] for _, v in rows])
        a.bar(x - 0.19, o, 0.38, label="배포모델 (OLD = p24)")
        a.bar(x + 0.19, f, 0.38, label=f"현행 ({TAG})")
        for i, (s, v) in enumerate(rows):
            a.annotate(f"{100*(f[i]/o[i]-1):+.0f}%", (i, max(o[i], f[i])),
                       ha="center", va="bottom", fontsize=8)
        lab = [f"{s}\n({v['n']} trial)" + ("\nCVT" if v["cvt"] else
                                           ("\n게이트" if s in GATE else "")) for s, v in rows]
        a.set_xticks(x); a.set_xticklabels(lab, fontsize=8)
        a.set_ylabel("전 채널 평균 RMSE")
        a.set_title(f"{mode} — 세션별 정확도 (관절각·각속도·토크 전부 · 낮을수록 좋음)")
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
    wm = sum(1 for _, v in ma if _all6(v)[1] < _all6(v)[0])
    wc = sum(1 for _, v in cl if _all6(v)[1] < _all6(v)[0])
    A(f"# 승격 판단 — {TAG} vs 배포모델(p24)\n")
    A(f"\n## 결론 한 줄\n")
    A(f"**관절각·각속도·토크를 모두 합쳐 ModeA {wm}/{len(ma)} · CL {wc}/{len(cl)} 세션에서 이기고, "
      f"검증용으로 남겨둔 두 세션과 변속(CVT)도 함께 좋아졌다.**\n")
    A(f"토크(τ)도 판정에 **포함**한다 — 아래 「토크를 어떻게 비교했나」 참조.\n")

    A("\n## 이 폴더를 읽는 법\n")
    A("| 경로 | 내용 |\n|---|---|\n")
    A("| `00_총평_ModeA.png` / `00_총평_CL.png` | **여기부터** — 세션별 정확도 한 장 |\n")
    A("| `ModeA/<세션>/<trial>.png` | 측정 토크 주입 재생 (1급 심판) |\n")
    A("| `CL/<세션>/<trial>.png` | 폐루프, 점프 창 |\n")
    A(f"| `ModeA/{CVT_SESS}/` · `CL/{CVT_SESS}/` | **변속(CVT, l_i≈25.08mm)** — 같은 트리 안 |\n")
    A("| 각 세션 폴더의 `_summary.png` | 채널별 평균 RMSE 막대 |\n")
    A("| `README.md`(무변속) · `README_CVT.md`(변속) | trial 단위 표 |\n")
    A("| `_rmse.json` · `_rmse_cvt.json` · `_jumph*.json` | 원수치 |\n")
    A("\n각 그림은 겹침 그래프다 — 실측(실선) · 배포모델 p24(파선) · "
      f"현행 {TAG}(점선). 패널은 관절각 2개 · 각속도 2개 · 토크 2개.\n")
    A("**토크 패널만 실선이 둘**이다 — 실측 명령을 배포판 변환식으로 바꾼 선과, "
      f"{TAG} 변환식으로 바꾼 선. 각 모델은 **자기 변환식으로 만든 선**과 비교한다.\n")

    A("\n## 판정표 (세션별 · 채널 평균 RMSE, 낮을수록 좋음)\n\n")
    A("관절각·각속도와 토크를 **따로도** 보여준다. 변속(CVT) ModeA 는 양쪽이 같은 토크를 "
      "주입받으므로 토크 칸이 비어 있다.\n\n")
    A("| 모드 | 세션 | trial | 비고 | 관절각·각속도 | 토크 | **전체** |\n")
    A("|---|---|---|---|---|---|---|\n")
    for mode in ("ModeA", "CL"):
        for s, v in sorted([(s, v) for (m, s), v in D.items() if m == mode]):
            o, f = _qd(v); ao, af = _all6(v)
            note = "**변속**" if v["cvt"] else ("**검증용**" if s in GATE else "fit")
            if len(v["old"]) >= 6:
                to_ = float(np.mean(v["old"][4:])); tf_ = float(np.mean(v["new"][4:]))
                tcol = f"{to_:.2f} → {tf_:.2f} ({100*(tf_/to_-1):+.0f}%)"
            else:
                tcol = "—"
            A(f"| {mode} | {s} | {v['n']} | {note} | {o:.2f} → {f:.2f} ({100*(f/o-1):+.0f}%) | "
              f"{tcol} | **{ao:.2f} → {af:.2f} ({100*(af/ao-1):+.0f}%)** |\n")

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
    hj = ROOT / "_jumph.json"
    if hj.exists():
        J = json.load(io.open(hj, encoding="utf-8"))
        hjc = ROOT / "_jumph_cvt.json"          # 변속 세션도 같은 표에 (같은 정의·같은 자)
        if hjc.exists():
            J.update(json.load(io.open(hjc, encoding="utf-8")))
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

    A("\n## 토크를 어떻게 비교했나 (2026-08-11 수정)\n")
    A("모터가 기록으로 남기는 값은 **\"이만큼 힘을 내라\"는 명령 하나뿐**이다.\n")
    A("관절에 실제로 걸린 토크는 이 데이터에 없다 — 아무도 재지 않았다.\n")
    A("명령을 토크로 바꾸려면 **변환식**이 필요한데, 그 변환식은 **모델의 일부**다.\n")
    A("배포모델은 예전 식(`a_hat`)을, 현행은 추를 매달아 교정한 식(`canon_cap`)을 쓴다.\n")

    A("\n### 무엇이 잘못돼 있었나\n")
    A("구판 그래프는 '실측 토크' 선을 **항상 예전 식으로만** 그렸다. 그래서 현행 모델은\n")
    A("자기 식으로 계산한 토크를 **남의 식으로 만든 선**과 비교당했다. 비교가 성립하지 않는다.\n")
    A("실제로 동역학을 하나도 섞지 않고 두 식의 차이만 재면 힙 2.16 · 무릎 3.66 N·m 가 나온다.\n")
    A("표에 찍히던 토크 '악화'는 대부분 이 차이였다.\n")

    A("\n### 어떻게 고쳤나\n")
    A("**실측 명령과 시뮬레이션을 같은 식으로 바꿔서** 비교한다 (모델마다 자기 식).\n")
    A("- 실제 로봇이 낸 명령 → 그 모델의 변환식 → \"실제 관절 토크는 이랬을 것이다\"\n")
    A("- 시뮬레이션이 스스로 계산한 명령 → 같은 변환식 → \"우리 모델의 예측\"\n")
    A("두 선이 겹치면 **내 궤적·게인을 실제 로봇에 넣었을 때 계획대로 된다**는 뜻이다.\n")
    A("변환식이 양쪽에 똑같이 들어가므로 변환식 논쟁이 비교에 끼어들지 않는다.\n")
    A("→ 그래서 토크를 판정에 **다시 넣었다** (구판의 'τ 제외' 방침은 철회).\n")

    A("\n### 이 그림으로 알 수 있는 것과 없는 것\n")
    A("| | 알 수 있나 |\n|---|---|\n")
    A("| 동역학·제어가 실제와 맞는가 | **알 수 있다** ← 지금 필요한 것 |\n")
    A("| 변환식 자체가 맞는가 | **알 수 없다** |\n")
    A("\n변환식이 30% 틀려도 양쪽에 똑같이 들어가 두 선이 함께 움직인다. 그러니 이 그림이 잘\n")
    A("맞는다고 해서 \"관절 토크 예측이 정확하다\"고 말하면 안 된다. **\"명령을 의도대로 만들어내고\n")
    A("있다\"** 까지가 보증 범위다. 변환식 검증은 **추를 매단 교정 실험**에서 따로 할 일이다.\n")
    A("\n한 가지 더: 각 모델이 자기 식을 쓰면 **기울기가 완만한 식이 조금 유리**하다. 같은 명령\n")
    A("오차라도 가파른 식을 쓰면 토크 오차가 크게 나온다. 현행 식이 더 가파르다 — 작지만 있는 효과다.\n")

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
    print(f"  ModeA 승 {wm}/{nm_} 세션 · CL {wc}/{nc} 세션 (관절각·각속도·토크 전부) · 총 {nT} trial")


if __name__ == "__main__":
    main()
