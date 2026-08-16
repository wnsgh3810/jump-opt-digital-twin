# -*- coding: utf-8 -*-
"""_GHP_energy — 미분이 필요 없는 대조판: **에너지 수지**로 부족분(손실)을 재고 짐에 회귀.

  ∫τ_명령·dq  (모터가 넣은 일, 현행 환산식)
  − ΔE_역학  (위치+운동 에너지 증가 — 창 양 끝 값만으로 결정, 미분 불필요)
  = 설명 안 되는 손실 [J]

  ΔE 의 짐 몫은 정확히 m·g·Δbz 이므로 "짐 1kg 을 그만큼 들어올리는 데 드는 에너지"와
  손실 기울기를 바로 견줄 수 있다.
"""
import os, sys, pickle
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
GFS = Path(__file__).parent
sys.path.insert(0, str(GFS)); os.chdir(GFS)
import numpy as np
import mujoco as mj
import fs_runner as FR, fs_cvt as FC

R = pickle.load(open(GFS / "_GHP_loadslope.pkl", "rb"))
G0 = 9.81
CVTC = ["cvt/no_load", "cvt/load_2.5", "cvt/load_5"]
PAY = {"cvt/no_load": 0.0, "cvt/load_2.5": 2.5, "cvt/load_5": 5.0, "no_cvt/no_load": 0.0}
STACK_M = 3.2990


def energy(sub):
    r = R[sub]
    ix = r["ix"]
    pay = PAY[sub]
    os.environ["FS_MASS"] = f"{STACK_M + pay:.4f}"
    FR._CACHE.clear()
    ft0 = FR.fs_twin()
    if r["cvt"]:
        FC._MC.clear(); FC._RT.clear()
        ft = FC.cvt_ft(r["l_i"], ft_base=ft0)
    else:
        ft = ft0
    m = ft["model"]; d = mj.MjData(m)
    # 위치·운동 에너지 (창 시작/끝)
    m.opt.disableflags |= mj.mjtDisableBit.mjDSBL_CONSTRAINT
    E = []
    for k in (ix[0], ix[-1]):
        d.qpos[:] = np.array(r["bz"][k] * 0 + 0)  # placeholder
        break
    # qpos 는 저장 안 했으므로 bz + 관절각으로 재구성 불가 → mj_energyPos 대신 직접 계산
    # (질량·CoM 은 모델에서, 위치는 저장된 bz + 정적 기여로)
    return ft, m


def mech_energy(ft, xs_row, v_row):
    m = ft["model"]; d = mj.MjData(m)
    d.qpos[:] = xs_row; d.qvel[:] = v_row
    mj.mj_kinematics(m, d); mj.mj_comPos(m, d); mj.mj_comVel(m, d)
    # 위치 에너지
    U = 0.0
    for b in range(1, m.nbody):
        # body CoM 월드 위치
        p = d.xipos[b]
        U += float(m.body_mass[b]) * G0 * float(p[2])
    # 운동 에너지: 0.5 v^T M v  (+ armature)
    M = np.zeros((m.nv, m.nv))
    mj.mj_crb(m, d)
    mj.mj_fullM(m, M, d.qM)
    T = 0.5 * float(v_row @ M @ v_row)
    return U, T


if __name__ == "__main__":
    # xs 를 다시 만들려면 map 이 필요 → _GHP_loadslope 의 analyse 를 재사용
    import _GHP_loadslope as LS
    import fs_data as FD
    print("=" * 112)
    print("표7 — 에너지 수지 (창 전체, 미분 불필요분은 양 끝값만 사용)  [J]")
    print("=" * 112)
    print(f"{'경우':16s} {'짐kg':>5s} | {'ΔU 위치':>8s} {'ΔT 운동':>8s} {'ΔE':>8s} |"
          f" {'W명령 힙':>9s} {'W명령 무릎':>10s} {'W명령 계':>9s} | {'손실=W−ΔE':>10s} | {'Δbz[m]':>7s}")
    out = {}
    for sub, pay, cvt in FD.S2S_CASES:
        r = LS.analyse(sub, pay, cvt)
        ix = r["ix"]
        # 트윈 재구성 (analyse 안에서 마지막으로 만든 것과 동일 env)
        os.environ["FS_MASS"] = f"{STACK_M + pay:.4f}"
        FR._CACHE.clear()
        ft0 = FR.fs_twin()
        ft = FC.cvt_ft(r["l_i"], ft_base=ft0) if cvt else ft0
        m = ft["model"]
        assert abs(float(m.body_mass.sum()) - (STACK_M + pay)) < 1e-3, \
            f"질량 미반영 {m.body_mass.sum()} vs {STACK_M+pay}"
        # 창 양 끝의 6-qpos/qvel 을 analyse 에서 재계산
        X = LS.make_map(ft, cvt, r["l_i"])
        x0, _ = X(r["q1"][ix[0]], r["q2"][ix[0]])
        x1, _ = X(r["q1"][ix[-1]], r["q2"][ix[-1]])
        v0 = r["vel"][ix[0]]; v1 = r["vel"][ix[-1]]
        U0, T0 = mech_energy(ft, x0, v0)
        U1, T1 = mech_energy(ft, x1, v1)
        dt = 0.002
        # 모터가 넣은 일 (실측 속도 × 환산 토크)
        w1 = float(np.sum(r["tau_cmd"][ix, 0] * r["dq1"][ix]) * dt)
        w2 = float(np.sum(r["tau_cmd"][ix, 1] * r["dq2"][ix]) * dt)
        # 관절별 필요 일 (합 = ΔE 여야 한다 — 파이프라인 검산)
        q1v = r["vel"][ix][:, ft["iq"]["hip_m"]] * -1.0     # dq1 (평활)
        rq1 = float(np.sum(r["tau_req"][ix, 0] * r["dq1"][ix]) * dt)
        rq2 = float(np.sum(r["tau_req"][ix, 1] * r["dq2"][ix]) * dt)
        # 평활 속도판 (교차확인)
        w1s = float(np.sum(r["tau_cmd"][ix, 0] * q1v) * dt)
        dE = (U1 - U0) + (T1 - T0)
        loss = w1 + w2 - dE
        dbz = float(r["bz"][ix[-1]] - r["bz"][ix[0]])
        out[sub] = dict(dU=U1 - U0, dT=T1 - T0, dE=dE, w1=w1, w2=w2, loss=loss, dbz=dbz,
                        rq1=rq1, rq2=rq2, l1=w1 - rq1, l2=w2 - rq2, w1s=w1s,
                        travel1=float(np.sum(np.abs(r["dq1"][ix])) * dt),
                        travel2=float(np.sum(np.abs(r["dq2"][ix])) * dt))
        o = out[sub]
        print(f"{sub:16s} {pay:5.1f} | {o['dU']:8.2f} {o['dT']:8.2f} {o['dE']:8.2f} |"
              f" {w1:9.2f} {w2:10.2f} {w1+w2:9.2f} | {loss:10.2f} | {dbz:7.3f}")
        print(f"{'':16s} {'':5s} | 필요일 힙 {rq1:6.2f} 무릎 {rq2:6.2f} 합 {rq1+rq2:6.2f} (=ΔE 검산 차 {rq1+rq2-dE:+.3f} J)"
              f" | 손실 힙몫 {w1-rq1:6.2f} 무릎몫 {w2-rq2:6.2f} J")

    x = np.array([PAY[c] for c in CVTC]); y = np.array([out[c]["loss"] for c in CVTC])
    A = np.vstack([x, np.ones_like(x)]).T
    sl, ic = np.linalg.lstsq(A, y, rcond=None)[0]
    dbz = np.mean([out[c]["dbz"] for c in CVTC])
    print()
    print(f"  손실 기울기 {sl:+.3f} J/kg · 절편 {ic:+.3f} J · 2계차 {y[2]-2*y[1]+y[0]:+.3f}")
    print(f"  짐 1kg 을 Δbz={dbz:.3f} m 들어올리는 데 필요한 에너지 = {G0*dbz:.3f} J/kg")
    print(f"  ⇒ 손실 기울기 / 들어올림 에너지 = {sl/(G0*dbz):.3f}  (= 짐 1kg 당 추가로 새는 비율)")
    print(f"  ΔE 기울기 실측 {np.linalg.lstsq(A, np.array([out[c]['dE'] for c in CVTC]), rcond=None)[0][0]:+.3f} J/kg (이론 {G0*dbz:.3f})")
    tr2 = np.mean([out[c]["travel2"] for c in CVTC])
    print(f"  무릎 크랭크 총 이동각 {tr2:.3f} rad → 손실 기울기를 등가 평균 토크로 {sl/tr2:+.3f} N·m/kg")
    for nm, key in (("힙몫", "l1"), ("무릎몫", "l2")):
        yy = np.array([out[c][key] for c in CVTC])
        s2, i2 = np.linalg.lstsq(A, yy, rcond=None)[0]
        print(f"  손실 {nm}: {yy[0]:+.2f} / {yy[1]:+.2f} / {yy[2]:+.2f} J → 기울기 {s2:+.3f} J/kg "
              f"절편 {i2:+.3f} J · 2계차 {yy[2]-2*yy[1]+yy[0]:+.3f}")
    with open(GFS / "_GHP_energy.pkl", "wb") as f:
        pickle.dump(out, f)
