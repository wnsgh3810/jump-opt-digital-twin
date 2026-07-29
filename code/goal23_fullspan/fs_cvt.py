# -*- coding: utf-8 -*-
"""fs_cvt — 0429 CVT(l_i=25.08) 세션의 fs 편입: CVT 모델 캡처+직렬 힌지 패치+골든.

정본 호출 규약 (H13 검증): RU.build_cvt23(x32, ref, sp, 0.02508, d_dq) →
RU.a_full23_log(model_c, True, d.l_i, d, law, o1_429, o2_429, c_cvt, spr=spr_resolve(model_c), k_rise).
골든: 기본(무패치) CVT 재생 dq2 RMSE ≈ 3.31 재현 → 러너 신뢰 후 fs 패치판 측정.
CLI: golden — 기본/fs 패치 CVT 재생 비교 (R19 구창 trial).
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
for _p in ("p25_task0", "p25_deploy", "p23_veins", "p19_jump", "p18_cvt", "p20_rise"):
    sys.path.insert(0, str(HERE.parent / "goal22" / _p))
import p25_a_twin as TW          # noqa: E402
import safe                      # noqa: E402
import mujoco as mjm             # noqa: E402
import fs_model as FM            # noqa: E402

RU = TW.RU; C = TW.C


def build_cvt_pair():
    """CVT XML 캡처 → (기본 model_c, fs 패치 model_cf, 파라미터)."""
    cand = safe.read_json(TW.CAND_PATH)
    nm = dict(zip(cand["names"], np.asarray(cand["x"], float)))
    tw = TW.twin()   # winit 보장
    v = RU.apply_freeze(RU.pad23(np.asarray(cand["x"], float)))
    x32, sp = C.x32_of(v[:20])
    ref = float(v[1]); d_dq = float(v[21])
    orig = mjm.MjModel.from_xml_string
    captured = []

    def cap(xml, *a, **k):
        captured.append(xml)
        return orig(xml, *a, **k)
    mjm.MjModel.from_xml_string = staticmethod(cap)
    try:
        model_c = RU.build_cvt23(x32, ref, sp, 0.02508, d_dq)
    finally:
        mjm.MjModel.from_xml_string = orig
    if not captured:
        raise RuntimeError("CVT XML 캡처 실패")
    xml_c = captured[-1]
    open(HERE / "_cvt_base.xml", "w", encoding="utf-8").write(xml_c)
    # fs 패치 시도 (hip 라인 구조가 flip과 같은지 검사 후)
    model_cf = None
    try:
        model_cf, xml_cf = FM.build_fs(base_xml=xml_c)
        open(HERE / "_cvt_fs.xml", "w", encoding="utf-8").write(xml_cf)
    except Exception as ex:
        print(f"fs 패치 실패 (hip 라인 상이?): {type(ex).__name__} {ex}", flush=True)
    return model_c, model_cf, dict(nm=nm, tw=tw, v=v)


def golden():
    model_c, model_cf, ctx = build_cvt_pair()
    tw = ctx["tw"]; nm = ctx["nm"]
    spr_c = RU.spr_resolve(model_c, tw["spr"])
    o1, o2, cc = nm["o1_429"], nm["o2_429"], nm["C_CVT"]
    for tag, mm in [("기본", model_c)] + ([("fs패치", model_cf)] if model_cf is not None else []):
        spr_m = RU.spr_resolve(mm, tw["spr"])
        rms = []
        for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in TW.R19.TRIALS:
            if ds != "jump_0429":
                continue
            try:
                res = RU.a_full23(mm, True, d.get("l_i", l_i), d, tw["law"], o1, o2,
                                  c_cvt=cc, spr=tw["spr"], k_rise=tw["kr"])
                rms.append(float(res[0]) if res else 9.9)
            except Exception as ex:
                rms.append(9.9)
                print(f"  {sub}: ERR {type(ex).__name__}", flush=True)
        print(f"{tag}: 0429 재생 dq2 RMSE 평균 {np.mean(rms):.3f} (n={len(rms)}, 골든 앵커 ~3.31)", flush=True)


if __name__ == "__main__":
    golden()
