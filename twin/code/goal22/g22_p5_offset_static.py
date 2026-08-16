"""GOAL22 P5 — q-offset 3°-레일 독립 검증 (정지 구간 중력 균형).

fit이 0324/0424에서 offsets를 ±3° 케이지 경계까지 미는 것이 실제 엔코더 영점 오차인지,
잔여 미모델 효과의 흡수인지 — fit과 무관한 정적 증거로 판정.
방법: 각 trial의 정지 구간(|dq|<0.05, 연속 >=0.15s)에서, sim을 (측정 q + offset) 상태·
qvel=qacc=0으로 놓고 mj_inverse가 주는 정적 토크 vs 측정 토크의 잔차를
(o1, o2) ±6° 그리드로 스캔 → argmin = 정적 offset 추정.
주의: 무릎은 4-bar 상쇄(B≈-0.0037)로 중력토크 ≈0 → o2는 정적으로 식별력 낮음(감도 보고).
스틱션 대역(±fc)이 편향 한계 — 잔차 절대값과 함께 보고.
"""
import sys, json
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13

OUT = Path(__file__).parent / "p5_offset_static.json"
GRID = np.radians(np.arange(-6.0, 6.01, 0.25))


def winit():
    PH.winit()
    P12 = P13._M["P12"]
    if P12._G["trials"] is None:
        P12.build_trials()
    return P12


def build_model(P12, x32):
    S = P12._G["S"]; FR = P12._G["FR"]; FL = P12._G["FL"]; mj = P12._G["mujoco"]
    dd = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = FL.build_xml_fourbar_flip(dd["arm_knee"], sc)
    xml = P13.apply_linkage_mods(xml, dict(zip(P13.N6, np.asarray(x32)[26:32])))
    return mj.MjModel.from_xml_string(xml), dd


def stationary_mask(td, min_len=75):
    dq1 = np.asarray(td["dq1"]); dq2 = np.asarray(td["dq2"])
    still = (np.abs(dq1) < 0.05) & (np.abs(dq2) < 0.05)
    # 연속 구간만 (>=min_len 샘플 = 0.15s @500Hz)
    m = np.zeros(len(still), bool)
    i = 0
    while i < len(still):
        if still[i]:
            j = i
            while j < len(still) and still[j]:
                j += 1
            if j - i >= min_len:
                m[i + 10:j - 10] = True   # 가장자리 트림
            i = j
        else:
            i += 1
    return m


def static_tau(mj, model, d, fg, q1c, q2c, S):
    """foot-on-floor 정적 상태에서 필요한 (tau_hip, tau_knee) — mj frame.
    base_z 잔차힘(qfrc_inverse[0])=0이 되도록 침투깊이 Newton 반복
    (프리 레일은 무게를 받지 않음 → 접촉력이 전 무게 지탱)."""
    q1 = -q1c - np.pi / 2; q2 = -q2c
    d.qpos[:] = [1.0, q1, q2, -q2, q2]
    mj.mj_forward(model, d)
    bz = 1.0 - float(d.geom_xpos[fg][2]) + S.FOOT_RADIUS
    k_eq = 1.3e5
    for _ in range(6):
        d.qpos[:] = [bz, q1, q2, -q2, q2]
        d.qvel[:] = 0; d.qacc[:] = 0
        mj.mj_inverse(model, d)
        f0 = float(d.qfrc_inverse[0])
        if abs(f0) < 0.5:
            break
        bz -= f0 / k_eq
    return float(d.qfrc_inverse[1]), float(d.qfrc_inverse[2])


def main():
    P12 = winit()
    mj = P12._G["mujoco"]; S = P12._G["S"]
    can = json.load(open(REPO / "code/goal21/fourbar_honest_canonical.json"))
    x32 = np.array(can["x"]); NAMES = can["names"]
    dd_fit = dict(zip(NAMES, x32))
    model, dd = build_model(P12, x32)
    d = mj.MjData(model)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")

    res = {}
    for tr_ in P12._G["trials"]:
        ds, sub, td, isj = tr_["ds"], tr_["sub"], tr_["td"], tr_["isj"]
        if isj:
            # 점프 로그는 모션 구간만 트림됨 → 시작부 crouch 준정적 샘플 사용
            dq1 = np.abs(np.asarray(td["dq1"])); dq2 = np.abs(np.asarray(td["dq2"]))
            m = np.zeros(len(dq1), bool)
            m[:20] = (dq1[:20] < 0.15) & (dq2[:20] < 0.15)
        else:
            m = stationary_mask(td, min_len=50)
        if m.sum() < 8:
            print(f"{ds}/{sub}: 정지샘플 {m.sum()} — 스킵", flush=True)
            continue
        q1r = np.asarray(td["q1"])[m]; q2r = np.asarray(td["q2"])[m]
        t1r = np.asarray(td["tau1_real"])[m]; t2r = np.asarray(td["tau2_real"])[m]
        # 대표점으로 압축 (연산 절약)
        step = max(1, m.sum() // 20)
        q1r, q2r, t1r, t2r = q1r[::step], q2r[::step], t1r[::step], t2r[::step]
        # o1 스캔 (o2=fit값 고정) + o2 스캔 (o1=fit값 고정) + 2D argmin
        k1, k2 = P12.OFFKEY.get(ds, (None, None))
        o1f = dd_fit.get(k1, 0.0) if k1 else 0.0
        o2f = dd_fit.get(k2, 0.0) if k2 else 0.0
        E = np.zeros((len(GRID), len(GRID)))
        for i, o1 in enumerate(GRID):
            for j, o2 in enumerate(GRID):
                e = 0.0
                for q1c, q2c, tm1, tm2 in zip(q1r, q2r, t1r, t2r):
                    th_mj, tk_mj = static_tau(mj, model, d, fg, q1c + o1, q2c + o2, S)
                    e += abs(-th_mj - tm1) + 0.3 * abs(-tk_mj - tm2)
                E[i, j] = e / len(q1r)
        i0, j0 = np.unravel_index(np.argmin(E), E.shape)
        # 감도: argmin 주변 1° 이동 시 잔차 증가량
        di = int(round(np.radians(1.0) / (GRID[1] - GRID[0])))
        s1 = E[min(i0 + di, len(GRID) - 1), j0] - E[i0, j0]
        s2 = E[i0, min(j0 + di, len(GRID) - 1)] - E[i0, j0]
        res[f"{ds}/{sub}"] = dict(
            o1_static=float(np.degrees(GRID[i0])), o2_static=float(np.degrees(GRID[j0])),
            o1_fit=float(np.degrees(o1f)), o2_fit=float(np.degrees(o2f)),
            resid=float(E[i0, j0]), sens1=float(s1), sens2=float(s2),
            n_still=int(m.sum()))
        print(f"{ds}/{sub}: o1_static={np.degrees(GRID[i0]):+.2f}° (fit {np.degrees(o1f):+.2f}°) "
              f"o2_static={np.degrees(GRID[j0]):+.2f}° (fit {np.degrees(o2f):+.2f}°) "
              f"resid={E[i0,j0]:.3f}Nm sens(1°)={s1:.3f}/{s2:.3f}", flush=True)

    # 데이터셋 요약 (중앙값)
    print("\n=== P5 요약 (데이터셋 중앙값) ===")
    summ = {}
    for ds in ["jump_position_0421", "jump_0424", "jump_0602", "jump_0324", "s2s_gnd_0319"]:
        ks = [k for k in res if k.startswith(ds + "/")]
        if not ks:
            continue
        med = lambda f: float(np.median([res[k][f] for k in ks]))
        summ[ds] = {f: med(f) for f in ["o1_static", "o2_static", "o1_fit", "o2_fit", "resid", "sens1", "sens2"]}
        s = summ[ds]
        print(f"{ds:22s} o1 {s['o1_static']:+.2f}°(fit {s['o1_fit']:+.2f}°)  "
              f"o2 {s['o2_static']:+.2f}°(fit {s['o2_fit']:+.2f}°)  resid {s['resid']:.3f}  "
              f"sens {s['sens1']:.3f}/{s['sens2']:.3f}", flush=True)
    json.dump(dict(per_trial=res, summary=summ), open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)


if __name__ == "__main__":
    main()
