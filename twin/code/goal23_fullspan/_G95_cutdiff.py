# -*- coding: utf-8 -*-
"""_G95_cutdiff — 절단 규칙 수정 **전후 비교** (마라톤G, 08-09).

왜: 접지 유효구간 절단이 `|cy−y0| > 8px` 로 **대칭**이라, 화면에서 아래로 흔들려도 잘랐다.
    이륙은 위로 뜨는 것이고 아래 흔들림은 푸시 모션블러의 추적 떨림이다.
    실제로 0723/60_0.75_60_2 는 푸시 슬립이 **+1.2 → −51.6mm** 로 뒤집혔다.
    (사용자 육안 −60mm 와 충돌하던 값이었다)

이 스크립트는 전(_G72_slipall_BEFORE_cutfix.json)과 후(_G72_slipall.json)를 나란히 놓는다.
CLI: python _G95_cutdiff.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
A = json.load(io.open(HERE / "_G72_slipall_BEFORE_cutfix.json", encoding="utf-8"))

# ⚠ 백업 오염 정정 — 회귀 검증으로 이 2건을 **먼저 재측정한 뒤** 백업을 떴다.
#   따라서 백업의 이 두 항목은 이미 '수정 후' 값이다. 대화 기록의 실제 '수정 전' 값으로 되돌린다.
_TRUE_BEFORE = {
    # key: (f_end, 하강, 바닥, 푸시, 전체)   ← 수정 전 실측 (G88 표)
    "26.07.23/60_0.75_60_2":   (217, -3.7, -0.2,  +1.2,  -2.6),
    "26.07.23/150_2.2_250_3":  (199, -7.5, -0.5, -42.0, -50.0),   # 변화 없음 (회귀 기준)
}
for _k, _v in _TRUE_BEFORE.items():
    if _k in A:
        A[_k] = dict(A[_k], f_end=_v[0],
                     seg={"하강전반": {"slip": _v[1]}, "하강후반": {"slip": 0.0},
                          "바닥유지": {"slip": _v[2]}, "푸시~이륙": {"slip": _v[3]},
                          "전체": {"slip": _v[4]}})
B = json.load(io.open(HERE / "_G72_slipall.json", encoding="utf-8"))


def seg(v, ph):
    g = v.get("seg")
    if not g:
        return float("nan")
    if ph == "하강":
        return g["하강전반"]["slip"] + g["하강후반"]["slip"]
    return g[ph]["slip"]


rows = []
for k in sorted(B):
    b = B[k]
    if not (b.get("ok") and "cut_why" in b):
        continue                                  # 아직 재측정 안 된 것
    a = A.get(k, {})
    rows.append(dict(k=k, fa=a.get("f_end"), fb=b["f_end"],
                     da=seg(a, "하강"), db=seg(b, "하강"),
                     pa=seg(a, "푸시~이륙"), pb=seg(b, "푸시~이륙"),
                     ta=seg(a, "전체"), tb=seg(b, "전체"),
                     why=b.get("cut_why"), qa=len(a.get("qc", [])), qb=len(b.get("qc", []))))

print(f"절단 규칙 수정 전후 — {len(rows)} trial\n")
print(f"{'세션/trial':32s}{'f_end':>11}{'푸시 전':>9}{'푸시 후':>9}{'변화':>9}"
      f"{'전체 전':>9}{'전체 후':>9}{'QC':>7}  절단사유")
big = []
for r in rows:
    dp = r["pb"] - r["pa"]
    if abs(dp) > 5:
        big.append(r)
    print(f"{r['k']:32s}{str(r['fa'])+'→'+str(r['fb']):>11}{r['pa']:9.1f}{r['pb']:9.1f}{dp:+9.1f}"
          f"{r['ta']:9.1f}{r['tb']:9.1f}{str(r['qa'])+'→'+str(r['qb']):>7}  {r['why'] or '-'}")

print(f"\n{'='*100}")
print(f"푸시 슬립이 5mm 넘게 바뀐 trial: {len(big)}/{len(rows)}")
for r in sorted(big, key=lambda z: -abs(z["pb"] - z["pa"])):
    print(f"  {r['k']:32s} {r['pa']:+7.1f} → {r['pb']:+7.1f}  ({r['pb']-r['pa']:+.1f}mm)  "
          f"프레임 {r['fa']}→{r['fb']}")

w = {}
for r in rows:
    w[r["why"] or "없음"] = w.get(r["why"] or "없음", 0) + 1
print(f"\n절단 사유 분포: " + " · ".join(f"{a} {b}건" for a, b in sorted(w.items(), key=lambda z: -z[1])))
