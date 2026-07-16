# -*- coding: utf-8 -*-
"""p23_sg_frametest — Phase 4b 게이트 스프링 부호/프레임/이산화 검증 (h=1 강제).

검증 2단:
  ① 정적: 원 XML 스프링 모델(a)과 스프링0 모델(b)의 qfrc_passive[knee] 차 ==
     stiff·(kref − q_knee) — MuJoCo 패시브 스프링 부호 규약 직접 확인.
  ② 동적: 무제어(ctrl=0) 지상 settle 롤아웃 0.5s 록스텝 — (a) vs (b)+스텝마다
     qfrc_applied[knee] = stiff·(kref − q_knee) (h=1). qpos 궤적 최대/최종 편차 보고.
     integrator=implicitfast: 스프링(위치항)은 명시적(암시부는 ∂/∂qvel만) →
     기대 편차 = 부동소수 합산 순서 차이(~1e-16/step)의 증폭분.
★ kref = 컴파일된 model.qpos_spring[knee] — 1차 실행에서 raw ref(1.78rad) 가정이
  1.28Nm 어긋남을 발견: XML springref는 MJCF 기본 angle='degree'로 해석돼
  radians(ref)≈0.031rad가 실효 기준각 (본 파일이 그 발견의 재현 증거).
모델 3종: flip(l_i=30 평행사변형) / CVT(l_i=25.08) / weld(공중, 무접촉).
env 무관 (빌더 직접 호출) — P23_SPRING_GATED 불필요.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p21_cma as C
import p23_runners as RN
import p23_v6_runners as RU
import safe


def rollout_pair(model_a, model_b, qpos0, qvel0, stiff, T=0.5, ground=True):
    """록스텝 비교: a=XML 스프링, b=스프링0+qfrc(h=1). 반환 (max|dq|, final|dq|, DT, N).
    kref = model_a의 컴파일된 qpos_spring[knee] (b에도 springref 속성은 남아 동일값)."""
    mj = C._W["mj"]
    id_k = safe.dofadr(model_b, "knee", mj)
    iq_k = safe.qadr(model_b, "knee", mj)
    kref = float(model_a.qpos_spring[iq_k])
    da, db = mj.MjData(model_a), mj.MjData(model_b)
    for d_ in (da, db):
        d_.qpos[:] = qpos0
        d_.qvel[:] = qvel0
        mj.mj_forward(model_a if d_ is da else model_b, d_)
    dt = model_a.opt.timestep
    N = int(round(T / dt))
    dev_max = 0.0
    for k in range(N):
        da.ctrl[:] = 0
        db.ctrl[:] = 0
        db.qfrc_applied[id_k] = stiff * (kref - float(db.qpos[iq_k]))  # h=1 강제
        mj.mj_step(model_a, da)
        mj.mj_step(model_b, db)
        dev = float(np.abs(np.asarray(da.qpos) - np.asarray(db.qpos)).max())
        dev_max = max(dev_max, dev)
    dev_fin = float(np.abs(np.asarray(da.qpos) - np.asarray(db.qpos)).max())
    return dev_max, dev_fin, dt, N


def static_check(model_a, model_b, qpos0, stiff):
    """qfrc_passive 차 == stiff·(kref − q_knee) 확인 (qvel=0 → damping 기여 0)."""
    mj = C._W["mj"]
    id_k = safe.dofadr(model_a, "knee", mj)
    iq_k = safe.qadr(model_a, "knee", mj)
    kref = float(model_a.qpos_spring[iq_k])
    da, db = mj.MjData(model_a), mj.MjData(model_b)
    da.qpos[:] = qpos0; da.qvel[:] = 0
    db.qpos[:] = qpos0; db.qvel[:] = 0
    mj.mj_forward(model_a, da)
    mj.mj_forward(model_b, db)
    got = float(da.qfrc_passive[id_k] - db.qfrc_passive[id_k])
    want = stiff * (kref - float(da.qpos[iq_k]))
    return got, want, float(abs(got - want))


def ground_qpos(model, sq1, sq2, cvt_li=None):
    """cl_run23 초기화 규약: 발이 바닥에 닿는 base_z."""
    mj = C._W["mj"]; P = C._W["P"]; S = P.J._P["S"]
    md = mj.MjData(model)
    if cvt_li is not None:
        from cvt_core import qpos_from_crank
        md.qpos[:] = qpos_from_crank(1.0, sq1, sq2, cvt_li)[0]
    else:
        md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    return np.array(md.qpos)


def main():
    safe.utf8_console()
    RU.ensure_init()
    P = C._W["P"]
    v = np.asarray(safe.read_json(HERE / "p23_diag_x.json")["x"], float)
    x32, sp = C.x32_of(v[:20])
    assert sp == "calf"
    stiff, ref = float(f"{float(v[0]):.6f}"), float(v[1])   # XML :.6f 양자화 미러 (spr_resolve 동형)
    x32z = x32.copy(); x32z[C.IDX["stiff"]] = 0.0
    print(f"stiff={stiff:.6f} ref={ref:.6f} (diag x)", flush=True)
    q1_0, q2_0 = 0.6, -1.2                    # 전형적 크라우치 (스프링 스트레치 有)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0

    # ── flip (l_i=30) ──
    ma, _ = P.build_flip(x32, ref, "calf")
    mb, _ = P.build_flip(x32z, ref, "calf")
    mj = C._W["mj"]
    kref = float(ma.qpos_spring[safe.qadr(ma, "knee", mj)])
    print(f"kref(compiled qpos_spring) = {kref:.6f} rad  (= radians(ref)? "
          f"{np.isclose(kref, np.radians(ref), atol=1e-6)})", flush=True)
    qp0 = ground_qpos(ma, sq1, sq2)
    g, w, e = static_check(ma, mb, qp0, stiff)
    print(f"[flip ] static: passive_diff={g:+.9f}  stiff*(kref-qk)={w:+.9f}  |err|={e:.3e}",
          flush=True)
    dmax, dfin, dt, N = rollout_pair(ma, mb, qp0, np.zeros(ma.nv), stiff)
    print(f"[flip ] rollout 0.5s (dt={dt} N={N}): max|dqpos|={dmax:.3e} final={dfin:.3e}",
          flush=True)

    # ── CVT (l_i=25.08) ──
    ma, _ = P.build_cvt(x32, ref, "calf", 0.02508)
    mb, _ = P.build_cvt(x32z, ref, "calf", 0.02508)
    qp0 = ground_qpos(ma, sq1, sq2, cvt_li=0.02508)
    g, w, e = static_check(ma, mb, qp0, stiff)
    print(f"[cvt  ] static: passive_diff={g:+.9f}  stiff*(kref-qk)={w:+.9f}  |err|={e:.3e}",
          flush=True)
    dmax, dfin, dt, N = rollout_pair(ma, mb, qp0, np.zeros(ma.nv), stiff)
    print(f"[cvt  ] rollout 0.5s (dt={dt} N={N}): max|dqpos|={dmax:.3e} final={dfin:.3e}",
          flush=True)

    # ── weld (공중, 무접촉) ──
    ma, _ = RN.build_flip_welded(x32, ref, "calf")
    mb, _ = RN.build_flip_welded(x32z, ref, "calf")
    qp0 = np.zeros(ma.nq)
    qp0[safe.qadr(ma, "hip", mj)] = sq1
    qp0[safe.qadr(ma, "knee_motor", mj)] = sq2
    qp0[safe.qadr(ma, "cpin", mj)] = -sq2
    qp0[safe.qadr(ma, "knee", mj)] = sq2
    g, w, e = static_check(ma, mb, qp0, stiff)
    print(f"[weld ] static: passive_diff={g:+.9f}  stiff*(kref-qk)={w:+.9f}  |err|={e:.3e}",
          flush=True)
    dmax, dfin, dt, N = rollout_pair(ma, mb, qp0, np.zeros(ma.nv), stiff,
                                     ground=False)
    print(f"[weld ] rollout 0.5s (dt={dt} N={N}): max|dqpos|={dmax:.3e} final={dfin:.3e}",
          flush=True)


if __name__ == "__main__":
    main()
