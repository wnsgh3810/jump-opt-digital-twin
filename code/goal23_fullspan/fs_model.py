# -*- coding: utf-8 -*-
"""fs_model — GOAL23 플랜트 내장 hip 직렬 스프링 빌더 (Cassie 패턴, 문헌 확정 설계).

구조: base → [hip_m 힌지: armature=반영 로터 관성, 기어박스 마찰(구 hip damping/frictionloss),
      액추에이터·인코더 여기] → hip_rotor(미소 관성) → [hip 힌지: stiffness=k_s, damping=b_s,
      springref=0 = 순수 처짐 좌표] → thigh. (goal19 실패 원인이던 로터 질량 바디 대신 armature.)
정본 XML은 TW.twin() 컴파일 시점 캡처 (canonical 무수정 — 문자열 위에 safe.xml_patch만).
2단 스프링(96/323@9)의 비선형분은 러너에서 qfrc 보정 (v1 플랜트는 선형 k_s).
관례: q1_limb = -(hip_m+hip)-π/2 · 인코더 θ_m = -hip_m-π/2 · 처짐(θ_m−q1) = +hip.
CLI: sanity — 컴파일·정적 처짐(τ/k 검증)·수동 낙하 에너지·장시간 발산 체크.
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
for _p in ("p25_task0", "p25_deploy", "p23_veins", "p19_jump", "p18_cvt"):
    sys.path.insert(0, str(HERE.parent / "goal22" / _p))
sys.path.insert(0, str(HERE))
import p25_a_twin as TW          # noqa: E402
import safe                      # noqa: E402
import mujoco as mjm             # noqa: E402

# v1 기본값 (물리 출처표: armature=반영 로터(문헌·H32), k_s=구조 유연성 in-situ, b_s=SEA-lite)
ARM_HIP = 0.01
KS_HIP = 150.0
BS_HIP = 1.5


def capture_base_xml():
    """정본 twin() 컴파일 XML 캡처 (canonical 무수정 — from_xml_string 래핑)."""
    orig = mjm.MjModel.from_xml_string
    captured = []

    def cap(xml, *a, **k):
        captured.append(xml)
        return orig(xml, *a, **k)
    mjm.MjModel.from_xml_string = staticmethod(cap)
    try:
        TW._T["tw"] = None          # twin 캐시 무효화 — 캡처를 위해 재컴파일 강제
        tw = TW.twin()
    finally:
        mjm.MjModel.from_xml_string = orig
    if not captured:
        raise RuntimeError("XML 캡처 실패 — twin 컴파일 경로 변경 여부 확인")
    return captured[-1], tw


def build_fs(ks=KS_HIP, bs=BS_HIP, arm=ARM_HIP, base_xml=None, endstop=False):
    """직렬 힌지 패치 모델 컴파일. 반환 (model, xml)."""
    if base_xml is None:
        base_xml, _ = capture_base_xml()
    old_j = '<body name="thigh" pos="0 0 -0.025">\n      <joint name="hip" type="hinge" armature="0" damping="0.312066" frictionloss="0.238254"/>'
    # 구 hip 감쇠/마찰(기어박스 몫)은 모터 힌지로 이동, 스프링 힌지는 k_s·b_s만
    new_j = ('<body name="hip_rotor" pos="0 0 -0.025">\n'
             f'      <joint name="hip_m" type="hinge" armature="{arm}" damping="0.312066" frictionloss="0.238254"/>\n'
             '      <inertial pos="0 0 0" mass="0.001" diaginertia="1e-07 1e-07 1e-07"/>\n'
             '      <body name="thigh" pos="0 0 0">\n'
             f'      <joint name="hip" type="hinge" armature="0" damping="{bs}" stiffness="{ks}" springref="0"/>')
    xml = safe.xml_patch(base_xml, old_j, new_j, count=1)
    # thigh 닫힘 뒤 rotor 닫힘 추가 (calf </body> → thigh </body> → base </body> 구조)
    xml = safe.xml_patch(xml, "      </body>\n    </body>\n  </body>\n</worldbody>",
                         "      </body>\n    </body>\n    </body>\n  </body>\n</worldbody>", count=1)
    # 액추에이터/인코더 = 모터 힌지
    xml = safe.xml_patch(xml, '<motor name="hip_motor" joint="hip" gear="1"/>',
                         '<motor name="hip_motor" joint="hip_m" gear="1"/>', count=1)
    if endstop:
        # 레일 하단 엔드스톱 (SEA P4: z_stop=0.169 soft) — s2s '의자'. 점프 자세는 구조적 미접촉
        xml = safe.xml_patch(xml, '<joint name="base_z" type="slide" axis="0 0 1"/>',
                             '<joint name="base_z" type="slide" axis="0 0 1" limited="true" range="0.169 2.0" solreflimit="0.01 1"/>', count=1)
    return mjm.MjModel.from_xml_string(xml), xml


def sanity():
    base_xml, tw = capture_base_xml()
    model, xml = build_fs(base_xml=base_xml)
    names = [mjm.mj_id2name(model, mjm.mjtObj.mjOBJ_JOINT, i) for i in range(model.njnt)]
    print("조인트:", names, "| nq =", model.nq)
    iq_m = safe.qadr(model, "hip_m", mjm); iq_s = safe.qadr(model, "hip", mjm)
    open(HERE / "_fs_model_v1.xml", "w", encoding="utf-8").write(xml)
    # ① 정적 처짐 검증: 서있는 자세 PD 유지 → 스프링 처짐 ≈ 유지토크/k_s
    P = tw["P"]; S = P.J._P["S"]
    q1_0, q2_0 = -0.785, -1.571
    md = mjm.MjData(model)
    iq = {n: safe.qadr(model, n, mjm) for n in names}
    md.qpos[iq["base_z"]] = 1.0
    md.qpos[iq["hip_m"]] = -q1_0 - np.pi / 2
    md.qpos[iq["hip"]] = 0.0
    md.qpos[iq["knee_motor"]] = -q2_0
    md.qpos[iq["cpin"]] = q2_0
    md.qpos[iq["knee"]] = -q2_0
    mjm.mj_forward(model, md)
    fg = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[iq["base_z"]] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    dt = model.opt.timestep
    tau_hold = 0.0
    for k in range(int(1.0 / dt)):
        thm = -md.qpos[iq["hip_m"]] - np.pi / 2
        q2c = -md.qpos[iq["knee_motor"]]
        c1 = 40.0 * (q1_0 - thm) - 1.5 * (-md.qvel[safe.dofadr(model, "hip_m", mjm)])
        c2 = 40.0 * (q2_0 - q2c) - 1.5 * (-md.qvel[safe.dofadr(model, "knee_motor", mjm)])
        md.ctrl[:] = [-c1, -c2]
        tau_hold = c1
        mjm.mj_step(model, md)
    defl = float(md.qpos[iq["hip"]])
    v_end = float(np.abs(md.qvel).max())
    print(f"① 정적: 유지토크 {tau_hold:+.2f}Nm | 스프링 처짐 {np.degrees(defl):+.3f}° "
          f"(τ/k 예측 {np.degrees(tau_hold/KS_HIP):+.3f}°) | 잔여속도 {v_end:.4f}")
    ok1 = abs(defl - tau_hold / KS_HIP) < np.radians(0.3) and v_end < 0.05
    # ② 수동 낙하 2s: 발산/에너지 폭주 없음
    md2 = mjm.MjData(model)
    md2.qpos[iq["base_z"]] = 0.6
    md2.qpos[iq["hip_m"]] = -q1_0 - np.pi / 2
    md2.qpos[iq["knee_motor"]] = -q2_0
    md2.qpos[iq["cpin"]] = q2_0
    md2.qpos[iq["knee"]] = -q2_0
    bad = False
    for k in range(int(2.0 / dt)):
        mjm.mj_step(model, md2)
        if not np.isfinite(md2.qpos).all() or abs(md2.qpos[iq["hip"]]) > 3.0:
            bad = True
            break
    print(f"② 수동 낙하 2s: {'발산!' if bad else 'OK'} (말단 |qvel|max {np.abs(md2.qvel).max():.2f})")
    # ③ 강성 상한 프로브: k=1000에서도 안정?
    m3, _ = build_fs(ks=1000.0, base_xml=base_xml)
    md3 = mjm.MjData(m3)
    md3.qpos[safe.qadr(m3, "base_z", mjm)] = 0.6
    md3.qpos[safe.qadr(m3, "hip_m", mjm)] = -q1_0 - np.pi / 2
    md3.qpos[safe.qadr(m3, "knee_motor", mjm)] = -q2_0
    md3.qpos[safe.qadr(m3, "cpin", mjm)] = q2_0
    md3.qpos[safe.qadr(m3, "knee", mjm)] = -q2_0
    bad3 = False
    for k in range(int(1.0 / dt)):
        mjm.mj_step(m3, md3)
        if not np.isfinite(md3.qpos).all():
            bad3 = True
            break
    print(f"③ k=1000 프로브 1s: {'발산!' if bad3 else 'OK'}")
    print("SANITY", "PASS" if (ok1 and not bad and not bad3) else "FAIL")


if __name__ == "__main__":
    sanity()
