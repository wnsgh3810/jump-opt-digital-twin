# -*- coding: utf-8 -*-
"""_GHE_inertia — 다리의 **회전 관성**을 공중 흔들기 데이터로 직접 식별한다 (마라톤H, 08-12).

왜 필요한가 (사용자 지시 "다리 회전 관성을 점수가 못 본다 — 판별 실험이 필요")
  08-12 확인: 링크 자체의 회전 관성을 ±50% 바꿔도 종합 점수가 0.06% 밖에 안 움직인다.
  즉 지금 쓰는 점수로는 이 값이 **정해지지 않는다.** 정해지지 않은 값을 들고
  새 상황(무거운 짐·앞으로 뛰기)을 예측하면 위험하다.

왜 "순간 가속도" 로는 못 재나 (08-12 에 한 번 헛짚었다)
  단위 토크를 넣고 즉시 생기는 가속도로 관성을 재려 했더니, 힙은 회전자만, 무릎은
  크랭크 근처만 느껴졌다. 힙에는 **직렬 스프링**이 있고 4절 고리 구속도 무한히 단단하지
  않아, **아주 짧은 순간에는 먼 쪽 링크가 아직 안 딸려온다.** 그래서 그 방법은 무효다.
  ⇒ 실제 시간 규모(0.2~0.3초)에서 **굴려서** 재야 한다.

방법
  로봇을 공중에 매달고 다리를 흔든 기록(`26_03_11/..._chirp_Air`, `26_03_24/sit2stand/*`)에서
  **가속이 큰 조각**만 골라, 조각마다 실측 상태에서 출발시켜 측정 토크를 주입하고
  0.25초 예측한다. 접촉이 없으므로 남는 것은 중력·마찰·**관성**뿐이고, 중력과 마찰은
  이미 같은 데이터에서 방향분해로 쟀다(`_GH9_friction`). 남는 자유도가 관성이다.
  관성 배율을 훑어 **예측이 실측과 가장 잘 맞는 값**을 찾는다.

★ 08-11~12 에 밟은 함정 3개를 여기서 전부 피한다
  ① 몸통 지지력을 **계산 안에** 넣는다 (사후 복원하면 자유낙하로 계산돼 다리가 무중력)
  ② 4절 고리의 커플러 핀을 **cpin = +q2** 로 닫는다 (0 이면 구속력 폭발)
  ③ 힙 직렬 스프링의 처짐을 주입 토크로 **미리 채운다** (0 이면 t=0 에 토크가 안 전달됨)

CLI: python _GHE_inertia.py
"""
import os, sys, io, json, collections
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GHE_inertia.json"
DATA = Path("C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
FOLDS = ["26_03_11/sit2stand_noTr_chirp_Air",
         "26_03_24/sit2stand/sit2stand_P60_D1.5_P60_D2",
         "26_03_24/sit2stand/sit2stand_P30_D1",
         "26_03_24/sit2stand/sit2stand_P20_D1"]
WIN = 0.25          # 조각 길이 [s] — 관성이 드러날 만큼 길고 발산 안 할 만큼 짧게
NSEG = 40           # trial 당 조각 수 (가속이 큰 순서로)
BZ = 1.5            # 발이 바닥에 안 닿는 높이 [m]
# ★ 매달아 놓은 몸통을 얼마나 단단히 붙잡는가. 실제로는 로봇이 매달려 흔들렸을 수 있고,
#   그러면 다리 입장에서는 **관성이 더 있는 것처럼** 보인다 — 관성 결손과 헷갈린다.
KB = float(os.environ.get("GHE_KBASE", "3000"))   # [N/m] · 0 이면 아예 안 붙잡음


def load(fold: Path):
    h = pd.read_excel(fold / "hip.xlsx"); k = pd.read_excel(fold / "knee.xlsx")
    n = min(len(h), len(k))
    g = lambda df, c: df[c].to_numpy(float)[:n]
    return dict(t=g(h, "Time") - g(h, "Time")[0],
                q1=g(h, "currentAngle"), q2=g(k, "currentAngle"),
                v1=g(h, "currentAngleVelocity"), v2=g(k, "currentAngleVelocity"),
                r1=g(h, "currentTorque"), r2=g(k, "currentTorque"))


def pick(d, nseg=NSEG, win=WIN):
    """가속이 큰 조각을 고른다 — 관성은 **가속에서만** 드러난다."""
    t = d["t"]; dt = float(np.median(np.diff(t)))
    nw = int(win / dt)
    if len(t) < 3 * nw:
        return []
    a1 = np.abs(np.gradient(d["v1"], dt)); a2 = np.abs(np.gradient(d["v2"], dt))
    sc = np.convolve(a1 + a2, np.ones(nw) / nw, mode="valid")
    order = np.argsort(sc)[::-1]
    out = []
    for i in order:
        if len(out) >= nseg:
            break
        if all(abs(i - j) > nw for j in out):
            out.append(int(i))
    return sorted(out), nw


def run(ft, d, segs, nw, tmap, KS):
    import mujoco as mjm
    m = ft["model"]; iq = ft["iq"]; dof = ft["dof"]
    dt = float(m.opt.timestep)
    E = []
    for a in segs:
        ix = np.arange(a, a + nw)
        tg = d["t"][ix] - d["t"][ix[0]]
        md = mjm.MjData(m)
        q1 = float(d["q1"][ix[0]]); q2 = float(d["q2"][ix[0]])
        s1 = tmap(float(d["r1"][ix[0]]), float(d["v1"][ix[0]]), 0)
        defl = float(np.clip(s1 / KS, -0.3, 0.3))      # ③ 힙 스프링 처짐 미리 채우기
        md.qpos[:] = 0
        md.qpos[iq["hip_m"]] = -q1 - np.pi / 2 - defl
        md.qpos[iq["hip"]] = defl
        md.qpos[iq["knee_motor"]] = -q2
        md.qpos[iq["cpin"]] = q2                        # ② 고리를 닫는 값
        md.qpos[iq["knee"]] = -q2
        md.qpos[iq["base_z"]] = BZ
        mjm.mj_forward(m, md)
        md.qvel[:] = 0
        md.qvel[dof["hip_m"]] = -float(d["v1"][ix[0]])
        md.qvel[dof["knee_motor"]] = -float(d["v2"][ix[0]])
        N = int(round(float(tg[-1]) / dt))
        Q = np.zeros((N, 2)); ok = True
        for kk in range(N):
            tc = kk * dt
            v1 = -float(md.qvel[dof["hip_m"]]); v2 = -float(md.qvel[dof["knee_motor"]])
            c1 = float(np.interp(tc, tg, d["r1"][ix])); c2 = float(np.interp(tc, tg, d["r2"][ix]))
            md.ctrl[:] = [-tmap(c1, v1, 0), -tmap(c2, v2, 1)]
            # ① 몸통 지지력을 계산 안에 넣는다
            md.qfrc_applied[dof["base_z"]] = KB * (BZ - md.qpos[iq["base_z"]]) \
                - 2.0 * np.sqrt(max(KB, 1e-9) * 3.3) * md.qvel[dof["base_z"]] \
                + float(sum(m.body_mass)) * 9.81      # 무게는 미리 받쳐 처짐을 없앤다
            mjm.mj_step(m, md)
            if not np.isfinite(md.qpos).all():
                ok = False; break
            # ★ 각도계는 **모터 쪽**을 잰다 (정본 채점판도 모터측 thm1 을 쓴다).
            #   힙은 모터와 링크 사이에 스프링이 있으므로, 처짐을 더하면 링크 쪽이 되어
            #   **측정과 다른 것을 비교하게 된다** — 08-12 에 한 번 그렇게 재고 있었다.
            Q[kk] = [-md.qpos[iq["hip_m"]] - np.pi / 2,
                     -md.qpos[iq["knee_motor"]]]
        if not ok:
            continue
        tl = np.arange(N) * dt
        e1 = np.degrees(np.sqrt(np.mean((np.interp(tg, tl, Q[:, 0]) - d["q1"][ix]) ** 2)))
        e2 = np.degrees(np.sqrt(np.mean((np.interp(tg, tl, Q[:, 1]) - d["q2"][ix]) ** 2)))
        if np.isfinite(e1) and np.isfinite(e2) and max(e1, e2) < 1e3:
            E.append([e1, e2])
    return np.array(E) if E else None


def main():
    import fs_runner as FR, fs_metric as FMET
    P = FMET.tw0["P"]; A = P.A_PAPER
    D = {f: load(DATA / f) for f in FOLDS if (DATA / f / "hip.xlsx").exists()}
    print("공중 흔들기로 다리 회전 관성 식별 — 가속이 큰 조각만 사용\n")
    for f, d in D.items():
        s, nw = pick(d)
        print(f"  {f.split('/')[-1][:30]:30s} 조각 {len(s)} 개 × {WIN}s")
    print()
    # ★ 관성 부족과 **토크 과다**는 이 시험에서 같은 그림을 만든다 (둘 다 덜 움직이게 한다).
    #   그래서 토크 크기 배율도 같이 훑어 **어느 쪽이 더 잘 맞추는지**로 가른다.
    # ★ 관성 부족과 **명령 지연**도 이 시험에서 같은 그림을 만든다 (둘 다 반응을 느리게).
    #   지연은 이미 스택에 3ms 가 있다 — 그것을 늘려 관성만큼 설명되는지 본다.
    SCAN = [("(현행)", None),
            ("힙 회전자 ×2", {"FS_HIPM_ARM": "0.020"}),
            ("힙 회전자 ×4", {"FS_HIPM_ARM": "0.040"}),
            ("힙 명령지연 ×2 (6ms)", {"FS_CMD_LPF": "0.0063,0.00292"}),
            ("힙 명령지연 ×4 (13ms)", {"FS_CMD_LPF": "0.0127,0.00292"}),
            ("힙 명령지연 ×8 (25ms)", {"FS_CMD_LPF": "0.0253,0.00292"}),
            ("힙 감쇠 ×3", {"FS_HIPM_DAMP": "0.29"}),
            ("힙 감쇠 ×6", {"FS_HIPM_DAMP": "0.58"}),
            ("회전자×4 + 지연 원래", {"FS_HIPM_ARM": "0.040"}),
            ("회전자×2 + 지연×2", {"FS_HIPM_ARM": "0.020", "FS_CMD_LPF": "0.0063,0.00292"})]
    print(f"{'바꾼 것':22s} | {'힙 각도 오차[도]':>15s} {'무릎 각도 오차[도]':>17s} {'합':>8s}")
    RES = {}
    base = None
    for nm, env in SCAN:
        saved = {}
        if env:
            for k, v in env.items():
                saved[k] = os.environ.get(k); os.environ[k] = v
        global KB
        KB = float(os.environ.get("GHE_KBASE", "3000"))
        FR._S2S = None
        ft = FR.fs_twin()
        tmap = FR._tmap_init(P, A)
        KS = float(os.environ.get("FS_KS_HIP", "150"))
        allE = []
        for f, d in D.items():
            s, nw = pick(d)
            E = run(ft, d, s, nw, tmap, KS)
            if E is not None:
                allE.append(E)
        for k, v in saved.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        FR._S2S = None
        if not allE:
            print(f"{nm:22s} | 실패"); continue
        E = np.vstack(allE); med = np.median(E, axis=0); tot = med.sum()
        if base is None:
            base = tot
        RES[nm] = dict(hip=float(med[0]), knee=float(med[1]), tot=float(tot), n=len(E))
        print(f"{nm:22s} | {med[0]:15.3f} {med[1]:17.3f} {tot:8.3f}"
              f"  ({100*(tot/base-1):+.1f}%)", flush=True)
    import safe
    safe.atomic_json_write(OUT, RES)
    print(f"\n저장 → {OUT}")
    print("※ 오차가 가장 작은 배율이 실제 관성에 가깝다. 배율을 바꿔도 오차가 안 변하면")
    print("  이 데이터로도 그 값은 **정해지지 않는다**는 뜻이다.")


if __name__ == "__main__":
    main()
