# -*- coding: utf-8 -*-
"""_G_ledger — 마라톤 G 데이터 대장: 전 trial `Real Data.txt` 원본 파싱 → `_G_real_ledger.json`.

지표 출처 원칙(metric-provenance-rule): 파생 JSON 승계 금지, **원본에서 직접 재유도**.

## Real Data.txt에서 취하는 것 = 딱 둘 (사용자 지시 08-02)
  h_real    실제 점프 높이 [m] — 지면 기준 베이스 중심 최고높이 (사용자 확정 정의, 2회)
  w1/w2/w3  시간 구간 [s, 절대] — 원 xlsx 창 / Extended(=*2) / Extended 3(=*3).
            셋의 중간값이 이륙 시각 t_to (전 trial 일치 검증).

## 쓰지 않는 것 (사용자 지시 08-02: "이륙 시점 base 높이 믿지마 그거 그냥 fk로 푼 추정치야")
  Base height at this timing · Base vertical velocity · Estimated final jump height ·
  Expected Maximum Jump State 블록의 각/속도 · GRF Summary · Mechanical Energy · Torque Integral.
  → **파싱하지 않는다.** FK 추정치를 실측 앵커로 승계하는 실수의 재발 방지.
CLI: python _G_ledger.py
"""
import os, sys, io, json, re
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD

OUT = HERE / "_G_real_ledger.json"
H_PAT = re.compile(r"실제 점프 높이\s*:\s*([-\d.]+)\s*m")
TRI = re.compile(r"^\s*([\d.]+)\s*~\s*([\d.]+)\s*~\s*([\d.]+)\s*$", re.M)


def parse(fold: Path):
    f = fold / "Real Data.txt"
    if not f.exists():
        return None
    txt = f.read_text(encoding="utf-8", errors="ignore")
    m = H_PAT.search(txt)
    if not m:
        return None
    h = float(m.group(1))
    r = {"h_real": h / 100.0 if h > 5.0 else h}      # 단위 혼재 방어: 0324/P100_D3만 cm(74.000)
    if h > 5.0:
        r["h_unit_fixed"] = True
    tri = TRI.findall(txt)
    for i, key in enumerate(["w1", "w2", "w3"]):
        r[key] = [float(x) for x in tri[i]] if i < len(tri) else None
    if r["w1"]:
        r["t_to"] = r["w1"][1]
    return r


def main():
    reg = FD.registry()
    led, miss = {}, []
    for s, p, g, cvt, ho in reg:
        r = parse(p)
        if r is None:
            miss.append(f"{s}/{p.name}")
            continue
        r["sess"], r["trial"], r["kind"], r["cvt"] = s, p.name, FD.kind_of(s), bool(cvt)
        r["gains"] = list(g) if g else None
        led[f"{s}/{p.name}"] = r
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(led, fh, ensure_ascii=False, indent=1)
    print(f"저장 {OUT.name}: {len(led)}/{len(reg)} trial (누락 {len(miss)})")
    if miss:
        print("  누락:", ", ".join(miss))

    bad = [k for k, r in led.items() if r["w2"] and r["w3"]
           and not (abs(r["w1"][1] - r["w2"][1]) < 1e-6 and abs(r["w1"][1] - r["w3"][1]) < 1e-6)]
    print(f"3창 이륙시각 일치: {len(led)-len(bad)}/{len(led)}" + (f"  불일치 {bad[:3]}" if bad else ""))
    print(f"*3 창(공중 전원인가 포함) 보유: {sum(1 for r in led.values() if r['w3'])}/{len(led)}")

    print(f"\n{'세션':<10} {'kind':<8} {'n':>3} {'h실측 중앙[m]':>13} {'범위[m]':>15} "
          f"{'채점창[s]':>10} {'*3 선행[s]':>10}")
    for s in sorted({r["sess"] for r in led.values()}):
        v = [r for r in led.values() if r["sess"] == s]
        h = np.array([r["h_real"] for r in v], float)
        d1 = np.median([r["w1"][2] - r["w1"][0] for r in v if r["w1"]])
        pre = [r["w2"][0] - r["w3"][0] for r in v if r["w2"] and r["w3"]]
        print(f"{s:<10} {v[0]['kind']:<8} {len(v):3d} {np.median(h):13.3f} "
              f"{f'{h.min():.3f}~{h.max():.3f}':>15} {d1:10.3f} "
              f"{(np.median(pre) if pre else np.nan):10.2f}")
    H = np.array([r["h_real"] for r in led.values()], float)
    print(f"{'전체':<10} {'':<8} {len(H):3d} {np.median(H):13.3f} {f'{H.min():.3f}~{H.max():.3f}':>15}")


if __name__ == "__main__":
    main()
