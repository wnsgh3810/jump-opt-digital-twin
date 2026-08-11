# -*- coding: utf-8 -*-
"""_GH7_airboard — **공중 구간** 채점판 (마라톤H, 2026-08-11).

왜 이게 근본적인가 (사용자 지적 "hip3/knee3 도 줬는데 더 할 게 없나 — 근본적으로 부족")
  지금까지의 모든 채점판(주입재생·폐루프)은 **발이 땅에 닿은 구간**만 본다.
  거기엔 마찰·슬립·접촉강성이 섞여 있어 오차가 **플랜트 탓인지 접촉 탓인지** 못 가른다.
  `*3` 파일에는 **접지 이전 공중 구간**(전원인가~바닥 안착)이 있다. 접촉이 없으므로
  남는 것은 **질량·관성·중력·전동계뿐**. 실제 66 trial (held-out 0324·변속 0429·미사용 0422 포함).

무엇을 재나
  공중 구간을 **짧은 조각**으로 나눠, 조각마다 실측 상태에서 다시 출발시켜
  측정 토크를 주입하고 관절각·각속도를 예측 → 실측과 비교.
  · 공중 오차가 작다 → 플랜트는 맞다. 남은 결손은 **접촉**에 있다.
  · 공중 오차가 크다 → 플랜트가 틀렸고, 지상에서 맞춘 것들은 그걸 **보상**하던 것이다.

★ 08-11 실수 기록: 처음엔 공중 창(10~40초)을 **통째로** 적분했다가 오차 9000° 로 완전 발산했다.
  개루프는 되먹임이 없어 긴 구간을 못 버틴다 — 지상 채점판이 0.4초 창을 쓰는 이유가 이것이다.
  조각마다 앵커를 다시 잡아야 **모델의 단기 예측력**을 재는 것이 된다.

★ 가정: 공중에서 몸통은 레일에 매달려 고정 (전원인가 시점). base_z 를 매 스텝 고정한다.
  가정이 깨지면 결과 무효 — 예측이 통째로 어긋나면 이걸 먼저 의심할 것.

CLI: python _GH7_airboard.py       (env: GH7_WIN 조각창[s] · GH7_STR 간격[s])
"""
import os, sys, io, json, collections
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("P25_CLIP_RAW", "35.5")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GH7_airboard.json"
WIN = float(os.environ.get("GH7_WIN", "0.4"))
STR = float(os.environ.get("GH7_STR", "0.3"))
BZ = 1.5                                   # 발이 바닥에 안 닿을 만큼 높은 위치 [m]


def _seg(ix, d3, ft, P, A, tmap, mjm):
    """조각 하나: 시작 실측 상태 앵커 → 측정 토크 주입 → 4채널 RMSE."""
    m = ft["model"]; iq = ft["iq"]; dof = ft["dof"]
    j0 = ix[0]
    tg = d3["t"][ix] - d3["t"][j0]
    md = mjm.MjData(m)
    md.qpos[:] = 0
    md.qpos[iq["base_z"]] = BZ
    md.qpos[iq["hip_m"]] = -float(d3["q1"][j0]) - np.pi / 2
    md.qpos[iq["knee_motor"]] = -float(d3["q2"][j0])
    md.qpos[iq["knee"]] = -float(d3["q2"][j0])
    mjm.mj_forward(m, md)
    md.qvel[:] = 0
    md.qvel[dof["hip_m"]] = -float(d3["dq1"][j0])
    md.qvel[dof["knee_motor"]] = -float(d3["dq2"][j0])
    dt = m.opt.timestep
    N = int(round(float(tg[-1]) / dt))
    if N < 5:
        return None
    r1 = d3["raw1"][ix]; r2 = d3["raw2"][ix]
    Q = np.zeros((N, 4))
    for k in range(N):
        tc = k * dt
        v1 = -float(md.qvel[dof["hip_m"]]); v2 = -float(md.qvel[dof["knee_motor"]])
        c1 = float(np.interp(tc, tg, r1)); c2 = float(np.interp(tc, tg, r2))
        if tmap is not None:
            s1 = tmap(c1, v1, 0); s2 = tmap(c2, v2, 1)
        else:
            s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1]))[0])
            s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2]))[0])
        md.ctrl[:] = [-s1, -s2]
        mjm.mj_step(m, md)
        md.qpos[iq["base_z"]] = BZ                 # 몸통 매달림 고정
        md.qvel[dof["base_z"]] = 0.0
        if not np.isfinite(md.qpos).all():
            return None
        Q[k] = [-md.qpos[iq["hip_m"]] - np.pi / 2, -md.qpos[iq["knee_motor"]],
                -md.qvel[dof["hip_m"]], -md.qvel[dof["knee_motor"]]]
    tl = np.arange(N) * dt
    g = lambda j: np.interp(tg, tl, Q[:, j])
    e = lambda a, b, deg: float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2))) * \
        (180 / np.pi if deg else 1)
    return [e(g(0), d3["q1"][ix], True), e(g(1), d3["q2"][ix], True),
            e(g(2), d3["dq1"][ix], False), e(g(3), d3["dq2"][ix], False)]


def run_trial(d3, w, ft, P, A, tmap):
    import mujoco as mjm
    t = d3["t"]
    msk = (t >= w[0]) & (t <= w[1])
    if msk.sum() < 60:
        return None
    idx = np.flatnonzero(msk)
    tt = t[idx]
    dt_d = float(np.median(np.diff(tt)))
    nw = max(5, int(WIN / dt_d)); ns = max(1, int(STR / dt_d))
    E = []
    for a in range(0, max(1, len(idx) - nw), ns):
        r = _seg(idx[a:a + nw], d3, ft, P, A, tmap, mjm)
        if r is not None:
            E.append(r)
    if not E:
        return None
    return np.array(E).mean(axis=0), float(tt[-1] - tt[0]), len(E)


def main():
    import fs_data as FD, fs_runner as FR, fs_metric as FMET
    ft = FR.fs_twin()
    P = FMET.tw0["P"]; A = P.A_PAPER
    tmap = FR._tmap_init(P, A)
    G = collections.defaultdict(list); nf = 0
    for s, p, g, cvt, ho in FD.registry():
        try:
            d3 = FD.load3(p)
            if d3 is None:
                continue
            w = FD.air_window(p, d3)
            if w is None:
                continue
            r = run_trial(d3, w, ft, P, A, tmap)
        except Exception:
            nf += 1; continue
        if r is None:
            nf += 1; continue
        ch, dur, nseg = r
        G[s].append(list(ch) + [dur, nseg])
    if not G:
        raise SystemExit(f"결과 없음 (실패 {nf})")
    print(f"공중 구간 — 조각 {WIN}s / 간격 {STR}s · 측정 토크 주입 · 접촉 없음 (실패 {nf})\n")
    print(f"{'세션':10s} {'n':>3s} {'조각':>4s} | {'힙각°':>7s} {'무릎각°':>8s} {'힙속':>7s} {'무릎속':>7s}")
    for s in sorted(G):
        a = np.array(G[s])
        print(f"{s:10s} {len(a):3d} {np.median(a[:,5]):4.0f} | " +
              " ".join(f"{np.median(a[:,i]):7.3f}" for i in range(4)))
    A_ = np.array([x for s in G for x in G[s]])
    print(f"\n전체 {len(A_)} trial 중앙: 힙각 {np.median(A_[:,0]):.3f}° · 무릎각 {np.median(A_[:,1]):.3f}° "
          f"· 힙속 {np.median(A_[:,2]):.3f} · 무릎속 {np.median(A_[:,3]):.3f}")
    import safe
    safe.atomic_json_write(OUT, {s: np.array(v).tolist() for s, v in G.items()})
    print(f"저장 → {OUT}")


if __name__ == "__main__":
    main()
