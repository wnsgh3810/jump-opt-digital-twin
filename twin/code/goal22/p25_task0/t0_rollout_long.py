# -*- coding: utf-8 -*-
"""t0_rollout_long — long 캠페인 최종 결정론 롤아웃 (기존 롤아웃 스크립트 재사용 래퍼).

사용: python t0_rollout_long.py nc|wc|wc2|fix:<li>[:<ctrl_ms>]
- T0_TAG = _long(nc/wc) | _long2(wc2) | _lifix<li>_long[_<ms>ms](fix) 설정 후
  t0nc_rollout / t0wc_rollout .main() 호출.
- fix 캠페인: T0_LI_FIXED(그 1점만 평가) + T0_CTRL_DT_MS(이산화 프로브) 병행 설정.
- 학습과 동일한 crouch 주입 (load_env_module이 담당: nc=G["CROUCH"], wc/wc2=CROUCH_FN
  보간, fix=교사 q0 상수) — 이것 없이는 정책이 학습한 시작자세와 달라 h가 왜곡.
- 골든·감사 규약은 각 롤아웃 스크립트가 수행 (run_golden + t0_spec.audit cvt=True).
"""
import os
import sys

import t0_train_long as TL

camp = sys.argv[1] if len(sys.argv) > 1 else "nc"
assert camp in ("nc", "nc05", "wc", "wc2") or camp.startswith("fix:"), \
    "usage: python t0_rollout_long.py nc|nc05|wc|wc2|fix:<li>[:<ctrl_ms>]"
if camp.startswith("fix:"):
    li, cdt, tag = TL.parse_fix(camp)
    os.environ["T0_TAG"] = tag
    os.environ["T0_LI_FIXED"] = repr(li)
    os.environ["T0_CTRL_DT_MS"] = repr(cdt * 1000.0)
elif camp == "nc05":
    os.environ["T0_TAG"] = "_long_05ms"
    os.environ["T0_CTRL_DT_MS"] = "0.5"
else:
    os.environ["T0_TAG"] = "_long2" if camp == "wc2" else "_long"


def main(campaign):
    TL.load_env_module(campaign)     # env import + crouch 패치 (롤아웃 전 필수)
    if campaign in ("nc", "nc05"):
        import t0nc_rollout as RO
    else:
        import t0wc_rollout as RO
    RO.main()


if __name__ == "__main__":
    main(camp)
