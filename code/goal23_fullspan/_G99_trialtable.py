# -*- coding: utf-8 -*-
"""_G99_trialtable — trial 별 슬립 표를 **결과 폴더에 쓴다** (마라톤G, 08-09).

왜 스크립트로 만드나
  처음엔 이 표를 한 번만 인라인으로 뽑았다. 그 뒤 절단 규칙·시드 반지름을 고쳐
  측정값이 바뀌었는데 **표만 낡은 채 남았다** (CSV 는 갱신, 표는 2시간 전 값).
  사용자가 발견했다. 산출물은 **한 번 만들고 마는 것이 아니라 재생성 가능해야** 한다.
  이제 `_G79_collect.py` 가 이걸 호출한다 — 모으면 표도 같이 새로 쓰인다.

CLI: python _G99_trialtable.py [출력폴더]
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
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
SRC = HERE / "_G72_slipall.json"
DEF_OUT = Path(os.environ.get("G79_OUT", (LEGACY_ROOT + "/G_slip_all_260809")))


def build(out_dir=None):
    out_dir = Path(out_dir or DEF_OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    d = json.load(io.open(SRC, encoding="utf-8"))
    rows = []
    for k, v in sorted(d.items()):
        if not (v.get("ok") and v.get("seg")):
            continue
        g = v["seg"]
        p = g["푸시~이륙"]
        rows.append(dict(
            sess=v["sess"], trial=v["trial"], fps=v["fps"], sc=v["scale"], dia=v["dia_px"],
            d1=g["하강전반"]["slip"], d2=g["하강후반"]["slip"],
            de=g["하강전반"]["slip"] + g["하강후반"]["slip"],
            fl=g["바닥유지"]["slip"], pu=p["slip"], tot=g["전체"]["slip"],
            pdx=p["dx"], prl=p["roll"],            # 푸시 구간의 Δx·구름 (성분 확인용)
            psum=p["roll"] + p["slip"],            # 구름+슬립 (= Δx, 항등식 검산)
            pabs=abs(p["roll"]) + abs(p["slip"]),  # 크기합 — 부호가 반대면 Δx 보다 훨씬 크다
            ddx=g["하강전반"]["dx"] + g["하강후반"]["dx"],
            drl=g["하강전반"]["roll"] + g["하강후반"]["roll"],
            # 구간 내 극값 — 끝점차만 보면 갔다가 돌아온 것이 안 보인다
            pmin=p.get("slip_min", float("nan")), pmax=p.get("slip_max", float("nan")),
            rl=g["전체"]["roll"], dx=g["전체"]["dx"],
            sens=v["sync_sens_mm"], qc=len(v.get("qc", [])),
            why=v.get("cut_why") or "-", fend=v.get("f_end")))

    L = []
    A = L.append
    A("# 슬립·구름 trial별 표 (2026-08-09 · 55 trial 전수)\n")
    A("\n> 이 파일은 `_G99_trialtable.py` 가 생성한다. 손으로 고치지 말 것 — "
      "측정이 갱신되면 `_G79_collect.py` 가 다시 쓴다.\n")
    A("\n부호: **+ = 화면 오른쪽 = 모델 +x** · 단위 mm\n")
    A("\n```\n슬립 = Δx(영상) − r·Δθ(엔코더),   r = 20.0 mm\n자   = 발 금속판 30.0mm / 측정 지름[px]  (영상마다 재측정)\n```\n")
    A("\n★ **슬립 열은 전부 구름을 뺀 값이다.** Δx·구름 열은 그 성분이다.\n")
    A("```\n검산:  하강슬립 + 바닥슬립 + 푸시슬립 = 전체슬립\n"
      "       전체Δx − 전체구름            = 전체슬립\n```\n")
    A("\n열 설명\n")
    A("- **Δx**: 영상이 본 발의 실제 이동 · **구름**: 엔코더가 말하는 굴러간 양 · 둘의 차가 **슬립**.\n")
    A("- **구름+슬립**: 정의상 **Δx 와 같다** (slip = Δx − roll). 눈으로 검산하라고 넣은 열이다.\n")
    A("- **크기합** = |구름| + |슬립|. 둘의 **부호가 반대면 Δx 보다 훨씬 크다** — "
      "발이 굴러간 만큼 못 가고 그 차이를 헛돈 것이다(휠스핀). 55 trial 중 **34건**이 이 경우다.\n")
    A("- **푸시슬립 극값**: 푸시 구간 **안에서** 슬립이 간 최소~최대. 끝점차와 크게 다르면 "
      "구간 안에서 갔다가 돌아온 것이다 (24fps 정렬 한계의 서명).\n")
    A("- **sens**: 영상-데이터 동기가 ±1프레임 어긋날 때 푸시 슬립이 흔들리는 폭. **작을수록 신뢰**.\n")
    A("- **절단**: 접지 구간을 어디서 끊었는지의 사유 (점수붕괴 / 이륙(위로) / 물리한계Δcx / 아래드리프트).\n")
    A("- **QC**: 경고 개수. 0이 최선.\n")
    prev = None
    for r in rows:
        if r["sess"] != prev:
            prev = r["sess"]
            A(f"\n## {r['sess']}  ({r['fps']:.0f}fps)\n\n")
            A("| trial | 자<br>mm/px | 지름<br>px "
              "| 하강<br>Δx | 하강<br>구름 | **하강<br>슬립** | 바닥<br>슬립 "
              "| 푸시<br>Δx | 푸시<br>구름 | **푸시<br>슬립** "
              "| **푸시<br>구름+슬립** | **푸시<br>크기합** | 푸시슬립<br>극값 "
              "| 전체<br>Δx | 전체<br>구름 | **전체<br>슬립** | sens | 절단 | QC |\n")
            A("|" + "---|" * 19 + "\n")      # 열 19개 — 헤더와 개수가 어긋나면 렌더가 깨진다
        ex = (f"{r['pmin']:+.1f}~{r['pmax']:+.1f}" if np.isfinite(r["pmin"]) else "—")
        A(f"| {r['trial']} | {r['sc']:.4f} | {r['dia']:.1f} "
          f"| {r['ddx']:+.1f} | {r['drl']:+.1f} | **{r['de']:+.1f}** | {r['fl']:+.1f} "
          f"| {r['pdx']:+.1f} | {r['prl']:+.1f} | **{r['pu']:+.1f}** "
          f"| **{r['psum']:+.1f}** | **{r['pabs']:.1f}** | {ex} "
          f"| {r['dx']:+.1f} | {r['rl']:+.1f} | **{r['tot']:+.1f}** "
          f"| {r['sens']:.1f} | {r['why']} | {r['qc']} |\n")

    A("\n---\n\n## 세션 요약\n\n")
    A("| 세션 | fps | n | 하강 중앙 | 하강 SD | 푸시 중앙 | 푸시 SD | sens 중앙 | QC0 |\n")
    A("|---|---|---|---|---|---|---|---|---|\n")
    for s in sorted({r["sess"] for r in rows}):
        a = [r for r in rows if r["sess"] == s]
        A(f"| {s} | {a[0]['fps']:.0f} | {len(a)} | {np.median([x['de'] for x in a]):+.1f} "
          f"| {np.std([x['de'] for x in a]):.2f} | {np.median([x['pu'] for x in a]):+.1f} "
          f"| {np.std([x['pu'] for x in a]):.2f} | {np.median([x['sens'] for x in a]):.1f} "
          f"| {sum(1 for x in a if x['qc'] == 0)}/{len(a)} |\n")
    fn = out_dir / "02_slip_trial표.md"
    io.open(fn, "w", encoding="utf-8").write("".join(L))
    return fn, len(rows)


if __name__ == "__main__":
    f, n = build(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"저장 {f}  ({n} trial)")
