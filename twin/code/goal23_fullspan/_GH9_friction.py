# -*- coding: utf-8 -*-
"""_GH9_friction — 매달린 상태에서 **중력과 마찰을 갈라낸다** (마라톤H, 2026-08-11).

왜 (사용자 지시 "기어비·모터 마찰·조인트 마찰의 영향도 고려해야 한다")
  `_GH8_statics` 에서 정지 평형으로 변환식을 확정했는데, 그 계산에는 **마찰이 통째로 빠져 있다.**
  정지 상태에서 건마찰(정지마찰)이 하중 일부를 대신 버티면 모터 명령은 "필요한 토크 − 마찰"이
  되므로 변환 비율이 그만큼 흔들린다. 그리고 공중 정지에서 힙 명령이 세션마다
  0.01~0.73 으로 **흩어진** 것 자체가 건마찰의 서명이다 (무게중심 오차라면 일정하게 어긋난다).

재는 법 — 방향 분해 (교과서적 방법)
  로봇을 공중에 매달고 다리를 천천히 왕복시킨다. **같은 자세**를 지날 때
      올라갈 때 명령 = 중력 + 마찰
      내려갈 때 명령 = 중력 − 마찰
  이므로
      중력 = (올라갈 때 + 내려갈 때) / 2
      마찰 = (올라갈 때 − 내려갈 때) / 2
  중력은 자세만의 함수, 마찰은 방향만의 함수라는 성질을 이용한다. 접촉이 없으므로
  바닥 마찰은 안 섞이고, 천천히 움직이므로 관성도 작다.

  마찰을 속도 구간별로 나눠 보면 **건마찰(속도와 무관한 일정값)** 과
  **점성마찰(속도에 비례)** 도 갈라진다. 기어박스를 거친 모터 마찰은 이 둘로 나타난다.

데이터
  `26_03_24/sit2stand/*` — 사용자 확인 공중(매달림) 세션. 힙 −46°~−18°, 무릎 −145°~−90° 왕복.
  `26_03_11/sit2stand_noTr_chirp_Air` — 공중 주파수 쓸기. 더 넓은 범위 (힙 −45°~0°).
  ※ 점프 trial 의 체공 구간은 **못 쓴다** — 로봇 전체가 자유낙하라 중력이 사라진다
    (떨어지는 엘리베이터 안에서 무중력). 거기서는 관성·마찰만 나온다.

CLI: python _GH9_friction.py
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
import os, sys, io, json, collections
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GH9_friction.json"
DATA = Path(DATA_ROOT)

FOLDS = [
    "26_03_24/sit2stand/sit2stand_P10_D0",
    "26_03_24/sit2stand/sit2stand_P10_D1",
    "26_03_24/sit2stand/sit2stand_P20_D1",
    "26_03_24/sit2stand/sit2stand_P30_D1",
    "26_03_24/sit2stand/sit2stand_P60_D1.5_P60_D2",
    "26_03_11/sit2stand_noTr_chirp_Air",
]
VLO, VHI = 0.05, 0.60          # 느리게 움직이는 구간만 (관성·점성 최소) [rad/s]
NBIN = 12


def load(fold: Path):
    h = pd.read_excel(fold / "hip.xlsx"); k = pd.read_excel(fold / "knee.xlsx")
    n = min(len(h), len(k))
    g = lambda df, c: df[c].to_numpy(float)[:n]
    return dict(t=g(h, "Time"), q1=g(h, "currentAngle"), q2=g(k, "currentAngle"),
                v1=g(h, "currentAngleVelocity"), v2=g(k, "currentAngleVelocity"),
                r1=g(h, "currentTorque"), r2=g(k, "currentTorque"))


def split(q, v, r, vlo=VLO, vhi=VHI, nbin=NBIN):
    """자세를 구간으로 나눠 **올라갈 때 / 내려갈 때** 명령의 평균을 각각 낸다."""
    sp = np.abs(v)
    ok = (sp > vlo) & (sp < vhi)
    if ok.sum() < 200:
        return None
    lo, hi = np.percentile(q[ok], [3, 97])
    ed = np.linspace(lo, hi, nbin + 1)
    out = []
    for i in range(nbin):
        m = ok & (q >= ed[i]) & (q < ed[i + 1])
        up = m & (v > 0); dn = m & (v < 0)
        if up.sum() < 20 or dn.sum() < 20:
            continue
        u, d = float(np.median(r[up])), float(np.median(r[dn]))
        out.append(((ed[i] + ed[i + 1]) / 2, (u + d) / 2, (u - d) / 2, int(up.sum()), int(dn.sum())))
    return np.array(out) if out else None


def vscan(q, v, r, nb=6):
    """마찰이 속도에 따라 어떻게 변하나 — 건마찰(일정)과 점성마찰(비례)을 가른다."""
    sp = np.abs(v); res = []
    ed = np.array([0.05, 0.15, 0.3, 0.6, 1.2, 2.4, 5.0])
    for i in range(len(ed) - 1):
        m = (sp >= ed[i]) & (sp < ed[i + 1])
        if m.sum() < 200:
            continue
        s = split(q[m], v[m], r[m], vlo=ed[i], vhi=ed[i + 1], nbin=6)
        if s is None:
            continue
        res.append(((ed[i] + ed[i + 1]) / 2, float(np.median(s[:, 2])), int(m.sum())))
    return np.array(res) if res else None


class Twin:
    """모델을 매달아놓고 그 자세를 버티는 데 필요한 관절토크를 잰다 (접촉 없음)."""

    def __init__(self):
        import mujoco as mjm, fs_runner as FR
        self.mjm = mjm
        ft = FR.fs_twin()
        self.m = ft["model"]; self.iq = ft["iq"]; self.dof = ft["dof"]

    def hold(self, q1, q2, n=5000):
        mjm = self.mjm; iq = self.iq; dof = self.dof
        md = mjm.MjData(self.m)
        md.qpos[:] = 0
        md.qpos[iq["hip_m"]] = -q1 - np.pi / 2
        md.qpos[iq["knee_motor"]] = -q2
        md.qpos[iq["cpin"]] = q2                # 4절 고리를 닫는 값
        md.qpos[iq["knee"]] = -q2
        md.qpos[iq["base_z"]] = 1.0
        mjm.mj_forward(self.m, md); md.qvel[:] = 0
        t1 = -q1 - np.pi / 2; t2 = -q2; T = []
        for k in range(n):
            md.qfrc_applied[dof["base_z"]] = \
                3000 * (1.0 - md.qpos[iq["base_z"]]) - 200 * md.qvel[dof["base_z"]]
            u1 = 400 * (t1 - md.qpos[iq["hip_m"]]) - 20 * md.qvel[dof["hip_m"]]
            u2 = 400 * (t2 - md.qpos[iq["knee_motor"]]) - 20 * md.qvel[dof["knee_motor"]]
            md.ctrl[:] = [u1, u2]
            mjm.mj_step(self.m, md)
            if k > n - 300:
                T.append([u1, u2])
        T = np.array(T)
        return -T[:, 0].mean(), -T[:, 1].mean()


def main():
    import fs_runner as FR
    TW = Twin()
    cv = lambda r, cap: float(FR.tmap_closed(r, 0.0, cap=cap))   # 명령 → 실제 축토크
    RES = {}
    print("매달린 상태에서 중력과 마찰 가르기 — 같은 자세를 올라갈 때 vs 내려갈 때\n")
    for f in FOLDS:
        p = DATA / f
        if not (p / "hip.xlsx").exists():
            print(f"  ✗ {f}: 없음"); continue
        d = load(p)
        s1 = split(d["q1"], d["v1"], d["r1"])
        s2 = split(d["q2"], d["v2"], d["r2"])
        if s1 is None or s2 is None:
            print(f"  ✗ {f}: 느린 왕복 구간 부족"); continue
        RES[f] = dict(hip=s1.tolist(), knee=s2.tolist())
        print(f"── {f}")
        print(f"   {'힙 자세°':>8s} {'중력(명령)':>10s} {'마찰(명령)':>10s} | "
              f"{'무릎 자세°':>10s} {'중력(명령)':>10s} {'마찰(명령)':>10s}")
        for i in range(max(len(s1), len(s2))):
            a = f"{np.degrees(s1[i,0]):8.1f} {s1[i,1]:10.2f} {s1[i,2]:10.3f}" if i < len(s1) else " " * 30
            b = f"{np.degrees(s2[i,0]):10.1f} {s2[i,1]:10.2f} {s2[i,2]:10.3f}" if i < len(s2) else ""
            print(f"   {a} | {b}")
        print(f"   → 마찰 중앙: 힙 {np.median(s1[:,2]):+.3f} · 무릎 {np.median(s2[:,2]):+.3f} (명령 단위)")
        print(f"     축토크로  : 힙 {cv(np.median(s1[:,2]),2.6):+.3f} · "
              f"무릎 {cv(np.median(s2[:,2]),3.8):+.3f} N·m\n")

    print("\n마찰이 속도에 따라 변하나 (건마찰=일정 · 점성마찰=속도 비례)")
    for f in FOLDS:
        p = DATA / f
        if not (p / "hip.xlsx").exists() or f not in RES:
            continue
        d = load(p)
        for nm, q, v, r in (("힙", d["q1"], d["v1"], d["r1"]), ("무릎", d["q2"], d["v2"], d["r2"])):
            vs = vscan(q, v, r)
            if vs is None:
                continue
            RES[f][f"vscan_{nm}"] = vs.tolist()
            txt = " · ".join(f"{a:.2f}rad/s→{b:+.3f}" for a, b, _ in vs)
            print(f"   {f.split('/')[-1][:28]:28s} {nm:4s} {txt}")

    print("\n\n중력 곡선: 실측(명령→축토크 변환) vs 모델")
    for f in list(RES)[:3]:
        d = load(DATA / f)
        s1 = np.array(RES[f]["hip"]); s2 = np.array(RES[f]["knee"])
        print(f"── {f}")
        print(f"   {'힙°':>7s} {'무릎°':>8s} | {'실측 힙':>8s} {'모델 힙':>8s} | {'실측 무릎':>10s} {'모델 무릎':>10s}")
        for i in range(min(len(s1), len(s2))):
            q1 = s1[i, 0]
            # 같은 시각의 무릎 자세를 찾는다 (두 관절이 함께 움직이므로)
            j = int(np.argmin(np.abs(d["q1"] - q1)))
            q2 = float(d["q2"][j])
            mh, mk = TW.hold(q1, q2)
            print(f"   {np.degrees(q1):7.1f} {np.degrees(q2):8.1f} | {cv(s1[i,1],2.6):8.2f} {mh:8.2f} | "
                  f"{cv(np.interp(q2, s2[:,0][::-1] if s2[0,0]>s2[-1,0] else s2[:,0], s2[:,1][::-1] if s2[0,0]>s2[-1,0] else s2[:,1]),3.8):10.2f} {mk:10.2f}")
        print()
    import safe
    safe.atomic_json_write(OUT, RES)
    print(f"저장 → {OUT}")


if __name__ == "__main__":
    main()
