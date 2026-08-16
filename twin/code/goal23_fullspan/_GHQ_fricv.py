# -*- coding: utf-8 -*-
"""_GHQ_fricv — **마찰이 속도에 따라 어떻게 변하나** (모델 없이, 08.07 무게추 왕복).

원리 (_GH9_friction 과 같음): 같은 자세를 지날 때
    올라갈 때 명령 = 중력 + 마찰 ,  내려갈 때 명령 = 중력 − 마찰
  ⇒ 마찰 = (올라갈때 − 내려갈때)/2 · 중력 = (올라갈때 + 내려갈때)/2
새로 하는 것: **자세 × 속도 2차원 칸**으로 갈라, 같은 자세 안에서 속도만 바꿔 가며 마찰을 본다.
  (자세와 속도는 왕복 궤적에서 상관돼 있으므로 자세를 고정하지 않으면 속도 의존을 못 읽는다)

속도는 dq 채널(1샘플 차분, 잡음 큼) 대신 **각도의 50ms 평활 미분**을 쓴다.
반전 직후 표본은 선택적으로 버린다 (되돌림 이력이 저속 마찰을 낮게 보이게 할 수 있다).

CLI: python _GHQ_fricv.py
"""
# --- 실험 데이터 경로: 단일 출처 (code/bench/datapaths.py) ---
import os as _o, sys as _s
_d = _o.path.dirname(_o.path.abspath(__file__))
while _d != _o.path.dirname(_d) and not _o.path.isdir(_o.path.join(_d, 'code', 'bench')):
    _d = _o.path.dirname(_d)
if _o.path.join(_d, 'code', 'bench') not in _s.path:
    _s.path.append(_o.path.join(_d, 'code', 'bench'))
from datapaths import DATA_ROOT, CVT_ROOT  # noqa: E402
# ---------------------------------------------------------------
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench")); os.chdir(HERE)
DATA = Path(DATA_ROOT)
OUT = HERE / "_GHQ_fricv.json"

FILES = [("0kg", "0kg/probe_sweep_v1"), ("0kg#2", "0kg/probe_sweep_v1 - 2"),
         ("2kg", "2kg/probe_sweep_v1"), ("4kg", "4kg/probe_sweep_v1")]
VED = np.array([0.015, 0.025, 0.04, 0.06, 0.09, 0.13, 0.18, 0.25, 0.35, 0.50, 0.70])
NPOS = 14
MINS = 12          # 칸마다 방향별 최소 표본수


def rd(p):
    df = pd.read_excel(p)
    c = {k.lower().replace(" ", ""): k for k in df.columns}
    g = lambda k: np.asarray(df[c[k]], float)
    return dict(t=g("time"), q=g("currentangle"), tau=g("currenttorque"))


def vel(t, q, w=25):
    dt = float(np.median(np.diff(t)))
    return np.convolve(np.gradient(q, dt), np.ones(w) / w, mode="same")


def rev_mask(v, dt, hold=0.25):
    """속도 부호가 바뀐 뒤 hold 초 이내면 True (버릴 표본)."""
    s = np.sign(v); s[s == 0] = 1
    ch = np.nonzero(np.diff(s) != 0)[0] + 1
    bad = np.zeros(len(v), bool)
    n = int(round(hold / dt))
    for i in ch:
        bad[i:i + n] = True
        bad[max(0, i - n):i] = True
    return bad


def cells(q, v, tau, drop_rev, dt):
    """(자세칸, 속도칸) → (마찰, 중력, n_up, n_dn, 자세중앙, 속도중앙)"""
    sp = np.abs(v)
    ok = sp >= VED[0]
    if drop_rev:
        ok &= ~rev_mask(v, dt)
    if ok.sum() < 500:
        return []
    lo, hi = np.percentile(q[ok], [2, 98])
    ped = np.linspace(lo, hi, NPOS + 1)
    out = []
    for i in range(NPOS):
        mp = ok & (q >= ped[i]) & (q < ped[i + 1])
        for j in range(len(VED) - 1):
            m = mp & (sp >= VED[j]) & (sp < VED[j + 1])
            up, dn = m & (v > 0), m & (v < 0)
            if up.sum() < MINS or dn.sum() < MINS:
                continue
            u, d = float(np.median(tau[up])), float(np.median(tau[dn]))
            out.append(dict(pos=float(np.degrees((ped[i] + ped[i + 1]) / 2)),
                            vbin=j, v=float(np.median(sp[m])),
                            fric=(u - d) / 2, grav=(u + d) / 2,
                            nu=int(up.sum()), nd=int(dn.sum())))
    return out


def report(tag, drop_rev):
    print("\n" + "=" * 108)
    print(f"■ {tag}  (반전 직후 0.25초 {'버림' if drop_rev else '포함'})")
    print("=" * 108)
    RES = {}
    for lab, rel in FILES:
        p = DATA / "26_08_07" / rel
        d = {nm: rd(p / f"{nm}.xlsx") for nm in ("hip", "knee")}
        for ch in ("hip", "knee"):
            x = d[ch]
            dt = float(np.median(np.diff(x["t"])))
            v = vel(x["t"], x["q"])
            cs = cells(x["q"], v, x["tau"], drop_rev, dt)
            if not cs:
                continue
            RES[f"{lab}/{ch}"] = cs
            # 속도칸별 집계 (자세는 칸 안에서 정규화하지 않은 생값)
            print(f"\n── {lab} {ch}  (칸 {len(cs)}개)")
            print(f"   {'속도칸[rad/s]':>16s} {'표본속도중앙':>12s} {'마찰(명령)':>12s} "
                  f"{'퍼짐(사분위)':>12s} {'칸수':>5s} {'|중력|중앙':>10s}")
            for j in range(len(VED) - 1):
                g = [c for c in cs if c["vbin"] == j]
                if len(g) < 2:
                    continue
                f = np.array([c["fric"] for c in g])
                print(f"   {VED[j]:.3f}~{VED[j+1]:.3f}".rjust(19)
                      + f" {np.median([c['v'] for c in g]):12.3f} {np.median(f):12.3f}"
                      + f" {np.percentile(f,25):5.3f}~{np.percentile(f,75):.3f}".rjust(13)
                      + f" {len(g):5d} {np.median([abs(c['grav']) for c in g]):10.2f}")
            # 자세를 고정한 짝짓기: 같은 자세칸 안에서 최저속칸 대비 비율
            byp = {}
            for c in cs:
                byp.setdefault(round(c["pos"], 1), []).append(c)
            rat = []
            for pos, g in byp.items():
                if len(g) < 2:
                    continue
                g = sorted(g, key=lambda c: c["v"])
                base = g[0]
                if abs(base["fric"]) < 1e-9:
                    continue
                for c in g[1:]:
                    rat.append((base["v"], c["v"], c["fric"] / base["fric"]))
            if rat:
                print(f"   같은 자세칸 안 짝짓기 {len(rat)}쌍: 느린쪽 {np.median([r[0] for r in rat]):.3f} → "
                      f"빠른쪽 {np.median([r[1] for r in rat]):.3f} rad/s 일 때 마찰비 중앙 "
                      f"{np.median([r[2] for r in rat]):.2f} "
                      f"(사분위 {np.percentile([r[2] for r in rat],25):.2f}~{np.percentile([r[2] for r in rat],75):.2f})")
                vlo, vhi = np.median([r[0] for r in rat]), np.median([r[1] for r in rat])
                print(f"     · tanh(v/0.3) 이라면 이 비는 {np.tanh(vhi/0.3)/np.tanh(vlo/0.3):.2f} 이어야 한다")
                print(f"     · 쿨롱(속도무관) 이라면 1.00")
    return RES


def main():
    A = report("A. 원본", False)
    B = report("B. 반전 직후 버림", True)
    import safe
    safe.atomic_json_write(OUT, dict(raw=A, norev=B))
    print(f"\n저장 → {OUT}")


if __name__ == "__main__":
    main()
