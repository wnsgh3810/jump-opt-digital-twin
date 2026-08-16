# -*- coding: utf-8 -*-
"""_GH8_statics — **정지 상태 두 개**로 모델을 검증한다 (마라톤H, 2026-08-11).

왜 이게 근본적인가 (사용자 지적 "hip3/knee3 도 줬는데 더 할 게 없나 — 근본적으로 부족")
  지금까지의 채점은 전부 **움직이는 구간**을 본다. 거기엔 관성·마찰·접촉·지연이 한꺼번에
  섞여 있어, 틀린 값 두 개가 서로를 가려도 점수는 좋게 나온다.
  `*3` 파일 앞부분에는 로봇이 **가만히 있는** 구간이 두 개 연달아 있다.
    ① 전원을 켜고 아직 바닥에 안 놓은 상태 (지면반력 ≈ 0)
    ② 바닥에 놓고 그 자세로 서 있는 상태 (지면반력 ≈ 로봇 무게)
  둘 다 속도 0·가속도 0 이므로 **관성이 지워진다**. 남는 것은 중력·기하·전동계뿐이다.
  ②−① 의 차이는 **체중이 다리에 실린 효과만** 남긴 값 — 접촉 마찰조차 세로힘이라 안 섞인다.

무엇을 재나
  · 각 trial 에서 두 평형의 (자세, 힙명령, 무릎명령, 지면반력) 을 뽑는다.
  · 같은 자세를 모델에 세워놓고 **버티는 데 필요한 관절토크**를 잰다.
  · 명령 → 실제 축토크 변환식 두 가지를 각각 대보고 어느 쪽이 정역학과 맞는지 본다.
    (모터는 **명령**만 기록한다. 축토크는 어디에도 측정되어 있지 않다.)

★ 08-11 실수 기록 3건 — 같은 함정을 다시 밟지 말 것
  ① 매 스텝이 끝난 뒤 몸통 높이를 되돌려놓았다 → 시뮬레이터는 로봇이 자유낙하 중이라고
     계산하므로 **다리에 중력이 안 걸린다**(엘리베이터 무중력). 유지토크가 전부 0 으로 나왔다.
     → 지지력을 **계산 안에** 넣어야 한다 (qfrc_applied).
  ② 4절 고리의 네 각도 중 커플러 핀을 0 으로 뒀다 → 고리가 벌어진 자세라 구속력이 폭발했다.
     → 정본 규약 cpin = +q2 (fs_runner 초기화와 동일).
  ③ 창의 뒤쪽 2/3 을 "공중"이라고 썼다 → 그 구간은 이미 **바닥에 놓인 뒤**였다.
     → 지면반력으로 두 평형을 갈라야 한다.

CLI: python _GH8_statics.py
"""
import os, sys, io, json, collections
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GH8_statics.json"
MIN_N = 100         # 평형 한 개로 인정할 최소 샘플 수 (500Hz 기준 0.2초)


def plateaus(d3, w):
    """창 안에서 **접촉 없는 정지**와 **접촉 있는 정지** 두 구간을 발밑 힘센서로 가른다.

    ★ 08-12 사용자 지시: 이 센서는 **절대값을 믿으면 안 되고**(측정이 정확하지 않다)
      **세션마다 교정이 달라 세션 간 비교도 안 된다.**
      → 그래서 고정된 절대 문턱(구 8.0)을 쓰지 않는다. **각 trial 이 자기 창 안에서**
        낮은 무리와 높은 무리의 중간을 문턱으로 삼는다 = 교정에 전혀 의존하지 않는다.
      쓰는 정보는 오직 "닿았나 / 안 닿았나" 뿐이고, 힘의 크기는 어디에도 안 들어간다.
      (두 무리 간격은 실측 28 [센서 단위] 이라 어떤 교정 오차로도 안 뒤집힌다.)
    """
    t = d3["t"]
    ix = np.flatnonzero((t >= w[0]) & (t <= w[1]))
    if len(ix) < 3 * MIN_N:
        return None
    g = d3["grf"][ix]
    lo, hi = np.percentile(g, 10), np.percentile(g, 90)
    if hi - lo < 5.0:                      # 두 무리가 안 갈리면 이 trial 은 버린다
        return None
    th = lo + 0.5 * (hi - lo)              # trial 자기 값으로만 정한 문턱
    air = ix[g < th]
    gnd = ix[g > th]
    if len(air) < MIN_N or len(gnd) < MIN_N:
        return None
    air = air[air < gnd.min()] if len(gnd) else air        # 접지 이전만
    gnd = gnd[gnd > gnd.min() + MIN_N]                     # 놓는 과도 제외
    if len(air) < MIN_N or len(gnd) < MIN_N:
        return None
    # 각 구간에서 가장 조용한 부분(속도가 가장 작은 절반)만 쓴다
    def calm(a):
        v = np.abs(d3["dq1"][a]) + np.abs(d3["dq2"][a])
        return a[v <= np.median(v)]
    return calm(air), calm(gnd)


def snap(d3, a):
    return dict(q1=float(np.median(d3["q1"][a])), q2=float(np.median(d3["q2"][a])),
                r1=float(np.median(d3["raw1"][a])), r2=float(np.median(d3["raw2"][a])),
                grf=float(np.median(d3["grf"][a])), n=int(len(a)))


class Twin:
    """모델을 세워놓고 **버티는 데 필요한 관절토크**를 재는 도구."""

    def __init__(self):
        import mujoco as mjm, fs_runner as FR
        self.mjm = mjm
        self.ft = FR.fs_twin()
        self.m = self.ft["model"]; self.iq = self.ft["iq"]; self.dof = self.ft["dof"]
        self.fg = mjm.mj_name2id(self.m, mjm.mjtObj.mjOBJ_GEOM, "foot")

    def _put(self, md, q1, q2, bz):
        iq = self.iq
        md.qpos[:] = 0
        md.qpos[iq["hip_m"]] = -q1 - np.pi / 2
        md.qpos[iq["knee_motor"]] = -q2
        md.qpos[iq["cpin"]] = q2                 # ★ 4절 고리를 닫는 값 (0 이면 폭발)
        md.qpos[iq["knee"]] = -q2
        md.qpos[iq["base_z"]] = bz
        self.mjm.mj_forward(self.m, md)
        md.qvel[:] = 0

    def hold(self, q1, q2, ground, n=8000):
        """반환 (힙토크, 크랭크토크, 남은자세오차°). ground=False 면 몸통을 매달아 지지한다."""
        mjm = self.mjm
        md = mjm.MjData(self.m)
        self._put(md, q1, q2, 1.0)
        if ground:                                # 발을 바닥에 정확히 올려놓는다
            md.qpos[self.iq["base_z"]] = 1.0 - float(md.geom_xpos[self.fg][2]) \
                + float(self.m.geom_size[self.fg][0])
            mjm.mj_forward(self.m, md); md.qvel[:] = 0
        t1 = -q1 - np.pi / 2; t2 = -q2
        T = []
        for k in range(n):
            if not ground:
                # 몸통은 틀이 붙잡는다 → 지지력을 **계산 안에** 넣는다 (사후 되돌리기 금지)
                md.qfrc_applied[self.dof["base_z"]] = \
                    3000 * (1.0 - md.qpos[self.iq["base_z"]]) - 200 * md.qvel[self.dof["base_z"]]
            u1 = 400 * (t1 - md.qpos[self.iq["hip_m"]]) - 20 * md.qvel[self.dof["hip_m"]]
            u2 = 400 * (t2 - md.qpos[self.iq["knee_motor"]]) - 20 * md.qvel[self.dof["knee_motor"]]
            md.ctrl[:] = [u1, u2]
            mjm.mj_step(self.m, md)
            if k > n - 500:
                T.append([u1, u2])
        T = np.array(T)
        er = max(abs(np.degrees(t1 - md.qpos[self.iq["hip_m"]])),
                 abs(np.degrees(t2 - md.qpos[self.iq["knee_motor"]])))
        return -T[:, 0].mean(), -T[:, 1].mean(), er


def main():
    import fs_data as FD, fs_runner as FR
    from sea_twin2 import ahat_np
    TW = Twin()
    cvA = lambda r: float(ahat_np(np.array([r]), np.array([0.0]))[0])       # 지금 쓰는 0.58배
    cvC = lambda r, cap: float(FR.tmap_closed(r, 0.0, cap=cap))             # 분동 저울 곡선
    G = collections.defaultdict(list)
    for s, p, g, cvt, ho in FD.registry():
        d3 = FD.load3(p)
        if d3 is None:
            continue
        w = FD.air_window(p, d3)
        if w is None:
            continue
        pl = plateaus(d3, w)
        if pl is None:
            continue
        A, B = snap(d3, pl[0]), snap(d3, pl[1])
        mh_a, mk_a, e_a = TW.hold(A["q1"], A["q2"], ground=False)
        mh_g, mk_g, e_g = TW.hold(B["q1"], B["q2"], ground=True)
        G[s].append(dict(trial=p.name, air=A, gnd=B, cvt=bool(cvt),
                         m_air=[mh_a, mk_a, e_a], m_gnd=[mh_g, mk_g, e_g]))
    if not G:
        raise SystemExit("평형을 못 찾음")

    print("두 정지 평형 — 모델이 요구하는 유지토크 vs 실제 명령\n")
    print("① 공중 (접촉 없음). 관성·접촉·마찰이 전부 빠지고 중력·기하만 남는다.")
    print(f"{'세션':10s} {'n':>3s} {'자세 q1,q2[°]':>14s} | {'모델 힙':>8s} {'실측 힙':>8s} | "
          f"{'모델 무릎':>9s} {'실측 무릎':>9s}")
    RA = []
    for s in sorted(G):
        v = G[s]
        a = np.array([[x["air"]["q1"], x["air"]["q2"], x["m_air"][0], x["air"]["r1"],
                       x["m_air"][1], x["air"]["r2"]] for x in v])
        RA += list(a)
        print(f"{s:10s} {len(v):3d} {np.degrees(np.median(a[:,0])):6.1f},{np.degrees(np.median(a[:,1])):6.1f} | "
              f"{np.median(a[:,2]):8.2f} {np.median(a[:,3]):8.2f} | {np.median(a[:,4]):9.2f} {np.median(a[:,5]):9.2f}")
    RA = np.array(RA)

    print("\n② 바닥에 서 있음 (체중이 다리에 실림).")
    print(f"{'세션':10s} {'n':>3s} {'자세 q1,q2[°]':>14s} | {'모델 힙':>8s} {'실측 힙':>8s} | "
          f"{'모델 무릎':>9s} {'실측 무릎':>9s} {'0.58배':>7s} {'분동곡선':>8s}")
    RG = []
    for s in sorted(G):
        v = G[s]
        a = np.array([[x["gnd"]["q1"], x["gnd"]["q2"], x["m_gnd"][0], x["gnd"]["r1"],
                       x["m_gnd"][1], x["gnd"]["r2"], cvA(x["gnd"]["r2"]),
                       cvC(x["gnd"]["r2"], 3.8)] for x in v])
        RG += list(a)
        print(f"{s:10s} {len(v):3d} {np.degrees(np.median(a[:,0])):6.1f},{np.degrees(np.median(a[:,1])):6.1f} | "
              f"{np.median(a[:,2]):8.2f} {np.median(a[:,3]):8.2f} | {np.median(a[:,4]):9.2f} "
              f"{np.median(a[:,5]):9.2f} {np.median(a[:,6]):7.2f} {np.median(a[:,7]):8.2f}")
    RG = np.array(RG)

    print("\n③ ②−① = **체중이 실린 효과만** (자세는 거의 같으므로 중력 레버 오차가 상쇄된다)")
    dh_m = np.median(RG[:, 2] - RA[:, 2]); dk_m = np.median(RG[:, 4] - RA[:, 4])
    dh_r = np.median(RG[:, 3] - RA[:, 3]); dk_r = np.median(RG[:, 5] - RA[:, 5])
    print(f"   모델이 필요하다고 하는 증가분 : 힙 {dh_m:+.2f} · 무릎 {dk_m:+.2f} N·m")
    print(f"   실제 명령의 증가분            : 힙 {dh_r:+.2f} · 무릎 {dk_r:+.2f}")
    print(f"   → 무릎에서 명령 1 이 실제 축토크 몇 N·m 인가 = {dk_m/dk_r:.3f}")
    print(f"      지금 쓰는 변환식은 0.58 · 분동 저울 곡선은 이 토크대에서 약 1.26")
    import safe
    safe.atomic_json_write(OUT, {s: G[s] for s in G})
    print(f"\n저장 → {OUT}")


if __name__ == "__main__":
    main()
