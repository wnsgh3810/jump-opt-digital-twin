# -*- coding: utf-8 -*-
"""_GB4_lagscan — 커맨드 지연을 폐루프에서 적합한다 (마라톤G, 08-11).

경위
  ① 08-11 데이터 동정(`_GB3_cmdlaw`): 실로봇 PD 는 **상태를 B 샘플 묵혀** 계산한다
     (B = 1~4, 1샘플 = 2ms). A−B = 2 로 데이터 사전의 "qd 2샘플 선행"도 확인됐다.
  ② 같은 날 측정: sim 무릎 토크가 실측보다 **10~34ms 이르다**. 지연이 없으면 sim 이
     즉시 반응하니 당연히 이르다 — ①과 앞뒤가 맞는다.
  ③ 그런데 `FS_CMD_DELAY` 노브는 **죽어 있었다** (_cv 람다 인자 수 불일치 TypeError).
     마라톤C P12 가 7~9ms 를 요구했는데 켤 수가 없었던 것. 08-11 픽스.

이 스크립트
  지연을 바꿔가며 **폐루프 6채널 RMSE + 무릎 토크 시간밀림**을 잰다.
  ★ 지연은 커맨드층이라 **폐루프에서만** 적합해야 한다 (철칙 10). ModeA(측정 토크 주입)는
    PD 루프가 없어 이 노브의 영향을 받지 않는다 → ModeA 게이트는 구조적으로 안전.

CLI: python _GB4_lagscan.py [지연,지연,...초]   (기본 0,0.004,0.006,0.008,0.012)
"""
import os, sys, io, json, importlib
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import safe                                                      # noqa: E402

VAR = os.environ.get("GB4_VAR", "FS_CMD_DELAY")   # 스캔할 노브
SESS = os.environ.get("GB4_SESS", "26.04.21,26.07.22,26.07.24,26.07.27").split(",")
OUT = HERE / "_compare_G50" / f"_lagscan_{os.environ.get('GB4_VAR','FS_CMD_DELAY')}.json"


def tshift(sim, ref, W=30):
    """sim 을 ±W 샘플 밀어 최소가 되는 지점. 음수 = sim 이 이르다."""
    sim = np.asarray(sim, float); ref = np.asarray(ref, float)
    tot = float(np.sqrt(np.mean((sim - ref) ** 2)))
    best = (0, tot)
    for k in range(-W, W + 1):
        a = sim[W + k:len(sim) - W + k]; b = ref[W:len(ref) - W]
        v = float(np.sqrt(np.mean((a - b) ** 2)))
        if v < best[1]:
            best = (k, v)
    return best[0] * 2.0, best[1], tot


def run(delay):
    os.environ[VAR] = f"{delay}"
    import fs_compare_plot as CP
    importlib.reload(CP)                 # 지연은 롤아웃 안에서 매번 env 를 읽으므로 실은 불필요
    import fs_data as FD
    rows = []
    for s, p, g, cvt, ho in FD.registry():
        if cvt or not g or s not in SESS:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            d["_sess"] = s; d["_fold"] = p
            r = CP.cl_pair(d, seg, g, s)
        except Exception as ex:
            print(f"    ✗ {s}/{p.name}: {type(ex).__name__} {str(ex)[:50]}", flush=True); continue
        if r is None:
            continue
        t, (mo, mf), old, fs, m, cmd, _ = r
        CH = ("q1", "q2", "dq1", "dq2", "a1", "a2")
        e = lambda a, b, deg: float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2))) * \
            (180 / np.pi if deg else 1)
        eo = [e(old[i], mo[k], k in ("q1", "q2")) for i, k in enumerate(CH)]
        ef = [e(fs[i], mf[k], k in ("q1", "q2")) for i, k in enumerate(CH)]
        sh, res, tot = tshift(fs[5], mf["a2"])
        sho, reso, toto = tshift(old[5], mo["a2"])
        rows.append(dict(sess=s, trial=p.name, old=eo, new=ef,
                         sh=sh, res=res, sh_old=sho, res_old=reso))
    return rows


def main():
    ds = [float(x) for x in (sys.argv[1] if len(sys.argv) > 1
                             else "0,0.004,0.006,0.008,0.012").split(",")]
    allr = {}
    print(f"세션 {SESS}\n")
    for dly in ds:
        rows = run(dly)
        if not rows:
            print(f"지연 {1000*dly:5.1f}ms : 결과 없음"); continue
        allr[f"{dly}"] = rows
        N = np.array([r["new"] for r in rows])
        O = np.array([r["old"] for r in rows])
        sh = np.array([r["sh"] for r in rows]); res = np.array([r["res"] for r in rows])
        tot = np.array([np.array(r["new"])[5] for r in rows])
        print(f"지연 {1000*dly:5.1f}ms | q·dq {N[:, :4].mean():5.2f} "
              f"| τ1 {N[:, 4].mean():5.2f} τ2 {N[:, 5].mean():5.2f} "
              f"| 무릎밀림 중앙 {np.median(sh):+6.1f}ms · 밀면 {res.mean():5.2f} "
              f"| 전채널 {N.mean():5.2f}", flush=True)
    O = np.array([r["old"] for r in allr[f"{ds[0]}"]])
    sho = np.array([r["sh_old"] for r in allr[f"{ds[0]}"]])
    print(f"\n(비교) 배포모델 OLD | q·dq {O[:, :4].mean():5.2f} | τ1 {O[:, 4].mean():5.2f} "
          f"τ2 {O[:, 5].mean():5.2f} | 무릎밀림 중앙 {np.median(sho):+6.1f}ms "
          f"| 전채널 {O.mean():5.2f}")
    safe.atomic_json_write(OUT, allr)
    print(f"\n저장 → {OUT}")


if __name__ == "__main__":
    main()
