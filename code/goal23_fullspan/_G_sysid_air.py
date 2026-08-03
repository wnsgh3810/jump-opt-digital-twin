# -*- coding: utf-8 -*-
"""_G_sysid_air — 마라톤G Phase1: **공중 동적 시스템 동정** (26_08_02 신규 실험).

데이터: `26_08_02/<게인>/sysid_air_k{070,095,118}_v1/` — 발을 뗀 상태에서 힙·무릎 사인 가진.
게인 3종(kp2 = 120 / 250 / 500)까지 사용자가 실행 → **벨트 α 가설의 직접 검증**도 가능.

## 토크 규약 (절대 주의)
`currentTorque`는 **항상 raw iTM 단위**다 (Nm 아님). 축토크는 `ahat_np(raw, dq)` 변환 필수.
레거시 `sys_id_compare_batch.py`가 이 변환 없이 raw로 적합하고 Nm 모델과 비교해
"+78%/+1081% 불일치"를 보고한 것이 G-F6 = **단위 아티팩트**였다.

## 회귀 모형 (직렬 2링크 등가 — 무변속 l_i=30이라 4-bar가 평행사변형)
  τ1 = Is1·q̈1 + Is2·q̈2 + Kv·[**2cos q2·q̈1** + cos q2·q̈2 − sin q2·(2q̇1q̇2 + q̇2²)]
       + gA·cos q1 + gB·cos(q1+q2) + fv1·q̇1 + fc1·tanh(q̇1/0.3) + off1
  τ2 = Is2·(q̈1+q̈2) + Kv·[cos q2·q̈1 + sin q2·q̇1²]
       + gB·cos(q1+q2) + fv2·q̇2 + fc2·tanh(q̇2/0.3) + off2
gA = g·(m1·r1 + m_p·r_p + m2·l1)  ·  gB = g·(m2·r2 − m_c·r_c − m_p·l_c)   [Nm]
★ 레거시 `sys_id_compare_batch.py`는 τ1 행의 **2·Kv·cos q2·q̈1 항이 누락**돼 있었다
  (M11 = Is1 + Is2 + 2Kv·cos q2 인데 q̈1 계수를 Is1 단독으로 놓음) — 여기서 바로잡았다.

## 내장 자기검증
플랜트 파라미터는 **PD 게인과 무관해야 한다**. 게인 3종에서 따로 적합해 값이 흩어지면
토크 변환·커맨드층 오염 신호다 (신뢰도 판정에 사용).
CLI: python _G_sysid_air.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
sys.path.insert(0, str(HERE.parent / "goal22" / "p26_sea"))
from sea_twin2 import ahat_np      # noqa: E402  (a_hat Paper — 정본)
import fs_data as FD               # noqa: E402  (ROOT 규약 단일 출처)

SESS = FD.ROOT / "26_08_02"
FS = 500.0
DT = 1.0 / FS
NAMES = ["Is1", "Is2", "Kv", "gA", "gB", "fv1", "fv2", "fc1", "fc2", "off1", "off2"]


def lpf(x, fc=10.0, order=4):
    b, a = butter(order, fc / (FS / 2), btype="low")
    return filtfilt(b, a, np.asarray(x, float))


def load(fold: Path):
    hip = pd.read_excel(fold / "hip.xlsx"); knee = pd.read_excel(fold / "knee.xlsx")
    n = min(len(hip), len(knee))
    hip, knee = hip.iloc[:n], knee.iloc[:n]
    q1 = lpf(hip["currentAngle"].to_numpy(float))
    q2 = lpf(knee["currentAngle"].to_numpy(float))
    v1 = lpf(hip["currentAngleVelocity"].to_numpy(float), 8.0)
    v2 = lpf(knee["currentAngleVelocity"].to_numpy(float), 8.0)
    r1 = hip["currentTorque"].to_numpy(float)
    r2 = knee["currentTorque"].to_numpy(float)
    # **raw → 축토크 [Nm]**: a_hat 변환 후에 필터 (변환이 비선형이므로 순서 중요)
    t1 = lpf(ahat_np(r1, hip["currentAngleVelocity"].to_numpy(float)), 8.0)
    t2 = lpf(ahat_np(r2, knee["currentAngleVelocity"].to_numpy(float)), 8.0)
    a1 = lpf(np.gradient(v1, DT), 6.0)
    a2 = lpf(np.gradient(v2, DT), 6.0)
    m = slice(300, n - 300)          # 필터 경계 제거
    return dict(q1=q1[m], q2=q2[m], dq1=v1[m], dq2=v2[m], ddq1=a1[m], ddq2=a2[m],
                t1=t1[m], t2=t2[m], raw1=r1[m], raw2=r2[m], n=n)


def regressor(d):
    q1, q2 = d["q1"], d["q2"]
    v1, v2, a1, a2 = d["dq1"], d["dq2"], d["ddq1"], d["ddq2"]
    n = len(q1)
    s2, c2 = np.sin(q2), np.cos(q2)
    Y = np.zeros((2 * n, len(NAMES)))
    Y[:n, 0] = a1                                     # Is1
    Y[:n, 1] = a2                                     # Is2
    Y[:n, 2] = 2 * c2 * a1 + c2 * a2 - s2 * (2 * v1 * v2 + v2 ** 2)   # Kv (M11의 2Kv·c2 포함)
    Y[:n, 3] = np.cos(q1)                             # gA
    Y[:n, 4] = np.cos(q1 + q2)                        # gB
    Y[:n, 5] = v1                                     # fv1
    Y[:n, 7] = np.tanh(v1 / 0.3)                      # fc1
    Y[:n, 9] = 1.0                                    # off1
    Y[n:, 1] = a1 + a2                                # Is2
    Y[n:, 2] = c2 * a1 + s2 * v1 ** 2                 # Kv
    Y[n:, 4] = np.cos(q1 + q2)                        # gB
    Y[n:, 6] = v2                                     # fv2
    Y[n:, 8] = np.tanh(v2 / 0.3)                      # fc2
    Y[n:, 10] = 1.0                                   # off2
    return Y, np.concatenate([d["t1"], d["t2"]])


def fit(folds):
    Ys, Ts, info = [], [], []
    for f in folds:
        d = load(f)
        Y, T = regressor(d)
        Ys.append(Y); Ts.append(T)
        info.append((f.parent.name, f.name, len(d["q1"]),
                     np.degrees(d["q2"]).mean(), np.abs(d["ddq1"]).max(), np.abs(d["t1"]).max()))
    Y = np.vstack(Ys); T = np.concatenate(Ts)
    th, *_ = np.linalg.lstsq(Y, T, rcond=None)
    pred = Y @ th
    ss = 1 - np.sum((T - pred) ** 2) / np.sum((T - T.mean()) ** 2)
    rms = float(np.sqrt(np.mean((T - pred) ** 2)))
    return th, ss, rms, info


def twin_params(comz, mthigh=1.05):
    """트윈의 등가 (M11(q2), gA, gB) — 검증된 경로만 사용.
    M11 = 힙축 둘레 총관성 (평행축 정리) · gA/gB = 중력토크를 cos(q1)·cos(q1+q2)로 회귀."""
    import mujoco as mjm
    os.environ["FS_MBODY"] = f"thigh={mthigh}"
    os.environ["FS_COMZ"] = f"thigh={comz}"
    sys.path.insert(0, str(HERE))
    import fs_runner as FR
    from _G_hang_pred import _ctx, BELOW
    ft = FR.fs_twin(); m = ft["model"]; iq, dof = ft["iq"], ft["dof"]
    ids, jid, mass = _ctx(ft)[1], _ctx(ft)[2], _ctx(ft)[3]

    def pose(q1, q2):
        md = mjm.MjData(m)
        md.qpos[iq["base_z"]] = 1.0
        md.qpos[iq["hip_m"]] = -q1 - np.pi / 2
        md.qpos[iq["hip"]] = 0.0
        md.qpos[iq["knee_motor"]] = -q2
        md.qpos[iq["cpin"]] = q2
        md.qpos[iq["knee"]] = -q2
        mjm.mj_forward(m, md)
        return md

    def M11(q2):
        md = pose(np.radians(-45.0), q2)
        anc = md.xanchor[jid]; I = 0.0
        for i in ids:
            d = md.xipos[i] - anc
            I += float(m.body_inertia[i][1]) + float(m.body_mass[i]) * (d[0] ** 2 + d[2] ** 2)
        return I

    # 중력토크 회귀 (qfrc_bias, qvel=0 → 순수 중력). 부호: 측정 τ1은 q1 방향이라 −를 붙인다.
    Q1 = np.radians(np.linspace(-60, -30, 13)); Q2 = np.radians(np.linspace(-125, -65, 13))
    r, X = [], []
    for a in Q1:
        for b in Q2:
            md = pose(a, b)
            r.append(-float(md.qfrc_bias[dof["hip_m"]]))
            X.append([np.cos(a), np.cos(a + b)])
    g, *_ = np.linalg.lstsq(np.array(X), np.array(r), rcond=None)
    return {q2d: M11(np.radians(q2d)) for q2d in (-107, -86, -68)}, float(g[0]), float(g[1])


def main():
    gains = sorted([p for p in SESS.iterdir() if p.is_dir()])
    print(f"세션 {SESS.name}: 게인 폴더 {[g.name for g in gains]}\n")
    allf = []
    for g in gains:
        for tr in sorted(g.iterdir()):
            if tr.is_dir() and (tr / "hip.xlsx").exists():
                allf.append(tr)
    print(f"{'게인':<16} {'trial':<20} {'표본':>7} {'q2평균[°]':>10} {'|q̈1|max':>9} {'|τ1|max[Nm]':>12}")
    _, _, _, info = fit(allf[:1])
    for f in allf:
        d = load(f)
        print(f"{f.parent.name:<16} {f.name:<20} {len(d['q1']):7d} {np.degrees(d['q2']).mean():10.1f} "
              f"{np.abs(d['ddq1']).max():9.1f} {np.abs(d['t1']).max():12.3f}")

    print("\n=== 게인별 독립 적합 (플랜트 값은 게인과 무관해야 한다 = 자기검증) ===")
    print(f"{'게인':<16} " + " ".join(f"{n:>8}" for n in NAMES) + f" {'R²':>7} {'RMS':>7}")
    TH = {}
    for g in gains:
        fs = [t for t in allf if t.parent == g]
        th, ss, rms, _ = fit(fs)
        TH[g.name] = th
        print(f"{g.name:<16} " + " ".join(f"{v:8.4f}" for v in th) + f" {ss:7.4f} {rms:7.4f}")
    A = np.array(list(TH.values()))
    print(f"{'게인간 변동(%)':<16} " + " ".join(
        f"{(A[:,i].std()/max(abs(A[:,i].mean()),1e-9)*100):8.1f}" for i in range(A.shape[1])))

    print("\n=== 전체 통합 적합 (9 trial) ===")
    th, ss, rms, _ = fit(allf)
    for n, v in zip(NAMES, th):
        print(f"  {n:<6} {v:+10.5f}")
    print(f"  R² = {ss:.4f}   RMS 잔차 = {rms:.4f} Nm")
    out = dict(names=NAMES, theta=[float(x) for x in th], r2=float(ss), rms=float(rms),
               per_gain={k: [float(x) for x in v] for k, v in TH.items()})
    with io.open(HERE / "_G_sysid_air.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"\n저장: _G_sysid_air.json")

    # ---- 트윈 후보와 맞대결 ----
    Is1, Is2, Kv, gA, gB = th[0], th[1], th[2], th[3], th[4]
    print("\n=== 실측 동정 vs 트윈 후보 ===")
    print(f"{'항목':<22} {'실측(동정)':>11} {'트윈 현행':>11} {'오차%':>8} | {'트윈 CAD':>10} {'오차%':>8}")
    cur = twin_params(0.0)
    cad = twin_params(0.053)
    for q2d in (-107, -86, -68):
        me = Is1 + Is2 + 2 * Kv * np.cos(np.radians(q2d))
        a, b = cur[0][q2d], cad[0][q2d]
        print(f"{f'M11 (q2={q2d}°)':<22} {me:11.5f} {a:11.5f} {(a/me-1)*100:+8.1f} | "
              f"{b:10.5f} {(b/me-1)*100:+8.1f}")
    print(f"{'gA [Nm]':<22} {gA:11.4f} {cur[1]:11.4f} {(cur[1]/gA-1)*100:+8.1f} | "
          f"{cad[1]:10.4f} {(cad[1]/gA-1)*100:+8.1f}")
    print(f"{'gB [Nm]':<22} {gB:11.4f} {cur[2]:11.4f} {(cur[2]/gB-1)*100:+8.1f} | "
          f"{cad[2]:10.4f} {(cad[2]/gB-1)*100:+8.1f}")
    print(f"\n마찰 실측: 힙 쿨롱 {abs(th[7]):.3f} Nm · 점성 {th[5]:.4f} Nm·s/rad  |  "
          f"무릎 쿨롱 {abs(th[8]):.3f} Nm · 점성 {th[6]:.4f}")
    print(f"  (현행 트윈 hip_m frictionloss 0.2383 · damping 0.3121 / "
          f"knee_motor frictionloss 0.2469 · damping 0.1496)")


if __name__ == "__main__":
    main()
