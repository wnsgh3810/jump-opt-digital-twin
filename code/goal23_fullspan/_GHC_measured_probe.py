# 가설: 힙 관성과 토크 환산은 **각각은 거부되지만 함께 넣으면 상쇄된다**
#   관성이 크면 같은 토크로 덜 가속한다 → 점프 재생이 뒤처진다.
#   그런데 실측 환산(작은 토크 1.26배 = 모델 0.68의 1.85배)이면 토크가 더 크게 들어간다.
#   둘 다 실측대로 넣으면 점프 재생이 회복돼야 한다. 아니면 "이중 흡수" 해석이 틀린 것이다.
import os, sys
os.environ.setdefault("FS_SWEEP_AIR", "1"); os.environ.setdefault("FS_SWEEP_S2S", "1")
from pathlib import Path
GFS = str(Path(__file__).parent)
sys.path.insert(0, GFS); os.chdir(GFS)
import numpy as np
import _GHB_sweep as S
S._ensure()
B = np.asarray(S.DEPLOY, float)

CASES = [
    ("지금 (관성 0.010 · 환산 1.0/1.0)",      0.0100, 1.00, 1.00),
    ("관성만 실측 (0.0164)",                  0.0164, 1.00, 1.00),
    ("환산만 실측 (1.85/13)",                 0.0100, 1.85, 13.0),
    ("둘 다 실측 (0.0164 · 1.85/13)",         0.0164, 1.85, 13.0),
    ("둘 다 실측 + 무릎마찰도 (0.423)",       0.0164, 1.85, 13.0),
]
print("전부 0 이 완벽")
print(f"{'설정':34s} {'점프주입':>9s} {'폐루프각속':>10s} {'폐루프토크':>10s} {'점프높이':>9s} {'매달림':>8s} {'일어서기':>9s}")
print("-"*96)
for i, (tag, arm, lin, sq) in enumerate(CASES):
    x = B.copy(); x[10] = arm; x[12] = lin; x[13] = sq
    if i == 4:
        x[0] = 0.423
    v, det = S.evaluate(("canon_cap", x))
    if det is None:
        print(f"{tag:34s}   평가 실패"); continue
    print(f"{tag:34s} {det['ma']:9.4f} {det['clq']:10.4f} {det['clt']:10.4f} "
          f"{det['h']:9.4f} {det['air']:8.4f} {det['s2s']:9.4f}")
print("-"*96)
print("점프주입이 '지금'(0.1747) 수준으로 회복되면 이중 흡수 해석이 맞다.")
