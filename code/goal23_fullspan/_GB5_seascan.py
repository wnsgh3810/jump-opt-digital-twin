# -*- coding: utf-8 -*-
"""_GB5_seascan — 무릎 벨트 직렬탄성(SEA) 강성 스캔 (마라톤G, 08-11, 사용자 승인).

왜 SEA 인가
  ① 폐루프 무릎 토크에서 배포모델이 이긴다 (세션 4승 5패, 7월24일 +61%).
     배포모델은 무릎에 α(kp) 표를 쓰고 현행은 안 쓴다.
  ② α 표를 켜보니 **무릎 토크는 잡히는데(3.51→3.20) 무릎 각도를 잃는다(1.42→2.54°)**.
     명령을 그냥 깎으니 관절이 덜 움직인다. 순수 이득이 아니라 맞바꿈.
  ③ 결정적: α 표를 스프링으로 환산하면 **하나의 값에 모인다**.
        ks = kp·α/(1−α):  kp 60→340 · 120→449 · 250→477 · 500→333
        게인이 8배 차이나는데 ks 는 400±64 (퍼짐 16%).
     α 가 임의 적합값이면 이럴 이유가 없다 → **하나의 물리 스프링**이라는 증거.
  ④ 스프링은 깎인 몫을 저장했다 돌려주므로 **각도를 안 잃고** 토크만 부드럽게 할 수 있다.

구현: `fs_runner.rollout_cl_fs` 의 FS_KNEE_SEA="ks[,bs[,Jm]]" (컨트롤러측 적분, p26_sea 계보).

한계 (정직하게)
  명시적 공동적분이라 ks ≳ 5000 에서 발산한다 (dt=0.5ms). 즉 **강체 극한으로의 수렴 골든을
  끝까지 못 찍는다.** 다만 ③이 요구하는 ks≈400 은 안정 범위 한복판이다.
  대신 검증은 "실효 게인 창발"로 한다 — SEA(ks) 가 α=ks/(kp+ks) 판과 닮아야 한다.

CLI: python _GB5_seascan.py [ks,ks,...]
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import safe                                                      # noqa: E402

CH = ("q1", "q2", "dq1", "dq2", "a1", "a2")
NM = ["힙각°", "무릎각°", "힙속", "무릎속", "힙토크", "무릎토크"]
OUT = HERE / "_compare_G50" / "_seascan.json"
BS = os.environ.get("GB5_BS", "1.0")
JM = os.environ.get("GB5_JM", "0.03")


def board():
    import fs_data as FD, fs_compare_plot as CP
    O = []; F = []
    for s, p, g, cvt, ho in FD.registry():
        if cvt or not g:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            d["_sess"] = s; d["_fold"] = p
            r = CP.cl_pair(d, seg, g, s)
        except Exception:
            continue
        if r is None:
            continue
        t, (mo, mf), old, fs, m, cmd, _ = r
        e = lambda a, b, k: float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2))) * \
            (180 / np.pi if k in ("q1", "q2") else 1)
        O.append([e(old[i], mo[k], k) for i, k in enumerate(CH)])
        F.append([e(fs[i], mf[k], k) for i, k in enumerate(CH)])
    return np.array(O), np.array(F)


def main():
    kss = sys.argv[1] if len(sys.argv) > 1 else "300,400,550,800"
    runs = [("현행 (강체)", None, None)]
    runs += [(f"SEA ks={k}", "sea", f"{k},{BS},{JM}") for k in kss.split(",")]
    runs += [("α 표 (참고)", "alpha", "table")]
    res = {}
    O = None
    for tag, kind, val in runs:
        os.environ.pop("FS_KNEE_SEA", None); os.environ.pop("FS_KNEE_A", None)
        if kind == "sea":
            os.environ["FS_KNEE_SEA"] = val
        elif kind == "alpha":
            os.environ["FS_KNEE_A"] = val
        o, f = board()
        if len(f) == 0 or not np.all(np.isfinite(f)):
            print(f"{tag:16s} → 발산/실패 ({np.sum(~np.isfinite(f))} 값)", flush=True); continue
        O = o if O is None else O
        res[tag] = f
        print(f"{tag:16s} n={len(f):3d} | 무릎각 {f[:,1].mean():5.2f}° 무릎토크 {f[:,5].mean():5.2f} "
              f"| 각도속도 {f[:,:4].mean():5.2f} | 전채널 {f.mean():5.2f}", flush=True)
    print("\n" + "=" * 84)
    print(f"{'채널':9s} {'배포모델':>8s} | " + " | ".join(f"{t:>15s}" for t in res))
    for i, nm in enumerate(NM):
        print(f"{nm:9s} {O[:, i].mean():8.2f} | " + " | ".join(
            f"{res[t][:, i].mean():7.2f} ({100*(res[t][:, i].mean()/O[:, i].mean()-1):+4.0f}%)" for t in res))
    print(f"{'─ 전채널':9s} {O.mean():8.2f} | " + " | ".join(
        f"{res[t].mean():7.2f} ({100*(res[t].mean()/O.mean()-1):+4.0f}%)" for t in res))
    safe.atomic_json_write(OUT, {t: res[t].tolist() for t in res} | {"OLD": O.tolist()})
    print(f"\n저장 → {OUT}")


if __name__ == "__main__":
    main()
