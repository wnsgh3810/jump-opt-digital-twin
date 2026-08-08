# -*- coding: utf-8 -*-
"""_G79_collect — 슬립·구름 전수 산출물을 **한 폴더로 모은다** (마라톤G, 08-09).

왜
  사용자 지시: "이미지도 버리지말고 한폴더에 정리 잘해서 모아두고".
  판독·검증 그림이 graphs/ 아래 여기저기 흩어져 있고, 결과는 JSON 한 덩어리다.
  나중에 다시 볼 사람(=내일의 우리)이 폴더만 열면 알 수 있게 만든다.

구조
  graphs/G79_slip_all/
    00_INDEX.md            ← 무엇이 어디에 있고 무엇을 믿을 수 있는지
    01_결과표.csv          ← trial × 구간 슬립/구름/Δx + QC
    02_seed/<세션>/        ← 시드 대조시트 · 격자 · 확대
    03_proof/<세션>/       ← 4컷 검증 시트 (초록 원이 롤러에 물렸는지)
    04_data/               ← _G72_slipall.json · _G77_seeds.json 사본
    05_trend/              ← 게인·세션별 경향 그림

CLI: python _G79_collect.py
"""
import os, sys, io, json, shutil, csv
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))

G = HERE / "graphs"
DST = G / "G79_slip_all"
SEGS = ("하강전반", "하강후반", "바닥유지", "푸시~이륙", "전체")


def _sess_of(name):
    """파일명에서 세션 태그(26_07_23)를 뽑는다."""
    for tok in name.replace(".png", "").split("__"):
        t = tok.replace("_zoom1_", "").replace("_zoom2_", "").replace("_sheet_", "")
        t = t.replace("_chk_", "")
        if t.count("_") == 2 and t[:2].isdigit():
            return t
    return "기타"


def collect_images():
    n = 0
    src = G / "G72_seed"
    if src.exists():
        for p in sorted(src.glob("*.png")):
            d = DST / "02_seed" / _sess_of(p.name)
            d.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, d / p.name); n += 1
    for sub in ("G72_proof", "G73_proof"):
        s2 = G / sub
        if not s2.exists():
            continue
        for p in sorted(s2.glob("*.png")):
            d = DST / "03_proof" / _sess_of(p.name)
            d.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, d / p.name); n += 1
    return n


def collect_data():
    d = DST / "04_data"; d.mkdir(parents=True, exist_ok=True)
    got = []
    for f in ("_G72_slipall.json", "_G77_seeds.json", "_G77_manual.json",
              "_G75_flo_cache.json"):
        p = HERE / f
        if p.exists():
            shutil.copy2(p, d / f); got.append(f)
    return got


def write_csv(res):
    DST.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in res:
        if not r.get("ok"):
            rows.append(dict(세션=r["sess"], trial=r["trial"], 상태="실패",
                             사유=r.get("reason", ""))); continue
        g = r["seg"]
        row = dict(세션=r["sess"], trial=r["trial"], 상태="성공",
                   fps=round(r["fps"], 2), 해상도=f"{r['vid_w']}x{r['vid_h']}",
                   자_mm_px=round(r["scale"], 4), 지름px=round(r["dia_px"], 2),
                   지름산포pct=round(r["rel_sd"] * 100, 1),
                   동기민감도mm=round(r["sync_sens_mm"], 1),
                   추적점수최저=round(r["score_min"], 0))
        for s in SEGS:
            row[f"Δx_{s}"] = round(g[s]["dx"], 2)
            row[f"구름_{s}"] = round(g[s]["roll"], 2)
            row[f"슬립_{s}"] = round(g[s]["slip"], 2)
        row["QC"] = " / ".join(r.get("qc", []))
        rows.append(row)
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with io.open(DST / "01_결과표.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    return rows


def write_index(rows, nimg, data):
    ok = [r for r in rows if r.get("상태") == "성공"]
    ng = [r for r in rows if r.get("상태") != "성공"]
    clean = [r for r in ok if not r.get("QC")]
    L = []
    A = L.append
    A("# 슬립·구름 전수 측정 — 산출물 모음 (마라톤G, 2026-08-09)\n")
    A("## 무엇을 잰 것인가\n")
    A("발이 땅 위에서 **미끄러진 양(슬립)** 과 **굴러간 양(구름)** 을 나눈 것이다.\n")
    A("바퀴가 굴러가면 발 위치는 변하지만 미끄러진 건 아니다 — 그래서 둘을 나눠야 한다.\n")
    A("```\n슬립(t) = Δx_발(영상으로 잰 실제 이동) − r · Δθ_발(엔코더로 계산한 회전)\n"
      "        r = 20mm (발 바깥지름 40mm = 금속판 30 + 고무 5×2, 사용자 실측)\n```\n")
    A("영상은 세상 좌표에서 '얼마나 갔나'를, 엔코더는 로봇 내부 형상에서 '얼마나 굴렀나'를\n"
      "알려준다. 어느 하나만으로는 슬립을 못 구한다.\n")
    A("\n## 자(mm/px)는 어떻게 정했나\n")
    A("**발 금속 원판 30.0mm** 을 자로 쓴다. 발과 같은 깊이에 있어 원근 왜곡이 없다.\n")
    A("**영상마다 다시 잰다** — 카메라 거리·줌이 세션마다 다르다 (금속판이 20~59px).\n")
    A("구 발판 플레이트 120mm 자(0.7453)는 폐기 — 발보다 뒤에 있어 24% 틀렸다.\n")
    A(f"\n## 성적\n")
    A(f"| 항목 | 개수 |\n|---|---|\n")
    A(f"| 측정 성공 | {len(ok)} |\n| QC 무경고(가장 신뢰) | {len(clean)} |\n"
      f"| 측정 실패 | {len(ng)} |\n| 수집 이미지 | {nimg} |\n")
    if ng:
        A("\n### 실패 목록\n")
        for r in ng:
            A(f"- {r['세션']}/{r['trial']} — {r.get('사유','')}\n")
    A("\n## 폴더 안내\n")
    A("| 폴더 | 내용 | 어떻게 보나 |\n|---|---|---|\n")
    A("| `01_결과표.csv` | trial × 구간 슬립/구름/Δx + QC | 엑셀로 열면 된다 |\n")
    A("| `02_seed/` | 발 시드 판독 그림 (`_sheet_*` = 세션 대조시트) | "
      "초록 원이 금속판 가장자리에 물렸는지 본다 |\n")
    A("| `03_proof/` | 4컷 검증 시트 (하강시작/바닥/푸시/마지막접지) | "
      "네 컷 모두 초록 원이 롤러에 있으면 그 trial 은 믿는다 |\n")
    A("| `04_data/` | 원본 JSON (측정값·시드) | 재분석용 |\n")
    A("| `05_trend/` | 게인·세션별 경향 그림 | |\n")
    A("\n## 읽을 때 주의\n")
    A("1. **QC 경고가 붙은 trial 은 숫자를 그대로 믿지 말 것.** 특히 "
      "`동기 ±1프레임 → 푸시슬립 ±N mm` 는 24fps 에서 푸시가 5프레임뿐이라 생기는 한계다.\n")
    A("2. **부호**: + = 화면 오른쪽 = 모델 +x.\n")
    A("3. **푸시가 지배한다.** 정본 trial 에서 전체 슬립의 84% 가 푸시~이륙 구간이다.\n")
    A("4. 그림은 하나도 지우지 않았다 — 실패한 판독 그림도 남아 있다 "
      "(무엇이 왜 틀렸는지가 다음 사람에게 제일 중요하다).\n")
    A(f"\n## 데이터 파일\n{', '.join('`'+d+'`' for d in data)}\n")
    A("\n## 만든 코드\n")
    A("`fs_slipmeas.py`(측정 정본) · `fs_vidscale.py`(자·추적 정본) · "
      "`_G77_footfit.py`(시드 맞춤) · `_G77_sheet.py`(시드 시트) · "
      "`_G72_proof.py`(검증 시트) · `_G79_collect.py`(이 모음)\n")
    io.open(DST / "00_INDEX.md", "w", encoding="utf-8").write("".join(L))


def main():
    DST.mkdir(parents=True, exist_ok=True)
    (DST / "05_trend").mkdir(exist_ok=True)
    p = HERE / "_G72_slipall.json"
    res = json.load(io.open(p, encoding="utf-8")) if p.exists() else []
    if isinstance(res, dict):
        res = list(res.values())
    rows = write_csv(res)
    nimg = collect_images()
    data = collect_data()
    write_index(rows, nimg, data)
    print(f"모음 완료 → {DST}\n  결과 {len(rows)}행 · 이미지 {nimg}장 · 데이터 {len(data)}개")


if __name__ == "__main__":
    main()
