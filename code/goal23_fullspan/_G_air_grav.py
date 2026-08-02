# -*- coding: utf-8 -*-
"""_G_air_grav — 마라톤G Phase1: **공중 중력 모멘트 독립 검증** (26.03.24/sit2stand).

왜 이 세션인가: 사용자 확인(07-16) **공중 매달림 세션** — 발이 지면에 닿지 않아
**지면 마찰·접촉이 섞이지 않는다**. 게다가 자세가 크게 쓸린다 (q1 −67~−12°, q2 −161~−76°)
→ 중력 레버(질량×팔길이)를 자세 의존성으로 분리할 수 있는 **유일한** 데이터.
(*3의 공중 구간은 자세가 q1 −45°·q2 −90° 한 점으로 고정 = G-F5, 회귀 불가.)

방법: 준정적 표본(|dq| 작음)만 골라
  실측 축토크 = ahat_np(raw, dq)   ← raw는 iTM 단위이므로 **a_hat(Paper) 변환 필수**
                                     (레거시 sys_id는 이 변환 없이 raw로 적합 = G-F6 단위 오염)
  모델 축토크 = 베이스를 레일에 **핀 고정**(매달림 재현)하고 PD로 그 자세를 유지시켰을 때
                수렴한 액추에이터 축토크 — fs_calib.hold_torque의 공중판.
두 값의 잔차를 자세(q1)에 대해 보면 중력 레버 오차가 cos(q1) 모양으로 드러난다.

주의 (해석 한계): 26.03.24는 **CVT 클러치 장착 전** 시기다. 허벅지 묶음은 그대로일 가능성이
높지만 **crank 조립은 다를 수 있다** → 이 세션은 thigh 레버 검증에 쓰고 crank엔 쓰지 않는다.
CLI: FS_MBODY=... FS_COMZ=... python _G_air_grav.py
"""
import os, sys, glob
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np
import pandas as pd
import mujoco as mjm

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
sys.path.insert(0, str(HERE.parent / "goal22" / "p26_sea"))
import safe
import fs_runner as FR
import p25_a_twin as TW
from sea_twin2 import ahat_np

S2S = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data/26.03.24/sit2stand")
DQ_MAX = float(os.environ.get("G_DQMAX", "0.15"))   # 준정적 판정 [rad/s]
STEP = 40              # 표본 간격 (500Hz → 80ms)
MAXN = 45              # trial당 표본 상한 — **자세(q1)로 층화 추출**해 스윕 전체를 고르게 덮는다
                       # (그냥 앞에서 자르면 한쪽 자세만 뽑혀 레버 추정이 편향된다)


def load_s2s():
    """sit2stand trial 로드 → (이름, q1, q2, dq1, dq2, a1, a2)."""
    out = []
    for f in sorted(S2S.glob("sit2stand_*")):
        if not f.is_dir():
            continue
        hip = pd.read_excel(f / "hip.xlsx"); knee = pd.read_excel(f / "knee.xlsx")
        n = min(len(hip), len(knee))
        q1 = hip["currentAngle"].to_numpy(float)[:n]
        q2 = knee["currentAngle"].to_numpy(float)[:n]
        v1 = hip["currentAngleVelocity"].to_numpy(float)[:n]
        v2 = knee["currentAngleVelocity"].to_numpy(float)[:n]
        r1 = hip["currentTorque"].to_numpy(float)[:n]
        r2 = knee["currentTorque"].to_numpy(float)[:n]
        out.append((f.name, q1, q2, v1, v2, ahat_np(r1, v1), ahat_np(r2, v2)))
    return out


def hold_air(ft, q1_0, q2_0, t_settle=0.6):
    """**공중 매달림** 유지토크: base_z를 매 스텝 고정(레일 지지 재현)하고 PD 수렴 축토크 반환."""
    model = ft["model"]; P = ft["P"]
    iq, dof = ft["iq"], ft["dof"]
    A = P.A_PAPER
    md = mjm.MjData(model)
    md.qpos[iq["hip_m"]] = -q1_0 - np.pi / 2
    md.qpos[iq["hip"]] = 0.0
    md.qpos[iq["knee_motor"]] = -q2_0
    md.qpos[iq["cpin"]] = q2_0
    md.qpos[iq["knee"]] = -q2_0
    bz0 = 1.0
    md.qpos[iq["base_z"]] = bz0
    md.qvel[:] = 0
    mjm.mj_forward(model, md)
    S = P.J._P["S"]
    dt = model.opt.timestep
    s1 = s2 = 0.0
    for _ in range(int(round(t_settle / dt))):
        q1c = -md.qpos[iq["hip_m"]] - np.pi / 2
        q2c = -md.qpos[iq["knee_motor"]]
        v1c = -md.qvel[dof["hip_m"]]; v2c = -md.qvel[dof["knee_motor"]]
        c1 = float(np.clip(S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c, -TW.R19.CLIP, TW.R19.CLIP))
        c2 = float(np.clip(S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        md.ctrl[:] = [-s1, -s2]              # 공중 = 지지층/스프링 보조 없음 (순수 중력 유지)
        mjm.mj_step(model, md)
        md.qpos[iq["base_z"]] = bz0          # 레일 핀 고정 (매달림)
        md.qvel[dof["base_z"]] = 0.0
    ok = abs(md.qvel[dof["hip_m"]]) < 0.05 and abs(md.qvel[dof["knee_motor"]]) < 0.05
    return s1, s2, bool(ok)


def _offset_free_rms(meas, model, trial_ids):
    """**토크 센서 오프셋 면역** 잔차: trial별 상수 1개를 최소제곱으로 흡수한 뒤의 RMS.
    → 남는 것은 순수 **자세 의존성**(중력 레버)의 불일치뿐이다."""
    r = meas - model
    out = np.empty_like(r)
    for tid in set(trial_ids):
        m = np.array([t == tid for t in trial_ids])
        out[m] = r[m] - r[m].mean()          # trial 상수 제거
    return float(np.sqrt((out ** 2).mean())), out


def scan():
    """후보 com_z별로 공중 중력 자세의존성 적합도를 비교 (오프셋 면역)."""
    vals = [float(x) for x in os.environ.get("G_COMZ_SCAN", "0.0,0.015,0.03,0.045,0.053").split(",")]
    data = load_s2s()
    # 표본 선정은 트윈과 무관하므로 한 번만
    P = []
    for nm, q1, q2, v1, v2, a1, a2 in data:
        qs = (np.abs(v1) < DQ_MAX) & (np.abs(v2) < DQ_MAX)
        cand = np.array([i for i in range(0, len(q1), STEP) if qs[i]], int)
        if len(cand) == 0:
            continue
        bins = np.linspace(q1[cand].min(), q1[cand].max() + 1e-9, MAXN + 1)
        which = np.digitize(q1[cand], bins) - 1
        for b in range(MAXN):
            w = np.where(which == b)[0]
            if len(w):
                i = int(cand[w[0]])
                P.append((nm, float(q1[i]), float(q2[i]), float(a1[i]), float(a2[i])))
    tid = [p[0] for p in P]
    q1a = np.array([p[1] for p in P]); q2a = np.array([p[2] for p in P])
    m1 = np.array([p[3] for p in P]); m2 = np.array([p[4] for p in P])
    print(f"준정적 표본 {len(P)}개 (|dq|<{DQ_MAX}, trial {len(set(tid))}개, "
          f"q1 {np.degrees(q1a).min():.0f}~{np.degrees(q1a).max():.0f}°)")
    print(f"\n{'Δcom_z':>7} {'com_z':>9} | {'τ1 잔차RMS':>11} {'τ2 잔차RMS':>11} | {'τ1 자세폭(모델)':>15} "
          f"{'τ1 자세폭(실측)':>15}")
    print(f"{'':>7} {'':>9} | {'(오프셋 제거)':>11} {'':>11} | {'std [Nm]':>15} {'std [Nm]':>15}")
    for v in vals:
        os.environ["FS_COMZ"] = f"thigh={v}"
        ft = FR.fs_twin()
        _i = mjm.mj_name2id(ft["model"], mjm.mjtObj.mjOBJ_BODY, "thigh")
        cz = float(ft["model"].body_ipos[_i][2])
        s1s, s2s, keep = [], [], []
        for k, (nm, a, b, _, _) in enumerate(P):
            x, y, ok = hold_air(ft, a, b)
            if ok:
                s1s.append(x); s2s.append(y); keep.append(k)
        keep = np.array(keep, int)
        if len(keep) < 10:
            print(f"{v:+7.3f} {cz:9.5f} | 수렴 표본 부족 ({len(keep)})"); continue
        r1, _ = _offset_free_rms(m1[keep], np.array(s1s), [tid[k] for k in keep])
        r2, _ = _offset_free_rms(m2[keep], np.array(s2s), [tid[k] for k in keep])
        print(f"{v:+7.3f} {cz:9.5f} | {r1:11.4f} {r2:11.4f} | {np.std(s1s):15.4f} "
              f"{np.std(m1[keep]):15.4f}   (수렴 {len(keep)}/{len(P)})", flush=True)


def main():
    if os.environ.get("G_SCAN"):
        return scan()
    ft = FR.fs_twin()
    _i = mjm.mj_name2id(ft["model"], mjm.mjtObj.mjOBJ_BODY, "thigh")
    print(f"트윈: thigh m={ft['model'].body_mass[_i]:.5f} com_z={ft['model'].body_ipos[_i][2]:+.5f} "
          f"총질량={ft['model'].body_mass.sum():.4f}")
    rows = []
    for nm, q1, q2, v1, v2, a1, a2 in load_s2s():
        qs = (np.abs(v1) < DQ_MAX) & (np.abs(v2) < DQ_MAX)
        cand = np.array([i for i in range(0, len(q1), STEP) if qs[i]], int)
        if len(cand) == 0:
            continue
        # 자세 층화: q1 범위를 MAXN 구간으로 나눠 각 구간 대표 1점
        bins = np.linspace(q1[cand].min(), q1[cand].max() + 1e-9, MAXN + 1)
        which = np.digitize(q1[cand], bins) - 1
        idx = [int(cand[np.where(which == b)[0][0]]) for b in range(MAXN) if (which == b).any()]
        for i in idx:
            s1, s2, ok = hold_air(ft, float(q1[i]), float(q2[i]))
            if ok:
                rows.append((nm, float(q1[i]), float(q2[i]), float(a1[i]), float(a2[i]), s1, s2))
    if not rows:
        print("준정적 표본 없음"); return
    A = np.array([[r[1], r[2], r[3], r[4], r[5], r[6]] for r in rows], float)
    r1 = A[:, 2] - A[:, 4]; r2 = A[:, 3] - A[:, 5]
    print(f"\n준정적 표본 {len(A)}개 (|dq|<{DQ_MAX}, {STEP/500*1000:.0f}ms 간격)")
    print(f"  τ1 실측 {A[:,2].mean():+.3f}±{A[:,2].std():.3f}  모델 {A[:,4].mean():+.3f}±{A[:,4].std():.3f}"
          f"  **잔차 {r1.mean():+.3f}±{r1.std():.3f} Nm** (RMS {np.sqrt((r1**2).mean()):.3f})")
    print(f"  τ2 실측 {A[:,3].mean():+.3f}±{A[:,3].std():.3f}  모델 {A[:,5].mean():+.3f}±{A[:,5].std():.3f}"
          f"  **잔차 {r2.mean():+.3f}±{r2.std():.3f} Nm** (RMS {np.sqrt((r2**2).mean()):.3f})")
    # 잔차의 cos(q1) 성분 = 힙 중력레버 오차의 서명
    c1 = np.cos(A[:, 0]); c12 = np.cos(A[:, 0] + A[:, 1])
    M = np.column_stack([c1, c12, np.ones_like(c1)])
    b1, *_ = np.linalg.lstsq(M, r1, rcond=None)
    b2, *_ = np.linalg.lstsq(np.column_stack([c12, np.ones_like(c1)]), r2, rcond=None)
    print(f"\n잔차 분해 τ1 = {b1[0]:+.4f}·cos(q1) {b1[1]:+.4f}·cos(q1+q2) {b1[2]:+.4f}")
    print(f"         τ2 = {b2[0]:+.4f}·cos(q1+q2) {b2[1]:+.4f}")
    print(f"  → cos(q1) 계수 {b1[0]:+.4f} Nm = 힙 중력레버 결손. "
          f"질량 1.05kg 기준 팔길이 환산 **{b1[0]/(1.05*9.81)*1000:+.1f} mm**")
    print(f"\n{'자세 구간(q1°)':<16} {'n':>4} {'τ1 실측':>9} {'τ1 모델':>9} {'잔차':>8}")
    for lo, hi in ((-70, -55), (-55, -45), (-45, -35), (-35, -25), (-25, -10)):
        m = (np.degrees(A[:, 0]) >= lo) & (np.degrees(A[:, 0]) < hi)
        if m.sum():
            print(f"{f'{lo}~{hi}':<16} {m.sum():4d} {A[m,2].mean():+9.3f} {A[m,4].mean():+9.3f} {r1[m].mean():+8.3f}")


if __name__ == "__main__":
    main()
