# -*- coding: utf-8 -*-
"""P22 — 게이트 통과 개체를 후보 JSON으로 등록 (p21 스키마, safe.candidate_save).

사용: python p22_register.py <gate_check row index> <tag>
예:   python p22_register.py 8 p22a     (i=34 = rows[8])
20-vec → 18-vec 역매핑: x18 = [v0, v1, v19(pre30)] + v[2:15] + [v17, v18(o429)];
p20 블록: c_qs=v[15], v0=v[16], C_dyn=0. cmdlayer = p21 후보 사본 + TM=v[14].
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "bench"))
import safe

ROW = int(sys.argv[1]) if len(sys.argv) > 1 else 8
TAG = sys.argv[2] if len(sys.argv) > 2 else "p22a"


def main():
    gc = safe.read_json(HERE / "p22_gate_check.json")
    row = gc["rows"][ROW]
    assert row["PASS"], f"row {ROW} did not pass the gate"
    v = np.array(row["x"], float)
    x18 = [float(a) for a in ([v[0], v[1], v[19]] + list(v[2:15]) + [v[17], v[18]])]
    p21 = safe.read_json(HERE.parent / "p20_rise" / "fourbar_p21_candidate.json")
    cmd = dict(p21["cmdlayer"])
    cmd["TM"] = float(v[14])
    cand = {
        "CANDIDATE": f"P22 {TAG} — NSGA-II gen{gc['gen']} i={row['i']} : v5 전 성분 P19 이하 "
                     "(통짜 재생·점프높이 포함 최초 전 전선 지배) (2026-07-16)",
        "judge": "p22",
        "names": p21["names"],
        "x": x18,
        "A": "paper",
        "cmdlayer": cmd,
        "p20": {"c_qs": float(v[15]), "v0": float(v[16]), "C_dyn": 0.0,
                "note": "NSGA-II 2목적(CLτ, 전체 25-trial 재생 dq) + 6제약 탐색 승자. "
                        "게이트: CL 0.972 / DQ 0.999 / OLdq 0.994 / H 0.842 / 창·s2s 전부 ≤1.0"},
        "v5_gate": row["gate"],
        "J_v5": row["J_v5"],
        "metric_full": float(sys.argv[3]) if len(sys.argv) > 3 else None,
        "heldout": float(sys.argv[4]) if len(sys.argv) > 4 else None,
        "origin": {"nsga_gen": gc["gen"], "pop_index": row["i"],
                   "ckpt": "p22_nsga_ckpt.json", "anchors": "p22_eval_anchors.json"},
    }
    out = HERE / f"fourbar_{TAG}_candidate.json"
    safe.candidate_save(out, cand)
    print(f"saved {out.name}", flush=True)


if __name__ == "__main__":
    main()
